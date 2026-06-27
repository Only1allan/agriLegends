"""
Chat Agent — Dynamic GraphRAG conversational interface for FarmWise.

Phase 1: LLM classifies intent + generates Cypher from Neo4j schema
Phase 2: Execute generated Cypher (sanitized, read-only)
Phase 3: Full subgraph extraction for rich context
Phase 4: Synthesize answer via Featherless with real data only
Phase 5: Multi-turn conversation memory (last 10 messages per farmer)
"""
import json
import re
from typing import Any

from services.featherless import chat, safe_content
from services.neo4j import query, query_one
from agents.diagnostic import extract_season_subgraph
from config import settings

NEO4J_SCHEMA = """
Node labels and properties:
- Plot: plotId, name, latitude, longitude, areaHa, variety, soilType, county, location, boundaryPolygon, stakeholderToken
- Season: seasonId, plantingDate, expectedHarvestDate, actualHarvestDate, status (ACTIVE/CLOSED), varietyName
- DailySnapshot: snapshotId, date, daily_precip_mm, daily_avg_temp_c, daily_avg_humidity, rolling_5d_precip, rolling_10d_precip, rolling_14d_precip, rolling_5d_temp_avg, rolling_5d_humidity_avg, has_satellite_data, cloud_cover_percentage, mean_ndvi, mean_evi, mean_ndre, mean_ndwi, mean_savi, mean_msi
- Alert: alertId, detected_condition, confidence, explanation, recommendation, urgency, status, sms_english, sms_swahili, createdAt, dispatchedAt, retryCount, masumiTxHash
- FarmerObservation: observationId, date, notes, imageUrl, interpretation, interpretationStatus
- Intervention: interventionId, actionTaken, date
- Expense: expenseId, category, description, amount, date
- YieldForecast: forecastId, date, predictedYield, confidenceLow, confidenceHigh, basis
- Sale: saleId, quantity_kg, unit_price, total_amount, buyer, sale_date
- GrowthStage: name, description, dayStart, dayEnd, startDaysAfterPlanting, endDaysAfterPlanting
- PotatoVariety: name, maturityDays
- Pest: name, scientificName
- Symptom: sensorType, threshold
- WeatherCondition: name, tempMin, tempMax, humidityMin
- Disease: name
- Agrochemical: name
- County: name, centroidLat, centroidLon
- Farmer: farmerId, phone, name, preferredChannel, preferredLanguage, registrationDate

Relationships:
- (Plot)-[:HAS_SEASON]->(Season)
- (Plot)-[:LOCATED_IN]->(County)
- (Plot)-[:OWNS]<-[:OWNS]-(Farmer)   // Farmer-[:OWNS]->Plot
- (Season)-[:HAS_SNAPSHOT]->(DailySnapshot)
- (Season)-[:HAS_OBSERVATION]->(FarmerObservation)
- (Season)-[:GENERATED]->(Alert)
- (Season)-[:PLANTED_WITH]->(PotatoVariety)
- (Season)-[:HAS_GROWTH_STAGE]->(GrowthStage)
- (Season)-[:HAS_EXPENSE]->(Expense)
- (Season)-[:HAS_FORECAST]->(YieldForecast)
- (Season)-[:HAS_SALE]->(Sale)
- (Alert)-[:TRIGGERED_BY]->(DailySnapshot)
- (Alert)-[:TRIGGERED_BY]->(FarmerObservation)
- (Farmer)-[:APPLIED]->(Intervention)
- (Intervention)-[:ADDRESSES]->(Alert)
- (Intervention)-[:HAS_EXPENSE]->(Expense)
- (PotatoVariety)-[:HAS_GROWTH_STAGE]->(GrowthStage)
- (GrowthStage)-[:HAS_RISK]->(Pest)
- (Pest)-[:DETECTED_BY]->(Symptom)
- (Symptom)-[:TREATED_BY]->(Intervention)
- (Pest)-[:THRIVES_IN]->(WeatherCondition)
- (WeatherCondition)-[:FAVORS]->(Disease)
- (PotatoVariety)-[:RESISTANT_TO]->(Disease)
- (Agrochemical)-[:MITIGATES]->(Disease)
"""

INTENT_SYSTEM_PROMPT = f"""You are a Cypher query generator for a Neo4j potato farming database. Given the schema below and a farmer's question, output ONLY a valid JSON object with two keys:
- "intent": short label for what the farmer wants (growth_stage, ndvi, weather, pest, yield, stress, recommendation, general, greeting, alerts, finances, or unknown)
- "cypher": a valid Neo4j Cypher READ-QUERY (MATCH...RETURN only, no CREATE/DELETE/SET/MERGE/DETACH) that answers the question. Use $plot_id as parameter. Limit results to 10.

Schema:
{NEO4J_SCHEMA}

Rules:
- ONLY output JSON, no markdown, no explanation
- Only MATCH/RETURN queries — no mutations
- If the question is a greeting or chit-chat, set cypher to null
- If you cannot determine a query, set cypher to null and intent to "unknown"
- For pest questions, traverse: Plot->Season->PotatoVariety->GrowthStage->Pest->Symptom->Intervention
- For weather, query DailySnapshot nodes via Season
- For NDVI/satellite, query DailySnapshot nodes
- For alerts, query Alert nodes via Season
- For general farm status, query the Season with latest DailySnapshot
- For finances, query Expense and Sale nodes via Season

Example output:
{{"intent": "ndvi", "cypher": "MATCH (p:Plot {{plotId: $plot_id}})-[:HAS_SEASON]->(s:Season)-[:HAS_SNAPSHOT]->(d:DailySnapshot) WHERE d.date >= date() - duration({{days: 14}}) AND d.has_satellite_data = true RETURN toString(d.date) AS date, d.mean_ndvi AS ndvi ORDER BY d.date DESC LIMIT 10"}}
"""

ANSWER_SYSTEM_PROMPT = """You are FarmWise AI, a potato farming assistant for Kenyan farmers. You have real farm data from Neo4j.

CRITICAL RULES — follow these exactly:
1. The DIRECT QUERY RESULTS section contains the data the farmer SPECIFICALLY asked for. Answer from THIS section first.
2. If DIRECT QUERY RESULTS says "QUERY RETURNED NO RESULTS", tell the farmer honestly: "I don't have [requested data] yet. Here's what IS available: [summary of supplementary context]."
3. NEVER answer with recommendation data when the farmer asked for weather, NDVI, soil, or growth stage data. 
4. NEVER fabricate data, measurements, or recommendations not present in the context.
5. If the farmer asked about satellite/NDVI data and there is none, say: "No satellite NDVI data is available yet for today. Satellite observations typically take 3-5 days after registration to appear."
6. The FARM SUBGRAPH section is SUPPLEMENTARY — use it to enrich your answer, not to replace the missing requested data.
7. Be conversational and friendly. Support both English and Swahili — reply in the same language.
8. Keep responses to 2-4 sentences unless the farmer asks for detail.

Respond with a JSON object:
{"answer": "your response to the farmer", "confidence": "high|medium|low"}

Confidence levels:
- "high": the specific data the farmer asked for is present in DIRECT QUERY RESULTS
- "medium": partial data available, some gaps in what was requested
- "low": the data the farmer asked for was NOT found (QUERY RETURNED NO RESULTS)
"""

CONVERSATION_BUFFER: dict[str, list[dict[str, str]]] = {}
MAX_HISTORY = 10
CONTEXT_EXCHANGES = 3


def _get_plot_context(farmer_id: str) -> dict:
    """Get farmer's plot and active season for context."""
    result = query_one("""
        MATCH (f:Farmer {farmerId: $fid})-[:OWNS]->(p:Plot)
        OPTIONAL MATCH (p)-[:HAS_SEASON]->(s:Season {status: "ACTIVE"})
        RETURN p.plotId AS plotId, p.name AS plotName, s.seasonId AS seasonId
        LIMIT 1
    """, {"fid": farmer_id})
    return result if result else {}


def _sanitize_cypher(cypher: str) -> str | None:
    """Strip markdown fences, validate read-only, return cleaned Cypher or None."""
    if not cypher or not cypher.strip():
        return None
    cleaned = cypher.strip()
    cleaned = re.sub(r"^```(?:cypher)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?\s*```$", "", cleaned)
    cleaned = cleaned.strip()
    if not cleaned:
        return None
    upper = cleaned.upper()
    forbidden = ["CREATE ", "DELETE ", "SET ", "MERGE ", "DETACH ", "REMOVE ", "DROP "]
    for kw in forbidden:
        if kw in upper:
            return None
    if not upper.startswith("MATCH"):
        return None
    if "RETURN" not in upper:
        return None
    return cleaned


def _format_history(history: list[dict[str, str]]) -> str:
    if not history:
        return ""
    lines = []
    for msg in history[-CONTEXT_EXCHANGES * 2:]:
        role = "Farmer" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


async def _classify_intent(message: str, farmer_id: str) -> dict:
    """Phase 1: Have Featherless classify intent and generate Cypher."""
    try:
        result = await chat(
            model=settings.FEATHERLESS_CHAT_MODEL,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
        )
        content = safe_content(result, "{}")
        content = content.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(content)
    except (json.JSONDecodeError, Exception):
        return {"intent": "unknown", "cypher": None}


async def _synthesize_answer(
    question: str,
    intent: str,
    subgraph: dict,
    pest_results: list[dict],
    cypher_results: list[dict] | None,
    history: list[dict[str, str]],
) -> dict:
    """Phase 4: Send full context to Featherless for answer synthesis."""
    context_parts = []
    has_requested_data = False

    if cypher_results is not None:
        has_requested_data = bool(cypher_results)
        context_parts.append(f"\n=== DIRECT QUERY RESULTS (intent: {intent}) ===")
        if cypher_results:
            context_parts.append(json.dumps(cypher_results[:10], default=str))
        else:
            context_parts.append(f"QUERY RETURNED NO RESULTS for intent '{intent}'. The farmer specifically asked for this data but it does not exist in the database yet.")

    if subgraph:
        context_parts.append(f"\n=== FARM SUBGRAPH (supplementary context) ===")
        plot_summary = {
            "name": subgraph.get("plotName"),
            "county": subgraph.get("countyName"),
            "variety": subgraph.get("variety"),
            "area": subgraph.get("areaHa"),
            "stage": subgraph.get("stage"),
            "planted": subgraph.get("plantingDate"),
            "expectedHarvest": subgraph.get("expectedHarvestDate"),
        }
        context_parts.append(f"Plot Summary: {json.dumps(plot_summary, default=str)}")
        snaps = subgraph.get("snapshots", [])
        if snaps:
            latest = snaps[0]
            context_parts.append(f"Latest telemetry (date: {latest.get('date')}): temp={latest.get('temp')}C, precip={latest.get('precip')}mm, humidity={latest.get('humidity')}%")
            if latest.get("hasSat"):
                context_parts.append(f"Satellite: NDVI={latest.get('ndvi')}, EVI={latest.get('evi')}, cloud={latest.get('cloud')}%")
            context_parts.append(f"Total snapshots available: {len(snaps)}")

    if pest_results:
        context_parts.append(f"\n=== PEST DIAGNOSIS ===")
        context_parts.append(json.dumps(pest_results[:5], default=str))

    if not subgraph and cypher_results is None:
        context_parts.append("=== NO DATA AVAILABLE ===")
        context_parts.append("This plot has no observations, recommendations, or pest data yet.")

    full_context = "\n".join(context_parts)

    history_text = _format_history(history)

    messages = [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
    ]

    if history_text:
        messages.append({"role": "system", "content": f"Previous conversation:\n{history_text}"})

    messages.append({
        "role": "user",
        "content": f"CONTEXT DATA:\n{full_context}\n\nFARMER'S QUESTION: {question}",
    })

    try:
        result = await chat(
            model=settings.FEATHERLESS_CHAT_MODEL,
            messages=messages,
        )
        content = safe_content(result, "{}")
        content = content.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(content)
        return {
            "answer": parsed.get("answer", content),
            "confidence": parsed.get("confidence", "medium"),
        }
    except (json.JSONDecodeError, Exception):
        return {
            "answer": "I found data for your farm but couldn't analyze it. Please try asking again.",
            "confidence": "low",
        }


def _check_day_one(subgraph: dict) -> bool:
    """Determine if the farmer is on day 1 with sparse data."""
    if not subgraph:
        return True
    snaps = subgraph.get("snapshots", [])
    return len(snaps) == 0


async def chat_query(farmer_id: str, message: str, context_hint: str = "") -> dict:
    ctx = _get_plot_context(farmer_id)
    plot_id = ctx.get("plotId")
    season_id = ctx.get("seasonId")

    buffer = CONVERSATION_BUFFER.setdefault(farmer_id, [])
    buffer.append({"role": "user", "content": message})
    if len(buffer) > MAX_HISTORY:
        buffer = buffer[-MAX_HISTORY:]
        CONVERSATION_BUFFER[farmer_id] = buffer

    if not plot_id:
        response = {
            "answer": "I don't see a registered plot for your account. Please register your farm first.",
            "cypher": None,
            "results": None,
            "confidence": "low",
        }
        buffer.append({"role": "assistant", "content": response["answer"]})
        return response

    cypher_results: list[dict] | None = None
    generated_cypher: str | None = None

    # Phase 1: Classify intent + generate Cypher
    intent_data = await _classify_intent(message, farmer_id)
    detected_intent = intent_data.get("intent", "unknown")
    raw_cypher = intent_data.get("cypher")

    # Phase 2: Execute generated Cypher if valid
    if raw_cypher:
        sanitized = _sanitize_cypher(raw_cypher)
        if sanitized:
            generated_cypher = sanitized
            try:
                cypher_results = query(sanitized, {"plot_id": plot_id})
            except Exception:
                cypher_results = []
    else:
        cypher_results = None

    # Phase 3: Extract pipeline model subgraph
    subgraph = await extract_season_subgraph(season_id) if season_id else {}

    # Phase 4: Synthesize answer
    if context_hint:
        message = f"{context_hint}\n{message}"
    synthesis = await _synthesize_answer(message, detected_intent, subgraph, [], cypher_results, buffer)

    is_day_one = _check_day_one(subgraph)
    if is_day_one and detected_intent == "general":
        plot_name = ctx.get("plotName", "your farm")
        synthesis["answer"] = (
            f"Welcome to FarmWise! I'm monitoring your {plot_name} field. "
            f"Satellite and weather data will appear here once our systems process your location. "
            f"This usually takes 1-2 days for satellite imagery and a few hours for weather data. "
            f"In the meantime, you can ask me about crop diseases, potato varieties, or farming practices."
        )

    response = {
        "answer": synthesis["answer"],
        "cypher": generated_cypher,
        "results": cypher_results,
        "confidence": synthesis.get("confidence", "medium"),
    }
    buffer.append({"role": "assistant", "content": response["answer"]})
    return response

