"""
MIP-003 Agent Adapter — exposes the diagnostic agent for Masumi health checks
and Registry registration compliance.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/diagnostic/mip003")


@router.get("/availability")
async def availability():
    return {"status": "available", "message": "FarmWise Potato Diagnostic Agent is online"}


@router.get("/input_schema")
async def input_schema():
    return {
        "type": "object",
        "properties": {
            "plotId": {"type": "string", "description": "Plot UUID"},
            "farmerId": {"type": "string", "description": "Farmer UUID"},
        },
        "required": ["plotId"],
    }
