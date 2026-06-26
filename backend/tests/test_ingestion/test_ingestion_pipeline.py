"""Tests for the registration ingestion pipeline wiring."""
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from main import app
from services.neo4j import query

client = TestClient(app)


@pytest.mark.ingestion
class TestIngestionPipeline:
    def test_registration_calls_all_ingestion_agents(self):
        with patch("agents.soil.ingest_soil", new_callable=AsyncMock) as m_soil, \
             patch("agents.weather.ingest_weather", new_callable=AsyncMock) as m_weather, \
             patch("agents.satellite.create_polygon", new_callable=AsyncMock) as m_poly, \
             patch("agents.satellite.ingest_satellite", new_callable=AsyncMock) as m_sat, \
             patch("agents.gdd.ingest_gdd", new_callable=AsyncMock) as m_gdd, \
             patch("agents.gdd.advance_growth_stage", new_callable=AsyncMock) as m_growth, \
             patch("agents.satellite.detect_stress", new_callable=AsyncMock) as m_stress, \
             patch("agents.diagnostic.run_diagnostic", new_callable=AsyncMock) as m_diag:
            m_soil.return_value = {"nitrogen_total": 0.18, "ph": 5.8, "carbon_total": 1.2}
            m_poly.return_value = "poly-123"
            m_sat.return_value = 30
            m_gdd.return_value = 580.0
            m_growth.return_value = "Tuber Initiation"
            m_stress.return_value = 0
            m_diag.return_value = {
                "action": "monitor_crop", "cause": "none", "urgencyHours": 24,
                "narrative": "All good.", "dataFreshness": 1,
                "masumiTxHash": "tx-abc",
            }

            fid = f"pipeline-{uuid.uuid4().hex[:8]}"
            reg = client.post(
                "/api/farmer/register",
                json={
                    "farmerId": fid, "county": "Nyandarua",
                    "plotName": "Pipeline Plot", "acres": 1.5, "variety": "Shangi",
                    "plantingDate": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
                    "channels": ["whatsapp_text"], "language": "en",
                },
            )
            assert reg.status_code == 200
            data = reg.json()
            assert data["plotId"]
            assert data["farmerId"] == fid

            report = data["ingestion_report"]
            assert report["soil"] == "success"
            assert report["polygon"] == "success"
            assert report["weather"] == "success"
            assert "30 days fetched" in report["satellite"]
            assert "accumulated" in report["gdd"]
            assert "advanced to" in report["growth_stage"]
            assert report["stress"] == "no stress detected"
            assert report["diagnostic"] == "recommendation stored"

            query("MATCH (f:Farmer {farmerId: $fid}) DETACH DELETE f", {"fid": fid})

    def test_registration_stores_polygon_id_on_plot(self):
        with patch("agents.soil.ingest_soil", new_callable=AsyncMock) as m_soil, \
             patch("agents.weather.ingest_weather", new_callable=AsyncMock) as m_weather, \
             patch("agents.satellite.create_polygon", new_callable=AsyncMock) as m_poly, \
             patch("agents.satellite.ingest_satellite", new_callable=AsyncMock) as m_sat, \
             patch("agents.gdd.ingest_gdd", new_callable=AsyncMock) as m_gdd, \
             patch("agents.gdd.advance_growth_stage", new_callable=AsyncMock) as m_growth, \
             patch("agents.satellite.detect_stress", new_callable=AsyncMock) as m_stress, \
             patch("agents.diagnostic.run_diagnostic", new_callable=AsyncMock) as m_diag:
            m_soil.return_value = {}
            m_poly.return_value = "polygon-xyz-456"
            m_sat.return_value = 15
            m_gdd.return_value = 320.0
            m_growth.return_value = None
            m_stress.return_value = 0
            m_diag.return_value = {}

            fid = f"poly-storage-{uuid.uuid4().hex[:8]}"
            reg = client.post(
                "/api/farmer/register",
                json={
                    "farmerId": fid, "county": "Nyandarua",
                    "plotName": "Poly Test", "acres": 2.0, "variety": "Shangi",
                    "plantingDate": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "channels": ["whatsapp_text"], "language": "en",
                },
            )
            assert reg.status_code == 200
            pid = reg.json()["plotId"]

            result = query(
                "MATCH (p:Plot {plotId: $pid}) RETURN p.agromonitoringPolygonId AS poly",
                {"pid": pid},
            )
            assert result[0]["poly"] == "polygon-xyz-456"

            query("MATCH (f:Farmer {farmerId: $fid}) DETACH DELETE f", {"fid": fid})

    def test_ingestion_continues_after_agent_failure(self):
        with patch("agents.soil.ingest_soil", new_callable=AsyncMock) as m_soil, \
             patch("agents.weather.ingest_weather", new_callable=AsyncMock) as m_weather, \
             patch("agents.satellite.create_polygon", new_callable=AsyncMock) as m_poly, \
             patch("agents.satellite.ingest_satellite", new_callable=AsyncMock) as m_sat, \
             patch("agents.gdd.ingest_gdd", new_callable=AsyncMock) as m_gdd, \
             patch("agents.gdd.advance_growth_stage", new_callable=AsyncMock) as m_growth, \
             patch("agents.satellite.detect_stress", new_callable=AsyncMock) as m_stress, \
             patch("agents.diagnostic.run_diagnostic", new_callable=AsyncMock) as m_diag:
            m_soil.side_effect = Exception("API down")
            m_poly.return_value = "poly-fail-1"
            m_weather.side_effect = Exception("Weather timeout")
            m_sat.side_effect = Exception("Satellite error")
            m_gdd.return_value = 0
            m_growth.return_value = None
            m_stress.return_value = 0
            m_diag.return_value = {}

            fid = f"fail-{uuid.uuid4().hex[:8]}"
            reg = client.post(
                "/api/farmer/register",
                json={
                    "farmerId": fid, "county": "Nyandarua",
                    "plotName": "Fail Test", "acres": 1.0, "variety": "Shangi",
                    "plantingDate": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
                    "channels": ["whatsapp_text"], "language": "en",
                },
            )
            assert reg.status_code == 200
            data = reg.json()
            report = data["ingestion_report"]

            assert "failed" in report["soil"]
            assert report["polygon"] == "success"
            assert "failed" in report["weather"]
            assert "failed" in report["satellite"]
            assert report["gdd"] == "success (accumulated: 0)"
            assert report["stress"] == "no stress detected"

            query("MATCH (f:Farmer {farmerId: $fid}) DETACH DELETE f", {"fid": fid})
