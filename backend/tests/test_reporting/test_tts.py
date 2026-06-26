"""Tests for TTS/translation API."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.mark.reporting
class TestTTSAPI:
    async def test_translate_to_swahili(self, respx_mock):
        respx_mock.post("https://api.featherless.ai/v1/chat/completions").respond(
            json={
                "choices": [{
                    "message": {
                        "content": "Paka dawa ya kuvu ndani ya masaa 48.",
                    },
                }],
            },
        )
        from agents.tts import translate_to_swahili
        result = await translate_to_swahili("Apply fungicide within 48 hours.")
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_generate_swahili_audio(self, respx_mock):
        respx_mock.post("https://api.featherless.ai/v1/chat/completions").respond(
            json={
                "choices": [{
                    "message": {
                        "content": "Paka dawa ya kuvu.",
                    },
                }],
            },
        )
        from agents.tts import generate_swahili_audio
        result = await generate_swahili_audio("Apply fungicide.")
        assert "swahiliText" in result
        assert result["audioUrl"] is None
