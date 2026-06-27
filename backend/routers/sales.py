import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from services.neo4j import query
from routers.auth import get_current_farmer

router = APIRouter()


class CreateSaleRequest(BaseModel):
    quantity_kg: float
    unit_price: float
    buyer: str
    sale_date: str


class SaleResponse(BaseModel):
    saleId: str
    quantity_kg: float
    unit_price: float
    total_amount: float
    buyer: str
    sale_date: str


@router.post("/seasons/{season_id}/sales")
async def create_sale(season_id: str, req: CreateSaleRequest, farmer: dict = Depends(get_current_farmer)):
    total = round(req.quantity_kg * req.unit_price, 2)
    sale_id = str(uuid.uuid4())

    query("""
        MATCH (s:Season {seasonId: $sid})
        CREATE (sa:Sale {
            saleId: $said, quantity_kg: $qty, unit_price: $price,
            total_amount: $total, buyer: $buyer, sale_date: $date
        })
        CREATE (s)-[:HAS_SALE]->(sa)
    """, {
        "sid": season_id, "said": sale_id, "qty": req.quantity_kg,
        "price": req.unit_price, "total": total, "buyer": req.buyer,
        "date": req.sale_date,
    })

    return SaleResponse(
        saleId=sale_id, quantity_kg=req.quantity_kg,
        unit_price=req.unit_price, total_amount=total,
        buyer=req.buyer, sale_date=req.sale_date,
    )


@router.get("/seasons/{season_id}/sales")
async def get_sales(season_id: str, farmer: dict = Depends(get_current_farmer)):
    sales = query("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_SALE]->(sa:Sale)
        RETURN sa.saleId AS saleId, sa.quantity_kg AS quantity_kg,
               sa.unit_price AS unit_price, sa.total_amount AS total_amount,
               sa.buyer AS buyer, sa.sale_date AS sale_date
        ORDER BY sa.sale_date DESC
    """, {"sid": season_id})

    total_kg = sum(s["quantity_kg"] for s in sales)
    total_revenue = sum(s["total_amount"] for s in sales)

    return {"sales": sales, "totalKg": round(total_kg, 2), "totalRevenue": round(total_revenue, 2)}
