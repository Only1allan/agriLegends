import uuid
import re
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.neo4j import query, query_one
from services.featherless import structured_completion
from routers.auth import get_current_farmer

logger = logging.getLogger("farmwise.observations")

router = APIRouter()

OBSERVATION_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["NORMAL", "WARNING", "CRITICAL"]},
        "detected_condition": {"type": "string"},
        "confidence": {"type": "number"},
        "explanation": {"type": "string"},
        "recommendation": {"type": "string"},
        "urgency": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "sms_english": {"type": "string", "maxLength": 160},
        "sms_swahili": {"type": "string", "maxLength": 160},
    },
    "required": ["status", "detected_condition", "confidence", "explanation", "recommendation", "urgency", "sms_english", "sms_swahili"],
}


class CreateObservationRequest(BaseModel):
    notes: str
    imageUrl: str | None = None
    date: str


@router.post("/seasons/{season_id}/observations")
async def create_observation(season_id: str, req: CreateObservationRequest, farmer: dict = Depends(get_current_farmer)):
    obs_id = str(uuid.uuid4())

    latest = query_one("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_SNAPSHOT]->(d:DailySnapshot)
        RETURN d
        ORDER BY d.date DESC LIMIT 1
    """, {"sid": season_id})

    vlm_result = None
    if req.imageUrl:
        try:
            from agents.ground_truth import classify_image
            vlm_result = await classify_image(req.imageUrl)
        except Exception as e:
            logger.warning("VLM classification failed: %s", e)

    snapshot_context = ""
    if latest:
        d = latest.get("d", latest)
        snapshot_context = (
            f"Latest snapshot: temp={d.get('daily_avg_temp_c', 'N/A')}°C, "
            f"precip={d.get('daily_precip_mm', 'N/A')}mm, NDVI={d.get('mean_ndvi', 'N/A')}"
        )

    system = (
        "You are reviewing a farmer's field observation for a Kenyan potato farm. "
        "Determine if there is a crop health issue. "
        f"Snapshots: {snapshot_context}"
    )
    if vlm_result:
        system += f" Image classification: {vlm_result}"

    interpretation = await structured_completion(
        system=system,
        user=req.notes,
        schema=OBSERVATION_SCHEMA,
    )

    interp_text = str(interpretation)

    query("""
        MATCH (s:Season {seasonId: $sid})
        CREATE (o:FarmerObservation {
            observationId: $oid, date: $date, notes: $notes,
            imageUrl: $img, interpretation: $interp,
            interpretationStatus: $status
        })
        CREATE (s)-[:HAS_OBSERVATION]->(o)
    """, {
        "sid": season_id, "oid": obs_id, "date": req.date,
        "notes": req.notes, "img": req.imageUrl or "",
        "interp": interp_text,
        "status": interpretation.get("status", "NORMAL"),
    })

    if interpretation.get("status") in ("WARNING", "CRITICAL"):
        alert_id = str(uuid.uuid4())
        import time
        now_ts = int(time.time() * 1000)
        sms_en = interpretation.get("sms_english", "")[:160]
        sms_sw = interpretation.get("sms_swahili", "")[:160]
        query("""
            MATCH (s:Season {seasonId: $sid})
            MATCH (o:FarmerObservation {observationId: $oid})
            CREATE (a:Alert {
                alertId: $aid, detected_condition: $condition,
                confidence: $conf, explanation: $expl, recommendation: $rec,
                urgency: $urgency, status: 'ACTIVE',
                sms_english: $sms_en, sms_swahili: $sms_sw,
                createdAt: $now, retryCount: 0
            })
            CREATE (s)-[:GENERATED]->(a)
            CREATE (a)-[:TRIGGERED_BY]->(o)
        """, {
            "sid": season_id, "oid": obs_id, "aid": alert_id,
            "condition": interpretation.get("detected_condition", ""),
            "conf": interpretation.get("confidence", 0),
            "expl": interpretation.get("explanation", ""),
            "rec": interpretation.get("recommendation", ""),
            "urgency": interpretation.get("urgency", "LOW"),
            "sms_en": sms_en, "sms_sw": sms_sw, "now": now_ts,
        })

    return {
        "observationId": obs_id, "date": req.date, "notes": req.notes,
        "interpretation": interp_text,
        "interpretationStatus": interpretation.get("status", "NORMAL"),
    }


@router.get("/seasons/{season_id}/observations")
async def get_observations(season_id: str, farmer: dict = Depends(get_current_farmer)) -> list[dict]:
    return query("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_OBSERVATION]->(o:FarmerObservation)
        RETURN o
        ORDER BY o.date DESC
    """, {"sid": season_id})
