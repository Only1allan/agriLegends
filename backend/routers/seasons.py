import json
import re as re_mod
import uuid
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.neo4j import query, query_one
from routers.auth import get_current_farmer

logger = logging.getLogger("farmwise.seasons")
router = APIRouter()


class CreateSeasonRequest(BaseModel):
    plantingDate: str
    varietyName: str = "Shangi"


class CloseSeasonRequest(BaseModel):
    actualHarvestDate: str


def _parse_date(d: str) -> datetime:
    """Parse planting/harvest date strings robustly."""
    if not d:
        raise HTTPException(status_code=400, detail="Date is required")
    d = str(d).replace("Z", "").split("T")[0].split(" ")[0]
    try:
        return datetime.fromisoformat(d)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {d}. Use YYYY-MM-DD.")


def _extract_coords(loc: any) -> tuple:
    if not loc:
        return None, None
    if isinstance(loc, dict):
        lat = loc.get("lat") or loc.get("latitude")
        lng = loc.get("lng") or loc.get("lon") or loc.get("longitude")
        if lat is not None and lng is not None:
            return float(lat), float(lng)
    if isinstance(loc, str):
        try:
            parsed = json.loads(loc)
            if isinstance(parsed, dict):
                lat = parsed.get("lat") or parsed.get("latitude")
                lng = parsed.get("lng") or parsed.get("lon")
                if lat is not None and lng is not None:
                    return float(lat), float(lng)
        except Exception:
            m = re_mod.search(r'"lat"\s*:\s*([-\d.]+).*?"lng"\s*:\s*([-\d.]+)', loc)
            if m:
                return float(m.group(1)), float(m.group(2))
    return None, None


@router.post("/plots/{plot_id}/seasons")
async def create_season(plot_id: str, req: CreateSeasonRequest, farmer: dict = Depends(get_current_farmer)):
    try:
        return await _create_season_impl(plot_id, req, farmer)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Season creation failed for plot %s: %s", plot_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to create season: {str(e)[:200]}")


async def _create_season_impl(plot_id: str, req: CreateSeasonRequest, farmer: dict):
    # 1. Lookup variety maturity
    variety = query_one("""
        MATCH (v:PotatoVariety {name: $name})
        RETURN coalesce(v.maturityDays, 90) AS maturityDays
    """, {"name": req.varietyName})
    maturity_days = (variety.get("maturityDays") or 90) if variety else 90

    # 2. Parse dates
    planting_date = _parse_date(req.plantingDate)
    expected_harvest = (planting_date + timedelta(days=int(maturity_days))).strftime("%Y-%m-%d")
    season_id = str(uuid.uuid4())

    # 3. Create Season node
    result = query("""
        MATCH (p:Plot {plotId: $pid})
        MERGE (v:PotatoVariety {name: $variety})
        ON CREATE SET v.maturityDays = $maturity
        CREATE (s:Season {
            seasonId: $sid,
            plantingDate: date($pdate),
            expectedHarvestDate: date($hdate),
            status: 'ACTIVE',
            varietyName: $variety
        })
        CREATE (p)-[:HAS_SEASON]->(s)
        CREATE (s)-[:PLANTED_WITH]->(v)
        RETURN s.seasonId AS seasonId
    """, {
        "pid": plot_id, "sid": season_id, "variety": req.varietyName,
        "pdate": req.plantingDate, "hdate": expected_harvest,
        "maturity": int(maturity_days),
    })
    if not result:
        raise HTTPException(status_code=404, detail=f"Plot {plot_id} not found")

    # 4. Get plot coords for real-data ingestion
    plot_data = query_one("""
        MATCH (p:Plot {plotId: $pid})-[:LOCATED_IN]->(c:County)
        RETURN p.location AS location, p.name AS name, p.areaHa AS areaHa
    """, {"pid": plot_id})

    lat, lng = _extract_coords(plot_data.get("location") if plot_data else None)

    ingestion = {"soil": "skipped", "weather": "skipped", "satellite": "skipped", "diagnostic": "skipped"}

    # 5. Soil data (iSDAsoil)
    if lat is not None and lng is not None:
        try:
            from agents.soil import ingest_soil
            soil_data = await ingest_soil(lat, lng, plot_id)
            ingestion["soil"] = "success" if soil_data else "no_data"
        except Exception as e:
            ingestion["soil"] = f"failed: {str(e)[:80]}"

    # 6. Satellite data (AgroMonitoring polygon + NDVI history)
    polygon_id = ""
    if lat is not None and lng is not None:
        try:
            from agents.satellite import create_polygon, ingest_satellite_to_season
            size_acres = (plot_data.get("areaHa") or 1.0) * 2.471 if plot_data else 2.5
            polygon_id = await create_polygon(lat, lng, plot_data.get("name", plot_id), size_acres)
            if polygon_id:
                query("MATCH (p:Plot {plotId: $pid}) SET p.boundaryPolygon = $poly",
                      {"pid": plot_id, "poly": polygon_id})
                sat_count = await ingest_satellite_to_season(polygon_id, season_id, days=30)
                ingestion["satellite"] = f"success ({sat_count} days)"
            else:
                ingestion["satellite"] = "polygon_creation_failed"
        except Exception as e:
            ingestion["satellite"] = f"failed: {str(e)[:80]}"

    # 7. Weather data (AgroMonitoring current weather)
    if lat is not None and lng is not None:
        try:
            from agents.weather import ingest_weather
            weather_result = await ingest_weather(season_id, lat, lng)
            ingestion["weather"] = "success" if weather_result else "no_data"
        except Exception as e:
            ingestion["weather"] = f"failed: {str(e)[:80]}"

    # 8. Diagnostic (evaluate risk based on ingested data)
    if ingestion.get("weather") == "success" or ingestion.get("satellite", "").startswith("success"):
        try:
            from agents.diagnostic import run_diagnostic
            diag = await run_diagnostic(season_id)
            if diag.get("alertId"):
                ingestion["diagnostic"] = f"alert: {diag.get('detected_condition', '')}"
            else:
                ingestion["diagnostic"] = diag.get("message", "ok")
        except Exception as e:
            ingestion["diagnostic"] = f"failed: {str(e)[:80]}"

    logger.info("Season %s created. Ingestion: %s", season_id, ingestion)

    return {
        "seasonId": season_id, "plotId": plot_id,
        "varietyName": req.varietyName,
        "plantingDate": req.plantingDate,
        "expectedHarvestDate": expected_harvest,
        "status": "ACTIVE",
        "ingestion": ingestion,
    }


@router.get("/plots/{plot_id}/seasons")
async def get_seasons(plot_id: str, farmer: dict = Depends(get_current_farmer)) -> list[dict]:
    return query("""
        MATCH (p:Plot {plotId: $pid})-[:HAS_SEASON]->(s:Season)
        OPTIONAL MATCH (s)-[:PLANTED_WITH]->(v:PotatoVariety)
        OPTIONAL MATCH (s)-[:HAS_GROWTH_STAGE]->(g:GrowthStage)
        RETURN s.seasonId AS seasonId,
               toString(s.plantingDate) AS plantingDate,
               toString(s.expectedHarvestDate) AS expectedHarvestDate,
               s.status AS status,
               s.varietyName AS varietyName,
               g.name AS growthStage
        ORDER BY s.plantingDate DESC
    """, {"pid": plot_id})


@router.patch("/seasons/{season_id}/close")
async def close_season(season_id: str, req: CloseSeasonRequest, farmer: dict = Depends(get_current_farmer)):
    try:
        _parse_date(req.actualHarvestDate)
    except HTTPException:
        raise
    query("""
        MATCH (s:Season {seasonId: $sid})
        SET s.status = 'CLOSED', s.actualHarvestDate = date($hdate)
    """, {"sid": season_id, "hdate": req.actualHarvestDate})
    return {"seasonId": season_id, "status": "CLOSED"}
