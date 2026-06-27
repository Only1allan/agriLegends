"""
Soil data endpoint: Returns real iSDA soil properties for a plot.
"""
from fastapi import APIRouter, Depends
from services.neo4j import query, query_one
from routers.auth import get_current_farmer

router = APIRouter()


@router.get("/plots/{plot_id}/soil")
async def get_soil(plot_id: str, farmer: dict = Depends(get_current_farmer)):
    result = query_one("""
        MATCH (f:Farmer {farmerId: $fid})-[:OWNS]->(p:Plot {plotId: $pid})
        OPTIONAL MATCH (p)-[:HAS_SEASON]->(s:Season {status: "ACTIVE"})
        OPTIONAL MATCH (s)-[:PLANTED_WITH]->(v:PotatoVariety)
        OPTIONAL MATCH (s)-[:HAS_GROWTH_STAGE]->(g:GrowthStage)
        OPTIONAL MATCH (sr:SoilRequirement {stage: g.name})
        RETURN p.soilBaseline_N AS nitrogen,
               p.soilBaseline_pH AS ph,
               p.soilBaseline_C AS carbon,
               p.soilBaseline_Al AS aluminium,
               p.soilBaseline_OC AS organicCarbon,
               p.name AS plotName, p.county AS county,
               coalesce(g.name, 'Unknown') AS growthStage,
               sr.nitrogenTarget AS targetN,
               sr.phTarget AS targetPH
    """, {"fid": farmer["farmerId"], "pid": plot_id})
    if not result:
        return None
    return result


@router.get("/seasons/{season_id}/pests")
async def get_pest_risks(season_id: str, farmer: dict = Depends(get_current_farmer)):
    """Get pest/disease risks for the current growth stage of a season."""
    stage_risks = """
        MATCH (s:Season {seasonId: $sid})-[:PLANTED_WITH]->(v:PotatoVariety)
        OPTIONAL MATCH (s)-[:HAS_GROWTH_STAGE]->(g:GrowthStage)
        MATCH (pest:Pest)
        OPTIONAL MATCH (pest)-[:THRIVES_IN]->(wc:WeatherCondition)
        OPTIONAL MATCH (pest)-[:DETECTED_BY]->(sym:Symptom)-[:TREATED_BY]->(inter:Intervention)
        WHERE EXISTS {
            OPTIONAL MATCH (s)-[:HAS_GROWTH_STAGE]->(g2:GrowthStage)
            WHERE (pest)-[:AFFECTS_STAGE|HAS_RISK]->(g2)
            WITH pest WHERE pest IS NOT NULL
        }
        RETURN coalesce(g.name, 'All Stages') AS stage,
               pest.name AS pest, pest.scientificName AS scientific,
               wc.name AS weatherCondition,
               collect(DISTINCT sym.sensorType) AS symptoms,
               collect(DISTINCT inter.action) AS treatments,
               collect(DISTINCT inter.method) AS methods
    """
    results = query("""
        MATCH (s:Season {seasonId: $sid})-[:PLANTED_WITH]->(v:PotatoVariety)
        OPTIONAL MATCH (s)-[:HAS_GROWTH_STAGE]->(g:GrowthStage)
        OPTIONAL MATCH (gs:GrowthStage)-[:HAS_RISK]->(pest:Pest)
        WHERE gs.name = COALESCE(g.name, 'Tuber Bulking')
        OPTIONAL MATCH (pest)-[:THRIVES_IN]->(wc:WeatherCondition)
        OPTIONAL MATCH (pest)-[:DETECTED_BY]->(sym:Symptom)-[:TREATED_BY]->(inter:Intervention)
        RETURN COALESCE(g.name, 'Tuber Bulking (default)') AS stage,
               pest.name AS pest, pest.scientificName AS scientific,
               wc.name AS weatherCondition,
               collect(DISTINCT sym.sensorType) AS symptoms,
               collect(DISTINCT inter.action) AS treatments,
               collect(DISTINCT inter.method) AS methods
    """, {"sid": season_id})
    if not results or not any(r.get("pest") for r in results):
        return {"stage": "Unknown", "pests": []}

    return {
        "stage": results[0]["stage"] if results else "Unknown",
        "pests": [
            {
                "name": r["pest"],
                "scientific": r.get("scientific", ""),
                "weatherCondition": r.get("weatherCondition", ""),
                "symptoms": r.get("symptoms", []),
                "treatments": r.get("treatments", []),
                "methods": r.get("methods", []),
            }
            for r in results if r.get("pest")
        ],
    }


@router.get("/seasons/{season_id}/weather-conditions")
async def get_active_weather_conditions(season_id: str, farmer: dict = Depends(get_current_farmer)):
    """Compare latest DailySnapshot weather against knowledge graph WeatherConditions."""
    latest = query_one("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_SNAPSHOT]->(d:DailySnapshot)
        RETURN d.rolling_5d_precip AS r5precip,
               d.daily_avg_temp_c AS temp,
               d.daily_avg_humidity AS humidity
        ORDER BY d.date DESC LIMIT 1
    """, {"sid": season_id})

    if not latest:
        return {"active": [], "message": "No weather data yet"}

    hum = float(latest.get("humidity", 0) or 0)
    temp = float(latest.get("temp", 0) or 0)

    conditions = query("""
        MATCH (wc:WeatherCondition)
        WHERE $temp >= coalesce(wc.tempMin, -50)
          AND $temp <= coalesce(wc.tempMax, 50)
        MATCH (wc)<-[:THRIVES_IN]-(pest:Pest)
        RETURN wc.name AS condition, wc.humidityMin AS hMin,
               collect(DISTINCT pest.name) AS diseases
        ORDER BY abs($hum - coalesce(wc.humidityMin, 50)) ASC
        LIMIT 3
    """, {"temp": temp, "hum": hum})

    return {
        "latest": {"temp": temp, "r5precip": latest.get("r5precip"), "humidity": hum},
        "active": [
            {"condition": c["condition"], "diseases": c.get("diseases", [])}
            for c in conditions
        ],
    }
