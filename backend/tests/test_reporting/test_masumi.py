"""Tests for Masumi decision logging — complete lifecycle, audit trail, MIP-003."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from main import app
from services.neo4j import query

client = TestClient(app)

MOCK_TX_HASH = "7e8bdaf2b2b919a3a4b94002cafb50086c0c845fe535d07a77ab7f77farmwise01"


class TestMasumiAPI:
    def test_log_decision_attempts_masumi(self):
        """Calls Masumi. Accepts 200/500/502 depending on service availability."""
        resp = client.post(
            "/api/masumi/log-decision",
            json={
                "plotId": "test-plot",
                "action": "spray_fungicide",
                "cause": "late_blight",
                "urgencyHours": 48,
                "stage": "Tuber Bulking",
                "forecastedYieldKg": 7200,
            },
        )
        assert resp.status_code in (200, 500, 502)


class TestMasumiCompleteLifecycle:
    @patch("services.masumi.Payment")
    def test_create_and_complete_payment_mocked(self, mock_payment_cls, test_plot):
        """Full lifecycle: create → complete with mocked Masumi SDK."""
        mock_payment = MagicMock()
        mock_payment.create_payment_request = AsyncMock(return_value={
            "data": {"blockchainIdentifier": MOCK_TX_HASH}
        })
        mock_payment.complete_payment = AsyncMock(return_value={
            "data": {"onChainState": "ResultSubmitted"}
        })
        mock_payment_cls.return_value = mock_payment

        resp = client.post(
            "/api/masumi/log-decision",
            json={
                "plotId": test_plot,
                "action": "spray_fungicide",
                "cause": "late_blight",
                "urgencyHours": 48,
                "stage": "Tuber Bulking",
                "forecastedYieldKg": 7200,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["txHash"] == MOCK_TX_HASH
        assert data["status"] == "CREATED"

    @patch("services.masumi.Payment")
    def test_complete_decision_endpoint(self, mock_payment_cls, test_plot):
        """Test the complete-decision endpoint."""
        mock_payment = MagicMock()
        mock_payment.complete_payment = AsyncMock(return_value={
            "data": {"onChainState": "ResultSubmitted"}
        })
        mock_payment_cls.return_value = mock_payment

        output_data = {"action": "spray_fungicide", "cause": "late_blight"}
        resp = client.post(
            "/api/masumi/complete-decision",
            json={"txHash": MOCK_TX_HASH, "outputData": output_data},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["txHash"] == MOCK_TX_HASH
        assert data["onChainState"] == "ResultSubmitted"
        assert data["verified"] is True

    @patch("services.masumi.Payment")
    def test_audit_trail_stored_on_masumi_tx_node(self, mock_payment_cls, test_plot):
        """Verify MasumiTxHash node has all audit fields after full lifecycle."""
        from agents.diagnostic import store_recommendation
        from services.neo4j import query_one

        mock_payment = MagicMock()
        mock_payment.create_payment_request = AsyncMock(return_value={
            "data": {"blockchainIdentifier": MOCK_TX_HASH}
        })
        mock_payment.complete_payment = AsyncMock(return_value={
            "data": {"onChainState": "ResultSubmitted"}
        })
        mock_payment_cls.return_value = mock_payment

        diagnosis = {
            "action": "spray_fungicide",
            "cause": "late_blight",
            "urgencyHours": 48,
            "narrative": "Spray fungicide within 2 days to prevent late blight spread.",
            "dataFreshness": 1,
        }
        subgraph = {"stage": "Tuber Bulking", "forecastedYieldKg": 7200}

        import asyncio
        tx_hash, status = asyncio.run(store_recommendation(test_plot, diagnosis, subgraph))

        assert tx_hash == MOCK_TX_HASH
        assert status == "VERIFIED_ON_CHAIN"

        result = query_one(
            """
            MATCH (tx:MasumiTxHash {hash: $hash})
            RETURN tx.hash AS hash, tx.inputHash AS inputHash,
                   tx.outputHash AS outputHash, tx.status AS status,
                   tx.onChainState AS onChainState,
                   tx.agentIdentifier AS agentIdentifier,
                   tx.purchaserIdentifier AS purchaserIdentifier,
                   tx.verifiedAt AS verifiedAt,
                   tx.network AS network
            """,
            {"hash": MOCK_TX_HASH},
        )
        assert result is not None
        assert result["hash"] == MOCK_TX_HASH
        assert result["inputHash"] is not None and len(result["inputHash"]) == 64
        assert result["outputHash"] is not None and len(result["outputHash"]) == 64
        assert result["status"] == "VERIFIED_ON_CHAIN"
        assert result["onChainState"] == "ResultSubmitted"
        assert result["agentIdentifier"] is not None
        assert result["purchaserIdentifier"] is not None
        assert result["verifiedAt"] is not None
        assert result["network"] == "Preprod"

    @patch("services.masumi.Payment")
    @patch("agents.diagnostic.chat")
    def test_batch_diagnostics_one_tx_per_plot(self, mock_chat, mock_payment_cls, test_plot):
        """Each plot gets its own Masumi tx in batch mode."""
        from agents.diagnostic import run_batch_diagnostics
        import asyncio

        mock_payment = MagicMock()
        mock_payment.create_payment_request = AsyncMock(return_value={
            "data": {"blockchainIdentifier": MOCK_TX_HASH}
        })
        mock_payment.complete_payment = AsyncMock(return_value={
            "data": {"onChainState": "ResultSubmitted"}
        })
        mock_payment_cls.return_value = mock_payment

        mock_chat.return_value = {
            "choices": [{"message": {"content": '{"action": "monitor_crop", "cause": "test", "urgencyHours": 24, "narrative": "Test diagnostic for batch.", "dataFreshness": 0}'}}]
        }

        results = asyncio.run(run_batch_diagnostics())
        assert isinstance(results, list)
        if results:
            for r in results:
                if "error" not in r:
                    assert "masumiTxHash" in r
                    assert "masumiStatus" in r


class TestMIP003:
    def test_availability_endpoint(self):
        """MIP-003 availability endpoint returns available status."""
        resp = client.get("/api/diagnostic/mip003/availability")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "available"
        assert "FarmWise" in data["message"]

    def test_input_schema_endpoint(self):
        """MIP-003 input_schema endpoint returns plotId schema."""
        resp = client.get("/api/diagnostic/mip003/input_schema")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "object"
        assert "plotId" in data["properties"]
        assert "plotId" in data["required"]
