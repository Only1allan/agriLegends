# FarmWise — Build & Technical Guide

*Python FastAPI backend + Next.js 16.2 TypeScript frontend. Companion docs: `workflow.md`, `userstories.md`, `onboarding.md`.*

---

## 1. Architecture

```
┌─────────────────────────────────────────┐
│           Next.js 16.2 Frontend          │
│   TypeScript · App Router · @serwist/next│
│   PWA mobile install · Tailwind CSS      │
│   localhost:3000                          │
└──────────────────┬──────────────────────┘
                   │ REST / JSON
┌──────────────────▼──────────────────────┐
│         FastAPI Python Backend           │
│   Python 3.12+ · async · uvicorn         │
│   localhost:8000                          │
│                                           │
│   Ingestion Agents (deterministic):       │
│   ├── AgroMonitoring → satellite/weather  │
│   ├── iSDAsoil → soil baselines           │
│   └── CSV seed → demo preloaded data      │
│                                           │
│   AI Agents (Featherless LLM/VLM):        │
│   ├── Ground Truth → image classification │
│   ├── Potato News → advisory summarization│
│   └── Daily Diagnostic → GraphRAG + LLM   │
└────┬────────┬──────────┬────────────────┘
     │        │          │
┌────▼──┐ ┌──▼───┐ ┌────▼─────┐
│Neo4j  │ │Twilio│ │Featherless│
│AuraDB │ │SMS + │ │LLM + TTS  │
│       │ │WA    │ │           │
└───────┘ └──────┘ └───────────┘
               │
        ┌──────▼──────┐
        │   Masumi    │
        │   Cardano   │
        └─────────────┘
```

## 2. Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python FastAPI | 0.115+ |
| ASGI Server | uvicorn | 0.34+ |
| Frontend | Next.js (App Router) | 16.2 |
| PWA | @serwist/next | 9.x |
| Styling | Tailwind CSS | 4.x |
| Charts | Recharts | 2.x |
| Database | Neo4j AuraDB | 5.x |
| Python Driver | neo4j (official) | 5.x |
| LLM | Featherless API | — |
| Messaging | Twilio (WhatsApp + SMS) | 9.x |
| Blockchain | masumi-sdk (Python) | latest |
| Auth | Twilio Verify | — |

## 3. Prerequisites

| Tool | Purpose |
|---|---|
| Python 3.12+ | Backend runtime |
| Node.js 20+ | Frontend runtime |
| Neo4j AuraDB (free tier) | Graph database |
| AgroMonitoring API key | Satellite NDVI + weather |
| iSDAsoil API key | Soil baseline data |
| Featherless API key | LLM + TTS |
| Twilio account | WhatsApp sandbox + SMS |
| Masumi (Cardano preprod) | Decision logging |
| Vercel (optional) | Frontend deploy |

## 4. Project Structure

```
farmwise/
├── backend/
│   ├── main.py                    # FastAPI app entry
│   ├── config.py                  # Env vars + settings
│   ├── requirements.txt
│   ├── routers/
│   │   ├── auth.py                # /api/auth/*
│   │   ├── farmer.py              # /api/farmer/*
│   │   ├── plot.py                # /api/plot/*
│   │   ├── diagnostic.py          # /api/diagnostic/*
│   │   ├── masumi.py              # /api/masumi/*
│   │   ├── twilio_webhook.py      # Twilio WhatsApp webhook
│   │   └── tts.py                 # /api/tts/*
│   ├── agents/
│   │   ├── satellite.py           # AgroMonitoring NDVI/imagery
│   │   ├── weather.py             # AgroMonitoring weather
│   │   ├── soil.py                # iSDAsoil baseline
│   │   ├── ground_truth.py        # Featherless VLM image classification
│   │   ├── potato_news.py         # Featherless LLM news summarization
│   │   └── diagnostic.py          # GraphRAG + LLM synthesis
│   ├── services/
│   │   ├── neo4j.py               # Neo4j driver + query helpers
│   │   ├── featherless.py         # Featherless API client
│   │   ├── twilio.py              # Twilio client
│   │   └── masumi.py              # Masumi SDK wrapper
│   ├── seed/
│   │   ├── knowledge_graph.cypher
│   │   ├── single_farmer.py       # Python seed script
│   │   └── farmer_network.py      # Python seed script
│   └── .env
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── sw.ts                  # Service worker
│   │   ├── manifest.ts            # PWA metadata
│   │   ├── onboarding/page.tsx
│   │   ├── dashboard/
│   │   │   ├── growth/page.tsx
│   │   │   ├── health/page.tsx
│   │   │   ├── yield/page.tsx
│   │   │   ├── certificate/page.tsx
│   │   │   └── tracker/page.tsx
│   │   └── ~offline/page.tsx
│   ├── components/
│   │   ├── ui/
│   │   │   ├── AdviceCard.tsx
│   │   │   ├── GrowthBar.tsx
│   │   │   ├── NdviChart.tsx
│   │   │   └── CertificatePDF.tsx
│   │   └── layout/
│   │       └── BottomNav.tsx
│   ├── lib/
│   │   └── api.ts                 # FastAPI client wrapper
│   ├── public/
│   │   ├── manifest.json
│   │   └── icons/
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   └── package.json
│
└── README.md
```

## 5. Backend Setup (FastAPI)

### 5.1 Install

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn neo4j twilio httpx python-dotenv masumi-sdk
pip freeze > requirements.txt
```

### 5.2 Environment (.env)

```bash
# Neo4j
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# AgroMonitoring
AGROMONITORING_API_KEY=your-key

# iSDAsoil (username/password auth, token expires 60 min)
ISDA_USERNAME=your-email@example.com
ISDA_PASSWORD=your-password

# Featherless
FEATHERLESS_API_KEY=sk-xxxxxxxx
FEATHERLESS_VISION_MODEL=Llama-3.2-11B-Vision
FEATHERLESS_CHAT_MODEL=Llama-3-8B-Instruct
FEATHERLESS_TTS_MODEL=AfriqueGemma-12B

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxx
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_NUMBER=+14155238886

# Masumi
MASUMI_SECRET_KEY=your-masumi-agent-key
MASUMI_NETWORK=preprod

# App
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

### 5.3 main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, farmer, plot, diagnostic, masumi, twilio_webhook, tts

app = FastAPI(title="FarmWise API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(farmer.router, prefix="/api/farmer", tags=["farmer"])
app.include_router(plot.router, prefix="/api/plot", tags=["plot"])
app.include_router(diagnostic.router, prefix="/api/diagnostic", tags=["diagnostic"])
app.include_router(masumi.router, prefix="/api/masumi", tags=["masumi"])
app.include_router(twilio_webhook.router, prefix="/api/twilio", tags=["twilio"])
app.include_router(tts.router, prefix="/api/tts", tags=["tts"])
```

### 5.4 services/neo4j.py

```python
from neo4j import GraphDatabase
from config import settings

driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
)

def query(cypher: str, params: dict = None):
    with driver.session() as session:
        return session.run(cypher, params or {})

def query_one(cypher: str, params: dict = None):
    result = query(cypher, params)
    record = result.single()
    return record.data() if record else None
```

### 5.5 services/featherless.py

```python
import httpx
from config import settings

FEATHERLESS_URL = "https://api.featherless.ai/v1"
HEADERS = {
    "Authorization": f"Bearer {settings.FEATHERLESS_API_KEY}",
    "Content-Type": "application/json",
}

async def chat(model: str, messages: list[dict]) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{FEATHERLESS_URL}/chat/completions",
            headers=HEADERS,
            json={"model": model, "messages": messages, "temperature": 0.3},
        )
        return res.json()

async def text_to_speech(text: str) -> bytes:
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{FEATHERLESS_URL}/audio/speech",
            headers=HEADERS,
            json={"model": settings.FEATHERLESS_TTS_MODEL, "input": text, "voice": "swahili-female"},
        )
        return res.content
```

### 5.6 services/twilio.py

```python
from twilio.rest import Client
from config import settings

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_whatsapp_text(to: str, body: str):
    return client.messages.create(
        from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
        to=f"whatsapp:{to}",
        body=body,
    )

def send_whatsapp_audio(to: str, audio_url: str):
    return client.messages.create(
        from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
        to=f"whatsapp:{to}",
        media_url=[audio_url],
    )

def send_sms(to: str, body: str):
    return client.messages.create(
        from_=settings.TWILIO_PHONE_NUMBER,
        to=to,
        body=body,
    )
```

### 5.7 services/masumi.py

```python
from masumi_sdk import MasumiAgentSigner, CardanoLedgerClient
from config import settings

signer = MasumiAgentSigner(secret_key=settings.MASUMI_SECRET_KEY)
ledger = CardanoLedgerClient(network=settings.MASUMI_NETWORK)

def log_decision(payload: dict) -> str:
    signed = signer.sign_payload(payload)
    tx_hash = ledger.submit_compliance_record(
        did="did:masumi:cardano:agent_diag_01",
        payload_hash=signed.hash,
        signature=signed.signature,
    )
    return tx_hash
```

## 6. Ingestion Agents

### 6.1 Satellite Agent (AgroMonitoring)

Uses the AgroMonitoring API to get NDVI zonal statistics per polygon.

```python
# agents/satellite.py
import httpx
from datetime import datetime, timedelta

AGRO_BASE = "https://api.agromonitoring.com/agro/1.0"

async def get_ndvi_history(polygon_id: str, days: int = 30):
    """Fetch daily NDVI statistics for a plot polygon."""
    end = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=days)).timestamp())

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{AGRO_BASE}/ndvi/history",
            params={
                "polyid": polygon_id,
                "start": start,
                "end": end,
                "appid": settings.AGROMONITORING_API_KEY,
            },
        )
        return res.json()
    # Response per day: {dt, source, dc, cl, data: {std, p25, min, max, median, mean, num}}

async def create_polygon(lat: float, lon: float, name: str) -> str:
    """Create an AgroMonitoring polygon from plot coordinates."""
    # AgroMonitoring uses GeoJSON polygon — create a 200m buffer around point
    polygon_geojson = {
        "type": "Feature",
        "properties": {"name": name},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [lon - 0.001, lat - 0.001],
                [lon + 0.001, lat - 0.001],
                [lon + 0.001, lat + 0.001],
                [lon - 0.001, lat + 0.001],
                [lon - 0.001, lat - 0.001],
            ]]
        }
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{AGRO_BASE}/polygons",
            params={"appid": settings.AGROMONITORING_API_KEY},
            json=polygon_geojson,
        )
        data = res.json()
        return data["id"]

async def ingest_satellite(polygon_id: str, plot_id: str):
    """Fetch NDVI history and write to Neo4j."""
    ndvi_data = await get_ndvi_history(polygon_id)
    from services.neo4j import query

    for entry in ndvi_data:
        date_str = datetime.utcfromtimestamp(entry["dt"]).strftime("%Y-%m-%d")
        stats = entry["data"]

        query("""
            MATCH (p:Plot {plotId: $plot_id})
            MERGE (d:TimeDay {date: date($date)})
            CREATE (obs:Observation_Satellite {
                ndvi: $ndvi, evi: $evi,
                ndvi_std: $std, ndvi_min: $min, ndvi_max: $max,
                cloudCover: $cl, dataCoverage: $dc, source: $source
            })
            CREATE (obs)-[:OCCURRED_ON]->(d)
            CREATE (p)-[:HAS_OBSERVATION]->(obs)
        """, {
            "plot_id": plot_id,
            "date": date_str,
            "ndvi": stats["mean"],
            "evi": stats.get("mean", stats.get("ndvi")),  # NDVI history returns mean as main stat
            "std": stats["std"],
            "min": stats["min"],
            "max": stats["max"],
            "cl": entry.get("cl", 0),
            "dc": entry.get("dc", 100),
            "source": entry.get("source", "combined"),
        })
```

### 6.2 Weather Agent (AgroMonitoring)

```python
# agents/weather.py
import httpx
from config import settings

AGRO_BASE = "https://api.agromonitoring.com/agro/1.0"

async def ingest_weather(lat: float, lon: float, plot_id: str):
    """Fetch current + forecast weather and write to Neo4j."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{AGRO_BASE}/weather",
            params={"lat": lat, "lon": lon, "appid": settings.AGROMONITORING_API_KEY},
        )
        data = res.json()

    from services.neo4j import query
    from datetime import datetime

    query("""
        MATCH (p:Plot {plotId: $plot_id})
        MERGE (d:TimeDay {date: date($date)})
        CREATE (obs:Observation_Weather {
            tempMax: $tmax, tempMin: $tmin,
            precipitation: $precip, humidity: $humidity
        })
        CREATE (obs)-[:OCCURRED_ON]->(d)
        CREATE (p)-[:HAS_OBSERVATION]->(obs)
    """, {
        "plot_id": plot_id,
        "date": datetime.utcfromtimestamp(data["dt"]).strftime("%Y-%m-%d"),
        "tmax": data["main"]["temp_max"],
        "tmin": data["main"]["temp_min"],
        "precip": data.get("rain", {}).get("1h", 0),
        "humidity": data["main"]["humidity"],
    })
```

### 6.3 Accumulated GDD (AgroMonitoring)

```python
# agents/gdd.py
import httpx
from datetime import datetime, timedelta
from config import settings

AGRO_BASE = "https://api.agromonitoring.com/agro/1.0"

async def ingest_gdd(polygon_id: str, plot_id: str, days: int = 30):
    """Fetch accumulated temperature for Growing Degree Days."""
    end = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=days)).timestamp())

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{AGRO_BASE}/accumulated_temperature",
            params={
                "polyid": polygon_id,
                "start": start,
                "end": end,
                "appid": settings.AGROMONITORING_API_KEY,
                "threshold": 8,  # Potato base temp: 8°C
            },
        )
        data = res.json()

    from services.neo4j import query
    query("""
        MATCH (p:Plot {plotId: $plot_id})
        SET p.accumulatedGDD = $gdd
    """, {"plot_id": plot_id, "gdd": data.get("accumulated_temperature", 0)})
```

### 6.4 Soil Baseline Agent (iSDAsoil)

```python
# agents/soil.py
import httpx
from config import settings

ISDA_BASE = "https://api.isda-africa.com/isdasoil/v2"

async def get_soil_baseline(lat: float, lon: float) -> dict:
    """Fetch iSDAsoil properties at 30m resolution for plot coordinates."""
    async with httpx.AsyncClient() as client:
        # Step 1: Login to iSDAsoil to get access token (60-min TTL)
        login_res = await client.post(
            f"{ISDA_BASE}/login",
            data={"username": settings.ISDA_USERNAME, "password": settings.ISDA_PASSWORD},
        )
        token = login_res.json()["access_token"]

        # Step 2: Query soil properties at coordinates per property
        for prop in ["ph", "N_tot", "C_tot"]:
            res = await client.get(
                f"{ISDA_BASE}/isdasoil/v2/soilproperty",
                params={"lat": lat, "lon": lon, "property": prop, "depth": "0-20"},
                headers={"Authorization": f"Bearer {token}"},
            )
            data = res.json()
            try:
                results[prop] = data["property"][prop][0]["value"]["value"]
            except (KeyError, IndexError):
                pass
        return results

async def ingest_soil(lat: float, lon: float, plot_id: str):
    """Fetch soil baseline and update plot properties."""
    soil = await get_soil_baseline(lat, lon)

    from services.neo4j import query
    query("""
        MATCH (p:Plot {plotId: $plot_id})
        SET p.soilBaseline_N = $n,
            p.soilBaseline_pH = $ph,
            p.soilBaseline_C = $carbon
    """, {
        "plot_id": plot_id,
        "n": soil.get("N_tot", 0),
        "ph": soil.get("ph", 7),
        "carbon": soil.get("C_tot", 0),
    })
```

## 7. AI Agents (Featherless)

### 7.1 Ground Truth Agent

```python
# agents/ground_truth.py
from services.featherless import chat

async def classify_farmer_image(image_url: str) -> dict:
    """Classify farmer WhatsApp photo using Featherless VLM."""
    result = await chat(
        model="Llama-3.2-11B-Vision",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Classify this potato crop image. Return JSON: {classification, confidence, notes}. Classifications: healthy, late_blight, early_blight, bacterial_wilt, nutrient_deficiency, pest_damage, moisture_stress, other."},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
        }],
    )
    return result  # Parse JSON from response
```

### 7.2 Daily Diagnostic Agent (GraphRAG)

```python
# agents/diagnostic.py
from services.neo4j import query_one
from services.featherless import chat
from services.masumi import log_decision
import json

async def run_diagnostic(plot_id: str) -> dict:
    """GraphRAG synthesis: extract subgraph, feed to LLM, store recommendation."""

    # Step 1: Extract connected subgraph
    context = query_one("""
        MATCH (p:Plot {plotId: $plot_id})-[:AT_STAGE]->(gs:GrowthStage)
        MATCH (p)-[:HAS_OBSERVATION]->(obs)-[:OCCURRED_ON]->(d:TimeDay {date: date()})
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(c:County)<-[:RELEVANT_TO]-(na:NewsAlert)
        OPTIONAL MATCH (p)-[:EXPERIENCED_STRESS]->(se:StressEvent)
            WHERE se.detectedAt >= datetime() - duration('P1D')
        OPTIONAL MATCH (gs)-[:HAS_RISK]->(pest:Pest)
        RETURN {
            plot: properties(p), stage: gs.name,
            todayObservations: collect(DISTINCT properties(obs)),
            activeAlerts: collect(DISTINCT na.headline),
            newStressEvents: collect(DISTINCT se.type),
            stageRisks: collect(DISTINCT pest.name),
            forecastedYieldKg: p.forecastedYieldKg
        } AS ctx
    """, {"plot_id": plot_id})

    # Step 2: Feed to Featherless LLM (translator, not decision-maker)
    result = await chat(
        model="Llama-3-8B-Instruct",
        messages=[{
            "role": "system",
            "content": (
                "You are an agricultural diagnostic translator. "
                "Given structured crop data, return a JSON object: "
                "{action, cause, urgencyHours, narrative, dataFreshness}. "
                "Do not invent actions. Translate the data into one clear farmer-facing sentence. "
                "If data is older than 1 day, note dataFreshness in the narrative."
            )
        }, {
            "role": "user",
            "content": json.dumps(context["ctx"])
        }],
    )

    parsed = json.loads(result["choices"][0]["message"]["content"])

    # Step 3: Store as (:DailyRecommendation) node
    query("""
        MATCH (p:Plot {plotId: $plot_id})
        CREATE (rec:DailyRecommendation {
            date: date(), action: $action, cause: $cause,
            urgencyHours: $urgency, narrative: $narrative,
            dataFreshness: $freshness
        })
        CREATE (p)-[:HAS_RECOMMENDATION]->(rec)
    """, {
        "plot_id": plot_id,
        "action": parsed["action"],
        "cause": parsed["cause"],
        "urgency": parsed["urgencyHours"],
        "narrative": parsed["narrative"],
        "freshness": parsed.get("dataFreshness", 0),
    })

    # Step 4: Log on Masumi
    tx_hash = log_decision({
        "plotId": plot_id,
        "action": parsed["action"],
        "cause": parsed["cause"],
        "urgencyHours": parsed["urgencyHours"],
        "stage": context["ctx"]["stage"],
        "forecastedYieldKg": context["ctx"].get("forecastedYieldKg", 0),
    })

    # Step 5: Link Masumi tx
    query("""
        MATCH (p:Plot {plotId: $plot_id})-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation {date: date()})
        CREATE (tx:MasumiTxHash {hash: $hash, blockNumber: 0, timestamp: datetime()})
        CREATE (rec)-[:HAS_TX]->(tx)
    """, {"plot_id": plot_id, "hash": tx_hash})

    return {**parsed, "masumiTxHash": tx_hash}
```

### 7.3 TTS Agent

```python
# agents/tts.py
from services.featherless import chat, text_to_speech
from pathlib import Path
import time

async def generate_swahili_audio(english_text: str) -> str:
    """Translate English → Swahili → TTS → .ogg file path."""
    translation = await chat(
        model="Llama-3-8B-Instruct",
        messages=[{
            "role": "system",
            "content": "Translate this agricultural advice to Kiswahili. Output ONLY the Swahili text."
        }, {
            "role": "user",
            "content": english_text,
        }],
    )
    swahili = translation["choices"][0]["message"]["content"]

    audio = await text_to_speech(swahili)
    filename = f"recommendation-{int(time.time())}.ogg"
    filepath = Path("static/audio") / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(audio)

    return f"/static/audio/{filename}"
```

## 8. API Routes

### Auth

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/send-otp` | Twilio Verify → SMS OTP |
| POST | `/api/auth/verify-otp` | Validate OTP → create `(:Farmer)` |

### Farmer & Plot

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/farmer/register` | Create farmer + plot + county + relationships |
| GET | `/api/farmer/{id}` | Farmer profile + all plots |
| GET | `/api/plot/{id}/recommendation` | Today's actionable sentence |
| GET | `/api/plot/{id}/observations?days=30` | NDVI + weather time series |
| GET | `/api/plot/{id}/certificate` | Production certificate + Masumi hashes |

### Diagnostic (Demo Trigger)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/diagnostic/run` | GraphRAG + LLM → create `(:DailyRecommendation)` + log on Masumi |

### Masumi

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/masumi/log-decision` | Log AI decision → Cardano tx hash |

### Twilio

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/twilio/whatsapp-webhook` | Receive farmer WhatsApp replies |
| POST | `/api/twilio/send-message` | Send WhatsApp text/audio or SMS |

### TTS

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/tts/generate` | English → Swahili → TTS → .ogg URL |

## 9. Frontend Setup (Next.js 16.2)

### 9.1 Install

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir=false
npm install @serwist/next recharts
npm install -D serwist
```

### 9.2 PWA Config (next.config.ts)

```typescript
import { spawnSync } from "node:child_process";
import withSerwistInit from "@serwist/next";
import type { NextConfig } from "next";

const revision = spawnSync("git", ["rev-parse", "HEAD"], { encoding: "utf-8" }).stdout ?? crypto.randomUUID();

const withSerwist = withSerwistInit({
  swSrc: "app/sw.ts",
  swDest: "public/sw.js",
  additionalPrecacheEntries: [{ url: "/~offline", revision }],
  disable: process.env.NODE_ENV === "development",
});

const nextConfig: NextConfig = {
  async rewrites() {
    return [{
      source: "/api/:path*",
      destination: "http://localhost:8000/api/:path*", // Proxy to FastAPI
    }];
  },
};

export default withSerwist(nextConfig);
```

### 9.3 lib/api.ts

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  return res.json();
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}
```

### 9.4 Run

```bash
# Terminal 1: Backend
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
# → http://localhost:3000 (proxies /api/* to backend)
```

## 10. Seed Database

### 10.1 Knowledge Graph

```bash
cd backend && source venv/bin/activate
cat seed/knowledge_graph.cypher | cypher-shell -u neo4j -p $NEO4J_PASSWORD
```

Creates: 4 growth stages, 5 pest profiles, symptoms, interventions, weather conditions, soil requirements. Data sourced from potato reference PDFs.

### 10.2 Single Farmer (Live Demo)

```bash
python seed/single_farmer.py
```

Creates via Python + Neo4j driver:
- 1 farmer (`+254712345678`), 1 plot ("Shamba ya Demo") in Nyandarua
- 30 `(:TimeDay)` nodes, 30 `(:Observation_Satellite)` entries (NDVI curve with dip at day 22)
- 30 `(:Observation_Weather)` entries
- 1 pre-computed `(:DailyRecommendation)` node
- 1 `(:StressEvent)`
- 1 `(:MasumiTxHash)` placeholder

### 10.3 Farmer Network (Scale Proof)

```bash
python seed/farmer_network.py
```

Creates: 50 farmers, 80 plots across 3 counties, 30 days observations each, varied stress patterns for spatial clustering.

## 11. Twilio WhatsApp Sandbox

1. Twilio Console → Messaging → WhatsApp Sandbox
2. Sandbox number: `+14155238886`
3. Join: send `join <code>` from WhatsApp to sandbox number
4. Webhook: `https://your-domain.ngrok.io/api/twilio/whatsapp-webhook` (use `ngrok http 8000` for local)
5. Set `TWILIO_WHATSAPP_NUMBER=+14155238886` in .env

## 12. Build & Deploy

### Development

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm run dev
```

### Production Build

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run build && npm start
```

### Vercel (Frontend Only)

```bash
cd frontend
# Set NEXT_PUBLIC_API_URL to your deployed FastAPI URL
vercel --prod
```

## 13. Demo Checklist

### Pre-Demo

- [ ] Neo4j AuraDB running, IP whitelisted
- [ ] `knowledge_graph.cypher` + `single_farmer.py` executed
- [ ] AgroMonitoring API key valid (test one polygon creation)
- [ ] iSDAsoil API key valid (test one point query)
- [ ] Featherless API key valid (test chat + TTS)
- [ ] Twilio sandbox joined + webhook configured
- [ ] Masumi agent registered on Cardano preprod
- [ ] Backend: `uvicorn main:app` running on port 8000
- [ ] Frontend: `npm run build && npm start` on port 3000
- [ ] PWA installs on demo phone
- [ ] `POST /api/diagnostic/run` works → `(:DailyRecommendation)` created
- [ ] Masumi Explorer shows tx hash verified
- [ ] WhatsApp text + voice note deliver

### Demo Flow (5 min)

| # | Step | Time |
|---|---|---|
| 1 | Problem slide | 45s |
| 2 | Onboard farmer | 30s |
| 3 | Home screen — today's advice | 20s |
| 4 | Growth timeline — stage bar | 20s |
| 5 | NDVI chart — 30-day curve | 30s |
| 6 | Trigger diagnostic → API call | 15s |
| 7 | Certificate + Masumi tx hash | 30s |
| 8 | Masumi Explorer → verified | 30s |
| 9 | WhatsApp voice note — Swahili | 15s |
| 10 | Architecture slide | 30s |
| 11 | Network graph + regional query | 30s |
| 12 | Impact slide | 30s |

## 14. Troubleshooting

| Issue | Check |
|---|---|
| Neo4j connection refused | IP whitelisted in AuraDB; `NEO4J_URI` correct |
| AgroMonitoring 401 | `AGROMONITORING_API_KEY` valid; polygon exists |
| iSDAsoil 401 | Login failed — check `ISDA_USERNAME`/`ISDA_PASSWORD`; token may have expired |
| Featherless 401 | `FEATHERLESS_API_KEY` valid; subscription active |
| Twilio webhook not receiving | ngrok tunnel on port 8000; webhook URL set |
| Masumi tx failing | `MASUMI_NETWORK=preprod`; sufficient test ADA |
| PWA not installing | HTTPS (ngrok/Vercel); `manifest.json` served |
| CORS errors | FastAPI `allow_origins` includes frontend URL |
| `@serwist/next` build errors | `npm install -D serwist`; check `next.config.ts` |
