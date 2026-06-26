"""
Satellite Agent: Fetches NDVI/EVI zonal statistics from AgroMonitoring API
and writes structured Observation_Satellite nodes to Neo4j.
"""
import httpx
from datetime import datetime, timedelta
from config import settings
from services.neo4j import query

AGRO_BASE = "https://api.agromonitoring.com/agro/1.0"


async def get_ndvi_history(polygon_id: str, days: int = 30) -> list[dict]:
    """Fetch daily NDVI statistics for a plot polygon."""
    end = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=days)).timestamp())

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{AGRO_BASE}/ndvi/history",
            params={
                "polyid": polygon_id,
                "start": start,
                "end": end,
                "appid": settings.AGROMONITORING_API_KEY,
            },
        )
        return res.json()


async def create_polygon(lat: float, lon: float, name: str, size_acres: float = 1.0) -> str:
    """Create an AgroMonitoring polygon from plot center coordinates."""
    if size_acres >= 5:
        buffer = 0.006
    elif size_acres >= 2:
        buffer = 0.004
    elif size_acres >= 0.5:
        buffer = 0.002
    else:
        buffer = 0.001
    polygon_payload = {
        "name": name,
        "geo_json": {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [lon - buffer, lat - buffer],
                    [lon + buffer, lat - buffer],
                    [lon + buffer, lat + buffer],
                    [lon - buffer, lat + buffer],
                    [lon - buffer, lat - buffer],
                ]]
            },
        }
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{AGRO_BASE}/polygons",
            params={
                "appid": settings.AGROMONITORING_API_KEY,
                "duplicated": "true",
            },
            json=polygon_payload,
        )
        res.raise_for_status()
        data = res.json()
        return data.get("id", "")


async def ingest_satellite(polygon_id: str, plot_id: str):
    """Fetch NDVI history for a polygon and write observations to Neo4j."""
    ndvi_data = await get_ndvi_history(polygon_id)

    count = 0
    for entry in ndvi_data:
        date_str = datetime.utcfromtimestamp(entry["dt"]).strftime("%Y-%m-%d")
        stats = entry.get("data", {})

        query(
            """
            MATCH (p:Plot {plotId: $plot_id})
            MERGE (d:TimeDay {date: date($date)})
            CREATE (obs:Observation_Satellite {
                ndvi: $ndvi,
                evi: $evi,
                cloudCover: $cloud,
                ndvi_std: $std,
                ndvi_min: $min,
                ndvi_max: $max,
                dc: $dc,
                source: $source
            })
            CREATE (obs)-[:OCCURRED_ON]->(d)
            CREATE (p)-[:HAS_OBSERVATION]->(obs)
            """,
            {
                "plot_id": plot_id,
                "date": date_str,
                "ndvi": stats.get("ndvi", stats.get("mean", 0)),
                "evi": stats.get("evi", 0),
                "cloud": entry.get("cl", 0),
                "std": stats.get("std", 0),
                "min": stats.get("min", 0),
                "max": stats.get("max", 0),
                "dc": entry.get("dc", 100),
                "source": entry.get("source", "combined"),
            },
        )
        count += 1
    return count


async def detect_stress(plot_id: str) -> int:
    """Run the 14-day rolling NDVI baseline stress detection."""
    result = query(
        """
        MATCH (p:Plot {plotId: $plot_id})-[:HAS_OBSERVATION]->(sat:Observation_Satellite)-[:OCCURRED_ON]->(d:TimeDay)
        WHERE d.date >= date() - duration('P14D')
        WITH p, avg(sat.ndvi) AS baseline, collect(sat.ndvi)[-1] AS current
        WHERE current < baseline * 0.85
        CREATE (p)-[:EXPERIENCED_STRESS]->(:StressEvent {
            eventId: randomUUID(),
            type: "CANOPY_NDVI_DROP",
            severity: 1.0 - (current / baseline),
            detectedAt: datetime()
        })
        RETURN count(*) AS stress_count
        """,
        {"plot_id": plot_id},
    )
    return result[0]["stress_count"] if result else 0
