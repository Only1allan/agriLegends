"""Tests for plot API routes."""
import pytest
from fastapi.testclient import TestClient
from main import app
from services.neo4j import query

client = TestClient(app)


@pytest.mark.reporting
class TestPlotAPI:
    def test_get_observations_no_data(self, test_plot):
        resp = client.get(f"/api/plot/{test_plot}/observations?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_observations_with_data(self, test_plot, test_observation_satellite):
        resp = client.get(f"/api/plot/{test_plot}/observations?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_get_recommendation_not_found(self, test_plot):
        resp = client.get(f"/api/plot/{test_plot}/recommendation")
        assert resp.status_code == 404

    def test_get_recommendation_returns_data(self, test_plot):
        query(
            "MATCH (p:Plot {plotId: $pid}) "
            "CREATE (rec:DailyRecommendation {date: date(), "
            "action: 'spray_fungicide', cause: 'late_blight', "
            "urgencyHours: 48, narrative: 'Test advice', dataFreshness: 1}) "
            "CREATE (p)-[:HAS_RECOMMENDATION]->(rec)",
            {"pid": test_plot},
        )
        resp = client.get(f"/api/plot/{test_plot}/recommendation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "spray_fungicide"

    def test_get_certificate(self, test_plot):
        resp = client.get(f"/api/plot/{test_plot}/certificate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plotId"] == test_plot

    def test_get_growth_stage(self, test_plot, test_growth_stage):
        resp = client.get(f"/api/plot/{test_plot}/growth")
        assert resp.status_code == 200
        data = resp.json()
        assert "stage" in data
        assert "progress" in data
