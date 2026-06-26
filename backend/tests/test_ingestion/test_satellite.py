"""Tests for the satellite ingestion agent."""
import pytest
from agents.satellite import ingest_satellite, create_polygon
from services.neo4j import query


@pytest.mark.ingestion
class TestSatelliteIngestion:
    async def test_create_polygon(self, respx_mock):
        respx_mock.post("https://api.agromonitoring.com/agro/1.0/polygons").respond(
            json={"id": "test-polygon-id"}, status_code=201,
        )
        polygon_id = await create_polygon(-0.1833, 36.4333, "Test")
        assert polygon_id == "test-polygon-id"

    async def test_create_polygon_scales_with_acres(self, respx_mock):
        respx_mock.post("https://api.agromonitoring.com/agro/1.0/polygons").respond(
            json={"id": "poly-scaled"}, status_code=201,
        )
        polygon_id = await create_polygon(-0.1833, 36.4333, "Big Farm", size_acres=6.0)
        assert polygon_id == "poly-scaled"

    async def test_ingest_satellite_creates_observation(self, respx_mock, test_plot):
        respx_mock.get("https://api.agromonitoring.com/agro/1.0/ndvi/history").respond(
            json=[{
                "dt": 1700000000, "source": "Sentinel-2", "dc": 95, "cl": 5,
                "data": {"ndvi": 0.72, "evi": 0.58, "std": 0.1, "min": 0.5,
                         "max": 0.8, "p25": 0.6, "median": 0.7, "num": 100},
            }],
        )
        await ingest_satellite("test-polygon-id", test_plot)
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:HAS_OBSERVATION]->"
            "(obs:Observation_Satellite) RETURN count(obs) AS cnt",
            {"pid": test_plot},
        )
        assert result[0]["cnt"] >= 1

    async def test_ingest_satellite_sets_ndvi(self, respx_mock, test_plot):
        respx_mock.get("https://api.agromonitoring.com/agro/1.0/ndvi/history").respond(
            json=[{
                "dt": 1700000000, "source": "Sentinel-2", "dc": 95, "cl": 5,
                "data": {"ndvi": 0.72, "evi": 0.58, "std": 0.1, "min": 0.5,
                         "max": 0.8, "p25": 0.6, "median": 0.7, "num": 100},
            }],
        )
        await ingest_satellite("test-polygon-id", test_plot)
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:HAS_OBSERVATION]->"
            "(obs:Observation_Satellite) RETURN obs.ndvi AS ndvi ORDER BY obs.ndvi DESC LIMIT 1",
            {"pid": test_plot},
        )
        assert result[0]["ndvi"] == 0.72

    async def test_evi_different_from_ndvi(self, respx_mock, test_plot):
        respx_mock.get("https://api.agromonitoring.com/agro/1.0/ndvi/history").respond(
            json=[{
                "dt": 1700000000, "source": "Sentinel-2", "dc": 95, "cl": 5,
                "data": {"ndvi": 0.72, "evi": 0.48, "std": 0.1, "min": 0.5,
                         "max": 0.8, "p25": 0.6, "median": 0.7, "num": 100},
            }],
        )
        await ingest_satellite("test-polygon-id", test_plot)
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:HAS_OBSERVATION]->"
            "(obs:Observation_Satellite) RETURN obs.ndvi AS ndvi, obs.evi AS evi "
            "ORDER BY obs.ndvi DESC LIMIT 1",
            {"pid": test_plot},
        )
        assert result[0]["ndvi"] == 0.72
        assert result[0]["evi"] == 0.48

    async def test_nested_data_evi_fallback(self, respx_mock, test_plot):
        respx_mock.get("https://api.agromonitoring.com/agro/1.0/ndvi/history").respond(
            json=[{
                "dt": 1700000000, "source": "Sentinel-2", "dc": 95, "cl": 5,
                "data": {"mean": 0.72, "std": 0.1, "min": 0.5, "max": 0.8,
                         "p25": 0.6, "median": 0.7, "num": 100, "evi": 0.52},
            }],
        )
        await ingest_satellite("test-polygon-id", test_plot)
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:HAS_OBSERVATION]->"
            "(obs:Observation_Satellite) RETURN obs.ndvi AS ndvi, obs.evi AS evi "
            "ORDER BY obs.ndvi DESC LIMIT 1",
            {"pid": test_plot},
        )
        assert result[0]["ndvi"] == 0.72
        assert result[0]["evi"] == 0.52
