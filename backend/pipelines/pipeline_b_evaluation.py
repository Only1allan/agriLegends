import uuid
import logging
from datetime import datetime, timedelta, timezone
from services.neo4j import query
from services.featherless import structured_completion

logger = logging.getLogger("farmwise.pipeline_b")

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


async def run_pipeline_b(season_id: str = None):
    logger.info("Pipeline B: Risk evaluation starting (season_id=%s)", season_id or "all")

    today = datetime.now(timezone.utc).date().isoformat()

    season_clause = ""
    params = {"today": today}
    if season_id:
        season_clause = "AND s.seasonId = $season_id"
        params["season_id"] = season_id

    rows = query(f"""
        MATCH (p:Plot)-[:HAS_SEASON]->(s:Season {{status: "ACTIVE"}})-[:HAS_SNAPSHOT]->(d:DailySnapshot)
        WHERE d.date = $today {season_clause}
        MATCH (s)-[:PLANTED_WITH]->(v:PotatoVariety)
        OPTIONAL MATCH (s)-[:HAS_GROWTH_STAGE]->(g:GrowthStage)
        RETURN p.plotId AS plotId, p.name AS plotName, s.seasonId AS seasonId,
               d, v.name AS variety, coalesce(g.name, 'Unknown') AS stage,
               coalesce(g.description, '') AS stageDesc
    """, params)

    logger.info("Pipeline B: %d seasons with today's snapshot", len(rows))

    for row in rows:
        sid = row["seasonId"]
        d = row.get("d", {}) or row
        try:
            conditions = _evaluate_conditions(d)
            if not conditions:
                logger.info("Pipeline B: No conditions triggered for season %s", sid)
                continue

            untriggered = []
            three_days_ago_ms = int((datetime.now(timezone.utc) - timedelta(days=3)).timestamp() * 1000)
            for cond in conditions:
                existing = query("""
                    MATCH (s:Season {seasonId: $sid})-[:GENERATED]->(a:Alert)
                    WHERE a.detected_condition = $cond
                      AND a.status IN ['ACTIVE', 'SENT']
                      AND coalesce(a.createdAt, 0) > $since
                    RETURN count(a) AS c
                """, {"sid": sid, "cond": cond, "since": three_days_ago_ms})
                if existing and existing[0]["c"] == 0:
                    untriggered.append(cond)

            if not untriggered:
                logger.info("Pipeline B: All conditions already alerted for %s", sid)
                continue

            knowledge = []
            for cond in untriggered:
                kg = query("""
                    MATCH (w:WeatherCondition {name: $cond})<-[:THRIVES_IN]-(pest:Pest)
                    OPTIONAL MATCH (pest)-[:DETECTED_BY]->(:Symptom)-[:TREATED_BY]->(i:Intervention)
                    RETURN pest.name AS disease,
                           'None' AS resistance,
                           collect(DISTINCT i.action) AS controls,
                           [] AS chemicals
                """, {"cond": cond, "variety": row["variety"]})
                knowledge.append({"condition": cond, "diseases": kg})

            context = _build_context(row, d, knowledge)
            result = await structured_completion(
                system="You are a potato agronomist AI for Kenyan smallholder farmers. "
                       "Analyze field conditions and disease risks.",
                user=context,
                schema=ALERT_SCHEMA,
            )

            status = result.get("status", "NORMAL")
            if status in ("WARNING", "CRITICAL"):
                alert_id = str(uuid.uuid4())
                now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
                sms_en = result.get("sms_english", "")[:160]
                sms_sw = result.get("sms_swahili", "")[:160]

                query("""
                    MATCH (s:Season {seasonId: $sid})
                    MATCH (d:DailySnapshot {snapshotId: $snapid})
                    CREATE (a:Alert {
                        alertId: $aid, detected_condition: $condition,
                        confidence: $conf, explanation: $expl, recommendation: $rec,
                        urgency: $urgency, status: 'ACTIVE',
                        sms_english: $sms_en, sms_swahili: $sms_sw,
                        createdAt: $now, retryCount: 0
                    })
                    CREATE (s)-[:GENERATED]->(a)
                    CREATE (a)-[:TRIGGERED_BY]->(d)
                """, {
                    "sid": sid, "snapid": d.get("snapshotId", ""),
                    "aid": alert_id, "condition": result.get("detected_condition", ""),
                    "conf": result.get("confidence", 0),
                    "expl": result.get("explanation", ""),
                    "rec": result.get("recommendation", ""),
                    "urgency": result.get("urgency", "LOW"),
                    "sms_en": sms_en, "sms_sw": sms_sw, "now": now_ts,
                })
                logger.info("Pipeline B: Alert %s created for season %s (%s)", alert_id, sid, status)

        except Exception as e:
            logger.exception("Pipeline B: Failed for season %s", sid)
            continue

    logger.info("Pipeline B: Complete")


def _evaluate_conditions(d: dict) -> list[str]:
    triggered = []
    precip_5d = float(d.get("rolling_5d_precip", 0) or 0)
    temp = float(d.get("daily_avg_temp_c", 0) or 0)
    has_sat = d.get("has_satellite_data", False)
    ndvi = float(d.get("mean_ndvi", 0) or 0) if has_sat else 0

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


def _build_context(row: dict, d: dict, knowledge: list) -> str:
    lines = [
        f"Plot: {row.get('plotName', 'Unknown')}",
        f"Variety: {row.get('variety', 'Unknown')}",
        f"Growth Stage: {row.get('stage', 'Unknown')} — {row.get('stageDesc', '')}",
        "",
        "Today's Telemetry:",
        f"  Temperature: {d.get('daily_avg_temp_c', 'N/A')} °C",
        f"  Precipitation: {d.get('daily_precip_mm', 'N/A')} mm",
        f"  Humidity: {d.get('daily_avg_humidity', 'N/A')}%",
        f"  5-day Rolling Precip: {d.get('rolling_5d_precip', 'N/A')} mm",
        f"  10-day Rolling Precip: {d.get('rolling_10d_precip', 'N/A')} mm",
    ]
    if d.get("has_satellite_data"):
        lines.extend([
            f"  NDVI: {d.get('mean_ndvi', 'N/A')}",
            f"  EVI: {d.get('mean_evi', 'N/A')}",
            f"  Cloud Cover: {d.get('cloud_cover_percentage', 'N/A')}%",
        ])

    lines.append("")
    lines.append("Knowledge Graph Findings:")
    for item in knowledge:
        lines.append(f"  Condition: {item['condition']}")
        for dis in item.get("diseases", []):
            lines.append(f"    Disease: {dis.get('disease', 'Unknown')} (Resistance: {dis.get('resistance', 'None')})")
            controls = [c for c in (dis.get("controls", []) or []) if c]
            if controls:
                lines.append(f"    Controls: {', '.join(controls)}")
            chemicals = [c for c in (dis.get("chemicals", []) or []) if c]
            if chemicals:
                lines.append(f"    Approved Chemicals: {', '.join(chemicals)}")

    return "\n".join(lines)
