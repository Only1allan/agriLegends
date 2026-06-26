# FarmWise — Architecture & Workflow

*Final architecture document. Consolidated from a 17-point grilling session against the Farm Mall Ventures problem statement. Companion docs: `userstories.md`, `BUILD.md`, `onboarding.md`.*

---

## Decision Log

| ID | Decision | Impact |
|---|---|---|
| D-001 | Multi-farmer, multi-plot regional network (not single farm) | Neo4j earns its cost; graph traversal becomes meaningful |
| D-002 | IoT removed, satellite-only focus | Aligns with problem statement; simplifies ingestion |
| D-003 | LLMs reserved for 3 channels. Satellite/Weather/Soil → deterministic TypeScript | Saves cost; LLMs only where AI adds value |
| D-004 | Masumi reoriented as farmer-owned production record (not lender-only) | Traceability connects to farmer benefit |
| D-005 | Neo4j over relational DB — 10 graph-native use cases | Graph traversal, GDS, spatial clustering, audit trail |
| D-006 | Potato knowledge graph as Neo4j nodes (growth stages, pests, symptoms, interventions, soil) | Static PDFs become traversable decision engine |
| D-007 | Single actionable sentence per farmer per day | Problem statement: "avoid dashboard without helping farmer decide" |
| D-008 | 4am EAT batch cron pre-computes `(:DailyRecommendation)` nodes | Eliminates farmer-facing latency |
| D-009 | Masumi retained — hackathon requirement | Competition category |
| D-010 | Masumi Decision Logging logs every AI agent decision on-chain | Three agents: Ground Truth, Potato News, Daily Diagnostic |
| D-011 | LLM as translator, not decision-maker | Graph determines action; LLM converts to natural language |
| D-012 | Voice via Featherless TTS (Swahili) | Single provider dependency; WhatsApp voice notes |
| D-013 | Smartphone-first for demo; USSD deferred | Hackathon time constraint |
| D-014 | `dataFreshness` field on `:DailyRecommendation` | 5-day satellite interval doesn't block daily diagnostics |
| D-015 | Demo scope: 1 farmer, 30-day preloaded data, single diagnostic run | Cypher + Masumi are real; ingestion agents are simulated |

---

## Demo Strategy

### Single Farmer (Live Walkthrough)

One farmer, one plot, 30 days of preloaded satellite/weather/soil data. The full value chain runs end-to-end in under 3 minutes:

1. **Onboarding** — register farmer via mobile app
2. **Home screen** — "Spray mancozeb fungicide within 48hrs. Late blight at tuber bulking."
3. **Growth Timeline** — visual stage bar at day 67
4. **Plot Health** — NDVI chart with 30-day curve
5. **Certificate** — PDF with Cardano tx hash → Masumi Explorer verification
6. **Voice note** — WhatsApp audio in Swahili

### Farmer Network (Scale Proof)

Separate Cypher script seeds 50 farmers, 80 plots across 3 counties with 30 days of observations. Not part of the live walkthrough — shown as:

- One slide: Neo4j graph visualization of the network
- One live query: regional stress cluster detection across all plots
- Proves the single-farmer architecture scales without changing a line of code

### Build Priority

| # | Screen | Live/Slide |
|---|---|---|
| 1 | Home (Today's Advice) | Live |
| 2 | Growth Timeline | Live |
| 3 | Certificate + Masumi | Live |
| 4 | Onboarding | Live |
| 5 | Plot Health (NDVI chart) | Nice-to-have |
| 6 | WhatsApp voice note | Bonus |
| 7 | Yield, Action Tracker, History, Settings | Slides |

---

## 1. Architecture Overview

The platform uses a **Python FastAPI** backend with a **Next.js 16.2** frontend (TypeScript, App Router, PWA via `@serwist/next`). Data is unified in a **Neo4j AuraDB** graph instance with a Fact-Dimension Model enriched by a potato knowledge graph.

**Ingestion:** All structured API data is handled by deterministic Python. Sat + weather via **AgroMonitoring API** (polygon-based satellite NDVI/EVI + historical NDVI + accumulated temperature for GDD). Soil baselines via **iSDAsoil API** (30m resolution point queries). Featherless AI is reserved for three inference channels: Ground Truth image classification (VLM), Potato News summarization (LLM), Daily Diagnostic synthesis (GraphRAG + LLM).

**Insight delivery:** A batch job pre-computes one actionable recommendation per plot per day as a `(:DailyRecommendation)` node. Critical alerts bypass the batch for real-time push via Twilio SMS.

**Verification:** Every AI agent decision is logged on-chain via **Masumi Network** on Cardano. The farmer owns their production record — shareable with any buyer, processor, or financial partner.

**Demo:** Single farmer with 30-day preloaded data shown live. 50-farmer network shown as graph visualization + one Cypher query.

## 2. Neo4j Graph Schema

### Core Entities (Dimensions)

```
(:Farmer {farmerId, name, phone, preferredChannel[], preferredLanguage, masumiDid})
(:Plot {plotId, name, latitude, longitude, variety, plantingDate, seasonDay,
        sizeAcres, soilBaseline_N, soilBaseline_pH, accumulatedGDD, forecastedYieldKg})
(:County {name, centroidLat, centroidLon})
(:TimeDay {date, dayOfYear})
(:ActionLog {date, status, reason, farmerNote})
```

### Observations (Facts)

```
(:Observation_Satellite {ndvi, evi, cloudCover})
(:Observation_Weather {tempMax, tempMin, precipitation})
(:FarmerLog {textRecord, mediaUrl, classification, confidence})
(:NewsAlert {headline, summary, county, source})
```

### Potato Knowledge Graph

```
(:GrowthStage {name, dayStart, dayEnd, criticalActions[]})
(:Pest {name, scientificName})
(:Symptom {sensorType, threshold})
(:Intervention {action, urgencyHours, method})
(:WeatherCondition {tempMin, tempMax, humidityMin})
(:SoilRequirement {stage, nitrogenTarget, phTarget})
```

### Insights & Compliance

```
(:StressEvent {eventId, type, severity, detectedAt})
(:DailyRecommendation {date, action, cause, urgencyHours, narrative, dataFreshness, masumiTxHash})
(:MasumiTxHash {hash, blockNumber, timestamp})
```

### Relationships

```
(:Farmer)-[:OWNS]->(:Plot)
(:Farmer)-[:LOGGED]->(:ActionLog)
(:ActionLog)-[:REFERS_TO]->(:DailyRecommendation)
(:Plot)-[:LOCATED_IN]->(:County)
(:Plot)-[:AT_STAGE]->(:GrowthStage)
(:Plot)-[:HAS_OBSERVATION]->(fact)-[:OCCURRED_ON]->(:TimeDay)
(:Plot)-[:EXPERIENCED_STRESS]->(:StressEvent)
(:Plot)-[:HAS_RECOMMENDATION]->(:DailyRecommendation)
(:Plot)-[:SOIL_COMPARED_TO]->(:SoilRequirement)
(:DailyRecommendation)-[:HAS_TX]->(:MasumiTxHash)

(:GrowthStage)-[:NEXT_STAGE]->(:GrowthStage)
(:GrowthStage)-[:HAS_RISK]->(:Pest)
(:Pest)-[:AFFECTS_STAGE]->(:GrowthStage)
(:Pest)-[:THRIVES_IN]->(:WeatherCondition)
(:Pest)-[:DETECTED_BY]->(:Symptom)
(:Symptom)-[:TREATED_BY]->(:Intervention)

(:NewsAlert)-[:RELEVANT_TO]->(:County)
```

## 3. Ingestion Engine

| Agent | Trigger | Engine | Function |
|---|---|---|---|
| Satellite Agent | AgroMonitoring polygon NDVI history | Deterministic Python | Fetches daily NDVI/EVI zonal stats → `(:Observation_Satellite)` |
| Weather Agent | AgroMonitoring weather API | Deterministic Python | Fetches current + forecast → `(:Observation_Weather)` |
| GDD Agent | AgroMonitoring accumulated temperature | Deterministic Python | Fetches GDD (threshold 8°C) → updates `plot.accumulatedGDD` |
| Soil Agent | iSDAsoil point query (on registration) | Deterministic Python | Fetches 30m soil baselines (N, pH, C) → `(:Plot)` properties |
| Ground Truth Agent | WhatsApp webhook | `Llama-3.2-11B-Vision` via Featherless | Classifies farmer photos → `(:FarmerLog)` |
| Potato News Agent | Demo: preloaded | `Llama-3-8B-Instruct` via Featherless | Summarizes KEPHIS bulletins → `(:NewsAlert)` |

## 4. Graph Processing (Cypher)

### Unit 1: Canopy Stress Detection

```cypher
MATCH (p:Plot)-[:HAS_OBSERVATION]->(sat:Observation_Satellite)-[:OCCURRED_ON]->(d:TimeDay)
WHERE d.date >= date() - duration('P14D')
WITH p, avg(sat.ndvi) AS baseline, collect(sat.ndvi)[-1] AS current
WHERE current < baseline * 0.85
CREATE (p)-[:EXPERIENCED_STRESS]->(:StressEvent {
    eventId: randomUUID(), type: "CANOPY_NDVI_DROP",
    severity: 1.0 - (current / baseline), detectedAt: datetime()
});
```

### Unit 2: Growth Stage Traversal

```cypher
MATCH (p:Plot {plotId: $plotId})-[:AT_STAGE]->(gs:GrowthStage)
WITH p, gs, p.seasonDay AS day
WHERE day > gs.dayEnd
MATCH (gs)-[:NEXT_STAGE]->(next:GrowthStage)
CREATE (p)-[:AT_STAGE]->(next)
DELETE MATCH (p)-[old:AT_STAGE]->(gs);
```

### Unit 3: Pest & Disease Diagnosis

```cypher
MATCH (p:Plot {plotId: $plotId})-[:AT_STAGE]->(gs:GrowthStage)
MATCH (p)-[:HAS_OBSERVATION]->(w:Observation_Weather)-[:OCCURRED_ON]->(d:TimeDay {date: date()})
MATCH (gs)-[:HAS_RISK]->(pest:Pest)-[:THRIVES_IN]->(wc:WeatherCondition)
WHERE w.tempMin >= wc.tempMin AND w.tempMax <= wc.tempMax
MATCH (pest)-[:DETECTED_BY]->(s:Symptom)-[:TREATED_BY]->(i:Intervention)
RETURN pest.name AS cause, i.action, i.urgencyHours, gs.name AS stage;
```

### Unit 4: Regional Disease Spread

```cypher
MATCH (p1:Plot)-[:EXPERIENCED_STRESS]->(se1:StressEvent {type: $type})
MATCH (p2:Plot)-[:EXPERIENCED_STRESS]->(se2:StressEvent {type: $type})
WHERE point.distance(
  point({latitude: p1.latitude, longitude: p1.longitude}),
  point({latitude: p2.latitude, longitude: p2.longitude})
) < 5000
AND abs(duration.between(se1.detectedAt, se2.detectedAt).days) <= 3
WITH p1, count(DISTINCT p2) AS nearby
WHERE nearby >= 2
RETURN p1.plotId, nearby + 1 AS clusterSize;
```

### Unit 5: Yield Forecast (GDS)

```cypher
MATCH (p:Plot)-[:HAS_OBSERVATION]->(w:Observation_Weather)-[:OCCURRED_ON]->(d:TimeDay)
WITH p, sum(CASE WHEN ((w.tempMax + w.tempMin)/2) - 8 > 0
  THEN ((w.tempMax + w.tempMin)/2) - 8 ELSE 0 END) AS gdd
SET p.accumulatedGDD = gdd;
```

### Unit 6: Soil Amendment Gap

```cypher
MATCH (p:Plot {plotId: $plotId})-[:AT_STAGE]->(gs:GrowthStage)
MATCH (p)-[:SOIL_COMPARED_TO]->(sr:SoilRequirement {stage: gs.name})
RETURN
  CASE WHEN p.soilBaseline_pH < sr.phTarget THEN 'pH below target — apply lime' END AS pH,
  CASE WHEN p.soilBaseline_N < sr.nitrogenTarget THEN 'N below target — top-dress' END AS N;
```

### Unit 7: Daily Diagnostic Synthesis (GraphRAG)

```cypher
MATCH (p:Plot)-[:AT_STAGE]->(gs:GrowthStage)
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
} AS diagnosticContext;
```

Graph output is structured: `{action, cause, urgencyHours, narrative, dataFreshness}`. Featherless LLM translates to natural language in farmer's preferred language. Created as `(:DailyRecommendation)` node.

## 5. Masumi Decision Logging

Three agents registered with DIDs on Masumi Network:

| Agent | DID | Logged Decision |
|---|---|---|
| Ground Truth | `did:masumi:ground-truth-01` | Photo classification `{classification, confidence}` |
| Potato News | `did:masumi:news-01` | Threat summary `{threat, county}` |
| Daily Diagnostic | `did:masumi:diag-01` | Daily action `{action, cause, urgencyHours}` |

Decision chain on Cardano:
```
Ground Truth Agent   → "Photo: early blight"     [Block #N]
Potato News Agent    → "KEPHIS: late blight"      [Block #N+1]
Daily Diagnostic     → "Spray fungicide 48hrs"     [Block #N+2]
```

### Farmer Production Certificate (Graph Path)

```cypher
MATCH (f:Farmer {farmerId: $id})-[:OWNS]->(p:Plot)
OPTIONAL MATCH (p)-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation)
OPTIONAL MATCH (p)-[:EXPERIENCED_STRESS]->(se:StressEvent)
RETURN {
  farmerId: f.farmerId, masumiDid: f.masumiDid,
  plots: collect({
    plotId: p.plotId,
    monitoringDays: count(DISTINCT rec),
    stressEventsResolved: count(DISTINCT se),
    currentYieldForecastKg: p.forecastedYieldKg,
    latestAdvice: rec.narrative
  })
} AS certificate;
```

### Stakeholder Audit Trail

```cypher
MATCH (f:Farmer {farmerId: $id})-[:OWNS]->(p:Plot)
MATCH (p)-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation)-[:HAS_TX]->(tx:MasumiTxHash)
MATCH (p)-[:EXPERIENCED_STRESS]->(se:StressEvent)
MATCH (p)-[:HAS_OBSERVATION]->(obs:Observation_Satellite)-[:OCCURRED_ON]->(d:TimeDay)
RETURN f.farmerId, p.plotId,
  collect(DISTINCT {date: rec.date, action: rec.action, tx: tx.hash}) AS decisionLog,
  count(DISTINCT se) AS stressEventCount, p.forecastedYieldKg;
```

## 6. Onboarding & Registration

Documented in `onboarding.md`. Summary:

1. Phone OTP verification (Twilio) → creates `(:Farmer)` node
2. Farm form (county, plot name, acres, variety, planting date) → creates `(:Plot)`, `(:County)`, `(:GrowthStage)` relationships
3. Channel preferences (WhatsApp text + optional audio, language)
4. Background: iSDAsoil fetch, Masumi DID creation

## 7. Omni-Channel Delivery

| Channel | Content | Trigger |
|---|---|---|
| PWA Home screen | Single actionable sentence | App open → Cypher read from pre-computed node |
| WhatsApp text | Actionable sentence in preferred language | Daily push |
| WhatsApp audio | Featherless TTS → Swahili voice note | Daily push (if opted in) |
| Twilio SMS | Critical alerts (NDVI drop >15%, disease, harvest) | Immediate on detection |
| Email | Weekly production certificate with Masumi links | Weekly cron |
| USSD (future) | Menu tree with numeric summaries | Post-hackathon |

### TTS Audio Pipeline

```
Daily recommendation (English) → Featherless LLM translation → Swahili text
  → Featherless TTS model → .ogg audio → Twilio WhatsApp voice note
```

## 8. End-to-End Data Flow

```
1. SEED (demo)
   Preloaded 30-day CSV → Cypher import → Neo4j nodes

2. KNOWLEDGE ACTIVATION
   GrowthStage chain, Pest→Symptom→Intervention graph → Cypher traversal

3. GRAPH COMPUTATION
   ├── Stress detection (rolling NDVI baseline)
   ├── Growth stage progression check
   ├── Pest/disease diagnosis (knowledge graph traversal)
   ├── Regional cluster scan (spatial + temporal)
   ├── Yield forecast (GDS)
   └── Soil amendment gap check

4. GRAPHRAG SYNTHESIS
   Subgraph extraction → Featherless LLM (translator)
   → CREATE (:DailyRecommendation)

5. FARMER DELIVERY
   PWA → MATCH (:DailyRecommendation {date: date()}) → single sentence
   WhatsApp → text + optional voice note

6. MASUMI LOGGING
   (:DailyRecommendation) → Masumi Decision Log → (:MasumiTxHash)

7. VERIFICATION
   Buyer queries: (:Farmer)→(:Plot)→(:DailyRecommendation)→(:MasumiTxHash)
```
