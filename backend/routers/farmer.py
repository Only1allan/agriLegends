import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.neo4j import query, query_one

router = APIRouter()


class RegisterRequest(BaseModel):
    farmerId: str
    name: str = ""
    county: str = "Nyandarua"
    plotName: str = "My Shamba"
    acres: float = 1.0
    variety: str = "Shangi"
    plantingDate: str
    channels: list[str] = ["whatsapp_text"]
    language: str = "en"
    latitude: float | None = None
    longitude: float | None = None


class RegisterResponse(BaseModel):
    plotId: str
    farmerId: str
    soilData: dict | None = None
    weatherData: dict | None = None
    recommendation: dict | None = None
    ingestion_report: dict = {}
    message: str = ""


class FarmerResponse(BaseModel):
    farmerId: str
    name: str
    phone: str
    plots: list[dict]


NYANDARUA_LAT = -0.1833
NYANDARUA_LON = 36.4333
NAKURU_LAT = -0.3031
NAKURU_LON = 36.0800
KIAMBU_LAT = -1.1714
KIAMBU_LON = 36.8356

COUNTY_COORDS = {
    "nyandarua": (NYANDARUA_LAT, NYANDARUA_LON),
    "nakuru": (NAKURU_LAT, NAKURU_LON),
    "kiambu": (KIAMBU_LAT, KIAMBU_LON),
}


@router.post("/register")
async def register_farmer(req: RegisterRequest) -> RegisterResponse:
    plot_id = str(uuid.uuid4())
    lat = req.latitude if req.latitude is not None else COUNTY_COORDS.get(req.county.lower(), (NYANDARUA_LAT, NYANDARUA_LON))[0]
    lon = req.longitude if req.longitude is not None else COUNTY_COORDS.get(req.county.lower(), (NYANDARUA_LAT, NYANDARUA_LON))[1]

    query(
        """
        MERGE (f:Farmer {farmerId: $fid})
        SET f.name = $name, f.preferredChannel = $channels, f.preferredLanguage = $lang
        MERGE (c:County {name: $county})
        ON CREATE SET c.centroidLat = $lat, c.centroidLon = $lon
        CREATE (p:Plot {
            plotId: $pid, name: $pname, latitude: $lat, longitude: $lon,
            sizeAcres: $acres, variety: $variety, plantingDate: date($pdate),
            seasonDay: 1, soilBaseline_N: 0, soilBaseline_pH: 7,
            accumulatedGDD: 0, forecastedYieldKg: 0,
            agromonitoringPolygonId: ''
        })
        CREATE (f)-[:OWNS]->(p)
        CREATE (p)-[:LOCATED_IN]->(c)
        MERGE (gs:GrowthStage {name: 'Emergence'})
        CREATE (p)-[:AT_STAGE]->(gs)
        """,
        {"fid": req.farmerId, "name": req.name, "channels": req.channels, "lang": req.language,
         "county": req.county, "lat": lat, "lon": lon, "pid": plot_id,
         "pname": req.plotName, "acres": req.acres, "variety": req.variety, "pdate": req.plantingDate},
    )

    msg_parts = ["Registration complete."]
    soil_data = None
    weather_data = None
    recommendation = None
    report = {}
    polygon_id = ""

    # 1. Fetch real iSDAsoil data
    try:
        from agents.soil import ingest_soil
        soil_data = await ingest_soil(lat, lon, plot_id)
        report["soil"] = "success"
        msg_parts.append("Soil data fetched.")
    except Exception as e:
        report["soil"] = f"failed: {str(e)[:80]}"
        msg_parts.append(f"Soil fetch skipped: {str(e)[:50]}")

    # 2. Create AgroMonitoring polygon
    try:
        from agents.satellite import create_polygon
        polygon_id = await create_polygon(lat, lon, req.plotName, size_acres=req.acres)
        if polygon_id:
            query(
                "MATCH (p:Plot {plotId: $pid}) SET p.agromonitoringPolygonId = $poly",
                {"pid": plot_id, "poly": polygon_id},
            )
        report["polygon"] = "success"
    except Exception as e:
        report["polygon"] = f"failed: {str(e)[:80]}"

    # 3. Fetch real weather from AgroMonitoring
    try:
        from agents.weather import ingest_weather
        await ingest_weather(lat, lon, plot_id)
        report["weather"] = "success"
        weather_data = {"source": "AgroMonitoring", "lat": lat, "lon": lon}
        msg_parts.append("Weather data fetched.")
    except Exception as e:
        report["weather"] = f"failed: {str(e)[:80]}"
        msg_parts.append(f"Weather fetch skipped: {str(e)[:50]}")

    # 4. Ingest satellite NDVI/EVI history (requires polygon_id)
    if polygon_id:
        try:
            from agents.satellite import ingest_satellite
            sat_count = await ingest_satellite(polygon_id, plot_id)
            report["satellite"] = f"success ({sat_count} days fetched)"
        except Exception as e:
            report["satellite"] = f"failed: {str(e)[:80]}"
    else:
        report["satellite"] = "skipped (no polygon)"

    # 5. Fetch accumulated GDD (requires polygon_id)
    if polygon_id:
        try:
            from agents.gdd import ingest_gdd
            gdd_value = await ingest_gdd(polygon_id, plot_id)
            report["gdd"] = f"success (accumulated: {gdd_value})"
        except Exception as e:
            report["gdd"] = f"failed: {str(e)[:80]}"
    else:
        report["gdd"] = "skipped (no polygon)"

    # 6. Advance growth stage
    try:
        from agents.gdd import advance_growth_stage
        stage = await advance_growth_stage(plot_id)
        if stage:
            report["growth_stage"] = f"advanced to {stage}"
        else:
            report["growth_stage"] = "not yet due"
    except Exception as e:
        report["growth_stage"] = f"failed: {str(e)[:80]}"

    # 7. NDVI stress detection
    try:
        from agents.satellite import detect_stress
        stress_count = await detect_stress(plot_id)
        if stress_count > 0:
            report["stress"] = f"{stress_count} stress event(s) detected"
        else:
            report["stress"] = "no stress detected"
    except Exception as e:
        report["stress"] = f"failed: {str(e)[:80]}"

    # 8. Run diagnostic (GraphRAG synthesis + Masumi logging)
    try:
        from agents.diagnostic import run_diagnostic
        diag_result = await run_diagnostic(plot_id)
        if diag_result and diag_result.get("action"):
            recommendation = {
                "action": diag_result["action"],
                "cause": diag_result["cause"],
                "urgencyHours": diag_result["urgencyHours"],
                "narrative": diag_result["narrative"],
                "dataFreshness": diag_result["dataFreshness"],
                "masumiTxHash": diag_result["masumiTxHash"],
            }
            report["diagnostic"] = "recommendation stored"
            msg_parts.append("First recommendation generated.")
    except Exception as e:
        report["diagnostic"] = f"failed: {str(e)[:80]}"
        msg_parts.append(f"Diagnostic pending: {str(e)[:50]}")

    return RegisterResponse(
        plotId=plot_id,
        farmerId=req.farmerId,
        soilData=soil_data,
        weatherData=weather_data,
        recommendation=recommendation,
        ingestion_report=report,
        message=" ".join(msg_parts),
    )


@router.get("/{farmer_id}")
async def get_farmer(farmer_id: str) -> FarmerResponse:
    result = query_one(
        """
        MATCH (f:Farmer {farmerId: $fid})
        OPTIONAL MATCH (f)-[:OWNS]->(p:Plot)
        OPTIONAL MATCH (p)-[:AT_STAGE]->(gs:GrowthStage)
        OPTIONAL MATCH (p)-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation {date: date()})
        RETURN f.farmerId AS farmerId, f.name AS name, f.phone AS phone,
               collect({
                   plotId: p.plotId, name: p.name, variety: p.variety,
                   stage: gs.name, seasonDay: p.seasonDay,
                   forecastedYieldKg: p.forecastedYieldKg,
                   todayRecommendation: rec.narrative
               }) AS plots
        """,
        {"fid": farmer_id},
    )

    if not result:
        raise HTTPException(status_code=404, detail="Farmer not found")

    return FarmerResponse(**result)
