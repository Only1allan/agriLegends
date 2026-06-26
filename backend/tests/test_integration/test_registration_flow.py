"""End-to-end registration flow with mocked external APIs."""
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from main import app
from services.neo4j import query

client = TestClient(app)


@pytest.mark.integration
class TestRegistrationFlow:
    def test_full_registration_triggers_all_ingestion(self):
        with patch("agents.soil.ingest_soil", new_callable=AsyncMock) as m_soil, \
             patch("agents.weather.ingest_weather", new_callable=AsyncMock) as m_weather, \
             patch("agents.satellite.create_polygon", new_callable=AsyncMock) as m_poly, \
             patch("agents.satellite.ingest_satellite", new_callable=AsyncMock) as m_sat, \
             patch("agents.gdd.ingest_gdd", new_callable=AsyncMock) as m_gdd, \
             patch("agents.gdd.advance_growth_stage", new_callable=AsyncMock) as m_growth, \
             patch("agents.satellite.detect_stress", new_callable=AsyncMock) as m_stress, \
             patch("agents.diagnostic.run_diagnostic", new_callable=AsyncMock) as m_diag:
            m_soil.return_value = {
                "nitrogen_total": 0.18, "ph": 5.8, "carbon_total": 1.2,
                "aluminium_extractable": 15.0, "carbon_organic": 0.5,
            }
            m_poly.return_value = "poly-e2e-test"
            m_sat.return_value = 30
            m_gdd.return_value = 580.0
            m_growth.return_value = "Tuber Initiation"
            m_stress.return_value = 0
            m_diag.return_value = {
                "action": "monitor_crop", "cause": "none", "urgencyHours": 24,
                "narrative": "All good.", "dataFreshness": 1,
                "masumiTxHash": "tx-e2e",
            }

            fid = f"e2e-{uuid.uuid4().hex[:8]}"
            planting = (datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d")
            reg = client.post(
                "/api/farmer/register",
                json={
                    "farmerId": fid, "name": "E2E Farmer", "county": "Nyandarua",
                    "plotName": "E2E Plot", "acres": 2.0, "variety": "Shangi",
                    "plantingDate": planting, "channels": ["whatsapp_text"],
                    "language": "en", "latitude": -0.1833, "longitude": 36.4333,
                },
            )
            assert reg.status_code == 200
            data = reg.json()

            assert data["farmerId"] == fid
            assert data["plotId"]
            assert data["soilData"] is not None
            assert data["recommendation"] is not None
            assert data["recommendation"]["masumiTxHash"] == "tx-e2e"

            report = data["ingestion_report"]
            assert "success" in report["soil"]
            assert "success" in report["polygon"]
            assert "30 days fetched" in report["satellite"]
            assert "accumulated" in report["gdd"]
            assert "Tuber Initiation" in report["growth_stage"]
            assert report["stress"] == "no stress detected"
            assert report["diagnostic"] == "recommendation stored"

            m_soil.assert_called_once()
            m_poly.assert_called_once()
            m_weather.assert_called_once()
            m_sat.assert_called_once()
            m_gdd.assert_called_once()
            m_growth.assert_called_once()
            m_stress.assert_called_once()
            m_diag.assert_called_once()

            query("MATCH (f:Farmer {farmerId: $fid}) DETACH DELETE f", {"fid": fid})

    def test_registration_sets_soil_data(self):
        with patch("agents.soil.ingest_soil", new_callable=AsyncMock) as m_soil, \
             patch("agents.weather.ingest_weather", new_callable=AsyncMock) as m_weather, \
             patch("agents.satellite.create_polygon", new_callable=AsyncMock) as m_poly, \
             patch("agents.satellite.ingest_satellite", new_callable=AsyncMock) as m_sat, \
             patch("agents.gdd.ingest_gdd", new_callable=AsyncMock) as m_gdd, \
             patch("agents.gdd.advance_growth_stage", new_callable=AsyncMock) as m_growth, \
             patch("agents.satellite.detect_stress", new_callable=AsyncMock) as m_stress, \
             patch("agents.diagnostic.run_diagnostic", new_callable=AsyncMock) as m_diag:
            m_soil.return_value = {
                "nitrogen_total": 0.22, "ph": 6.1, "carbon_total": 1.5,
                "aluminium_extractable": 10.0, "carbon_organic": 0.8,
            }
            m_poly.return_value = "poly-soil"
            m_sat.return_value = 5
            m_gdd.return_value = 200.0
            m_growth.return_value = None
            m_stress.return_value = 0
            m_diag.return_value = {
                "action": "monitor_crop", "cause": "none", "urgencyHours": 24,
                "narrative": "No issues.", "dataFreshness": 1,
                "masumiTxHash": "tx-soil",
            }

            fid = f"soil-e2e-{uuid.uuid4().hex[:8]}"
            reg = client.post(
                "/api/farmer/register",
                json={
                    "farmerId": fid, "county": "Nyandarua",
                    "plotName": "Soil Test", "acres": 1.0, "variety": "Shangi",
                    "plantingDate": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
                    "channels": ["whatsapp_text"], "language": "en",
                },
            )
            assert reg.status_code == 200
            data = reg.json()

            soil = data["soilData"]
            assert soil["nitrogen_total"] == 0.22
            assert soil["ph"] == 6.1
            assert soil["carbon_total"] == 1.5
            assert soil["aluminium_extractable"] == 10.0
            assert soil["carbon_organic"] == 0.8

            query("MATCH (f:Farmer {farmerId: $fid}) DETACH DELETE f", {"fid": fid})
