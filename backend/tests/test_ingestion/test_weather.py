"""Tests for the weather ingestion agent."""
import pytest
from agents.weather import ingest_weather
from services.neo4j import query


@pytest.mark.ingestion
class TestWeatherIngestion:
    async def test_ingest_weather_creates_observation(self, respx_mock, test_plot):
        respx_mock.get("https://api.agromonitoring.com/agro/1.0/weather").respond(
            json={
                "dt": 1700000000, "main": {
                    "temp_max": 24.0, "temp_min": 12.0, "humidity": 70,
                },
                "rain": {"1h": 3.0},
            },
        )
        await ingest_weather(-0.1833, 36.4333, test_plot)
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:HAS_OBSERVATION]->"
            "(obs:Observation_Weather) RETURN count(obs) AS cnt",
            {"pid": test_plot},
        )
        assert result[0]["cnt"] >= 1

    async def test_ingest_weather_sets_temperature(self, respx_mock, test_plot):
        respx_mock.get("https://api.agromonitoring.com/agro/1.0/weather").respond(
            json={
                "dt": 1700000000, "main": {
                    "temp_max": 24.0, "temp_min": 12.0, "humidity": 70,
                },
                "rain": {"1h": 3.0},
            },
        )
        await ingest_weather(-0.1833, 36.4333, test_plot)
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:HAS_OBSERVATION]->"
            "(obs:Observation_Weather) RETURN obs.tempMax AS tmax, "
            "obs.tempMin AS tmin LIMIT 1",
            {"pid": test_plot},
        )
        assert result[0]["tmax"] == 24.0
        assert result[0]["tmin"] == 12.0
