import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.neo4j import query
from routers.auth import get_current_farmer

router = APIRouter()

EXPENSE_CATEGORIES = [
    "Land Preparation", "Seed", "Fertilizer", "Labour",
    "Pesticide", "Transport", "Irrigation",
]


class CreateExpenseRequest(BaseModel):
    category: str
    description: str
    amount: float
    date: str


@router.get("/seasons/{season_id}/expenses")
async def get_expenses(season_id: str, farmer: dict = Depends(get_current_farmer)):
    direct = query("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_EXPENSE]->(e:Expense)
        RETURN e.expenseId AS expenseId, e.category AS category,
               e.description AS description, e.amount AS amount, e.date AS date,
               'direct' AS source
    """, {"sid": season_id})

    indirect = query("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_OBSERVATION]->()-[:GENERATED]->(a:Alert)
        MATCH (i:Intervention)-[:ADDRESSES]->(a)
        MATCH (i)-[:HAS_EXPENSE]->(e:Expense)
        RETURN e.expenseId AS expenseId, e.category AS category,
               e.description AS description, e.amount AS amount, e.date AS date,
               'intervention' AS source
    """, {"sid": season_id})

    all_expenses = direct + indirect

    by_category = {}
    total = 0.0
    for e in all_expenses:
        cat = e["category"]
        if cat not in by_category:
            by_category[cat] = {"count": 0, "total": 0.0}
        by_category[cat]["count"] += 1
        by_category[cat]["total"] += e["amount"]
        total += e["amount"]

    return {
        "expenses": all_expenses,
        "byCategory": by_category,
        "totalAmount": round(total, 2),
    }


@router.post("/seasons/{season_id}/expenses")
async def create_expense(season_id: str, req: CreateExpenseRequest, farmer: dict = Depends(get_current_farmer)):
    if req.category not in EXPENSE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {EXPENSE_CATEGORIES}")

    expense_id = str(uuid.uuid4())
    query("""
        MATCH (s:Season {seasonId: $sid})
        CREATE (e:Expense {
            expenseId: $eid, category: $cat, description: $desc,
            amount: $amt, date: $date
        })
        CREATE (s)-[:HAS_EXPENSE]->(e)
    """, {
        "sid": season_id, "eid": expense_id, "cat": req.category,
        "desc": req.description, "amt": req.amount, "date": req.date,
    })
    return {"expenseId": expense_id, "category": req.category, "amount": req.amount, "date": req.date}
