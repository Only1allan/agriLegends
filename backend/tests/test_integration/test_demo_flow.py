"""End-to-end demo flow: register → seed data → direct recommendation → certificate."""
import uuid
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from main import app
from services.neo4j import query

client = TestClient(app)


@pytest.mark.integration
class TestDemoFlow:
    def test_full_demo_flow(self):
        farmer_id = f"demo-{uuid.uuid4().hex[:8]}"

        # Step 1: Register farmer + plot
        reg_resp = client.post(
            "/api/farmer/register",
            json={
                "farmerId": farmer_id,
                "name": "Demo Farmer",
                "county": "Nyandarua",
                "plotName": "Demo Plot",
                "acres": 1.5,
                "variety": "Shangi",
                "plantingDate": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
                "channels": ["whatsapp_text"],
                "language": "en",
            },
        )
        assert reg_resp.status_code == 200
        plot_id = reg_resp.json()["plotId"]

        # Step 2: Seed 30 days of satellite + weather observations
        for day_offset in range(30):
            date = (datetime.now() - timedelta(days=30 - day_offset)).strftime("%Y-%m-%d")
            ndvi = 0.35 + (day_offset / 30) * 0.40
            query(
                "MATCH (p:Plot {plotId: $pid}) "
                "MERGE (d:TimeDay {date: date($date)}) "
                "CREATE (obs_s:Observation_Satellite {ndvi: $ndvi, evi: $evi, "
                "cloudCover: 5, source: 'Sentinel-2', dc: 95, "
                "ndvi_std: 0.1, ndvi_min: 0.3, ndvi_max: $ndvi}) "
                "CREATE (obs_s)-[:OCCURRED_ON]->(d) "
                "CREATE (p)-[:HAS_OBSERVATION]->(obs_s) "
                "CREATE (obs_w:Observation_Weather {tempMax: 22.0, tempMin: 12.0, "
                "precipitation: 3.0, humidity: 70}) "
                "CREATE (obs_w)-[:OCCURRED_ON]->(d) "
                "CREATE (p)-[:HAS_OBSERVATION]->(obs_w)",
                {"pid": plot_id, "date": date, "ndvi": round(ndvi, 4),
                 "evi": round(ndvi * 0.82, 4)},
            )

        # Step 3: Link growth stage (remove old Emergence link first)
        query(
            "MATCH (p:Plot {plotId: $pid})-[old:AT_STAGE]->(:GrowthStage) "
            "DELETE old "
            "WITH p "
            "MATCH (gs:GrowthStage {name: 'Tuber Bulking'}) "
            "CREATE (p)-[:AT_STAGE]->(gs) "
            "SET p.seasonDay = 67",
            {"pid": plot_id},
        )

        # Step 3.5: Remove any recommendation created during registration
        query(
            "MATCH (p:Plot {plotId: $pid})-[r:HAS_RECOMMENDATION]->(rec:DailyRecommendation) "
            "DETACH DELETE rec",
            {"pid": plot_id},
        )

        # Step 4: Seed a DailyRecommendation directly
        query(
            "MATCH (p:Plot {plotId: $pid}) "
            "CREATE (rec:DailyRecommendation {date: date(), "
            "action: 'spray_fungicide', cause: 'late_blight', "
            "urgencyHours: 48, narrative: 'Apply fungicide within 48 hours for late blight.', "
            "dataFreshness: 1}) "
            "CREATE (p)-[:HAS_RECOMMENDATION]->(rec) "
            "CREATE (tx:MasumiTxHash {hash: 'tx-hash-for-test-' + substring($pid, 0, 8), "
            "blockNumber: 0, timestamp: datetime()}) "
            "CREATE (rec)-[:HAS_TX]->(tx)",
            {"pid": plot_id},
        )

        # Step 5: GET recommendation
        rec_resp = client.get(f"/api/plot/{plot_id}/recommendation")
        assert rec_resp.status_code == 200
        rec_data = rec_resp.json()
        assert "narrative" in rec_data
        assert rec_data["action"] == "spray_fungicide"

        # Step 6: GET observations
        obs_resp = client.get(f"/api/plot/{plot_id}/observations?days=30")
        assert obs_resp.status_code == 200
        obs_data = obs_resp.json()
        assert len(obs_data) >= 1
        assert "date" in obs_data[0]
        assert isinstance(obs_data[0]["date"], str)

        # Step 7: GET growth stage
        growth_resp = client.get(f"/api/plot/{plot_id}/growth")
        assert growth_resp.status_code == 200
        growth_data = growth_resp.json()
        assert growth_data["stage"] == "Tuber Bulking"
        assert 0 <= growth_data["progress"] <= 100

        # Step 8: GET certificate
        cert_resp = client.get(f"/api/plot/{plot_id}/certificate")
        assert cert_resp.status_code == 200
        cert_data = cert_resp.json()
        assert cert_data["plotId"] == plot_id
        assert len(cert_data["recommendationNarrative"]) > 0

        # Cleanup
        query(
            "MATCH (f:Farmer {farmerId: $fid}) DETACH DELETE f",
            {"fid": farmer_id},
        )
