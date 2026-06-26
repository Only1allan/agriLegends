"""Tests for the daily ingestion scheduler."""
import pytest
from unittest.mock import patch, AsyncMock
from scheduler import daily_ingestion_cycle


@pytest.mark.ingestion
class TestScheduler:
    def test_scheduler_iterates_all_plots(self, test_plot):
        with patch("agents.weather.ingest_weather", new_callable=AsyncMock) as m_w, \
             patch("agents.satellite.ingest_satellite", new_callable=AsyncMock) as m_s, \
             patch("agents.satellite.detect_stress", new_callable=AsyncMock) as m_ds, \
             patch("agents.gdd.ingest_gdd", new_callable=AsyncMock) as m_g, \
             patch("agents.gdd.advance_growth_stage", new_callable=AsyncMock) as m_gs, \
             patch("agents.diagnostic.run_diagnostic", new_callable=AsyncMock) as m_diag:
            import asyncio
            asyncio.run(daily_ingestion_cycle())

            assert m_w.called
            assert m_s.called
            assert m_g.called
            assert m_gs.called
            assert m_ds.called
            assert m_diag.called

    def test_scheduler_skips_plots_without_polygon(self, test_plot):
        from services.neo4j import query
        query(
            "MATCH (p:Plot {plotId: $pid}) SET p.agromonitoringPolygonId = ''",
            {"pid": test_plot},
        )

        with patch("agents.weather.ingest_weather", new_callable=AsyncMock) as m_w, \
             patch("agents.satellite.ingest_satellite", new_callable=AsyncMock) as m_s:
            import asyncio
            asyncio.run(daily_ingestion_cycle())

            my_plot_calls_w = [
                c for c in m_w.call_args_list
                if c.args and len(c.args) >= 3 and c.args[2] == test_plot
            ]
            my_plot_calls_s = [
                c for c in m_s.call_args_list
                if c.args and len(c.args) >= 2 and c.args[1] == test_plot
            ]
            assert len(my_plot_calls_w) == 0, f"Expected weather not called for {test_plot}"
            assert len(my_plot_calls_s) == 0, f"Expected satellite not called for {test_plot}"

    def test_scheduler_continues_after_agent_failure(self, test_plot):
        from services.neo4j import query
        query(
            "MATCH (p:Plot {plotId: $pid}) SET p.agromonitoringPolygonId = 'poly-test'",
            {"pid": test_plot},
        )

        call_count = {"weather": 0}

        async def failing_weather(*args, **kwargs):
            call_count["weather"] += 1
            raise Exception("Weather API down")

        with patch("agents.weather.ingest_weather", new=failing_weather), \
             patch("agents.satellite.ingest_satellite", new_callable=AsyncMock), \
             patch("agents.satellite.detect_stress", new_callable=AsyncMock), \
             patch("agents.gdd.ingest_gdd", new_callable=AsyncMock), \
             patch("agents.gdd.advance_growth_stage", new_callable=AsyncMock), \
             patch("agents.diagnostic.run_diagnostic", new_callable=AsyncMock):
            import asyncio
            asyncio.run(daily_ingestion_cycle())

            assert call_count["weather"] > 0
