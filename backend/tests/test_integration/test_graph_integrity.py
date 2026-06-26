"""Validate graph schema and data integrity."""
import pytest
from services.neo4j import query


@pytest.mark.integration
class TestGraphIntegrity:
    def test_knowledge_graph_has_growth_stages(self):
        stages = query(
            "MATCH (gs:GrowthStage) RETURN gs.name AS name, "
            "gs.dayStart AS start, gs.dayEnd AS end "
            "ORDER BY gs.dayStart"
        )
        assert len(stages) == 4
        names = [s["name"] for s in stages]
        assert names == ["Emergence", "Tuber Initiation", "Tuber Bulking", "Maturation"]

    def test_growth_stages_form_chain(self):
        chain = query(
            "MATCH path = (gs:GrowthStage)-[:NEXT_STAGE*3]->() "
            "RETURN length(path) AS depth LIMIT 1"
        )
        assert len(chain) >= 1
        assert chain[0]["depth"] == 3

    def test_knowledge_graph_has_pests(self):
        pests = query(
            "MATCH (gs:GrowthStage)-[:HAS_RISK]->(p:Pest) "
            "RETURN DISTINCT p.name AS pest, collect(gs.name) AS stages"
        )
        assert len(pests) >= 4

    def test_pests_have_interventions(self):
        interventions = query(
            "MATCH (p:Pest)-[:DETECTED_BY]->(:Symptom)-[:TREATED_BY]->(i:Intervention) "
            "RETURN DISTINCT i.action AS action"
        )
        assert len(interventions) >= 4

    def test_soil_requirements_exist(self):
        soil = query(
            "MATCH (sr:SoilRequirement) RETURN sr.stage AS stage, "
            "sr.nitrogenTarget AS n, sr.phTarget AS ph"
        )
        assert len(soil) == 4

    def test_weather_conditions_exist(self):
        weather = query("MATCH (wc:WeatherCondition) RETURN count(wc) AS cnt")
        assert weather[0]["cnt"] >= 3
