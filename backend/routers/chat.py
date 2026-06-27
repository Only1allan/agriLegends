"""
Chat Router: Simple, resilient farm chat that queries real data, passes to LLM,
and falls back to structured data response if LLM is unavailable.
"""
import json
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from services.neo4j import query, query_one
from services.featherless import chat, safe_content
from config import settings

logger = logging.getLogger("farmwise.chat_router")
router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    farmerId: str
    message: str
    history: list[ChatMessage] | None = None
    seasonId: str | None = None


class ChatResponse(BaseModel):
    answer: str
    cypher: str | None = None
    results: list | None = None
    confidence: str = "medium"


@router.post("/query")
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    # 1. Get farmer's latest farm data
    context = _build_context(req.farmerId, req.seasonId)

    # 2. Try LLM synthesis
    try:
        system = (
            "You are FarmWise AI, a potato farming assistant for Kenyan smallholders. "
            "You have access to real farm data including satellite NDVI, weather, soil, alerts, "
            "and pest risks. Answer the farmer's question using ONLY the provided context data. "
            "Be conversational and helpful. Support English and Swahili. "
            "If data is not available, tell the farmer honestly. "
            "Keep responses to 2-5 sentences."
        )

        messages = [{"role": "system", "content": system}]
        if req.history:
            recent = req.history[-6:]
            for m in recent:
                messages.append({"role": m.role, "content": m.content})
        messages.append({
            "role": "user",
            "content": f"FARM DATA CONTEXT:\n{context}\n\nFARMER'S QUESTION: {req.message}",
        })

        result = await chat(
            model=settings.FEATHERLESS_CHAT_MODEL,
            messages=messages,
            temperature=0.7,
        )
        answer = safe_content(result, "")

        if answer and len(answer.strip()) > 10:
            return ChatResponse(answer=answer.strip(), confidence="high")
    except Exception as e:
        logger.warning("Featherless chat failed: %s", e)

    # 3. Fallback: return structured data summary
    fallback = _build_fallback(context)
    return ChatResponse(answer=fallback, confidence="low")


def _build_context(farmer_id: str, season_id: str | None) -> str:
    parts = []

    # Get farmer's first plot
    plot = query_one("""
        MATCH (f:Farmer {farmerId: $fid})-[:OWNS]->(p:Plot)
        RETURN p.plotId AS plotId, p.name AS name, p.county AS county, p.areaHa AS areaHa
        LIMIT 1
    """, {"fid": farmer_id})

    if not plot:
        return "No registered farm plot found."

    parts.append(f"Plot: {plot['name']} in {plot['county']} ({plot['areaHa']} ha)")

    # Get active season
    sid = season_id
    if not sid:
        season = query_one("""
            MATCH (p:Plot {plotId: $pid})-[:HAS_SEASON]->(s:Season {status: "ACTIVE"})
            RETURN s.seasonId AS seasonId, s.varietyName AS variety,
                   toString(s.plantingDate) AS planted, toString(s.expectedHarvestDate) AS harvest
        """, {"pid": plot["plotId"]})
    else:
        season = query_one("""
            MATCH (s:Season {seasonId: $sid})
            RETURN s.seasonId AS seasonId, s.varietyName AS variety,
                   toString(s.plantingDate) AS planted, toString(s.expectedHarvestDate) AS harvest
        """, {"sid": sid})
    if season:
        sid = season["seasonId"]
        parts.append(f"Season: {season['variety']} planted {season['planted']}, harvest {season['harvest']}")

    if not sid:
        return "\n".join(parts) + "\n(No active season. Start a season to see crop data.)"

    # Latest snapshot
    latest = query_one("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_SNAPSHOT]->(d:DailySnapshot)
        RETURN d.date AS date, d.daily_avg_temp_c AS temp,
               d.daily_precip_mm AS precip, d.daily_avg_humidity AS humidity,
               d.rolling_5d_precip AS r5precip, d.has_satellite_data AS hasSat,
               d.mean_ndvi AS ndvi, d.mean_evi AS evi, d.cloud_cover_percentage AS cloud
        ORDER BY d.date DESC LIMIT 1
    """, {"sid": sid})
    if latest:
        parts.append(f"Latest weather ({latest['date']}): {latest['temp']}C, {latest['precip']}mm rain, {latest['humidity']}% humidity, 5-day rolling precip: {latest['r5precip']}mm")
        if latest.get("hasSat"):
            parts.append(f"Latest satellite: NDVI={latest['ndvi']:.4f}, EVI={latest['evi']}, cloud cover={latest['cloud']}%")
        else:
            parts.append("No satellite data available for latest day (high cloud cover)")

    # Snapshot summary
    all_snaps = query("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_SNAPSHOT]->(d:DailySnapshot)
        RETURN count(d) AS total, collect(d.date)[0..3] AS recent
    """, {"sid": sid})
    if all_snaps:
        parts.append(f"Total monitoring days: {all_snaps[0]['total']}")

    # Active alerts
    alerts = query("""
        MATCH (s:Season {seasonId: $sid})-[:GENERATED]->(a:Alert)
        WHERE a.status IN ['ACTIVE', 'SENT']
        RETURN a.detected_condition AS condition, a.urgency AS urgency,
               a.recommendation AS recommendation
        LIMIT 3
    """, {"sid": sid})
    if alerts:
        parts.append(f"Active alerts ({len(alerts)}):")
        for a in alerts:
            parts.append(f"  - {a['condition']} ({a['urgency']}): {a['recommendation']}")

    # Soil data
    soil = query_one("""
        MATCH (p:Plot {plotId: $pid})
        RETURN p.soilBaseline_N AS n, p.soilBaseline_pH AS ph, p.soilBaseline_C AS carbon
    """, {"pid": plot["plotId"]})
    if soil and soil.get("n"):
        parts.append(f"Soil: pH={soil['ph']}, Nitrogen={soil['n']} g/kg, Carbon={soil['carbon']} g/kg (source: iSDAsoil)")

    # Expenses
    expenses = query("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_EXPENSE]->(e:Expense)
        RETURN sum(e.amount) AS total
    """, {"sid": sid})
    if expenses and expenses[0]["total"]:
        parts.append(f"Total expenses: KES {expenses[0]['total']}")

    return "\n".join(parts)


def _build_fallback(context: str) -> str:
    """Generate a structured response from raw data."""
    lines = ["Here's what I know about your farm:\n"]

    for line in context.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "Latest weather" in line:
            lines.append(f"🌤️ {line}")
        elif "Latest satellite" in line or "No satellite" in line:
            lines.append(f"🛰️ {line}")
        elif "Active alert" in line or "  -" in line:
            lines.append(f"⚠️ {line}")
        elif "Soil:" in line:
            lines.append(f"🧪 {line}")
        elif "Total expenses" in line:
            lines.append(f"💰 {line}")
        elif "Total monitoring" in line:
            lines.append(f"📊 {line}")
        elif "Plot:" in line:
            lines.append(f"🏡 {line}")
        elif "Season:" in line:
            lines.append(f"🌱 {line}")

    lines.append("\n(I generated this from your live farm data. The AI assistant is temporarily unavailable for deeper analysis.)")
    return "\n".join(lines)
