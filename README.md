# FarmWise

Satellite-based AI potato crop monitoring platform with verifiable Cardano production records. Built for Kenyan potato farmers — dual-graph Neo4j knowledge system, real-time satellite/weather/soil ingestion, GraphRAG AI diagnostics, multilingual TTS, Twilio WhatsApp messaging, and on-chain audit trails via Masumi + Cardano.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       FRONTEND (Next.js 16.2 PWA)                             │
│                                                                               │
│  /onboarding   /home   /chat   /dashboard/*   /ground-truth   /profile       │
│  ┌─────────┐  ┌─────┐  ┌────┐  ┌──────────┐  ┌────────────┐  ┌────────┐    │
│  │ 6 steps │  │ KPIs│  │GRAG│  │growth     │  │pests/yield │  │history │    │
│  │ +VLM    │  │ 12  │  │ UI │  │health     │  │soil/stress │  │account │    │
│  └─────────┘  │tools│  │    │  │weather    │  │groundTruth │  │        │    │
│               └─────┘  └────┘  └──────────┘  └────────────┘  └────────┘    │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ HTTP REST
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI + uvicorn)                                │
│                                                                               │
│  Routes: auth  farmer  plot  chat  diagnostic  tts  twilio_webhook            │
│  masumi  masumi_mip003  demo  ground_truth                                    │
│                                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  soil.py     │  │ weather.py   │  │ satellite.py │  │   gdd.py        │  │
│  │ iSDAsoil API │  │ AgroMonitor  │  │ AgroMonitor  │  │ AgroMonitor     │  │
│  │ pH,N,C,Al,OC │  │ K→°C convert │  │ NDVI/EVI     │  │ accumulated GDD │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────────┘  │
│         │                 │                 │                  │              │
│  ┌──────┴─────────────────┴─────────────────┴──────────────────┴──────────┐  │
│  │                     diagnostic.py (GraphRAG Engine)                     │  │
│  │  extract_subgraph() ──→  LLM synthesis  ──→  store_recommendation()    │  │
│  │       │                       │                      │                  │  │
│  │  Neo4j subgraph         Featherless AI          Masumi Cardano tx       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │  chat_agent.py (Dynamic GraphRAG)  │  ground_truth.py  │  tts.py          │ │
│  │  Intent→Cypher→Execute→Synthesize │  VLM classification│  EN→SW TTS       │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
└────┬────────┬──────────┬─────────────────────────────────────────────────────┘
     │        │          │
┌────▼──┐ ┌──▼───┐ ┌────▼─────┐     ┌──────────────┐
│Neo4j  │ │Twilio│ │Featherless│     │   Masumi     │
│AuraDB │ │SMS+WA│ │LLM+VLM+TTS│     │  (Cardano)   │
└───────┘ └──────┘ └───────────┘     └──────────────┘
```

## Dual-Graph Model (Neo4j)

### Knowledge Layer (Agronomic Graph)
Permanent potato domain knowledge — growth stages, pests, diseases, interventions.

| Label | Count | Description |
|-------|-------|-------------|
| GrowthStage | 4 | Emergence, Tuber Initiation, Tuber Bulking, Maturation |
| Pest | 5 | Late Blight, Early Blight, Bacterial Wilt, Aphids, Potato Tuber Moth |
| Symptom | 5 | NDVI thresholds, ground truth markers |
| Intervention | 7 | spray_fungicide, remove_infected_plants, apply_insecticide, etc. |
| PotatoVariety | 5 | Shangi, Kenya Mpya, Dutch Robjin, Tigoni, Asante |

### Observation Layer (Time-Series + Metrics)
Per-farm, per-plot monitoring data with blockchain audit trail.

| Label | Description |
|-------|-------------|
| Farmer / Plot | Registered farmers and their shambas |
| Observation_Satellite | NDVI/EVI readings (~30 per plot) |
| Observation_Weather | Temperature, precipitation, humidity |
| StressEvent | NDVI anomaly detections |
| DailyRecommendation | LLM-generated daily actions |
| MasumiTxHash | Cardano blockchain audit records |
| FarmerLog | Farmer-contributed ground truth |

**Bridge:** `Plot-[:AT_STAGE]->GrowthStage` connects the operational and knowledge graphs.

## Chat Architecture (GraphRAG)

```
Farmer message (English/Swahili)
        │
  Phase 1: Intent Classification (Featherless LLM → Cypher)
  Phase 2: Cypher Sanitization & Execution (read-only against Neo4j)
  Phase 3: Full Subgraph Extraction (plot context + pest diagnosis)
  Phase 4: Answer Synthesis (Featherless LLM, no fabrication)
        │
  Response: {answer, cypher, results, confidence}
```

- Multi-turn memory (last 10 messages per farmer)
- English + Swahili support
- Confidence: high / medium / low (day 1 honesty)

## Data Ingestion Pipeline

**On registration** (`POST /api/farmer/register`): Create farmer + plot → ingest soil (iSDAsoil, 5 properties) → create AgroMonitoring polygon → ingest 30 days satellite NDVI + weather + GDD → advance growth stage → detect stress → run diagnostic → log Masumi tx.

**Background scheduler** (every 6 hours via APScheduler): For each registered plot — fresh weather, satellite NDVI/EVI, GDD accumulation, growth stage advancement, stress detection, and diagnostic recommendation → Masumi Cardano tx.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python FastAPI 0.115+, uvicorn 0.34+ |
| Database | Neo4j AuraDB 5.x (graph database) |
| Frontend | Next.js 16.2 (App Router), TypeScript, PWA |
| AI | Featherless API (LLM, VLM, TTS, embeddings) |
| Satellite/Weather | AgroMonitoring API |
| Soil | iSDAsoil API (pH, N, C, Al, OC, 30m resolution) |
| Messaging | Twilio (WhatsApp + SMS + Verify OTP) |
| Blockchain | Masumi SDK + Cardano Preprod |
| Styling | Tailwind CSS 4, Recharts |
| PWA | @serwist/next 9.x (offline support, mobile install) |

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app entry (11 route mounts)
│   ├── config.py             # Environment variables via dotenv
│   ├── scheduler.py          # 6-hour APScheduler ingestion cycle
│   ├── requirements.txt
│   ├── routers/              # 11 API routers
│   │   ├── auth.py           # /api/auth/* (OTP send/verify)
│   │   ├── farmer.py         # /api/farmer/* (registration + data ingestion)
│   │   ├── plot.py           # /api/plot/* (data + certificates)
│   │   ├── diagnostic.py     # /api/diagnostic/* (GraphRAG pipeline)
│   │   ├── chat.py           # /api/chat/query (conversational AI)
│   │   ├── tts.py            # /api/tts/* (Swahili TTS)
│   │   ├── twilio_webhook.py # /api/twilio/* (WhatsApp webhook)
│   │   ├── masumi.py         # /api/masumi/* (Cardano decisions)
│   │   ├── masumi_mip003.py  # MIP-003 protocol
│   │   ├── demo.py           # /api/demo/*
│   │   └── ground_truth.py   # Farmer field verification
│   ├── agents/               # 10 AI/data agents
│   │   ├── satellite.py      # AgroMonitoring NDVI/EVI
│   │   ├── weather.py        # AgroMonitoring weather
│   │   ├── soil.py           # iSDAsoil baselines
│   │   ├── gdd.py            # Growing Degree Days
│   │   ├── diagnostic.py     # GraphRAG + LLM synthesis
│   │   ├── chat_agent.py     # 4-phase conversational GraphRAG
│   │   ├── ground_truth.py   # Featherless VLM classification
│   │   ├── potato_news.py    # LLM news summarization
│   │   ├── tts.py            # English→Swahili TTS
│   │   └── farmer_profile.py # Profile aggregation
│   ├── services/             # API client wrappers
│   │   ├── neo4j.py          # Neo4j driver + query helpers
│   │   ├── featherless.py    # Featherless API (chat, TTS, embedding)
│   │   ├── twilio.py         # Twilio Verify + WhatsApp/SMS
│   │   └── masumi.py         # Masumi Cardano SDK
│   ├── seed/                 # Database seed scripts
│   │   ├── knowledge_graph.cypher  # Agronomic knowledge graph
│   │   ├── single_farmer.py        # 1 farmer + 30 days demo data
│   │   └── farmer_network.py       # 50 farmers scale proof
│   └── tests/                # 28 test files (ingestion, processing, reporting, integration)
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx        # Root layout (DM Sans, Cormorant Garamond)
│   │   ├── globals.css       # Tailwind + glassmorphism design tokens
│   │   ├── sw.ts             # PWA service worker (Serwist)
│   │   ├── page.tsx          # Root redirect (/home or /onboarding)
│   │   ├── landing/          # Marketing page
│   │   ├── onboarding/       # 6-step farmer registration
│   │   ├── home/             # Dashboard (KPIs + 12 tools)
│   │   ├── chat/             # AI chat with Recharts visuals
│   │   ├── dashboard/        # 12 sub-pages (growth, health, soil, etc.)
│   │   └── ~offline/         # PWA offline fallback
│   ├── lib/api.ts            # Typed FastAPI client wrapper
│   ├── public/
│   │   ├── manifest.json     # PWA manifest
│   │   └── icons/            # App icons
│   └── next.config.ts        # Serwist PWA + API proxy rewrites
│
└── docker/masumi/            # Masumi Cardano node (registry + payment + postgres)
```

## Prerequisites

| Tool | Purpose |
|------|---------|
| Python 3.12+ | Backend runtime |
| Node.js 20+ | Frontend runtime |
| Neo4j AuraDB (free tier) | Graph database |
| AgroMonitoring API key | Satellite NDVI + weather |
| iSDAsoil API credentials | Soil baseline data |
| Featherless API key | LLM + VLM + TTS |
| Twilio account | WhatsApp, SMS, Verify OTP |
| Masumi + Cardano Preprod | Blockchain audit trail |

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in credentials
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # Set NEXT_PUBLIC_API_URL
```

### Masumi Docker Node (optional, for blockchain features)

```bash
cd docker/masumi
cp .env.example .env   # Fill in credentials
docker compose up -d
```

## Running

```bash
# Backend (http://localhost:8000)
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Frontend (http://localhost:3000)
cd frontend
npm run dev
```

### Seed Data

```bash
cd backend
source venv/bin/activate
# Agronomic knowledge graph (pests, stages, interventions)
python -c "from services.neo4j import query; exec(open('seed/knowledge_graph.cypher').read())"
# Demo farmer with 30 days synthetic data
python seed/single_farmer.py
# Scale proof: 50 farmers, 80 plots
python seed/farmer_network.py
```

## Environment Variables

See `backend/.env.example` for the full template. Key variables:

| Variable | Description |
|----------|-------------|
| `NEO4J_URI` | Neo4j AuraDB connection (e.g., `neo4j+s://xxxx.databases.neo4j.io`) |
| `NEO4J_USERNAME` / `NEO4J_PASSWORD` | Neo4j credentials |
| `AGROMONITORING_API_KEY` | AgroMonitoring API key |
| `ISDA_USERNAME` / `ISDA_PASSWORD` | iSDAsoil login |
| `FEATHERLESS_API_KEY` | Featherless AI key |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | Twilio credentials |
| `TWILIO_VERIFY_SERVICE_SID` | Twilio Verify service |
| `MASUMI_PAYMENT_SERVICE_URL` | Masumi payment node URL |
| `MASUMI_PAYMENT_API_KEY` | Masumi payment API key |
| `BACKEND_URL` | Backend deployment URL (for CORS) |
| `FRONTEND_URL` | Frontend deployment URL (for CORS) |

## API Routes

| Route | Purpose |
|-------|---------|
| `POST /api/auth/send-otp` | Send OTP via Twilio |
| `POST /api/auth/verify-otp` | Verify OTP |
| `POST /api/farmer/register` | Register farmer + plot + trigger full ingestion pipeline |
| `GET /api/farmer/{id}` | Get farmer profile + plot data |
| `GET /api/plot/{id}` | Get plot details + recommendations |
| `GET /api/plot/{id}/certificate` | Get production certificate |
| `POST /api/diagnostic/run` | Trigger GraphRAG diagnostic |
| `POST /api/chat/query` | Conversational AI (GraphRAG) |
| `POST /api/tts/generate` | English→Swahili TTS audio |
| `POST /api/twilio/send` | Send WhatsApp message |
| `POST /api/twilio/webhook` | Twilio webhook receiver |
| `POST /api/masumi/log-decision` | Log Cardano decision |
| `GET /api/health` | Health check |
| `POST /api/demo/*` | Demo/test endpoints |

## Masumi Audit Trail

Every diagnostic recommendation is logged on-chain:

```
log_decision(input_data)
  → Create Purchase (Masumi Payment Service)
  → Fund purchase with test ADA (Cardano Preprod)
  → Submit decision metadata transaction
  → Store MasumiTxHash in Neo4j linked to DailyRecommendation
  → Verifiable on Cardano Preprod explorer
```

## Deployment

### Frontend → Vercel

1. Import repo on Vercel, set **Root Directory** to `frontend`
2. Add env var: `NEXT_PUBLIC_API_URL=https://your-backend-url`
3. Deploy — Next.js auto-detected

### Backend → Render (or Railway/Fly.io)

1. Create a new **Web Service**, set **Root Directory** to `backend`
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add all environment variables from `.env.example`
5. **Post-deploy**: Whitelist Render's outbound IP in Neo4j AuraDB console
