"""
Background scheduler: runs ingestion cycle every 6 hours for all registered plots.
"""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.neo4j import query

logger = logging.getLogger("farmwise.scheduler")


async def daily_ingestion_cycle():
    plots = query(
        """
        MATCH (p:Plot)
        RETURN p.plotId AS plotId, p.latitude AS latitude, p.longitude AS longitude,
               p.agromonitoringPolygonId AS agromonitoringPolygonId, p.name AS name
        """
    )
    logger.info("Daily ingestion cycle: %d plots found", len(plots))

    for plot in plots:
        plot_id = plot["plotId"]
        try:
            if plot.get("agromonitoringPolygonId"):
                from agents.weather import ingest_weather
                from agents.satellite import ingest_satellite, detect_stress
                from agents.gdd import ingest_gdd, advance_growth_stage
                from agents.diagnostic import run_diagnostic

                await ingest_weather(plot["latitude"], plot["longitude"], plot_id)
                await ingest_satellite(plot["agromonitoringPolygonId"], plot_id)
                await ingest_gdd(plot["agromonitoringPolygonId"], plot_id)
                await advance_growth_stage(plot_id)
                await detect_stress(plot_id)
                await run_diagnostic(plot_id)
                logger.info("Ingestion cycle complete for plot %s", plot_id)
        except Exception:
            logger.exception("Ingestion cycle failed for plot %s", plot_id)
            continue


scheduler = AsyncIOScheduler()


def start_scheduler():
    scheduler.add_job(
        daily_ingestion_cycle,
        "interval",
        hours=6,
        id="daily_ingestion",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started: daily ingestion cycle every 6 hours")


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")
