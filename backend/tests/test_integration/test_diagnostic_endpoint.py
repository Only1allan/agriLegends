"""Tests for the diagnostic API endpoint with mocked LLM."""
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from main import app
from services.neo4j import query

client = TestClient(app)


@pytest.mark.integration
class TestDiagnosticEndpoint:
    """Test POST /api/diagnostic/run with mocked LLM."""

    def test_diagnostic_creates_recommendation(self):
        with patch("agents.diagnostic.chat", new_callable=AsyncMock) as mock_chat, \
             patch("agents.diagnostic.log_decision", new_callable=AsyncMock) as mock_log:
            mock_chat.return_value = {
                "choices": [{
                    "message": {
                        "content": '{"action": "spray_fungicide", '
                                   '"cause": "late_blight", "urgencyHours": 48, '
                                   '"narrative": "Apply fungicide.", '
                                   '"dataFreshness": 1}',
                    },
                }],
            }
            mock_log.return_value = "mock-tx-hash-123abc"

            farmer_id = f"demo-{uuid.uuid4().hex[:8]}"
            reg = client.post(
                "/api/farmer/register",
                json={
                    "farmerId": farmer_id,
                    "county": "Nyandarua",
                    "plotName": "Test",
                    "acres": 1.5,
                    "variety": "Shangi",
                    "plantingDate": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
                    "channels": ["whatsapp_text"],
                    "language": "en",
                },
            )
            assert reg.status_code == 200
            plot_id = reg.json()["plotId"]

            for i in range(14):
                query(
                    "MATCH (p:Plot {plotId: $pid}) "
                    "MERGE (d:TimeDay {date: date() - duration({days: $i})}) "
                    "CREATE (obs:Observation_Satellite {ndvi: 0.72, evi: 0.59, "
                    "cloudCover: 5, source: 'Sentinel-2', dc: 95}) "
                    "CREATE (obs)-[:OCCURRED_ON]->(d) "
                    "CREATE (p)-[:HAS_OBSERVATION]->(obs)",
                    {"pid": plot_id, "i": i},
                )

            query(
                "MATCH (p:Plot {plotId: $pid}) "
                "MATCH (gs:GrowthStage {name: 'Tuber Bulking'}) "
                "CREATE (p)-[:AT_STAGE]->(gs) SET p.seasonDay = 67",
                {"pid": plot_id},
            )

            diag = client.post("/api/diagnostic/run", json={"plotId": plot_id})
            assert diag.status_code == 200, f"Diagnostic failed: {diag.text[:300]}"
            data = diag.json()
            assert data["action"] == "spray_fungicide"
            assert data["masumiTxHash"], "Expected a non-empty txHash"

            rec = client.get(f"/api/plot/{plot_id}/recommendation")
            assert rec.status_code == 200, f"Recommendation endpoint failed: {rec.text[:200]}"

            query("MATCH (f:Farmer {farmerId: $fid}) DETACH DELETE f", {"fid": farmer_id})
