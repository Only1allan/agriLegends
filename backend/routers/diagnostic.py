import json
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agents.diagnostic import run_diagnostic as run_diagnostic_agent, run_pest_diagnosis

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
            detail=f"Rate limited. Wait {remaining // 60}m {remaining % 60}s before running another diagnostic for this plot.",
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
async def run_diagnostic_endpoint(req: DiagnosticRequest) -> DiagnosticResponse:
    _check_rate(req.plotId)
    result = await run_diagnostic_agent(req.plotId)
    if not result.get("narrative") and not result.get("masumiTxHash"):
        raise HTTPException(status_code=404, detail="Plot not found or no data")
    return DiagnosticResponse(**result)


@router.get("/pest-check/{plot_id}")
async def pest_check(plot_id: str) -> list[PestDiagnosisItem]:
    results = await run_pest_diagnosis(plot_id)
    return [PestDiagnosisItem(**r) for r in results]
