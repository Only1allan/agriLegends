"""
GDD Agent: Fetches accumulated temperature from AgroMonitoring API
for Growing Degree Day calculation (potato threshold: 8°C).
"""
import asyncio
import logging
import httpx
from datetime import datetime, timedelta
from config import settings
from services.neo4j import query

logger = logging.getLogger("farmwise.gdd")

AGRO_BASE = "https://api.agromonitoring.com/agro/1.0"

MAX_RETRIES = 2
BASE_DELAY = 1.5


async def get_accumulated_temperature(polygon_id: str, days: int = 90) -> float:
    """Fetch accumulated temperature (threshold 8°C) for a polygon."""
    end = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=days)).timestamp())

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
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
                if res.status_code == 429:
                    wait = BASE_DELAY * (2 ** attempt)
                    await asyncio.sleep(wait)
                    continue
                if res.status_code != 200:
                    logger.warning("GDD API HTTP %d: %s", res.status_code, res.text[:200])
                    return 0.0
                raw = res.text.strip()
                if not raw:
                    logger.warning("GDD API returned empty body (polygon data not yet available)")
                    return 0.0
                data = res.json()
                return data.get("accumulated_temperature", 0)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning("GDD API attempt %d failed: %s", attempt + 1, e)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(BASE_DELAY * (2 ** attempt))
    return 0.0


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
        WITH p, gs,
             CASE WHEN p.plantingDate IS NOT NULL
                  THEN duration.between(p.plantingDate, date()).days
                  ELSE p.seasonDay END AS computedDay
        WHERE computedDay > gs.dayEnd
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


async def sync_growth_stage(plot_id: str) -> str | None:
    """Force-sync the plot to the correct growth stage based on planting date.
    Advances through all needed stages in one call. Safe to call on every request."""
    max_iterations = 5
    changed = False
    for _ in range(max_iterations):
        prev = await advance_growth_stage(plot_id)
        if prev is None:
            break
        changed = True
    if changed:
        result = query(
            """
            MATCH (p:Plot {plotId: $plot_id})-[:AT_STAGE]->(gs:GrowthStage)
            RETURN gs.name AS stage
            """,
            {"plot_id": plot_id},
        )
        return result[0]["stage"] if result else None
    return None


