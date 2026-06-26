"""Tests for NDVI stress detection."""
import pytest
from services.neo4j import query


@pytest.mark.processing
class TestStressDetection:
    def test_stress_event_created_on_ndvi_drop(self, test_plot):
        for i in range(13):
            query(
                "MATCH (p:Plot {plotId: $pid}) "
                "MERGE (d:TimeDay {date: date() - duration({days: $i})}) "
                "CREATE (obs:Observation_Satellite {ndvi: 0.75, evi: 0.6, "
                "cloudCover: 5, source: 'Sentinel-2', dc: 95}) "
                "CREATE (obs)-[:OCCURRED_ON]->(d) "
                "CREATE (p)-[:HAS_OBSERVATION]->(obs)",
                {"pid": test_plot, "i": i},
            )
        query(
            "MATCH (p:Plot {plotId: $pid}) "
            "MERGE (d:TimeDay {date: date()}) "
            "CREATE (obs:Observation_Satellite {ndvi: 0.50, evi: 0.4, "
            "cloudCover: 5, source: 'Sentinel-2', dc: 95}) "
            "CREATE (obs)-[:OCCURRED_ON]->(d) "
            "CREATE (p)-[:HAS_OBSERVATION]->(obs)",
            {"pid": test_plot},
        )
        query(
            "MATCH (p:Plot {plotId: $pid})-[:HAS_OBSERVATION]->"
            "(sat:Observation_Satellite)-[:OCCURRED_ON]->(d:TimeDay) "
            "WHERE d.date >= date() - duration('P14D') "
            "WITH p, avg(sat.ndvi) AS baseline, collect(sat.ndvi)[-1] AS current "
            "WHERE current < baseline * 0.85 "
            "CREATE (p)-[:EXPERIENCED_STRESS]->(:StressEvent {"
            "eventId: randomUUID(), type: 'CANOPY_NDVI_DROP', "
            "severity: 1.0 - (current / baseline), detectedAt: datetime()}) "
            "RETURN count(*) AS created",
            {"pid": test_plot},
        )
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:EXPERIENCED_STRESS]->"
            "(se:StressEvent) RETURN count(se) AS cnt",
            {"pid": test_plot},
        )
        assert result[0]["cnt"] >= 1

    def test_no_stress_when_ndvi_stable(self, test_plot):
        for i in range(14):
            query(
                "MATCH (p:Plot {plotId: $pid}) "
                "MERGE (d:TimeDay {date: date() - duration({days: $i})}) "
                "CREATE (obs:Observation_Satellite {ndvi: 0.72, evi: 0.59, "
                "cloudCover: 5, source: 'Sentinel-2', dc: 95}) "
                "CREATE (obs)-[:OCCURRED_ON]->(d) "
                "CREATE (p)-[:HAS_OBSERVATION]->(obs)",
                {"pid": test_plot, "i": i},
            )
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:HAS_OBSERVATION]->"
            "(sat:Observation_Satellite)-[:OCCURRED_ON]->(d:TimeDay) "
            "WHERE d.date >= date() - duration('P14D') "
            "WITH p, avg(sat.ndvi) AS baseline, collect(sat.ndvi)[-1] AS current "
            "WHERE current < baseline * 0.85 "
            "RETURN count(*) AS would_stress",
            {"pid": test_plot},
        )
        assert result[0]["would_stress"] == 0
