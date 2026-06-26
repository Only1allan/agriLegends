# FarmWise Production Architecture

## System Overview

FarmWise is a satellite-based AI potato crop monitoring platform with verifiable Cardano production records. It serves Kenyan potato farmers through a dual-graph Neo4j knowledge system, real-time API ingestion, AI-powered diagnostics, and blockchain audit trails via Masumi.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js 16.2)                             │
│                                                                               │
│  /onboarding   /home   /chat   /dashboard/*   /ground-truth   /profile       │
│  ┌─────────┐  ┌─────┐  ┌────┐  ┌──────────┐  ┌────────────┐  ┌────────┐    │
│  │ 5 steps │  │ KPIs│  │GRAG│  │growth     │  │pests/yield │  │history │    │
│  │ +photos │  │ 12  │  │ UI │  │health     │  │soil/stress │  │ account│    │
│  │ +docs   │  │tools│  │    │  │weather    │  │groundTruth │  │        │    │
│  └─────────┘  └─────┘  └────┘  └──────────┘  └────────────┘  └────────┘    │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ HTTP REST (localhost:8000)
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     BACKEND ROUTERS (FastAPI)                                  │
│                                                                               │
│  auth.py     farmer.py    plot.py    chat.py    diagnostic.py                 │
│  demo.py     masumi.py    tts.py     twilio_webhook.py    ground_truth.py     │
└───┬───────────┬───────────┬──────────┬────────────┬──────────────┬───────────┘
    │           │           │          │            │              │
    ▼           ▼           ▼          ▼            ▼              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          AGENT LAYER                                           │
│                                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  soil.py     │  │ weather.py   │  │ satellite.py │  │   gdd.py        │  │
│  │              │  │              │  │              │  │                 │  │
│  │ iSDAsoil API │  │ AgroMonitor  │  │ AgroMonitor  │  │ AgroMonitor     │  │
│  │ ──login──→   │  │ ──weather──→ │  │ ──polygon──→ │  │ ──accum temp──→ │  │
│  │ 5 properties │  │ K→°C convert │  │ NDVI/EVI     │  │ GDD computed    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────────┘  │
│         │                 │                 │                  │              │
│  ┌──────┴─────────────────┴─────────────────┴──────────────────┴──────────┐  │
│  │                       diagnostic.py (GraphRAG Engine)                   │  │
│  │                                                                         │  │
│  │  extract_subgraph() ──→  LLM synthesis  ──→  store_recommendation()    │  │
│  │       │                       │                      │                  │  │
│  │  Neo4j subgraph         Featherless AI          Masumi Cardano tx       │  │
│  └─────────────────────────────┬───────────────────────────────────────────┘  │
│                                │                                               │
│  ┌─────────────────────────────┴───────────────────────────────────────────┐  │
│  │                     chat_agent.py (Dynamic GraphRAG)                     │  │
│  │                                                                         │  │
│  │  Featherless → CypherGen → Neo4j Execute → Full Context → Synthesize    │  │
│  │  Multi-turn memory │ Swahili+English │ Day 1 honesty │ No fabrication    │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  ground_truth.py  │  potato_news.py  │  tts.py  │  farmer_profile.py    │  │
│  │                    │                  │          │                       │  │
│  │  VLM classify      │  KEPHIS bulletins│  Swahili │  Profile + logs       │  │
│  └────────────────────┴──────────────────┴──────────┴───────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
    │           │               │                │
    ▼           ▼               ▼                ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────┐
│ iSDAsoil  │ │AgroMonitor │ │Featherless│ │   Masumi     │
│   API     │ │    API     │ │    AI     │ │  (Cardano)   │
│           │ │            │ │           │ │              │
│ Soil pH,N │ │ NDVI, EVI, │ │ Chat VLM  │ │ Payment Svc  │
│ C, Al, OC │ │ Weather,   │ │ Embedding │ │ Registry     │
│ 30m res   │ │ GDD, Poly  │ │ TTS       │ │ Ports 3100   │
└───────────┘ └───────────┘ └───────────┘ │    3101      │
                                           └──────────────┘
    │               │               │              │
    └───────────────┴───────┬───────┴──────────────┘
                            │
                            ▼
                ┌──────────────────────────────┐
                │       Neo4j AuraDB            │
                │  neo4j+s://xxxxxxxx...        │
                │                               │
                │  ┌─────────────────────────┐  │
                │  │   AGRONOMIC GRAPH        │  │
                │  │   (Knowledge Layer)      │  │
                │  │                          │  │
                │  │  GrowthStage (4)         │  │
                │  │  Pest (5)                │  │
                │  │  Symptom (5)             │  │
                │  │  Intervention (7)        │  │
                │  │  WeatherCondition (4)    │  │
                │  │  PotatoVariety (5)       │  │
                │  │                          │  │
                │  │  Hosted as Potato        │  │
                │  │  Diagnostic Agent        │  │
                │  │  on Masumi Network       │  │
                │  └───────────┬──────────────┘  │
                │              │ [:AT_STAGE]       │
                │  ┌───────────┴──────────────┐  │
                │  │   OBSERVATION GRAPH       │  │
                │  │   (Time-Series + Metrics) │  │
                │  │                           │  │
                │  │  Farmer (N)               │  │
                │  │  Plot (N)                 │  │
                │  │  County (11)              │  │
                │  │  Observation_Satellite    │  │
                │  │  Observation_Weather      │  │
                │  │  StressEvent             │  │
                │  │  DailyRecommendation      │  │
                │  │  MasumiTxHash (audit)     │  │
                │  │  FarmerLog (ground truth) │  │
                │  │  FarmerProfile             │  │
                │  │  SoilRequirement          │  │
                │  │  Embedding Vector Index   │  │
                │  └───────────────────────────┘  │
                └──────────────────────────────────┘
```

---

## Dual-Graph Model

### 1. Agronomic Graph (Knowledge Layer)
**Purpose:** Potato-specific domain knowledge — growth stages, pests, diseases, interventions, weather thresholds, and variety data.

**Nodes:**
| Label | Count | Description |
|-------|-------|-------------|
| GrowthStage | 4 | Emergence, Tuber Initiation, Tuber Bulking, Maturation |
| Pest | 5 | Late Blight, Early Blight, Bacterial Wilt, Aphids, Potato Tuber Moth |
| Symptom | 5 | NDVI_15, NDVI_10, GroundTruth, Temperature_22, Precipitation_5 |
| Intervention | 7 | spray_fungicide, spray_late_blight_fungicide, remove_infected_plants, apply_insecticide, improve_ridging, irrigate, monitor |
| WeatherCondition | 4 | cool_wet, warm_wet, warm_dry, cool_dry |
| PotatoVariety | 5 | Shangi, Kenya Mpya, Dutch Robjin, Tigoni, Asante |
| SoilRequirement | 4 | Per-stage nitrogen and pH targets |

**Key Relationships:**
- `GrowthStage-[:NEXT_STAGE]->GrowthStage` — Stage pipeline
- `GrowthStage-[:HAS_RISK]->Pest` → `Pest-[:AFFECTS_STAGE]->GrowthStage` — Bidirectional
- `Pest-[:THRIVES_IN]->WeatherCondition` — Weather-pest correlation
- `Pest-[:DETECTED_BY]->Symptom-[:TREATED_BY]->Intervention` — Detection & treatment chain

**Hosting:** Registered as "FarmWise Potato Diagnostic Agent" on Masumi Network. Exposed via masumi-connector proxy for registry health checks.

### 2. Observation Graph (Time-Series + Metrics)
**Purpose:** Per-farm, per-plot monitoring data — satellite NDVI, weather, soil, stress events, recommendations, farmer logs, and blockchain audit trail.

**Nodes:**
| Label | Count | Description |
|-------|-------|-------------|
| Farmer | N | Registered potato farmers |
| Plot | N | Individual farm plots (shambas) |
| County | 11 | Kenyan counties |
| Observation_Satellite | ~388 | NDVI/EVI measurements |
| Observation_Weather | ~207 | Temperature/precipitation/humidity |
| StressEvent | Dynamic | NDVI drop anomalies |
| DailyRecommendation | Dynamic | LLM-generated daily actions |
| MasumiTxHash | Dynamic | Cardano blockchain audit records |
| FarmerLog | Dynamic | Farmer-contributed ground truth |
| FarmerProfile | N | Aggregated farmer metadata |
| TimeDay | ~32 | Calendar date nodes |

**Key Relationships:**
- `Farmer-[:OWNS]->Plot` — Ownership
- `Plot-[:AT_STAGE]->GrowthStage` — **BRIDGE** to Agronomic Graph
- `Plot-[:HAS_OBSERVATION]->(Observation_Satellite\|Observation_Weather)` — Time-series
- `Plot-[:EXPERIENCED_STRESS]->StressEvent` — Stress detection
- `Plot-[:HAS_RECOMMENDATION]->DailyRecommendation-[:HAS_TX]->MasumiTxHash` — Audit chain
- `Farmer-[:HAS_LOG]->FarmerLog` — Ground truth
- `Farmer-[:HAS_PROFILE]->FarmerProfile` — Profile aggregation
- `Plot-[:LOCATED_IN]->County` — Geographic
- `Observation-[:OCCURRED_ON]->TimeDay` — Temporal

---

## Data Ingestion Flow

### Registration (POST /api/farmer/register)
```
1. Create Farmer + Plot + County + GrowthStage nodes in Neo4j
2. ingest_soil(lat, lon, plot_id)
   └── iSDAsoil API → 5 properties: pH, N, C, Al, OC → Plot node
3. create_polygon(lat, lon, acres)
   └── AgroMonitoring API → polygon_id → Plot.agromonitoringPolygonId
4. ingest_weather(lat, lon, plot_id)
   └── AgroMonitoring API → Observation_Weather node (today)
5. ingest_satellite(polygon_id, plot_id)
   └── AgroMonitoring API → Observation_Satellite nodes (30 days)
6. ingest_gdd(polygon_id, plot_id)
   └── AgroMonitoring API → Plot.accumulatedGDD
7. advance_growth_stage(plot_id)
   └── SeasonDay check → [:AT_STAGE] advancement
8. detect_stress(plot_id)
   └── 14-day NDVI baseline → StressEvent nodes
9. run_diagnostic(plot_id)
   └── GraphRAG → DailyRecommendation → Masumi tx
```

### Daily Scheduler (APScheduler, every 6 hours)
```
For each plot with a polygon_id:
  1. ingest_weather() → fresh weather
  2. ingest_satellite() → fresh NDVI/EVI
  3. ingest_gdd() → accumulated GDD
  4. advance_growth_stage() → stage progression
  5. detect_stress() → NDVI anomaly check
  6. run_diagnostic() → new recommendation → Masumi tx
```

---

## Chat Architecture (Dynamic GraphRAG)

```
Farmer Message (English/Swahili)
  │
  ▼
Phase 1: Intent Classification (Featherless LLM)
  "Classify this farmer question and generate a Cypher query.
   Schema: [all node types, rels, props]. Read-only queries only."
  → {intent, cypher}
  │
  ▼
Phase 2: Cypher Sanitization & Execution
  - Strip markdown fences
  - Reject CREATE/DELETE/SET/MERGE/DETACH
  - Execute against Neo4j
  → {results}
  │
  ▼
Phase 3: Full Subgraph Extraction
  - extract_subgraph(plot_id) → full plot context
  - run_pest_diagnosis(plot_id) → pest+weather match
  → {subgraph, pest_diagnosis}
  │
  ▼
Phase 4: Answer Synthesis (Featherless LLM)
  "Farmer asked: '{question}'. Here is their real farm data: {subgraph}.
   Answer using ONLY this data. If data is insufficient, say what's been
   collected and what's coming. Never fabricate. Be conversational."
  → {answer, confidence}
  │
  ▼
Response: {answer, cypher, results, confidence}
```

### Multi-turn Memory
- `CONVERSATION_BUFFER`: dict keyed by farmerId
- Last 10 messages stored per farmer
- Last 3 exchanges passed as context to LLM

### No-Fabrication Guarantee
- System prompt explicitly forbids inventing data
- Confidence: high (rich data) / medium (some data) / low (day 1)
- Day 1 banner shows what's collected vs what's pending

---

## Masumi Audit Trail

### Payment Lifecycle
```
log_decision(input_data)
  │
  ▼
create_payment_request() → tx_hash
  │
  ▼
Store: MasumiTxHash {hash, inputHash, agentIdentifier, purchaserIdentifier}
  │
  ▼
complete_decision(tx_hash, output_data)
  │
  ▼
Update: MasumiTxHash {onChainState: "ResultSubmitted", outputHash, verifiedAt}
```

### Audit Trail Data Model
```cypher
(DailyRecommendation)-[:HAS_TX]->(MasumiTxHash {
    hash:               string   // Cardano tx hash
    inputHash:          string   // SHA-256 of canonical input JSON
    outputHash:         string   // SHA-256 of canonical output JSON
    status:             string   // VERIFIED_ON_CHAIN | CREATED | COMPLETE_PENDING
    onChainState:       string   // ResultSubmitted | FundsLocked
    agentIdentifier:    string   // Full agent DID
    purchaserIdentifier: string  // Hex purchaser ID
    verifiedAt:         datetime // UTC timestamp
    network:            string   // "Preprod"
})
```

### Certificate Verification
- `verified = True` only when ALL conditions met:
  1. `masumiStatus == "VERIFIED_ON_CHAIN"`
  2. `txHash` exists (64 hex chars)
  3. `inputHash` exists
  4. `outputHash` exists
  5. `onChainState == "ResultSubmitted"`

### Audit Trail Endpoint
`GET /api/plot/{plot_id}/audit-trail`
Returns full chain per recommendation: action, cause, narrative, all 3 hashes, onChainState, agent info.

---

## Agent Registration on Masumi Network

### Potato Diagnostic Agent
- **Name:** "FarmWise Potato Diagnostic Agent"
- **Type:** Web3CardanoV1 on Preprod
- **Capability:** Custom Agent / 1.0.0
- **Tags:** `["agriculture", "potato", "kenya", "satellite", "ndvi", "diagnostic"]`
- **Hosted at:** masumi-connector proxy → `http://localhost:8000/api/diagnostic`

### MIP-003 Compliance Endpoints
| Endpoint | Method | Response |
|----------|--------|----------|
| `/api/diagnostic/mip003/availability` | GET | `{"status":"available"}` |
| `/api/diagnostic/mip003/input_schema` | GET | `{"type":"object","properties":{"plotId":"string"}}` |

---

## Embedding Strategy

### Vector Index
- Neo4j vector index on `Plot.embedding` (1536-dim cosine similarity)
- Enables semantic search: "Find farms with similar soil conditions"
- Enables precedent-based recommendations: "What worked for farms like mine?"

### Embedding Sources
- **Plot metadata** → aggregated text description of farm → `Plot.embedding`
- **FarmerLog text** → farmer-contributed observations → `FarmerLog.embedding`
- **DailyRecommendation narratives** → recommendation text → semantic clustering

---

## Ground Truth Collection

### Data Sources
1. **Onboarding (Step 1.5):** Photo upload, farm history text, document upload, known pest selections
2. **Dashboard Widget:** Pest sightings, yield reports, crop observations with photos
3. **Chat Conversations:** Farmer shares information conversationally — logged as FarmerLog
4. **Featherless VLM:** Classifies submitted photos as healthy, late_blight, early_blight, bacterial_wilt, nutrient_deficiency, pest_damage, moisture_stress

### Storage
```
Farmer-[:HAS_PROFILE]->FarmerProfile {metadata, updatedAt}
Farmer-[:HAS_LOG]->FarmerLog {textRecord, mediaUrl, classification, confidence, timestamp}
Plot-[:HAS_OBSERVATION]->FarmerLog (classified as ground truth)
```

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Next.js 16.2, TypeScript, Lucide React, Recharts |
| Backend | Python 3.10, FastAPI, Uvicorn |
| Graph DB | Neo4j AuraDB (cloud) |
| AI/LLM | Featherless AI (DeepSeek-V4-Pro, Qwen2.5-VL) |
| Satellite/Weather | AgroMonitoring API |
| Soil | iSDAsoil API (30m resolution) |
| Blockchain | Masumi Network (Cardano Preprod) |
| Messaging | Twilio (WhatsApp/SMS/Verify) |
| Scheduler | APScheduler 3.10 |
| Docker | Masumi Registry :3100, Payment :3101, Postgres :5442/:5443 |

---

## Production Readiness

### Scalability
- Neo4j supports million-node graphs with property indexes
- Vector index enables fast similarity search at scale
- APScheduler can iterate thousands of plots with per-plot error isolation
- Masumi supports batch logging (one tx per recommendation)

### Data Integrity
- All API calls use try/except with per-step error isolation
- Fallback defaults for missing data (e.g., pH=7, N=0)
- Kelvin→Celsius conversion with >100 threshold detection
- Canonical JSON hashing for Masumi input/output (deterministic)

### Observability
- Each ingestion step reports status in registration response
- Scheduler logs per-plot success/failure
- MasumiTxHash stores complete audit trail
- Frontend shows confidence level for AI answers

---

*Document version: 1.0. Generated 2026-06-25. Updated with all 5 agent implementations.*
