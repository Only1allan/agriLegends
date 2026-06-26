"""Tests for embedding infrastructure."""
import pytest
from services.neo4j import create_vector_index
from services.featherless import get_embedding


@pytest.mark.ingestion
class TestEmbeddings:
    def test_vector_index_creation(self):
        result = create_vector_index("plot_embedding", 1536)
        assert result is True

    async def test_embedding_generation(self, respx_mock):
        respx_mock.post("https://api.featherless.ai/v1/chat/completions").respond(
            json={
                "choices": [{
                    "message": {
                        "content": "[0.1,0.2,0.3]",
                    },
                }],
            },
        )
        result = await get_embedding("test text")
        assert result == [0.1, 0.2, 0.3]

    async def test_embedding_generation_invalid_response(self, respx_mock):
        respx_mock.post("https://api.featherless.ai/v1/chat/completions").respond(
            json={
                "choices": [{
                    "message": {
                        "content": "not an array",
                    },
                }],
            },
        )
        result = await get_embedding("test text")
        assert result is None
