"""Tests for farmer API routes."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.mark.reporting
class TestFarmerAPI:
    def test_get_farmer_not_found(self):
        resp = client.get("/api/farmer/nonexistent-id")
        assert resp.status_code == 404

    def test_get_farmer_returns_farmer(self, test_farmer):
        resp = client.get(f"/api/farmer/{test_farmer}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["farmerId"] == test_farmer
