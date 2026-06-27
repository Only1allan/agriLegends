"""
Intervention Router: Farmer actions taken against alerts.
Each intervention MUST include a cost (expense).
Creating an intervention auto-resolves the alert.
"""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from services.neo4j import query
from routers.auth import get_current_farmer

router = APIRouter()

EXPENSE_CATEGORIES = [
    "Land Preparation", "Seed", "Fertilizer", "Labour",
    "Pesticide", "Transport", "Irrigation",
]


class CreateInterventionRequest(BaseModel):
    actionTaken: str = Field(..., min_length=1, description="What did you do to address the alert?")
    date: str
    category: str = Field(..., description="Expense category")
    description: str = Field("", description="Short description of the expense")
    amount: float = Field(..., gt=0, description="Cost in KES")


@router.post("/alerts/{alert_id}/interventions")
async def create_intervention(alert_id: str, req: CreateInterventionRequest, farmer: dict = Depends(get_current_farmer)):
    if req.category not in EXPENSE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {EXPENSE_CATEGORIES}")

    intervention_id = str(uuid.uuid4())
    expense_id = str(uuid.uuid4())

    # Create intervention + expense + resolve alert in one query
    query("""
        MATCH (a:Alert {alertId: $aid})
        MATCH (f:Farmer {farmerId: $fid})
        CREATE (i:Intervention {
            interventionId: $iid, actionTaken: $action, date: $date
        })
        CREATE (e:Expense {
            expenseId: $eid, category: $cat, description: $desc,
            amount: $amt, date: $date
        })
        CREATE (f)-[:APPLIED]->(i)
        CREATE (i)-[:ADDRESSES]->(a)
        CREATE (i)-[:HAS_EXPENSE]->(e)
        MATCH (s:Season)-[:GENERATED]->(a)
        CREATE (s)-[:HAS_EXPENSE]->(e)
        SET a.status = 'RESOLVED'
    """, {
        "aid": alert_id, "fid": farmer["farmerId"],
        "iid": intervention_id, "eid": expense_id,
        "action": req.actionTaken, "date": req.date,
        "cat": req.category, "desc": req.description, "amt": req.amount,
    })

    return {
        "interventionId": intervention_id,
        "expenseId": expense_id,
        "actionTaken": req.actionTaken,
        "category": req.category,
        "amount": req.amount,
        "date": req.date,
        "alertStatus": "RESOLVED",
    }
