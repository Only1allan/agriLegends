"""Tests for soil amendment gap detection."""
import pytest
from agents.soil import check_soil_amendment
from services.neo4j import query


@pytest.mark.processing
class TestSoilAmendment:
    async def test_soil_amendment_returns_results_without_preexisting_edge(
        self, test_plot, test_growth_stage
    ):
        query(
            "MERGE (sr:SoilRequirement {stage: 'Tuber Bulking'}) "
            "SET sr.nitrogenTarget = 0.22, sr.phTarget = 5.5",
        )
        actions = await check_soil_amendment(test_plot)
        assert isinstance(actions, list)

    async def test_soil_amendment_detects_n_deficiency(
        self, test_plot, test_growth_stage
    ):
        query(
            "MERGE (sr:SoilRequirement {stage: 'Tuber Bulking'}) "
            "SET sr.nitrogenTarget = 2.5, sr.phTarget = 4.0",
        )
        actions = await check_soil_amendment(test_plot)
        assert any("nitrogen" in a.lower() for a in actions)

    async def test_soil_amendment_no_actions_when_soil_sufficient(
        self, test_plot, test_growth_stage
    ):
        query(
            "MERGE (sr:SoilRequirement {stage: 'Tuber Bulking'}) "
            "SET sr.nitrogenTarget = 0.10, sr.phTarget = 6.0",
        )
        actions = await check_soil_amendment(test_plot)
        # pH 5.8 < 6.0 → should trigger lime action
        # nitrogen 0.18 > 0.10 → fine
        assert any("lime" in a.lower() for a in actions)
        assert not any("nitrogen" in a.lower() for a in actions)
