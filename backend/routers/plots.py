import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.neo4j import query, query_one
from routers.auth import get_current_farmer

router = APIRouter()


class CreatePlotRequest(BaseModel):
    name: str
    county: str
    areaHa: float = 1.0
    boundaryPolygon: str | None = None
    soilType: str | None = None
    location: dict | None = None


class PlotResponse(BaseModel):
    plotId: str
    name: str
    county: str
    areaHa: float
    stakeholderToken: str
    activeSeasonCount: int = 0
    activeAlertCount: int = 0


@router.post("")
async def create_plot(req: CreatePlotRequest, farmer: dict = Depends(get_current_farmer)):
    plot_id = str(uuid.uuid4())
    stakeholder_token = str(uuid.uuid4())
    loc = req.location or {}
    loc_json = str(loc).replace("'", '"')

    query("""
        MERGE (c:County {name: $county})
        MATCH (f:Farmer {farmerId: $fid})
        CREATE (p:Plot {
            plotId: $pid, name: $name, county: $county, areaHa: $area,
            boundaryPolygon: $boundary, soilType: $soil,
            location: $loc, stakeholderToken: $token
        })
        CREATE (f)-[:OWNS]->(p)
        CREATE (p)-[:LOCATED_IN]->(c)
    """, {
        "fid": farmer["farmerId"], "pid": plot_id, "name": req.name,
        "county": req.county, "area": req.areaHa, "boundary": req.boundaryPolygon or "",
        "soil": req.soilType or "", "loc": loc_json, "token": stakeholder_token,
    })

    return {
        "plotId": plot_id, "name": req.name, "county": req.county,
        "areaHa": req.areaHa, "stakeholderToken": stakeholder_token,
    }


@router.get("")
async def get_plots(farmer: dict = Depends(get_current_farmer)) -> list[dict]:
    results = query("""
        MATCH (f:Farmer {farmerId: $fid})-[:OWNS]->(p:Plot)
        OPTIONAL MATCH (p)-[:HAS_SEASON]->(s:Season {status: "ACTIVE"})
        OPTIONAL MATCH (s)-[:GENERATED]->(a:Alert {status: "ACTIVE"})
        WITH p, count(DISTINCT s) AS activeSeasonCount,
           collect(DISTINCT s.seasonId) AS seasonIds,
           count(DISTINCT a) AS activeAlertCount
        RETURN p.plotId AS plotId, p.name AS name, p.county AS county,
               p.areaHa AS areaHa, p.stakeholderToken AS stakeholderToken,
               activeSeasonCount,
               seasonIds[0] AS activeSeasonId,
               activeAlertCount
        ORDER BY p.name
    """, {"fid": farmer["farmerId"]})
    return results


@router.get("/{plot_id}")
async def get_plot(plot_id: str, farmer: dict = Depends(get_current_farmer)):
    try:
        result = query_one("""
            MATCH (f:Farmer {farmerId: $fid})-[:OWNS]->(p:Plot {plotId: $pid})
            OPTIONAL MATCH (p)-[:LOCATED_IN]->(c:County)
            WITH p, c.name AS countyName
            OPTIONAL MATCH (p)-[:HAS_SEASON]->(s:Season {status: "ACTIVE"})
            WITH p, countyName, s
            OPTIONAL MATCH (s)-[:GENERATED]->(a:Alert {status: "ACTIVE"})
            OPTIONAL MATCH (s)-[:HAS_SNAPSHOT]->(d:DailySnapshot)
            WITH p, countyName, s,
                 count(DISTINCT a) AS alertCount,
                 count(DISTINCT d) AS snapshotCount
            RETURN p.plotId AS plotId, p.name AS name, p.county AS county,
                   p.areaHa AS areaHa, p.soilType AS soilType,
                   countyName,
                   s.seasonId AS activeSeasonId,
                   toString(s.plantingDate) AS plantingDate,
                   toString(s.expectedHarvestDate) AS expectedHarvestDate,
                   s.status AS seasonStatus,
                   s.varietyName AS varietyName,
                   alertCount, snapshotCount
            ORDER BY s.plantingDate DESC LIMIT 1
        """, {"fid": farmer["farmerId"], "pid": plot_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    if not result:
        # Try just the plot without season data
        result = query_one("""
            MATCH (f:Farmer {farmerId: $fid})-[:OWNS]->(p:Plot {plotId: $pid})
            OPTIONAL MATCH (p)-[:LOCATED_IN]->(c:County)
            RETURN p.plotId AS plotId, p.name AS name, p.county AS county,
                   p.areaHa AS areaHa, p.soilType AS soilType,
                   c.name AS countyName
        """, {"fid": farmer["farmerId"], "pid": plot_id})

    if not result:
        raise HTTPException(status_code=404, detail="Plot not found")
    return result


@router.post("/{plot_id}/stakeholder-token")
async def regenerate_stakeholder_token(plot_id: str, farmer: dict = Depends(get_current_farmer)):
    token = str(uuid.uuid4())
    query("""
        MATCH (f:Farmer {farmerId: $fid})-[:OWNS]->(p:Plot {plotId: $pid})
        SET p.stakeholderToken = $token
    """, {"fid": farmer["farmerId"], "pid": plot_id, "token": token})
    return {"token": token, "url": f"/stakeholder/{plot_id}?token={token}"}
