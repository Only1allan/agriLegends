"""
GDD Agent: Fetches accumulated temperature from AgroMonitoring API
for Growing Degree Day calculation (potato threshold: 8°C).
"""
import httpx
from datetime import datetime, timedelta
from config import settings
from services.neo4j import query

AGRO_BASE = "https://api.agromonitoring.com/agro/1.0"


async def get_accumulated_temperature(polygon_id: str, days: int = 90) -> float:
    """Fetch accumulated temperature (threshold 8°C) for a polygon."""
    end = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=days)).timestamp())

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{AGRO_BASE}/accumulated_temperature",
            params={
                "polyid": polygon_id,
                "start": start,
                "end": end,
                "appid": settings.AGROMONITORING_API_KEY,
                "threshold": 8,
            },
        )
        data = res.json()
        return data.get("accumulated_temperature", 0)


async def ingest_gdd(polygon_id: str, plot_id: str):
    """Fetch accumulated GDD and update plot properties."""
    gdd = await get_accumulated_temperature(polygon_id)

    query(
        """
        MATCH (p:Plot {plotId: $plot_id})
        SET p.accumulatedGDD = $gdd
        """,
        {"plot_id": plot_id, "gdd": gdd},
    )

    return gdd


async def advance_growth_stage(plot_id: str) -> str | None:
    """Check if plot should advance to next growth stage based on season day, and increment day."""
    query(
        """
        MATCH (p:Plot {plotId: $plot_id})-[:AT_STAGE]->(gs:GrowthStage)
        WHERE p.seasonDay > gs.dayEnd
        MATCH (gs)-[:NEXT_STAGE]->(next:GrowthStage)
        WITH p, gs, next
        MATCH (p)-[old:AT_STAGE]->(gs)
        DELETE old
        CREATE (p)-[:AT_STAGE]->(next)
        """,
        {"plot_id": plot_id},
    )
    stage_before = query(
        """
        MATCH (p:Plot {plotId: $plot_id})-[:AT_STAGE]->(gs:GrowthStage)
        RETURN gs.name AS stage
        """,
        {"plot_id": plot_id},
    )
    pre_stage = stage_before[0]["stage"] if stage_before else None

    query(
        """
        MATCH (p:Plot {plotId: $plot_id})
        SET p.seasonDay = p.seasonDay + 1
        """,
        {"plot_id": plot_id},
    )

    result = query(
        """
        MATCH (p:Plot {plotId: $plot_id})-[:AT_STAGE]->(gs:GrowthStage)
        RETURN gs.name AS stage
        """,
        {"plot_id": plot_id},
    )
    current_stage = result[0]["stage"] if result else None

    if current_stage != pre_stage and current_stage:
        return current_stage
    return None


