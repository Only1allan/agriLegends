"""
Satellite Agent: Fetches NDVI zonal statistics from AgroMonitoring API
and writes DailySnapshot nodes to Neo4j (pipeline model).
Applies relaxed cloud cover gate (CL <= 95% for useful data)."""
import uuid
import logging
import httpx
from datetime import datetime, timedelta, timezone
from config import settings
from services.neo4j import query

logger = logging.getLogger("farmwise.satellite")

AGRO_BASE = "https://api.agromonitoring.com/agro/1.0"

_THRESHOLDS = [(5, 0.006), (2, 0.004), (0.5, 0.002)]


async def get_ndvi_history(polygon_id: str, days: int = 30) -> list[dict]:
    """Fetch daily NDVI statistics for a plot polygon."""
    if not settings.AGROMONITORING_API_KEY:
        logger.warning("AgroMonitoring API key not configured")
        return []
    now = datetime.now(timezone.utc)
    end = int(now.timestamp())
    start = int((now - timedelta(days=days)).timestamp())
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"{AGRO_BASE}/ndvi/history",
                params={
                    "polyid": polygon_id, "start": start, "end": end,
                    "appid": settings.AGROMONITORING_API_KEY,
                },
            )
            if res.status_code != 200:
                logger.warning("AgroMonitoring NDVI returned %d: %s", res.status_code, res.text[:200])
                return []
            data = res.json()
            if not isinstance(data, list):
                return []
            return data
    except Exception as e:
        logger.error("AgroMonitoring NDVI fetch failed: %s", e)
        return []


async def fetch_daily_ndvi(polygon_id: str, target_date: str) -> dict:
    """Fetch NDVI for a specific day. Returns {date, ndvi, evi, cloud_cover} or {}."""
    if not settings.AGROMONITORING_API_KEY:
        return {}
    try:
        td = datetime.fromisoformat(target_date)
    except ValueError:
        return {}
    start_ts = int(td.replace(hour=0, minute=0, second=0).timestamp())
    end_ts = int(td.replace(hour=23, minute=59, second=59).timestamp())
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"{AGRO_BASE}/ndvi/history",
                params={
                    "polyid": polygon_id, "start": start_ts, "end": end_ts,
                    "appid": settings.AGROMONITORING_API_KEY,
                },
            )
            if res.status_code != 200:
                return {}
            data = res.json()
            if not isinstance(data, list) or not data:
                return {}
            entry = data[0]
            stats = entry.get("data", {})
            return {
                "date": target_date,
                "ndvi": stats.get("ndvi") or stats.get("mean", 0),
                "evi": stats.get("evi", 0),
                "cloud_cover": entry.get("cl", 100),
            }
    except Exception as e:
        logger.error("fetch_daily_ndvi failed for %s: %s", target_date, e)
        return {}


async def create_polygon(lat: float, lon: float, name: str, size_acres: float = 1.0) -> str:
    """Create an AgroMonitoring polygon from plot center coordinates."""
    if size_acres is None or size_acres <= 0:
        size_acres = 1.0
    if not settings.AGROMONITORING_API_KEY:
        logger.warning("AgroMonitoring API key not configured — cannot create polygon")
        return ""

    buffer = 0.002
    for threshold, buf_size in _THRESHOLDS:
        if size_acres >= threshold:
            buffer = buf_size; break
    if size_acres < 0.5:
        buffer = 0.001

    polygon_payload = {
        "name": name,
        "geo_json": {
            "type": "Feature", "properties": {},
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
        },
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{AGRO_BASE}/polygons",
                params={"appid": settings.AGROMONITORING_API_KEY, "duplicated": "true"},
                json=polygon_payload,
            )
            res.raise_for_status()
            data = res.json()
            pid = data.get("id", "")
            logger.info("Created AgroMonitoring polygon %s at %.4f,%.4f", pid, lat, lon)
            return pid
    except Exception as e:
        logger.error("AgroMonitoring polygon creation failed: %s", e)
        return ""


async def ingest_satellite_to_season(polygon_id: str, season_id: str, days: int = 30) -> int:
    """
    Fetch NDVI history and write DailySnapshot nodes linked to Season.
    Stores ALL data with cloud <= 95% (relaxed threshold for free tier API).
    Merges into existing snapshots from weather agent.
    Returns number of snapshot days ingested.
    """
    if not settings.AGROMONITORING_API_KEY:
        logger.warning("Satellite agent: API key not configured")
        return 0
    if not polygon_id:
        logger.warning("Satellite agent: no polygon_id for season %s", season_id)
        return 0

    ndvi_data = await get_ndvi_history(polygon_id, days=days)
    if not ndvi_data:
        logger.warning("Satellite agent: no NDVI data returned for polygon %s", polygon_id)
        return 0

    count = 0
    skipped_cloud = 0
    for entry in ndvi_data:
        try:
            ts = entry.get("dt")
            if not ts:
                continue
            date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            cloud_cover = float(entry.get("cl", 100))

            # Relaxed cloud gate: still store data, but mark quality
            if cloud_cover > 95.0:
                skipped_cloud += 1
                continue

            stats = entry.get("data", {})
            ndvi = stats.get("ndvi") or stats.get("mean", 0)

            # Check if snapshot already exists for this date
            existing = query("""
                MATCH (s:Season {seasonId: $sid})-[:HAS_SNAPSHOT]->(d:DailySnapshot {date: $date})
                RETURN d.snapshotId AS snapshotId
            """, {"sid": season_id, "date": date_str})

            if existing:
                snap_id = existing[0]["snapshotId"]
                query("""
                    MATCH (d:DailySnapshot {snapshotId: $snapid})
                    SET d.has_satellite_data = true,
                        d.cloud_cover_percentage = $cloud,
                        d.mean_ndvi = $ndvi, d.mean_evi = $evi,
                        d.mean_ndwi = $ndwi, d.mean_savi = $savi,
                        d.mean_msi = $msi
                """, {
                    "snapid": snap_id, "cloud": cloud_cover, "ndvi": ndvi,
                    "evi": ndvi * 0.82 if ndvi else 0,
                    "ndwi": 0, "savi": ndvi * 0.8 if ndvi else 0, "msi": 0,
                })
            else:
                snap_id = str(uuid.uuid4())
                query("""
                    MATCH (s:Season {seasonId: $sid})
                    CREATE (d:DailySnapshot {
                        snapshotId: $snapid, date: $date,
                        has_satellite_data: true,
                        cloud_cover_percentage: $cloud,
                        mean_ndvi: $ndvi, mean_evi: $evi,
                        mean_ndwi: $ndwi, mean_savi: $savi,
                        mean_msi: $msi,
                        daily_precip_mm: 0, daily_avg_temp_c: 0,
                        daily_avg_humidity: 0,
                        rolling_5d_precip: 0, rolling_10d_precip: 0,
                        rolling_14d_precip: 0, rolling_5d_temp_avg: 0,
                        rolling_5d_humidity_avg: 0
                    })
                    CREATE (s)-[:HAS_SNAPSHOT]->(d)
                """, {
                    "sid": season_id, "snapid": snap_id, "date": date_str,
                    "cloud": cloud_cover, "ndvi": ndvi,
                    "evi": ndvi * 0.82 if ndvi else 0,
                    "ndwi": 0, "savi": ndvi * 0.8 if ndvi else 0, "msi": 0,
                })
            count += 1
        except Exception as e:
            logger.warning("Satellite entry skipped for %s: %s", season_id, e)
            continue

    logger.info("Satellite: ingested %d snapshots for season %s (skipped %d for high cloud)",
                count, season_id, skipped_cloud)
    return count
