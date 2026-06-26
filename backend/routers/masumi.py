from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.masumi import log_decision, complete_decision

router = APIRouter()


class LogDecisionRequest(BaseModel):
    plotId: str
    action: str
    cause: str
    urgencyHours: int
    stage: str
    forecastedYieldKg: float


class LogDecisionResponse(BaseModel):
    txHash: str
    status: str


class CompleteDecisionRequest(BaseModel):
    txHash: str
    outputData: dict


class CompleteDecisionResponse(BaseModel):
    txHash: str
    onChainState: str | None
    verified: bool


@router.post("/log-decision")
async def log_decision_endpoint(req: LogDecisionRequest) -> LogDecisionResponse:
    try:
        tx_hash = await log_decision(req.model_dump())
        return LogDecisionResponse(txHash=tx_hash, status="CREATED")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Masumi decision logging failed: {str(e)}")


@router.post("/complete-decision")
async def complete_decision_endpoint(req: CompleteDecisionRequest) -> CompleteDecisionResponse:
    try:
        result = await complete_decision(req.txHash, req.outputData)
        return CompleteDecisionResponse(
            txHash=result["txHash"],
            onChainState=result.get("onChainState"),
            verified=result.get("verified", False),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Masumi decision completion failed: {str(e)}")
