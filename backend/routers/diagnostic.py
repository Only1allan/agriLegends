"""
Diagnostic Router: Backward-compatible endpoints for the new pipeline model.
"""
import time
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.neo4j import query, query_one
from routers.auth import get_current_farmer

router = APIRouter()

_diag_cooldowns: dict[str, float] = {}
DIAG_COOLDOWN_SECONDS = 3600


def _check_rate(plot_id: str):
    now = time.time()
    last = _diag_cooldowns.get(plot_id, 0)
    if now - last < DIAG_COOLDOWN_SECONDS:
        remaining = int(DIAG_COOLDOWN_SECONDS - (now - last))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limited. Wait {remaining // 60}m {remaining % 60}s before running another diagnostic.",
        )
    _diag_cooldowns[plot_id] = now


class DiagnosticRequest(BaseModel):
    plotId: str


class DiagnosticResponse(BaseModel):
    action: str
    cause: str
    urgencyHours: int
    narrative: str
    dataFreshness: int
    masumiTxHash: str


class PestDiagnosisItem(BaseModel):
    cause: str
    scientific: str
    action: str
    urgencyHours: int
    method: str
    stage: str


@router.post("/run")
async def run_diagnostic_endpoint(req: DiagnosticRequest):
    _check_rate(req.plotId)

    active = query_one("""
        MATCH (p:Plot {plotId: $pid})-[:HAS_SEASON]->(s:Season {status: "ACTIVE"})
        RETURN s.seasonId AS seasonId
    """, {"pid": req.plotId})

    if not active:
        raise HTTPException(status_code=404, detail="No active season found for this plot")

    from agents.diagnostic import run_diagnostic as run_diag
    result = await run_diag(active["seasonId"])

    if result.get("status") == "no_data":
        raise HTTPException(status_code=404, detail="No snapshot data available for evaluation")

    return DiagnosticResponse(
        action=result.get("recommendation", "monitor_crop"),
        cause=result.get("detected_condition", "unknown"),
        urgencyHours=24,
        narrative=result.get("explanation", ""),
        dataFreshness=1,
        masumiTxHash=result.get("masumiTxHash", ""),
    )


@router.get("/pest-check/{plot_id}")
async def pest_check(plot_id: str):
    results = query("""
        MATCH (p:Plot {plotId: $pid})-[:HAS_SEASON]->(s:Season {status: "ACTIVE"})
        OPTIONAL MATCH (s)-[:PLANTED_WITH]->(v:PotatoVariety)
        OPTIONAL MATCH (s)-[:HAS_GROWTH_STAGE]->(g:GrowthStage)
        OPTIONAL MATCH (g)-[:HAS_RISK]->(pest:Pest)-[:THRIVES_IN]->(wc:WeatherCondition)
        OPTIONAL MATCH (pest)-[:DETECTED_BY]->(symptom:Symptom)-[:TREATED_BY]->(intervention:Intervention)
        RETURN pest.name AS cause, pest.scientificName AS scientific,
               intervention.action AS action, intervention.urgencyHours AS urgencyHours,
               intervention.method AS method, coalesce(g.name, 'Unknown') AS stage
        LIMIT 5
    """, {"pid": plot_id})

    if not results or not any(r.get("cause") for r in results if r):
        return []

    out = []
    for r in results:
        if not r.get("cause"):
            continue
        out.append(PestDiagnosisItem(
            cause=r.get("cause", "unknown"),
            scientific=r.get("scientific", ""),
            action=r.get("action", "monitor"),
            urgencyHours=r.get("urgencyHours", 24) or 24,
            method=r.get("method", ""),
            stage=r.get("stage", "Unknown"),
        ))
    return out
