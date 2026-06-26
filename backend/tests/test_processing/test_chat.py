"""Tests for the dynamic GraphRAG chat agent."""
import json
from unittest.mock import patch, AsyncMock
import pytest
from agents.chat_agent import (
    chat_query,
    _sanitize_cypher,
    _get_plot_id,
    _check_day_one,
    CONVERSATION_BUFFER,
)


class TestSanitizeCypher:
    def test_valid_read_query(self):
        result = _sanitize_cypher(
            "MATCH (p:Plot {plotId: $plot_id}) RETURN p.name"
        )
        assert result is not None
        assert "MATCH" in result

    def test_strips_markdown_fences(self):
        result = _sanitize_cypher(
            "```cypher\nMATCH (p:Plot {plotId: $plot_id}) RETURN p\n```"
        )
        assert result == "MATCH (p:Plot {plotId: $plot_id}) RETURN p"

    def test_rejects_create(self):
        assert _sanitize_cypher("CREATE (n:Node) RETURN n") is None

    def test_rejects_delete(self):
        assert _sanitize_cypher("MATCH (n) DELETE n") is None

    def test_rejects_set(self):
        assert _sanitize_cypher("MATCH (n) SET n.x = 1 RETURN n") is None

    def test_rejects_merge(self):
        assert _sanitize_cypher("MERGE (n:Node) RETURN n") is None

    def test_rejects_detach(self):
        assert _sanitize_cypher("MATCH (n) DETACH DELETE n") is None

    def test_rejects_empty(self):
        assert _sanitize_cypher("") is None

    def test_rejects_none(self):
        assert _sanitize_cypher(None) is None

    def test_rejects_no_return(self):
        assert _sanitize_cypher("MATCH (n)") is None

    def test_accepts_multi_match(self):
        result = _sanitize_cypher(
            "MATCH (p:Plot)-[:AT_STAGE]->(gs) MATCH (p)-[:HAS_OBSERVATION]->(obs) RETURN gs.name, obs.ndvi"
        )
        assert result is not None


class TestGetPlotId:
    def test_returns_none_for_unknown_farmer(self):
        result = _get_plot_id("nonexistent-farmer-xyz-12345")
        assert result is None


class TestCheckDayOne:
    def test_empty_subgraph_is_day_one(self):
        assert _check_day_one({}) is True

    def test_no_observations_is_day_one(self):
        assert _check_day_one({"todayObservations": []}) is True

    def test_with_observations_not_day_one(self):
        assert (
            _check_day_one({"todayObservations": [{"ndvi": 0.72}]}) is False
        )


class TestConversationBuffer:
    def test_buffer_stores_messages(self):
        fid = "test-buffer-farmer"
        CONVERSATION_BUFFER.clear()
        CONVERSATION_BUFFER[fid] = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        assert len(CONVERSATION_BUFFER[fid]) == 2

    @pytest.mark.asyncio
    async def test_buffer_caps_at_max(self, test_farmer_with_plot):
        fid = test_farmer_with_plot
        from agents.chat_agent import MAX_HISTORY
        CONVERSATION_BUFFER.clear()
        CONVERSATION_BUFFER[fid] = [
            {"role": "user", "content": "overflow"} for _ in range(MAX_HISTORY + 5)
        ]
        with patch(
            "agents.chat_agent._classify_intent", new_callable=AsyncMock
        ) as mock_intent, patch(
            "agents.chat_agent.extract_subgraph", new_callable=AsyncMock
        ) as mock_subgraph, patch(
            "agents.chat_agent.run_pest_diagnosis", new_callable=AsyncMock
        ) as mock_pest, patch(
            "agents.chat_agent._synthesize_answer", new_callable=AsyncMock
        ) as mock_synth:
            mock_intent.return_value = {"intent": "general", "cypher": None}
            mock_subgraph.return_value = {}
            mock_pest.return_value = []
            mock_synth.return_value = {"answer": "ok", "confidence": "medium"}
            await chat_query(fid, "test")
        assert len(CONVERSATION_BUFFER.get(fid, [])) <= MAX_HISTORY


@pytest.mark.processing
class TestChatQuery:
    @pytest.mark.asyncio
    async def test_chat_with_no_farmer_returns_honest_message(self, unique_id):
        fid = f"nonexistent-{unique_id[:8]}"
        result = await chat_query(fid, "What growth stage am I in?")
        assert "answer" in result
        assert result["confidence"] == "low"
        assert "registered" in result["answer"].lower() or "don't see" in result["answer"].lower()

    @pytest.mark.asyncio
    async def test_chat_swahili_input_accepted(self, test_farmer_with_plot, unique_id):
        with patch("agents.chat_agent._classify_intent", new_callable=AsyncMock) as mock_intent, \
             patch("agents.chat_agent.extract_subgraph", new_callable=AsyncMock) as mock_subgraph, \
             patch("agents.chat_agent.run_pest_diagnosis", new_callable=AsyncMock) as mock_pest, \
             patch("agents.chat_agent._synthesize_answer", new_callable=AsyncMock) as mock_synth:
            mock_intent.return_value = {"intent": "general", "cypher": None}
            mock_subgraph.return_value = {}
            mock_pest.return_value = []
            mock_synth.return_value = {
                "answer": "Habari! Karibu FarmWise.",
                "confidence": "medium",
            }
            result = await chat_query(test_farmer_with_plot, "Habari, shamba langu likoje?")
            assert "answer" in result
            assert isinstance(result["answer"], str)
            assert result["confidence"] in ("high", "medium", "low")

    @pytest.mark.asyncio
    async def test_chat_extracts_subgraph_when_called(self, test_farmer_with_plot, unique_id):
        with patch("agents.chat_agent._classify_intent", new_callable=AsyncMock) as mock_intent, \
             patch("agents.chat_agent.extract_subgraph", new_callable=AsyncMock) as mock_subgraph, \
             patch("agents.chat_agent.run_pest_diagnosis", new_callable=AsyncMock) as mock_pest, \
             patch("agents.chat_agent._synthesize_answer", new_callable=AsyncMock) as mock_synth:
            mock_intent.return_value = {"intent": "ndvi", "cypher": None}
            mock_subgraph.return_value = {
                "plot": {"plotId": "test-123", "name": "Test"},
                "stage": "Tuber Bulking",
                "todayObservations": [{"ndvi": 0.72}],
            }
            mock_pest.return_value = []
            mock_synth.return_value = {
                "answer": "Your NDVI is 0.72, healthy.",
                "confidence": "high",
            }
            result = await chat_query(test_farmer_with_plot, "What is my NDVI?")
            mock_subgraph.assert_called_once()
            mock_synth.assert_called_once()
            assert "answer" in result
            assert result["confidence"] == "high"

    @pytest.mark.asyncio
    async def test_chat_runs_pest_diagnosis(self, test_farmer_with_plot, unique_id):
        with patch("agents.chat_agent._classify_intent", new_callable=AsyncMock) as mock_intent, \
             patch("agents.chat_agent.extract_subgraph", new_callable=AsyncMock) as mock_subgraph, \
             patch("agents.chat_agent.run_pest_diagnosis", new_callable=AsyncMock) as mock_pest, \
             patch("agents.chat_agent._synthesize_answer", new_callable=AsyncMock) as mock_synth:
            mock_intent.return_value = {"intent": "pest", "cypher": None}
            mock_subgraph.return_value = {}
            mock_pest.return_value = [{"cause": "Late Blight", "action": "spray_fungicide"}]
            mock_synth.return_value = {
                "answer": "Late Blight risk detected.",
                "confidence": "high",
            }
            result = await chat_query(test_farmer_with_plot, "What pests threaten my farm?")
            mock_pest.assert_called_once()
            assert "answer" in result

    @pytest.mark.asyncio
    async def test_chat_dynamic_cypher_generated_and_executed(
        self, test_farmer_with_plot, unique_id,
    ):
        cypher = "MATCH (p:Plot {plotId: $plot_id}) RETURN p.variety AS variety, p.forecastedYieldKg AS yield"

        def query_side_effect(cypher_text, params=None):
            if params and "fid" in params:
                return [{"pid": test_farmer_with_plot}]
            return [{"variety": "Shangi", "yield": 7200}]

        with patch("agents.chat_agent._classify_intent", new_callable=AsyncMock) as mock_intent, \
             patch("agents.chat_agent.extract_subgraph", new_callable=AsyncMock) as mock_subgraph, \
             patch("agents.chat_agent.run_pest_diagnosis", new_callable=AsyncMock) as mock_pest, \
             patch("agents.chat_agent._synthesize_answer", new_callable=AsyncMock) as mock_synth, \
             patch("agents.chat_agent.query", side_effect=query_side_effect):
            mock_intent.return_value = {"intent": "yield", "cypher": cypher}
            mock_subgraph.return_value = {}
            mock_pest.return_value = []
            mock_synth.return_value = {
                "answer": "Your Shangi plot is forecasted to yield 7200 kg.",
                "confidence": "high",
            }
            result = await chat_query(test_farmer_with_plot, "What is my yield forecast?")
            assert result["cypher"] == cypher
            assert "answer" in result

    @pytest.mark.asyncio
    async def test_chat_empty_graph_honest_message(self, test_farmer_with_plot, unique_id):
        with patch("agents.chat_agent._classify_intent", new_callable=AsyncMock) as mock_intent, \
             patch("agents.chat_agent.extract_subgraph", new_callable=AsyncMock) as mock_subgraph, \
             patch("agents.chat_agent.run_pest_diagnosis", new_callable=AsyncMock) as mock_pest, \
             patch("agents.chat_agent._synthesize_answer", new_callable=AsyncMock) as mock_synth:
            mock_intent.return_value = {"intent": "ndvi", "cypher": None}
            mock_subgraph.return_value = {}
            mock_pest.return_value = []
            mock_synth.return_value = {
                "answer": "No NDVI data available yet. Satellite readings take 3-5 days.",
                "confidence": "low",
            }
            result = await chat_query(test_farmer_with_plot, "Show me NDVI data")
            mock_subgraph.assert_called_once()
            assert "answer" in result
            assert result["confidence"] == "low"

    @pytest.mark.asyncio
    async def test_chat_multi_turn_context_passed(self, test_farmer_with_plot, unique_id):
        CONVERSATION_BUFFER.clear()
        with patch("agents.chat_agent._classify_intent", new_callable=AsyncMock) as mock_intent, \
             patch("agents.chat_agent.extract_subgraph", new_callable=AsyncMock) as mock_subgraph, \
             patch("agents.chat_agent.run_pest_diagnosis", new_callable=AsyncMock) as mock_pest, \
             patch("agents.chat_agent._synthesize_answer", new_callable=AsyncMock) as mock_synth:
            mock_intent.return_value = {"intent": "general", "cypher": None}
            mock_subgraph.return_value = {
                "plot": {"plotId": "test", "name": "Farm"},
                "stage": "Tuber Bulking",
                "todayObservations": [{"ndvi": 0.72, "tempMax": 24}],
            }
            mock_pest.return_value = []
            mock_synth.return_value = {
                "answer": "Your crop is at Tuber Bulking.",
                "confidence": "high",
            }

            # First turn
            result1 = await chat_query(test_farmer_with_plot, "What stage?")
            assert result1["answer"] == "Your crop is at Tuber Bulking."

            # Second turn should include history
            mock_synth.return_value = {
                "answer": "As I mentioned, Tuber Bulking.",
                "confidence": "high",
            }
            result2 = await chat_query(test_farmer_with_plot, "Tell me again?")
            # Verify history was passed to synthesize
            history_arg = mock_synth.call_args[1].get("history")
            assert history_arg is not None
            assert len(history_arg) >= 1

    @pytest.mark.asyncio
    async def test_chat_day_one_honesty_no_fabrication(
        self, test_farmer_with_plot, unique_id,
    ):
        with patch("agents.chat_agent._classify_intent", new_callable=AsyncMock) as mock_intent, \
             patch("agents.chat_agent.extract_subgraph", new_callable=AsyncMock) as mock_subgraph, \
             patch("agents.chat_agent.run_pest_diagnosis", new_callable=AsyncMock) as mock_pest:
            mock_intent.return_value = {"intent": "recommendation", "cypher": None}
            mock_subgraph.return_value = {
                "plot": {
                    "plotId": "test-xyz",
                    "name": "New Plot",
                    "variety": "Shangi",
                    "seasonDay": 1,
                    "soilBaseline_pH": 5.8,
                    "soilBaseline_N": 0.18,
                },
                "todayObservations": [],
            }
            mock_pest.return_value = []

            result = await chat_query(test_farmer_with_plot, "What should I do today?")

            assert "answer" in result
            answer_lower = result["answer"].lower()
            assert "day 1" in answer_lower
            assert result["confidence"] == "low"

    @pytest.mark.asyncio
    async def test_chat_real_neo4j_data_in_results(
        self, test_farmer_with_plot, test_plot, test_growth_stage,
        test_observation_satellite,
    ):
        with patch("agents.chat_agent._classify_intent", new_callable=AsyncMock) as mock_intent, \
             patch("agents.chat_agent._synthesize_answer", new_callable=AsyncMock) as mock_synth:
            mock_intent.return_value = {"intent": "ndvi", "cypher": None}
            mock_synth.return_value = {
                "answer": "Your latest NDVI is 0.72 — the crop is healthy.",
                "confidence": "high",
            }
            result = await chat_query(test_farmer_with_plot, "Show my NDVI")
            assert result["results"] is not None
            assert result["confidence"] == "high"

    @pytest.mark.asyncio
    async def test_chat_returns_confidence_field(self, test_farmer_with_plot, unique_id):
        with patch("agents.chat_agent._classify_intent", new_callable=AsyncMock) as mock_intent, \
             patch("agents.chat_agent.extract_subgraph", new_callable=AsyncMock) as mock_subgraph, \
             patch("agents.chat_agent.run_pest_diagnosis", new_callable=AsyncMock) as mock_pest, \
             patch("agents.chat_agent._synthesize_answer", new_callable=AsyncMock) as mock_synth:
            mock_intent.return_value = {"intent": "general", "cypher": None}
            mock_subgraph.return_value = {}
            mock_pest.return_value = []
            mock_synth.return_value = {"answer": "Hello!", "confidence": "medium"}
            result = await chat_query(test_farmer_with_plot, "Hello")
            assert "confidence" in result
            assert result["confidence"] in ("high", "medium", "low")
