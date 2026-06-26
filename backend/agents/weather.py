"""
Weather Agent: Fetches current weather from AgroMonitoring API
and writes Observation_Weather nodes to Neo4j.
"""
import httpx
from datetime import datetime
from config import settings
from services.neo4j import query

AGRO_BASE = "https://api.agromonitoring.com/agro/1.0"


async def get_current_weather(lat: float, lon: float) -> dict:
    """Fetch current weather for a geographic coordinate."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{AGRO_BASE}/weather",
            params={
                "lat": lat,
                "lon": lon,
                "appid": settings.AGROMONITORING_API_KEY,
            },
        )
        return res.json()


async def ingest_weather(lat: float, lon: float, plot_id: str):
    """Fetch current weather and write observation to Neo4j."""
    data = await get_current_weather(lat, lon)
    main = data.get("main", {})
    rain = data.get("rain", {}).get("1h", 0) if data.get("rain") else 0

    # Kelvin to Celsius conversion (if API returns Kelvin values above 100)
    temp = main.get("temp", main.get("temp_max", 15))
    temp_min_raw = main.get("temp_min", temp)
    tmax = round(temp - 273.15, 1) if temp > 100 else round(temp, 1)
    tmin = round(temp_min_raw - 273.15, 1) if temp_min_raw > 100 else round(temp_min_raw, 1)

    query(
        """
        MATCH (p:Plot {plotId: $plot_id})
        MERGE (d:TimeDay {date: date()})
        CREATE (obs:Observation_Weather {
            tempMax: $tmax,
            tempMin: $tmin,
            precipitation: $precip,
            humidity: $humidity
        })
        CREATE (obs)-[:OCCURRED_ON]->(d)
        CREATE (p)-[:HAS_OBSERVATION]->(obs)
        """,
        {
            "plot_id": plot_id,
            "tmax": tmax,
            "tmin": tmin,
            "precip": rain,
            "humidity": main.get("humidity", 0),
        },
    )
