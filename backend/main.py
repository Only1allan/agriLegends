from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from routers import auth, farmer, plot, diagnostic, masumi, masumi_mip003, twilio_webhook, tts, chat, demo, ground_truth
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from scheduler import start_scheduler, shutdown_scheduler
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="FarmWise API", version="1.0.0", lifespan=lifespan)

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


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "farmwise-api"}
