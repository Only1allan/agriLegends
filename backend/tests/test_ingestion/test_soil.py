"""Tests for the soil baseline agent."""
import pytest
from agents.soil import ingest_soil, get_soil_baseline
from services.neo4j import query


@pytest.mark.ingestion
class TestSoilIngestion:
    async def test_get_soil_baseline(self, respx_mock):
        respx_mock.post("https://api.isda-africa.com/login").respond(
            json={"access_token": "test-token", "token_type": "bearer"},
        )
        respx_mock.get("https://api.isda-africa.com/isdasoil/v2/soilproperty").respond(
            json={"property": {"ph": [{"value": {"value": 5.8}}],
                               "nitrogen_total": [{"value": {"value": 0.18}}],
                               "carbon_total": [{"value": {"value": 1.2}}],
                               "aluminium_extractable": [{"value": {"value": 15.0}}],
                               "carbon_organic": [{"value": {"value": 0.5}}]}},
        )
        soil = await get_soil_baseline(-0.1833, 36.4333)
        assert soil.get("ph") == 5.8
        assert soil.get("nitrogen_total") == 0.18

    async def test_ingest_soil_updates_plot(self, respx_mock, test_plot):
        respx_mock.post("https://api.isda-africa.com/login").respond(
            json={"access_token": "test-token", "token_type": "bearer"},
        )
        respx_mock.get("https://api.isda-africa.com/isdasoil/v2/soilproperty").respond(
            json={"property": {"ph": [{"value": {"value": 5.8}}],
                               "nitrogen_total": [{"value": {"value": 0.18}}],
                               "carbon_total": [{"value": {"value": 1.2}}]}},
        )
        await ingest_soil(-0.1833, 36.4333, test_plot)
        result = query(
            "MATCH (p:Plot {plotId: $pid}) "
            "RETURN p.soilBaseline_pH AS ph, p.soilBaseline_N AS n, "
            "p.soilBaseline_C AS carbon",
            {"pid": test_plot},
        )
        assert result[0]["ph"] == 5.8
        assert result[0]["n"] == 0.18

    async def test_ingest_soil_stores_all_five_properties(self, respx_mock, test_plot):
        respx_mock.post("https://api.isda-africa.com/login").respond(
            json={"access_token": "test-token", "token_type": "bearer"},
        )
        respx_mock.get("https://api.isda-africa.com/isdasoil/v2/soilproperty").respond(
            json={"property": {"ph": [{"value": {"value": 5.8}}],
                               "nitrogen_total": [{"value": {"value": 0.18}}],
                               "carbon_total": [{"value": {"value": 1.2}}],
                               "aluminium_extractable": [{"value": {"value": 15.0}}],
                               "carbon_organic": [{"value": {"value": 0.5}}]}},
        )
        await ingest_soil(-0.1833, 36.4333, test_plot)
        result = query(
            "MATCH (p:Plot {plotId: $pid}) "
            "RETURN p.soilBaseline_N AS n, p.soilBaseline_pH AS ph, "
            "p.soilBaseline_C AS carbon, p.soilBaseline_Al AS al, "
            "p.soilBaseline_OC AS oc",
            {"pid": test_plot},
        )
        assert result[0]["ph"] == 5.8
        assert result[0]["n"] == 0.18
        assert result[0]["carbon"] == 1.2
        assert result[0]["al"] == 15.0
        assert result[0]["oc"] == 0.5
