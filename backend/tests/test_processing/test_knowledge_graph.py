"""Tests for the knowledge graph agronomic model."""
import pytest
from services.neo4j import query


@pytest.mark.processing
class TestKnowledgeGraph:
    def test_late_blight_exists(self):
        pests = query(
            "MATCH (p:Pest {name: 'Late Blight'}) "
            "RETURN p.name AS name, p.scientificName AS sci"
        )
        assert len(pests) == 1
        assert pests[0]["name"] == "Late Blight"
        assert pests[0]["sci"] == "Phytophthora infestans"

    def test_all_four_weather_conditions_exist(self):
        wc = query(
            "MATCH (wc:WeatherCondition) "
            "RETURN wc.name AS name ORDER BY wc.name"
        )
        names = {r["name"] for r in wc}
        assert names == {"cool_wet", "warm_wet", "warm_dry", "cool_dry"}

    def test_has_risk_and_affects_stage_are_bidirectional(self):
        pairs = query(
            "MATCH (gs:GrowthStage)-[:HAS_RISK]->(p:Pest) "
            "RETURN gs.name AS stage, p.name AS pest ORDER BY stage, pest"
        )
        assert len(pairs) >= 5

        reverse = query(
            "MATCH (p:Pest)-[:AFFECTS_STAGE]->(gs:GrowthStage) "
            "RETURN gs.name AS stage, p.name AS pest ORDER BY stage, pest"
        )
        assert len(reverse) >= 5

        forward_set = {(r["stage"], r["pest"]) for r in pairs}
        reverse_set = {(r["stage"], r["pest"]) for r in reverse}

        for stage, pest in forward_set:
            assert (stage, pest) in reverse_set, f"HAS_RISK {stage}->{pest} missing AFFECTS_STAGE"

    def test_five_potato_varieties_exist(self):
        varieties = query(
            "MATCH (pv:PotatoVariety) "
            "RETURN pv.name AS name, pv.maturity AS maturity, "
            "pv.blightResistance AS blight ORDER BY pv.maturity"
        )
        assert len(varieties) >= 5
        names = {v["name"] for v in varieties}
        assert "Shangi" in names
        assert "Kenya Mpya" in names
        assert "Dutch Robjin" in names
        assert "Tigoni" in names
        assert "Asante" in names

    def test_detected_by_and_treated_by_chains_intact(self):
        chains = query(
            "MATCH (p:Pest)-[:DETECTED_BY]->(s:Symptom)-[:TREATED_BY]->(i:Intervention) "
            "RETURN p.name AS pest, s.sensorType AS sensor, s.threshold AS threshold, "
            "i.action AS intervention, i.urgencyHours AS urgency "
            "ORDER BY pest, sensor"
        )
        assert len(chains) >= 8

        late_blight_chains = [c for c in chains if c["pest"] == "Late Blight"]
        assert len(late_blight_chains) >= 2

        early_blight_chains = [c for c in chains if c["pest"] == "Early Blight"]
        assert len(early_blight_chains) >= 1

    def test_four_growth_stages_in_chain(self):
        stages = query(
            "MATCH (gs:GrowthStage) "
            "RETURN gs.name AS name, gs.dayStart AS start, gs.dayEnd AS end "
            "ORDER BY gs.dayStart"
        )
        assert len(stages) == 4
        names = [s["name"] for s in stages]
        assert names == [
            "Emergence",
            "Tuber Initiation",
            "Tuber Bulking",
            "Maturation",
        ]

    def test_late_blight_thrives_in_cool_wet(self):
        result = query(
            "MATCH (p:Pest {name: 'Late Blight'})-[:THRIVES_IN]->"
            "(wc:WeatherCondition {name: 'cool_wet'}) RETURN count(*) AS cnt"
        )
        assert result[0]["cnt"] >= 1

    def test_soil_requirements_exist_for_all_stages(self):
        sr = query(
            "MATCH (sr:SoilRequirement) "
            "RETURN sr.stage AS stage, sr.nitrogenTarget AS n, sr.phTarget AS ph "
            "ORDER BY sr.stage"
        )
        assert len(sr) == 4
        stages = {r["stage"] for r in sr}
        assert stages == {
            "Emergence",
            "Tuber Initiation",
            "Tuber Bulking",
            "Maturation",
        }
