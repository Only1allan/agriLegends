import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from services.neo4j import query, query_one
from services.featherless import structured_completion
from routers.auth import get_current_farmer

router = APIRouter()

FORECAST_SCHEMA = {
    "type": "object",
    "properties": {
        "predictedYield": {"type": "number"},
        "confidenceLow": {"type": "number"},
        "confidenceHigh": {"type": "number"},
        "basis": {"type": "string"},
    },
    "required": ["predictedYield", "confidenceLow", "confidenceHigh", "basis"],
}


@router.get("/seasons/{season_id}/forecast")
async def get_forecast(season_id: str, farmer: dict = Depends(get_current_farmer)):
    result = query_one("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_FORECAST]->(f:YieldForecast)
        RETURN f
        ORDER BY f.date DESC LIMIT 1
    """, {"sid": season_id})
    return result


@router.post("/seasons/{season_id}/forecast/generate")
async def generate_forecast(season_id: str, farmer: dict = Depends(get_current_farmer)):
    snapshots = query("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_SNAPSHOT]->(d:DailySnapshot)
        RETURN d.mean_ndvi AS ndvi, d.daily_avg_temp_c AS temp,
               d.daily_precip_mm AS precip, d.date AS date
        ORDER BY d.date DESC LIMIT 14
    """, {"sid": season_id})

    season_data = query_one("""
        MATCH (p:Plot)-[:HAS_SEASON]->(s:Season {seasonId: $sid})
        MATCH (s)-[:PLANTED_WITH]->(v:PotatoVariety)
        OPTIONAL MATCH (s)-[:HAS_GROWTH_STAGE]->(g:GrowthStage)
        RETURN p.areaHa AS areaHa, v.name AS variety, g.name AS stage
    """, {"sid": season_id})

    if not season_data:
        season_data = {"areaHa": 1.0, "variety": "Shangi", "stage": "Unknown"}

    context = (
        f"Area: {season_data.get('areaHa', 1.0)} ha. "
        f"Variety: {season_data.get('variety', 'Shangi')}. "
        f"Growth stage: {season_data.get('stage', 'Unknown')}. "
        f"Recent satellite snapshots: {str(snapshots)}"
    )

    result = await structured_completion(
        system="You are a crop yield estimation AI for Kenyan potato farms. "
               "Estimate yield based on area, variety, satellite NDVI health, and weather. "
               "Provide a predicted yield in kg with confidence range.",
        user=context,
        schema=FORECAST_SCHEMA,
    )

    forecast_id = str(uuid.uuid4())
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    query("""
        MATCH (s:Season {seasonId: $sid})
        CREATE (f:YieldForecast {
            forecastId: $fid, date: $date,
            predictedYield: $yield, confidenceLow: $low,
            confidenceHigh: $high, basis: $basis
        })
        CREATE (s)-[:HAS_FORECAST]->(f)
    """, {
        "sid": season_id, "fid": forecast_id, "date": today,
        "yield": result.get("predictedYield", 0),
        "low": result.get("confidenceLow", 0),
        "high": result.get("confidenceHigh", 0),
        "basis": result.get("basis", ""),
    })

    return {
        "forecastId": forecast_id, "date": today,
        "predictedYield": result.get("predictedYield", 0),
        "confidenceLow": result.get("confidenceLow", 0),
        "confidenceHigh": result.get("confidenceHigh", 0),
        "basis": result.get("basis", ""),
    }
