"""Tests for the GDD accumulation agent."""
import pytest
from agents.gdd import ingest_gdd, advance_growth_stage
from services.neo4j import query


@pytest.mark.ingestion
class TestGDDIngestion:
    async def test_ingest_gdd_updates_plot(self, respx_mock, test_plot):
        respx_mock.get("https://api.agromonitoring.com/agro/1.0/accumulated_temperature").respond(
            json={"accumulated_temperature": 580.0},
        )
        await ingest_gdd("test-polygon-id", test_plot)
        result = query(
            "MATCH (p:Plot {plotId: $pid}) RETURN p.accumulatedGDD AS gdd",
            {"pid": test_plot},
        )
        assert result[0]["gdd"] == 580.0

    async def test_advance_growth_stage(self, test_plot):
        # Link to emergence stage first
        query(
            "MATCH (gs:GrowthStage {name: 'Emergence'}) "
            "MERGE (p:Plot {plotId: $pid})-[:AT_STAGE]->(gs) "
            "SET p.seasonDay = 25",
            {"pid": test_plot},
        )
        # seasonDay(25) > Emergence.dayEnd(21) → advances to Tuber Initiation
        await advance_growth_stage(test_plot)
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:AT_STAGE]->(gs:GrowthStage) "
            "RETURN gs.name AS stage, p.seasonDay AS day",
            {"pid": test_plot},
        )
        assert result[0]["stage"] == "Tuber Initiation"
        assert result[0]["day"] == 26  # incremented by 1
