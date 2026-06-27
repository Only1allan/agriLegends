from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from routers import (
    auth, farmer, plot, diagnostic, masumi, masumi_mip003,
    twilio_webhook, tts, chat, demo, ground_truth,
    plots, seasons, snapshots, alerts, observations,
    interventions, expenses, sales, forecasts, stakeholder,
    soil_pests, certificate,
)
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.neo4j import apply_constraints
    await apply_constraints()
    from services.at_service import init_at
    init_at()
    from scheduler import start_scheduler, shutdown_scheduler
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="FarmWise API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pathlib import Path

Path("static/audio").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(farmer.router, prefix="/api/farmer", tags=["farmer"])
app.include_router(plot.router, prefix="/api/plot", tags=["plot"])
app.include_router(diagnostic.router, prefix="/api/diagnostic", tags=["diagnostic"])
app.include_router(masumi.router, prefix="/api/masumi", tags=["masumi"])
app.include_router(twilio_webhook.router, prefix="/api/twilio", tags=["twilio"])
app.include_router(tts.router, prefix="/api/tts", tags=["tts"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(demo.router, prefix="/api/demo", tags=["demo"])
app.include_router(masumi_mip003.router, tags=["masumi-mip003"])
app.include_router(ground_truth.router, prefix="/api/farmer", tags=["ground-truth"])

app.include_router(plots.router, prefix="/api/plots", tags=["plots"])
app.include_router(seasons.router, prefix="/api", tags=["seasons"])
app.include_router(snapshots.router, prefix="/api", tags=["snapshots"])
app.include_router(alerts.router, prefix="/api", tags=["alerts"])
app.include_router(observations.router, prefix="/api", tags=["observations"])
app.include_router(interventions.router, prefix="/api", tags=["interventions"])
app.include_router(expenses.router, prefix="/api", tags=["expenses"])
app.include_router(sales.router, prefix="/api", tags=["sales"])
app.include_router(forecasts.router, prefix="/api", tags=["forecasts"])
app.include_router(stakeholder.router, prefix="/api", tags=["stakeholder"])
app.include_router(soil_pests.router, prefix="/api", tags=["soil", "pests"])
app.include_router(certificate.router, prefix="/api", tags=["certificate"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "farmwise-api"}


@app.get("/api/health/freshness")
async def health_freshness():
    from services.neo4j import query
    try:
        plot_count = query("MATCH (p:Plot) RETURN count(p) AS count")
        farmer_count = query("MATCH (f:Farmer) RETURN count(f) AS count")
        season_count = query("MATCH (s:Season) RETURN count(s) AS count")
        return {
            "status": "ok",
            "plots": plot_count[0]["count"] if plot_count else 0,
            "farmers": farmer_count[0]["count"] if farmer_count else 0,
            "seasons": season_count[0]["count"] if season_count else 0,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


from routers.auth import get_current_farmer
from pipelines.pipeline_a_ingestion import run_pipeline_a
from pipelines.pipeline_b_evaluation import run_pipeline_b
from pipelines.pipeline_c_dispatcher import run_pipeline_c


@app.post("/api/admin/run-pipeline-a")
async def trigger_a(farmer: dict = Depends(get_current_farmer)):
    await run_pipeline_a()
    return {"status": "Pipeline A triggered"}


@app.post("/api/admin/run-pipeline-b")
async def trigger_b(farmer: dict = Depends(get_current_farmer)):
    await run_pipeline_b()
    return {"status": "Pipeline B triggered"}


@app.post("/api/admin/run-pipeline-c")
async def trigger_c(farmer: dict = Depends(get_current_farmer)):
    await run_pipeline_c()
    return {"status": "Pipeline C triggered"}
