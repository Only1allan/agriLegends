"""Tests for growth stage computation."""
import pytest
from services.neo4j import query


@pytest.mark.processing
class TestGrowthStage:
    def test_stage_progression_query(self, test_plot, test_growth_stage):
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:AT_STAGE]->(gs:GrowthStage) "
            "RETURN gs.name AS stage, p.seasonDay AS day, "
            "gs.dayStart AS start, gs.dayEnd AS end",
            {"pid": test_plot},
        )
        assert result[0]["stage"] == "Tuber Bulking"
        assert result[0]["day"] == 67
        assert result[0]["start"] == 46
        assert result[0]["end"] == 80

    def test_stage_advancement_manual(self, test_plot):
        # Link to Tuber Bulking (dayEnd=80), set seasonDay=85 → advances to Maturation
        query(
            "MATCH (p:Plot {plotId: $pid}) "
            "MATCH (gs:GrowthStage {name: 'Tuber Bulking'}) "
            "CREATE (p)-[:AT_STAGE]->(gs) "
            "SET p.seasonDay = 85",
            {"pid": test_plot},
        )
        query(
            "MATCH (p:Plot {plotId: $pid})-[:AT_STAGE]->(gs:GrowthStage) "
            "WHERE p.seasonDay > gs.dayEnd "
            "MATCH (gs)-[:NEXT_STAGE]->(next:GrowthStage) "
            "MATCH (p)-[old:AT_STAGE]->(gs) "
            "DELETE old "
            "CREATE (p)-[:AT_STAGE]->(next)",
            {"pid": test_plot},
        )
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:AT_STAGE]->(gs:GrowthStage) "
            "RETURN gs.name AS stage",
            {"pid": test_plot},
        )
        assert result[0]["stage"] == "Maturation"

    def test_stage_progress_percentage(self, test_plot, test_growth_stage):
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:AT_STAGE]->(gs:GrowthStage) "
            "RETURN gs.dayStart AS start, gs.dayEnd AS end, "
            "p.seasonDay AS day",
            {"pid": test_plot},
        )
        r = result[0]
        progress = (r["day"] - r["start"]) / max(1, r["end"] - r["start"]) * 100
        assert 0 <= progress <= 100
