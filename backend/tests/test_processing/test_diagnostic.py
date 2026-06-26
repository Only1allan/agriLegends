"""Tests for the GraphRAG diagnostic pipeline."""
import pytest
from agents.diagnostic import extract_subgraph, run_pest_diagnosis


@pytest.mark.processing
class TestDiagnosticPipeline:
    async def test_extract_subgraph_empty(self, test_plot):
        result = await extract_subgraph(test_plot)
        assert isinstance(result, dict)

    async def test_extract_subgraph_with_observations(
        self, test_plot, test_growth_stage, test_observation_satellite,
    ):
        result = await extract_subgraph(test_plot)
        assert result.get("stage") is not None
        assert isinstance(result.get("todayObservations"), list)

    async def test_run_pest_diagnosis(
        self, test_plot, test_growth_stage, test_observation_weather,
    ):
        result = await run_pest_diagnosis(test_plot)
        assert isinstance(result, list)
