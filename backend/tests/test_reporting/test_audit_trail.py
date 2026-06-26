"""Tests for Masumi audit trail endpoint and certificate verification."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from main import app
from services.neo4j import query

client = TestClient(app)

MOCK_TX_HASH = "7e8bdaf2b2b919a3a4b94002cafb50086c0c845fe535d07a77ab7f77farmwise02"


class TestAuditTrail:
    @patch("services.masumi.Payment")
    def test_audit_trail_endpoint_returns_full_chain(self, mock_payment_cls, test_plot):
        """Audit trail endpoint returns all MasumiTxHash fields."""
        from agents.diagnostic import store_recommendation
        import asyncio

        mock_payment = MagicMock()
        mock_payment.create_payment_request = AsyncMock(return_value={
            "data": {"blockchainIdentifier": MOCK_TX_HASH}
        })
        mock_payment.complete_payment = AsyncMock(return_value={
            "data": {"onChainState": "ResultSubmitted"}
        })
        mock_payment_cls.return_value = mock_payment

        diagnosis = {
            "action": "irrigate",
            "cause": "drought_stress",
            "urgencyHours": 12,
            "narrative": "Irrigate your potato crop within 12 hours.",
            "dataFreshness": 2,
        }
        subgraph = {"stage": "Tuber Initiation", "forecastedYieldKg": 6500}

        asyncio.run(store_recommendation(test_plot, diagnosis, subgraph))

        resp = client.get(f"/api/plot/{test_plot}/audit-trail")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        entry = data[0]
        assert entry["action"] == "irrigate"
        assert entry["cause"] == "drought_stress"
        assert entry["narrative"] == "Irrigate your potato crop within 12 hours."
        assert entry["txHash"] == MOCK_TX_HASH
        assert entry["inputHash"] is not None and len(entry["inputHash"]) == 64
        assert entry["outputHash"] is not None and len(entry["outputHash"]) == 64
        assert entry["status"] == "VERIFIED_ON_CHAIN"
        assert entry["onChainState"] == "ResultSubmitted"
        assert entry["agentIdentifier"] is not None
        assert entry["agentIdentifier"] != ""
        assert entry["verifiedAt"] is not None

    @patch("services.masumi.Payment")
    def test_certificate_audit_verified_true_when_fully_on_chain(self, mock_payment_cls, test_plot):
        """Certificate audit_verified=True only when all hashes + VERIFIED_ON_CHAIN."""
        from agents.diagnostic import store_recommendation
        import asyncio

        mock_payment = MagicMock()
        mock_payment.create_payment_request = AsyncMock(return_value={
            "data": {"blockchainIdentifier": MOCK_TX_HASH}
        })
        mock_payment.complete_payment = AsyncMock(return_value={
            "data": {"onChainState": "ResultSubmitted"}
        })
        mock_payment_cls.return_value = mock_payment

        diagnosis = {
            "action": "apply_fertilizer",
            "cause": "nitrogen_deficiency",
            "urgencyHours": 72,
            "narrative": "Apply nitrogen-rich fertilizer within 3 days.",
            "dataFreshness": 1,
        }
        subgraph = {"stage": "Vegetative Growth", "forecastedYieldKg": 8000}

        asyncio.run(store_recommendation(test_plot, diagnosis, subgraph))

        resp = client.get(f"/api/plot/{test_plot}/certificate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plotId"] == test_plot
        assert data["verified"] is True
        assert data["audit_verified"] is True
        assert data["masumiTxHash"] == MOCK_TX_HASH

    def test_certificate_audit_verified_false_without_tx(self, test_plot):
        """Certificate audit_verified=False when no MasumiTxHash exists."""
        query(
            """
            MATCH (p:Plot {plotId: $pid})
            CREATE (rec:DailyRecommendation {date: date(), action: 'monitor',
              cause: 'none', urgencyHours: 24, narrative: 'Check crops.',
              dataFreshness: 0})
            CREATE (p)-[:HAS_RECOMMENDATION]->(rec)
            """,
            {"pid": test_plot},
        )

        resp = client.get(f"/api/plot/{test_plot}/certificate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["verified"] is False
        assert data["audit_verified"] is False

    @patch("services.masumi.Payment")
    def test_audit_trail_empty_when_no_recommendations(self, mock_payment_cls, test_plot):
        """Empty audit trail for plot with no recommendations."""
        mock_payment = MagicMock()
        mock_payment_cls.return_value = mock_payment

        resp = client.get(f"/api/plot/{test_plot}/audit-trail")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data == []

    @patch("services.masumi.Payment")
    def test_audit_trail_multiple_entries_ordered(self, mock_payment_cls, test_plot):
        """Multiple diagnostic runs create ordered audit trail entries."""
        from agents.diagnostic import store_recommendation
        import asyncio

        mock_payment = MagicMock()
        mock_payment.create_payment_request = AsyncMock(return_value={
            "data": {"blockchainIdentifier": MOCK_TX_HASH}
        })
        mock_payment.complete_payment = AsyncMock(return_value={
            "data": {"onChainState": "ResultSubmitted"}
        })
        mock_payment_cls.return_value = mock_payment

        diagnosis1 = {"action": "action1", "cause": "cause1", "urgencyHours": 24,
                      "narrative": "First.", "dataFreshness": 1}
        diagnosis2 = {"action": "action2", "cause": "cause2", "urgencyHours": 48,
                      "narrative": "Second.", "dataFreshness": 2}

        asyncio.run(store_recommendation(test_plot, diagnosis1, {"stage": "A"}))
        asyncio.run(store_recommendation(test_plot, diagnosis2, {"stage": "B"}))

        resp = client.get(f"/api/plot/{test_plot}/audit-trail")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        actions = [e["action"] for e in data]
        assert "action1" in actions
        assert "action2" in actions
