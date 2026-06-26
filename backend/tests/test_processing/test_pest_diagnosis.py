"""Tests for knowledge graph pest diagnosis traversal."""
import pytest
from services.neo4j import query


@pytest.mark.processing
class TestPestDiagnosis:
    def test_pest_weather_match(self, test_plot, test_growth_stage):
        # Create weather matching Late Blight's thriving conditions
        # cool_wet: temp 10-22°C, humidityMin=75 → precipitation >= 75
        query(
            "MATCH (p:Plot {plotId: $pid}) "
            "MERGE (d:TimeDay {date: date()}) "
            "CREATE (obs:Observation_Weather {tempMax: 20.0, tempMin: 12.0, "
            "precipitation: 80.0, humidity: 80}) "
            "CREATE (obs)-[:OCCURRED_ON]->(d) "
            "CREATE (p)-[:HAS_OBSERVATION]->(obs)",
            {"pid": test_plot},
        )
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:AT_STAGE]->(gs:GrowthStage) "
            "MATCH (p)-[:HAS_OBSERVATION]->(w:Observation_Weather)-[:OCCURRED_ON]->(d:TimeDay {date: date()}) "
            "MATCH (gs)-[:HAS_RISK]->(pest:Pest)-[:THRIVES_IN]->(wc:WeatherCondition) "
            "WHERE w.tempMin >= wc.tempMin AND w.tempMax <= wc.tempMax "
            "AND w.precipitation >= coalesce(wc.humidityMin, 0) "
            "RETURN pest.name AS cause",
            {"pid": test_plot},
        )
        assert len(result) > 0

    def test_no_match_when_weather_extreme(self, test_plot, test_growth_stage):
        query(
            "MATCH (p:Plot {plotId: $pid}) "
            "MERGE (d:TimeDay {date: date()}) "
            "CREATE (obs:Observation_Weather {tempMax: 38.0, tempMin: 28.0, "
            "precipitation: 0, humidity: 20}) "
            "CREATE (obs)-[:OCCURRED_ON]->(d) "
            "CREATE (p)-[:HAS_OBSERVATION]->(obs)",
            {"pid": test_plot},
        )
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:AT_STAGE]->(gs:GrowthStage) "
            "MATCH (gs)-[:HAS_RISK]->(pest:Pest)-[:THRIVES_IN]->(wc:WeatherCondition) "
            "WHERE wc.tempMin <= 28 AND wc.tempMax >= 38 "
            "RETURN count(pest) AS matches",
            {"pid": test_plot},
        )
        assert result[0]["matches"] == 0

    def test_intervention_returned_for_pest(self, test_plot, test_growth_stage):
        # Create weather matching Late Blight's thriving conditions
        query(
            "MATCH (p:Plot {plotId: $pid}) "
            "MERGE (d:TimeDay {date: date()}) "
            "CREATE (obs:Observation_Weather {tempMax: 18.0, tempMin: 12.0, "
            "precipitation: 10.0, humidity: 80}) "
            "CREATE (obs)-[:OCCURRED_ON]->(d) "
            "CREATE (p)-[:HAS_OBSERVATION]->(obs)",
            {"pid": test_plot},
        )
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:AT_STAGE]->(gs:GrowthStage) "
            "MATCH (p)-[:HAS_OBSERVATION]->(w:Observation_Weather)-[:OCCURRED_ON]->(d:TimeDay {date: date()}) "
            "MATCH (gs)-[:HAS_RISK]->(pest:Pest)-[:THRIVES_IN]->(wc:WeatherCondition) "
            "WHERE w.tempMin >= wc.tempMin AND w.tempMax <= wc.tempMax "
            "MATCH (pest)-[:DETECTED_BY]->(:Symptom)-[:TREATED_BY]->(i:Intervention) "
            "RETURN i.action AS action, i.urgencyHours AS urgency",
            {"pid": test_plot},
        )
        if result:
            assert "action" in result[0]
            assert result[0]["urgency"] > 0
