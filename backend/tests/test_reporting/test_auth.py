"""Tests for auth/OTP API routes."""
import pytest
from fastapi.testclient import TestClient
from main import app
from services.neo4j import query

client = TestClient(app)


@pytest.mark.reporting
class TestAuthAPI:
    def test_send_otp_returns_status(self):
        resp = client.post(
            "/api/auth/send-otp",
            json={"phone": "+254700000001"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_verify_otp_creates_farmer(self):
        resp = client.post(
            "/api/auth/verify-otp",
            json={"phone": "+254700000002", "code": "123456"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "farmerId" in data
        assert "token" in data
        query("MATCH (f:Farmer {phone: '+254700000002'}) DETACH DELETE f")

    def test_verify_otp_returns_existing_farmer(self):
        resp = client.post(
            "/api/auth/verify-otp",
            json={"phone": "+254700000002", "code": "123456"},
        )
        fid1 = resp.json()["farmerId"]
        resp2 = client.post(
            "/api/auth/verify-otp",
            json={"phone": "+254700000002", "code": "123456"},
        )
        fid2 = resp2.json()["farmerId"]
        assert fid1 == fid2
        query("MATCH (f:Farmer {phone: '+254700000002'}) DETACH DELETE f")
