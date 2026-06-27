import logging
import httpx
from datetime import date, timedelta
from config import settings

logger = logging.getLogger("farmwise.weather_service")

OWM_HISTORY_URL = "https://api.openweathermap.org/data/3.0/onecall/day_summary"


async def fetch_daily_weather(lat: float, lng: float, target_date: str) -> dict:
    default = {"daily_precip_mm": 0.0, "daily_avg_temp_c": 0.0, "daily_avg_humidity": 0.0}

    if not settings.OWM_API_KEY:
        logger.warning("OWM_API_KEY not configured, returning defaults")
        return default

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(
                OWM_HISTORY_URL,
                params={
                    "lat": lat,
                    "lon": lng,
                    "date": target_date,
                    "appid": settings.OWM_API_KEY,
                },
            )
            if res.status_code != 200:
                logger.warning("OWM returned %d for %s: %s", res.status_code, target_date, res.text[:200])
                return default

            data = res.json()
            temp = data.get("temperature", {})
            precip = data.get("precipitation", {})
            humidity = data.get("humidity", {})

            return {
                "daily_precip_mm": float(precip.get("total", 0) or 0),
                "daily_avg_temp_c": _celsius(temp.get("day", 0) or 0),
                "daily_avg_humidity": float(humidity.get("afternoon", 0) or 0),
            }
    except Exception as e:
        logger.error("OWM fetch failed for (%s,%s) on %s: %s", lat, lng, target_date, e)
        return default


def _celsius(kelvin_value) -> float:
    try:
        k = float(kelvin_value)
        if k > 200:
            return round(k - 273.15, 1)
        return k
    except (TypeError, ValueError):
        return 0.0
