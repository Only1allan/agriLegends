import uuid
import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.neo4j import query, query_one

router = APIRouter()


class GroundTruthRequest(BaseModel):
    type: str
    text: Optional[str] = None
    imageBase64: Optional[str] = None
    metadata: Optional[dict] = None


class GroundTruthResponse(BaseModel):
    logId: str
    type: str
    classification: Optional[str] = None
    confidence: Optional[float] = None
    message: str


@router.post("/{farmer_id}/ground-truth")
async def submit_ground_truth(farmer_id: str, req: GroundTruthRequest) -> GroundTruthResponse:
    log_id = str(uuid.uuid4())
    classification = None
    confidence = None

    plot_result = query_one(
        "MATCH (f:Farmer {farmerId: $fid})-[:OWNS]->(p:Plot) RETURN p.plotId AS plotId LIMIT 1",
        {"fid": farmer_id},
    )
    plot_id = plot_result["plotId"] if plot_result else None

    media_url = None
    if req.imageBase64:
        try:
            import aiofiles
            from pathlib import Path
            Path("static/ground_truth").mkdir(parents=True, exist_ok=True)
            filename = f"{log_id}.jpg"
            filepath = Path("static/ground_truth") / filename
            img_data = base64.b64decode(req.imageBase64)
            with open(filepath, "wb") as f:
                f.write(img_data)
            media_url = f"/static/ground_truth/{filename}"
        except Exception:
            pass

    if req.type == "pest_sighting" and req.imageBase64:
        try:
            from agents.ground_truth import classify_farmer_image
            img_url = media_url or ""
            caption = req.text or ""
            result = await classify_farmer_image(img_url, caption)
            classification = result.get("classification", "unclassified")
            confidence = result.get("confidence", 0.5)
        except Exception:
            classification = "unclassified"
            confidence = 0.5
    elif req.type == "yield_report":
        classification = "yield_report"
        confidence = 1.0
    elif req.type == "farmer_observation":
        classification = "farmer_observation"
        confidence = 1.0
    else:
        classification = req.type
        confidence = 0.5

    query(
        """
        CREATE (log:FarmerLog {
            logId: $log_id,
            textRecord: $text,
            mediaUrl: $media_url,
            classification: $class,
            confidence: $conf,
            type: $type,
            metadata: $meta,
            timestamp: datetime()
        })
        """,
        {
            "log_id": log_id,
            "text": req.text or "",
            "media_url": media_url,
            "class": classification,
            "conf": confidence,
            "type": req.type,
            "meta": req.metadata or {},
        },
    )

    if plot_id:
        query(
            """
            MATCH (log:FarmerLog {logId: $log_id})
            MATCH (p:Plot {plotId: $plot_id})
            CREATE (p)-[:HAS_OBSERVATION]->(log)
            """,
            {"log_id": log_id, "plot_id": plot_id},
        )

    farmer = query_one(
        "MATCH (f:Farmer {farmerId: $fid}) RETURN f.name AS name, f.phone AS phone, f.preferredLanguage AS lang",
        {"fid": farmer_id},
    )

    return GroundTruthResponse(
        logId=log_id,
        type=req.type,
        classification=classification,
        confidence=confidence,
        message=f"Ground truth entry recorded for {farmer['name'] if farmer else farmer_id}.",
    )


@router.get("/{farmer_id}/ground-truth")
async def get_ground_truth_logs(farmer_id: str):
    results = query(
        """
        MATCH (f:Farmer {farmerId: $fid})-[:OWNS]->(p:Plot)-[:HAS_OBSERVATION]->(log:FarmerLog)
        RETURN log.logId AS logId, log.textRecord AS textRecord, log.mediaUrl AS mediaUrl,
               log.classification AS classification, log.confidence AS confidence,
               log.type AS type, log.metadata AS metadata, toString(log.timestamp) AS timestamp
        ORDER BY log.timestamp DESC
        LIMIT 50
        """,
        {"fid": farmer_id},
    )
    return results


@router.get("/{farmer_id}/profile")
async def get_farmer_profile(farmer_id: str):
    profile = query_one(
        """
        MATCH (f:Farmer {farmerId: $fid})
        OPTIONAL MATCH (f)-[:OWNS]->(p:Plot)
        OPTIONAL MATCH (p)-[:AT_STAGE]->(gs:GrowthStage)
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(c:County)
        OPTIONAL MATCH (p)-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation)
        OPTIONAL MATCH (p)-[:HAS_OBSERVATION]->(log:FarmerLog)
        RETURN f.farmerId AS farmerId, f.name AS name, f.phone AS phone,
               f.preferredLanguage AS language, f.preferredChannel AS channels,
               collect(DISTINCT {
                   plotId: p.plotId, name: p.name, variety: p.variety,
                   acres: p.sizeAcres, stage: gs.name, seasonDay: p.seasonDay,
                   county: c.name
               }) AS plots,
               collect(DISTINCT {
                   action: rec.action, cause: rec.cause,
                   urgencyHours: rec.urgencyHours, narrative: rec.narrative,
                   date: toString(rec.date)
               }) AS recommendations,
               collect(DISTINCT {
                   logId: log.logId, textRecord: log.textRecord,
                   mediaUrl: log.mediaUrl, classification: log.classification,
                   type: log.type, timestamp: toString(log.timestamp)
               }) AS groundTruthEntries
        """,
        {"fid": farmer_id},
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Farmer not found")

    profile["plots"] = [p for p in profile.get("plots", []) if p.get("plotId")]
    profile["recommendations"] = [r for r in profile.get("recommendations", []) if r.get("action")]
    profile["groundTruthEntries"] = [e for e in profile.get("groundTruthEntries", []) if e.get("logId")]

    return profile
