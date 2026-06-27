"""
Background scheduler: 3-pipeline nightly cycle for FarmWise.
Pipeline A: 00:00 UTC — Telemetry ingestion
Pipeline B: 00:05 UTC — Risk evaluation
Pipeline C: 03:30 UTC — Alert dispatch (06:30 EAT)
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pipelines.pipeline_a_ingestion import run_pipeline_a
from pipelines.pipeline_b_evaluation import run_pipeline_b
from pipelines.pipeline_c_dispatcher import run_pipeline_c

logger = logging.getLogger("farmwise.scheduler")

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler():
    scheduler.add_job(
        run_pipeline_a, "cron", hour=0, minute=0,
        id="pipeline_a", replace_existing=True, max_instances=1,
    )
    scheduler.add_job(
        run_pipeline_b, "cron", hour=0, minute=5,
        id="pipeline_b", replace_existing=True, max_instances=1,
    )
    scheduler.add_job(
        run_pipeline_c, "cron", hour=3, minute=30,
        id="pipeline_c", replace_existing=True, max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started: Pipeline A 00:00, B 00:05, C 03:30 UTC")


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")
