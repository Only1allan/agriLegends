"""Tests for the ground truth agent (VLM image classification)."""
import pytest
from agents.ground_truth import classify_farmer_image, ingest_ground_truth
from services.neo4j import query


@pytest.mark.ingestion
class TestGroundTruth:
    async def test_classify_farmer_image(self, respx_mock):
        respx_mock.post("https://api.featherless.ai/v1/chat/completions").respond(
            json={
                "choices": [{
                    "message": {
                        "content": '{"classification": "late_blight", "confidence": 0.92, "notes": "Leaf lesions visible"}',
                    },
                }],
            },
        )
        result = await classify_farmer_image(
            "https://example.com/potato.jpg", "Wilting leaves"
        )
        assert result["classification"] == "late_blight"
        assert result["confidence"] == 0.92

    async def test_ingest_ground_truth_creates_farmer_log(self, respx_mock, test_farmer, test_plot):
        respx_mock.post("https://api.featherless.ai/v1/chat/completions").respond(
            json={
                "choices": [{
                    "message": {
                        "content": '{"classification": "healthy", "confidence": 0.85, "notes": "Crop looks good"}',
                    },
                }],
            },
        )
        await ingest_ground_truth(
            test_farmer, test_plot,
            "https://example.com/potato.jpg",
        )
        result = query(
            "MATCH (p:Plot {plotId: $pid})-[:HAS_OBSERVATION]->"
            "(log:FarmerLog) RETURN count(log) AS cnt",
            {"pid": test_plot},
        )
        assert result[0]["cnt"] >= 1

    async def test_farmer_log_has_log_relationship(self, respx_mock, test_farmer, test_plot):
        respx_mock.post("https://api.featherless.ai/v1/chat/completions").respond(
            json={
                "choices": [{
                    "message": {
                        "content": '{"classification": "late_blight", "confidence": 0.90, "notes": "Dark spots on leaves"}',
                    },
                }],
            },
        )
        await ingest_ground_truth(
            test_farmer, test_plot,
            "https://example.com/spots.jpg",
            "Dark spots",
        )
        result = query(
            "MATCH (f:Farmer {farmerId: $fid})-[:HAS_LOG]->"
            "(log:FarmerLog) RETURN count(log) AS cnt",
            {"fid": test_farmer},
        )
        assert result[0]["cnt"] >= 1
