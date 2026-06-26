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
from services.neo4j import query
from agents.diagnostic import extract_subgraph, run_pest_diagnosis
from config import settings

NEO4J_SCHEMA = """
Node labels and properties:
- Plot: plotId, name, latitude, longitude, sizeAcres, variety, plantingDate, seasonDay, soilBaseline_N, soilBaseline_pH, soilBaseline_C, accumulatedGDD, forecastedYieldKg, agromonitoringPolygonId
- GrowthStage: name, dayStart, dayEnd
- Observation_Satellite: ndvi, evi, cloudCover
- Observation_Weather: tempMax, tempMin, precipitation, humidity
- Pest: name, scientificName
- Symptom: sensorType, threshold
- Intervention: action, urgencyHours, method
- StressEvent: type, detectedAt
- DailyRecommendation: action, cause, urgencyHours, narrative, date
- MasumiTxHash: hash, status
- Farmer: farmerId, phone, name, preferredChannel, preferredLanguage, registrationDate
- TimeDay: date
- NewsAlert: headline, url, publishedAt, region
- County: name, centroidLat, centroidLon

Relationships:
- (Plot)-[:AT_STAGE]->(GrowthStage)
- (Plot)-[:HAS_OBSERVATION]->(Observation_Satellite)
- (Plot)-[:HAS_OBSERVATION]->(Observation_Weather)
- (Plot)-[:EXPERIENCED_STRESS]->(StressEvent)
- (Plot)-[:HAS_RECOMMENDATION]->(DailyRecommendation)
- (Plot)-[:LOCATED_IN]->(County)
- (Plot)-[:OWNED_BY]->(Farmer)   // Farmer-[:OWNS]->Plot
- (GrowthStage)-[:HAS_RISK]->(Pest)
- (Pest)-[:DETECTED_BY]->(Symptom)
- (Symptom)-[:TREATED_BY]->(Intervention)
- (Pest)-[:THRIVES_IN]->(WeatherCondition)
- (Observation_Satellite)-[:OCCURRED_ON]->(TimeDay)
- (Observation_Weather)-[:OCCURRED_ON]->(TimeDay)
- (DailyRecommendation)-[:HAS_TX]->(MasumiTxHash)
- (County)<-[:RELEVANT_TO]-(NewsAlert)
"""

INTENT_SYSTEM_PROMPT = f"""You are a Cypher query generator for a Neo4j potato farming database. Given the schema below and a farmer's question, output ONLY a valid JSON object with two keys:
- "intent": short label for what the farmer wants (growth_stage, ndvi, weather, pest, yield, stress, recommendation, general, greeting, or unknown)
- "cypher": a valid Neo4j Cypher READ-QUERY (MATCH...RETURN only, no CREATE/DELETE/SET/MERGE/DETACH) that answers the question. Use $plot_id as parameter. Limit results to 10.

Schema:
{NEO4J_SCHEMA}

Rules:
- ONLY output JSON, no markdown, no explanation
- Only MATCH/RETURN queries — no mutations
- If the question is a greeting or chit-chat, set cypher to null
- If you cannot determine a query, set cypher to null and intent to "unknown"
- For pest questions, traverse: Plot->GrowthStage->Pest->Symptom->Intervention
- For weather, join via OCCURRED_ON to TimeDay
- For NDVI, query Observation_Satellite nodes
- For general farm status, query the Plot itself

Example output:
{{"intent": "ndvi", "cypher": "MATCH (p:Plot {{plotId: $plot_id}})-[:HAS_OBSERVATION]->(obs:Observation_Satellite)-[:OCCURRED_ON]->(d:TimeDay) WHERE d.date >= date() - duration('P14D') RETURN toString(d.date) AS date, obs.ndvi AS ndvi ORDER BY d.date"}}
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


def _get_plot_id(farmer_id: str) -> str | None:
    results = query(
        "MATCH (f:Farmer {farmerId: $fid})-[:OWNS]->(p:Plot) RETURN p.plotId AS pid LIMIT 1",
        {"fid": farmer_id},
    )
    return results[0]["pid"] if results else None


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
        if subgraph.get("plot"):
            p = subgraph["plot"]
            plot_summary = {
                "name": p.get("name"), "variety": p.get("variety"),
                "seasonDay": p.get("seasonDay"), "stage": subgraph.get("stage"),
                "soil_pH": p.get("soilBaseline_pH"), "soil_N": p.get("soilBaseline_N"),
            }
            context_parts.append(f"Plot Summary: {json.dumps(plot_summary, default=str)}")
        if subgraph.get("todayObservations"):
            context_parts.append(f"Recent Observations (count: {len(subgraph['todayObservations'])}): {json.dumps(subgraph['todayObservations'][:3], default=str)}")
        if subgraph.get("stageRisks"):
            context_parts.append(f"Stage Pest Risks: {subgraph['stageRisks']}")

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
    obs = subgraph.get("todayObservations", [])
    return len(obs) == 0


async def chat_query(farmer_id: str, message: str) -> dict:
    plot_id = _get_plot_id(farmer_id)

    buffer = CONVERSATION_BUFFER.setdefault(farmer_id, [])
    buffer.append({"role": "user", "content": message})
    if len(buffer) > MAX_HISTORY:
        buffer = buffer[-MAX_HISTORY:]
        CONVERSATION_BUFFER[farmer_id] = buffer

    if not plot_id:
        response = {
            "answer": "I don't see a registered plot for your account. Please register your farm first from the home screen.",
            "cypher": None,
            "results": None,
            "confidence": "low",
        }
        buffer.append({"role": "assistant", "content": response["answer"]})
        return response

    cypher_results: list[dict] | None = None
    cypher_was_generated = False
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
            cypher_was_generated = True
            try:
                cypher_results = query(sanitized, {"plot_id": plot_id})
            except Exception:
                cypher_results = []
    else:
        cypher_results = None

    # Phase 3: Extract full subgraph context
    subgraph = await extract_subgraph(plot_id)

    # Also run pest diagnosis
    pest_results: list[dict] = []
    try:
        pest_results = await run_pest_diagnosis(plot_id)
    except Exception:
        pest_results = []

    # Phase 4: Synthesize answer
    synthesis = await _synthesize_answer(
        question=message,
        intent=detected_intent,
        subgraph=subgraph,
        pest_results=pest_results,
        cypher_results=cypher_results,
        history=buffer[:-1] if len(buffer) > 1 else [],
    )

    answer = synthesis["answer"]
    confidence = synthesis["confidence"]

    # Day 1 handling — force low confidence when no observations exist
    if _check_day_one(subgraph):
        day1_data = []
        if subgraph.get("plot"):
            p = subgraph["plot"]
            if p.get("soilBaseline_pH"):
                day1_data.append(f"soil pH {p['soilBaseline_pH']}")
            if p.get("soilBaseline_N"):
                day1_data.append(f"nitrogen {p['soilBaseline_N']} g/kg")
            if p.get("variety"):
                day1_data.append(f"variety: {p['variety']}")
            if p.get("seasonDay"):
                day1_data.append(f"day {p['seasonDay']} of season")
        data_str = ", ".join(day1_data) if day1_data else "basic registration info"
        answer = (
            f"🌱 You're on day 1. We've just started monitoring your farm. "
            f"Here's what we've collected so far: [{data_str}]. "
            f"Satellite NDVI data takes 3-5 days to arrive. Check back soon! Once we have "
            f"enough data, I can give you detailed recommendations about pests, growth, and yield."
        )
        confidence = "low"

    # Combine results for response
    all_results: list[dict] = []
    if cypher_results:
        all_results.extend(cypher_results)
    if subgraph:
        all_results.append({"subgraph": subgraph})

    buffer.append({"role": "assistant", "content": answer})
    if len(buffer) > MAX_HISTORY:
        buffer = buffer[-MAX_HISTORY:]
        CONVERSATION_BUFFER[farmer_id] = buffer

    return {
        "answer": answer,
        "cypher": generated_cypher,
        "results": all_results if all_results else None,
        "confidence": confidence,
    }
