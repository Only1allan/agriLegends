"""
Weather Agent: Fetches current weather from AgroMonitoring API
and writes DailySnapshot nodes to Neo4j (pipeline model)."""
import uuid
import logging
import httpx
from datetime import datetime, timedelta, timezone
from config import settings
from services.neo4j import query

logger = logging.getLogger("farmwise.weather")

AGRO_BASE = "https://api.agromonitoring.com/agro/1.0"


async def _fetch_weather(lat: float, lon: float) -> dict | None:
    if not settings.AGROMONITORING_API_KEY:
        logger.warning("Weather agent: API key not configured")
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(
                f"{AGRO_BASE}/weather",
                params={"lat": lat, "lon": lon, "appid": settings.AGROMONITORING_API_KEY},
            )
            if res.status_code != 200:
                logger.warning("AgroMonitoring weather returned %d: %s", res.status_code, res.text[:200])
                return None
            data = res.json()
            if not data or not data.get("main"):
                logger.warning("AgroMonitoring weather empty response")
                return None
            return data
    except Exception as e:
        logger.error("AgroMonitoring weather fetch failed: %s", e)
        return None


async def get_current_weather(lat: float, lon: float) -> dict:
    """Fetch current weather with 1 retry."""
    data = await _fetch_weather(lat, lon)
    if data is None:
        import asyncio
        await asyncio.sleep(2)
        data = await _fetch_weather(lat, lon)
    return data or {}


async def ingest_weather(season_id: str, lat: float, lon: float,
                         date_str: str = None, include_yesterday: bool = False) -> dict:
    if not lat or not lon:
        logger.warning("Weather agent: no coordinates for season %s", season_id)
        return {}

    data = await get_current_weather(lat, lon)
    if not data:
        return {}

    main = data.get("main", {})
    rain = data.get("rain", {})
    precip = rain.get("1h", 0) or rain.get("3h", 0) or 0 if isinstance(rain, dict) else 0
    temp_raw = main.get("temp", main.get("temp_max", 15))
    temp = round(temp_raw - 273.15, 1) if temp_raw > 100 else round(temp_raw, 1)
    humidity = main.get("humidity", 0)

    target_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    result = _store_snapshot(season_id, target_date, temp, precip, humidity)
    logger.info("Weather agent: stored snapshot for season %s date %s", season_id, target_date)

    if include_yesterday:
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        yest_data = await _fetch_weather(lat, lon)
        if yest_data:
            y_main = yest_data.get("main", {})
            y_rain = yest_data.get("rain", {})
            y_precip = y_rain.get("1h", 0) or y_rain.get("3h", 0) or 0 if isinstance(y_rain, dict) else 0
            y_temp_raw = y_main.get("temp", y_main.get("temp_max", 15))
            y_temp = round(y_temp_raw - 273.15, 1) if y_temp_raw > 100 else round(y_temp_raw, 1)
            y_humidity = y_main.get("humidity", 0)
            _store_snapshot(season_id, yesterday, y_temp, y_precip, y_humidity)
            logger.info("Weather agent: also stored yesterday snapshot %s", yesterday)

    return result


def _store_snapshot(season_id: str, date_str: str, temp: float, precip: float, humidity: float) -> dict:
    """Simplified helper: create or update a DailySnapshot for the given date."""
    existing = query("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_SNAPSHOT]->(d:DailySnapshot {date: $date})
        RETURN d.snapshotId AS snapshotId
    """, {"sid": season_id, "date": date_str})

    if existing:
        snap_id = existing[0]["snapshotId"]
        query("""
            MATCH (d:DailySnapshot {snapshotId: $snapid})
            SET d.daily_precip_mm = $precip,
                d.daily_avg_temp_c = $temp,
                d.daily_avg_humidity = $hum,
                d.rolling_5d_precip = $precip,
                d.rolling_10d_precip = $precip,
                d.rolling_14d_precip = $precip,
                d.rolling_5d_temp_avg = $temp,
                d.rolling_5d_humidity_avg = $hum
        """, {"snapid": snap_id, "precip": precip, "temp": temp, "hum": humidity})
    else:
        snap_id = str(uuid.uuid4())
        query("""
            MATCH (s:Season {seasonId: $sid})
            CREATE (d:DailySnapshot {
                snapshotId: $snapid, date: $date,
                daily_precip_mm: $precip, daily_avg_temp_c: $temp,
                daily_avg_humidity: $hum, has_satellite_data: false,
                rolling_5d_precip: $precip, rolling_10d_precip: $precip,
                rolling_14d_precip: $precip, rolling_5d_temp_avg: $temp,
                rolling_5d_humidity_avg: $hum
            })
            CREATE (s)-[:HAS_SNAPSHOT]->(d)
        """, {"sid": season_id, "snapid": snap_id, "date": date_str,
              "precip": precip, "temp": temp, "hum": humidity})

    return {"snapshot_id": snap_id, "daily_precip_mm": precip,
            "daily_avg_temp_c": temp, "daily_avg_humidity": humidity}
