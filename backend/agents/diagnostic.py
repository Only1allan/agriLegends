"""
Diagnostic Agent: GraphRAG synthesis — reads from DailySnapshot pipeline model,
sends to Featherless LLM, stores as Alert nodes, and logs decisions on Masumi.
"""
import json
import uuid as uuid_mod
from datetime import datetime, timezone
from services.neo4j import query_one, query
from services.featherless import structured_completion
from services.masumi import (
    log_decision, complete_decision,
    build_canonical_input, build_canonical_output,
    sha256_hash, _build_agent_identifier, _build_purchaser_id,
)
from config import settings


ALERT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["NORMAL", "WARNING", "CRITICAL"]},
        "detected_condition": {"type": "string"},
        "confidence": {"type": "number"},
        "justification": {"type": "string"},
        "explanation": {"type": "string"},
        "recommendation": {"type": "string"},
        "urgency": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "sms_english": {"type": "string", "maxLength": 160},
        "sms_swahili": {"type": "string", "maxLength": 160},
    },
    "required": ["status", "detected_condition", "confidence", "explanation", "recommendation", "urgency", "sms_english", "sms_swahili"],
}


async def extract_season_subgraph(season_id: str) -> dict:
    """Extract the full subgraph for a season from the pipeline model."""
    result = query_one("""
        MATCH (p:Plot)-[:HAS_SEASON]->(s:Season {seasonId: $sid})
        OPTIONAL MATCH (s)-[:PLANTED_WITH]->(v:PotatoVariety)
        OPTIONAL MATCH (s)-[:HAS_GROWTH_STAGE]->(g:GrowthStage)
        OPTIONAL MATCH (s)-[:HAS_SNAPSHOT]->(d:DailySnapshot)
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(c:County)
        WITH p, s, v, g, c,
             collect(DISTINCT d)[0..14] AS recentSnaps
        RETURN p.plotId AS plotId, p.name AS plotName,
               p.county AS county, p.areaHa AS areaHa,
               s.seasonId AS seasonId,
               toString(s.plantingDate) AS plantingDate,
               toString(s.expectedHarvestDate) AS expectedHarvestDate,
               coalesce(v.name, 'Shangi') AS variety,
               coalesce(g.name, 'Unknown') AS stage,
               coalesce(g.description, '') AS stageDesc,
               c.name AS countyName,
               [d IN recentSnaps | {
                   date: d.date, precip: d.daily_precip_mm,
                   temp: d.daily_avg_temp_c, humidity: d.daily_avg_humidity,
                   hasSat: d.has_satellite_data, ndvi: d.mean_ndvi,
                   evi: d.mean_evi, cloud: d.cloud_cover_percentage,
                   r5precip: d.rolling_5d_precip, r5temp: d.rolling_5d_temp_avg
               }] AS snapshots
    """, {"sid": season_id})
    return result if result else {}


async def run_diagnostic(season_id: str) -> dict:
    """Full diagnostic pipeline: extract subgraph → LLM synthesis → store Alert + Masumi."""
    subgraph = await extract_season_subgraph(season_id)
    if not subgraph or not subgraph.get("snapshots"):
        return {"status": "no_data", "message": "No snapshots available for evaluation"}

    latest = subgraph["snapshots"][0] if subgraph["snapshots"] else {}

    conditions = _evaluate_conditions(latest)
    if not conditions:
        return {"status": "normal", "message": "No risk conditions detected"}

    knowledge = []
    variety = subgraph.get("variety", "Shangi")
    for cond in conditions:
        kg = query("""
            MATCH (w:WeatherCondition {name: $cond})<-[:THRIVES_IN]-(pest:Pest)
            OPTIONAL MATCH (pest)-[:DETECTED_BY]->(:Symptom)-[:TREATED_BY]->(i:Intervention)
            RETURN pest.name AS disease,
                   'None' AS resistance,
                   collect(DISTINCT i.action) AS controls,
                   [] AS chemicals
        """, {"cond": cond, "variety": variety})
        knowledge.append({"condition": cond, "diseases": kg})

    context = _build_llm_context(subgraph, latest, knowledge)

    result = await structured_completion(
        system="You are a potato agronomist AI for Kenyan smallholder farmers. "
               "Analyze field conditions and disease risks using scientific knowledge.",
        user=context,
        schema=ALERT_SCHEMA,
    )

    status = result.get("status", "NORMAL")
    if status not in ("WARNING", "CRITICAL"):
        return {"status": "normal", "conditions": conditions, "message": "Conditions present but not severe"}

    alert_id = str(uuid_mod.uuid4())
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    sms_en = str(result.get("sms_english", ""))[:160]
    sms_sw = str(result.get("sms_swahili", ""))[:160]

    query("""
        MATCH (s:Season {seasonId: $sid})
        CREATE (a:Alert {
            alertId: $aid,
            detected_condition: $condition,
            confidence: $conf,
            explanation: $expl,
            recommendation: $rec,
            urgency: $urgency,
            status: 'ACTIVE',
            sms_english: $sms_en,
            sms_swahili: $sms_sw,
            createdAt: $now,
            retryCount: 0
        })
        CREATE (s)-[:GENERATED]->(a)
    """, {
        "sid": season_id, "aid": alert_id,
        "condition": result.get("detected_condition", conditions[0]) if conditions else "",
        "conf": result.get("confidence", 0),
        "expl": result.get("explanation", ""),
        "rec": result.get("recommendation", ""),
        "urgency": result.get("urgency", "LOW"),
        "sms_en": sms_en, "sms_sw": sms_sw, "now": now_ts,
    })

    if latest.get("snapid"):
        query("""
            MATCH (a:Alert {alertId: $aid})
            MATCH (d:DailySnapshot {snapshotId: $snapid})
            CREATE (a)-[:TRIGGERED_BY]->(d)
        """, {"aid": alert_id, "snapid": latest.get("snapid")})

    masumi_status = "NOT_LOGGED"
    tx_hash = ""
    try:
        masumi_payload = {
            "seasonId": season_id,
            "alertId": alert_id,
            "condition": result.get("detected_condition", ""),
            "urgency": result.get("urgency", ""),
            "explanation": result.get("explanation", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        tx_hash = await log_decision(masumi_payload)
        if tx_hash:
            masumi_status = "CREATED"
            query("""
                MATCH (a:Alert {alertId: $aid})
                SET a.masumiTxHash = $hash
            """, {"aid": alert_id, "hash": tx_hash})
            try:
                completion = await complete_decision(tx_hash, masumi_payload)
                if completion.get("verified"):
                    masumi_status = "VERIFIED_ON_CHAIN"
                    query("""
                        MATCH (a:Alert {alertId: $aid})
                        SET a.masumiStatus = 'VERIFIED_ON_CHAIN'
                    """, {"aid": alert_id})
            except Exception:
                masumi_status = "COMPLETE_PENDING"
    except Exception as e:
        masumi_status = f"CREATE_FAILED: {str(e)[:100]}"

    return {
        "alertId": alert_id, "status": status,
        "detected_condition": result.get("detected_condition", ""),
        "confidence": result.get("confidence", 0),
        "explanation": result.get("explanation", ""),
        "recommendation": result.get("recommendation", ""),
        "urgency": result.get("urgency", ""),
        "masumiTxHash": tx_hash, "masumiStatus": masumi_status,
    }


def _evaluate_conditions(d: dict) -> list[str]:
    triggered = []
    if not d:
        return triggered
    precip_5d = float(d.get("r5precip", 0) or 0)
    temp = float(d.get("temp", 0) or 0)
    has_sat = d.get("hasSat", False)
    ndvi = float(d.get("ndvi", 0) or 0) if has_sat else 0

    if precip_5d == 0.0 and temp > 26.0:
        triggered.append("Hot & Dry")
    if precip_5d > 15.0 and 18.0 <= temp <= 24.0:
        triggered.append("Warm & Humid")
    if temp < 10.0:
        triggered.append("Cold Stress")
    if precip_5d > 40.0:
        triggered.append("Waterlogged")
    if has_sat and ndvi < 0.3:
        triggered.append("Low NDVI")
    return triggered


def _build_llm_context(subgraph: dict, latest: dict, knowledge: list) -> str:
    lines = [
        f"Plot: {subgraph.get('plotName', 'Unknown')}",
        f"County: {subgraph.get('countyName', '')}",
        f"Variety: {subgraph.get('variety', 'Unknown')}",
        f"Growth Stage: {subgraph.get('stage', 'Unknown')} — {subgraph.get('stageDesc', '')}",
        f"Planted: {subgraph.get('plantingDate', '')}",
        "",
        "Latest Telemetry:",
        f"  Date: {latest.get('date', 'N/A')}",
        f"  Temperature: {latest.get('temp', 'N/A')} C",
        f"  Precipitation: {latest.get('precip', 'N/A')} mm",
        f"  Humidity: {latest.get('humidity', 'N/A')}%",
        f"  5-day Rolling Precip: {latest.get('r5precip', 'N/A')} mm",
    ]
    if latest.get("hasSat"):
        lines.extend([
            f"  NDVI: {latest.get('ndvi', 'N/A')}",
            f"  EVI: {latest.get('evi', 'N/A')}",
            f"  Cloud Cover: {latest.get('cloud', 'N/A')}%",
        ])

    lines.append("")
    lines.append("Knowledge Graph Disease Findings:")
    for item in knowledge:
        lines.append(f"  Condition: {item['condition']}")
        for dis in item.get("diseases", []):
            lines.append(f"    Disease: {dis.get('disease', 'Unknown')} (Resistance: {dis.get('resistance', 'None')})")
            lines.append(f"    Controls: {', '.join([c for c in (dis.get('controls', []) or []) if c])}")
            lines.append(f"    Chemicals: {', '.join([c for c in (dis.get('chemicals', []) or []) if c])}")
    return "\n".join(lines)
