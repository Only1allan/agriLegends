"""Tests for the potato news agent (LLM summarization)."""
import pytest
from agents.potato_news import summarize_bulletin, ingest_news
from services.neo4j import query


@pytest.mark.ingestion
class TestPotatoNews:
    async def test_summarize_bulletin(self, respx_mock):
        respx_mock.post("https://api.featherless.ai/v1/chat/completions").respond(
            json={
                "choices": [{
                    "message": {
                        "content": '{"headline": "Late blight warning Nyandarua", "threats": ["late_blight"], "urgency": "high", "action": "spray_fungicide"}',
                    },
                }],
            },
        )
        result = await summarize_bulletin(
            "Late blight reported in Nyandarua.", "Nyandarua"
        )
        assert result["urgency"] == "high"
        assert "late_blight" in result["threats"]

    async def test_ingest_news_creates_news_alert(self, respx_mock, test_county):
        respx_mock.post("https://api.featherless.ai/v1/chat/completions").respond(
            json={
                "choices": [{
                    "message": {
                        "content": '{"headline": "Test alert", "threats": ["aphids"], "urgency": "medium", "action": "monitor"}',
                    },
                }],
            },
        )
        await ingest_news(test_county, "Aphid warning.")
        result = query(
            "MATCH (c:County {name: $name})<-[:RELEVANT_TO]-(na:NewsAlert) "
            "RETURN count(na) AS cnt",
            {"name": test_county},
        )
        assert result[0]["cnt"] >= 1
