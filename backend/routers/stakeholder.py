from fastapi import APIRouter, HTTPException, Depends
from services.neo4j import query_one, query
from routers.auth import get_current_farmer

router = APIRouter()


@router.get("/stakeholder/{plot_id}/report")
async def get_stakeholder_report(plot_id: str, token: str = ""):
    result = query_one("""
        MATCH (p:Plot {plotId: $pid})
        WHERE p.stakeholderToken = $token
        OPTIONAL MATCH (p)-[:HAS_SEASON]->(s:Season {status: "ACTIVE"})
        OPTIONAL MATCH (s)-[:PLANTED_WITH]->(v:PotatoVariety)
        OPTIONAL MATCH (s)-[:HAS_SNAPSHOT]->(d:DailySnapshot)
        OPTIONAL MATCH (s)-[:GENERATED]->(a:Alert)
        OPTIONAL MATCH (s)-[:HAS_OBSERVATION]->()-[:GENERATED]->()-[:ADDRESSES]-(i:Intervention)
        OPTIONAL MATCH (s)-[:HAS_FORECAST]->(f:YieldForecast)
        OPTIONAL MATCH (s)-[:HAS_SALE]->(sa:Sale)
        RETURN p.name AS plotName, p.county AS county, p.areaHa AS areaHa,
               p.soilType AS soilType,
               s.plantingDate AS plantingDate,
               s.expectedHarvestDate AS expectedHarvestDate,
               v.name AS variety,
               count(DISTINCT i) AS interventionCount,
               count(DISTINCT sa) AS saleCount,
               d.mean_ndvi AS latestNdvi, d.date AS lastUpdated
        ORDER BY d.date DESC LIMIT 1
    """, {"pid": plot_id, "token": token})

    if not result:
        raise HTTPException(status_code=404, detail="Invalid token or plot not found")

    ndvi = result.get("latestNdvi", 0) or 0
    if ndvi > 0.5:
        health = "Healthy"
    elif ndvi > 0.3:
        health = "Moderate Stress"
    else:
        health = "Critical Stress"

    forecast = query_one("""
        MATCH (s:Season)-[:HAS_FORECAST]->(f:YieldForecast)
        WHERE (s)-[:HAS_SEASON]-(:Plot {plotId: $pid})
        RETURN f.predictedYield AS predictedYield,
               f.confidenceLow AS confidenceLow,
               f.confidenceHigh AS confidenceHigh
        ORDER BY f.date DESC LIMIT 1
    """, {"pid": plot_id})

    sales = query("""
        MATCH (s:Season)-[:HAS_SALE]->(sa:Sale)
        WHERE (s)-[:HAS_SEASON]-(:Plot {plotId: $pid})
        RETURN sa.quantity_kg AS quantity_kg, sa.unit_price AS unit_price,
               sa.total_amount AS total_amount, sa.buyer AS buyer,
               sa.sale_date AS date
    """, {"pid": plot_id})

    return {
        "plotName": result.get("plotName"),
        "county": result.get("county"),
        "areaHa": result.get("areaHa"),
        "soilType": result.get("soilType"),
        "variety": result.get("variety"),
        "plantingDate": str(result.get("plantingDate", "")),
        "expectedHarvestDate": str(result.get("expectedHarvestDate", "")),
        "ndviHealth": health,
        "latestNdvi": ndvi,
        "lastUpdated": str(result.get("lastUpdated", "")),
        "interventionCount": result.get("interventionCount", 0),
        "forecast": forecast,
        "sales": sales,
        "verification": "Verified by FarmWise satellite monitoring",
    }
