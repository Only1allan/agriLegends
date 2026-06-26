## 1. Business Context & Core Problem

Our prototype serves a **network of smallholder potato farmers** in a specified Kenyan region, each potentially managing **multiple farm plots**, with observations collected **daily** across the farmer network.

The core problem is both agronomic and commercial. Agronomically, potato crops are vulnerable to fast-acting diseases like late blight and severe moisture stress. Relying on manual visual checks means damage is caught too late, leading to yield loss. Commercially, buyers, processors, aggregators, and financial partners have low confidence in farmer-reported production because there is little objective field monitoring, no continuous crop records, and weak traceability.

The platform processes satellite-derived crop intelligence through a native graph database to provide immediate, actionable insights to farmers, while generating a verifiable production record that farmers can use to access markets, financing, and pre-harvest buying commitments.

**Demo scope:** Single farmer with 30-day preloaded data shown live. A separate Cypher script seeds 50 farmers across 3 counties to prove the architecture scales. Smartphone-first (PWA); USSD deferred to post-hackathon.

## 2. User Personas

- **The Smallholder Farmer (Primary):** Operates one or more potato plots. Uses a PWA mobile app and WhatsApp to receive one clear, actionable recommendation per day — not raw metrics. Can opt into WhatsApp audio (Swahili voice note via Featherless TTS). Needs the system to synthesize satellite, weather, soil, and regional news data into a single decision: spray, irrigate, harvest, or wait.
- **The Buyer / Processor / Aggregator (Secondary):** Needs verified production records and harvest forecasts to confidently plan sourcing from smallholder farmers.
- **The Financial Partner (Secondary):** Evaluates creditworthiness through cryptographically secure, verifiable compliance ledgers generated from the farmer's plot history.

## 3. Epics and User Stories

### Epic 1: Multi-Agent Data Ingestion & Onboarding

**Objective:** Capture and normalize a continuous stream of satellite, weather, soil, and ground-truth observations for every registered farm plot. Deterministic Python handles structured API data via AgroMonitoring and iSDAsoil; Featherless LLMs are reserved for channels requiring AI intelligence.

- **Story 1.1 (Satellite Agent):** As the system, I need a deterministic Python agent to poll AgroMonitoring NDVI history per polygon every 3-5 days and write structured `(:Observation_Satellite)` nodes with zonal statistics (mean, std, min, max) to Neo4j.
- **Story 1.2 (Weather Agent):** As the system, I need a deterministic Python agent to poll AgroMonitoring current weather per plot coordinates every 6 hours and log structured `(:Observation_Weather)` nodes.
- **Story 1.3 (GDD Accumulation Agent):** As the system, I need a deterministic Python agent to fetch AgroMonitoring accumulated temperature (threshold 8°C) per plot polygon to compute growing degree days for yield forecasting.
- **Story 1.4 (Soil Baseline Agent):** As the system, I need a deterministic Python agent to query iSDAsoil at 30m resolution upon plot registration, establishing each plot's foundational `(:Plot)` properties (pH, nitrogen, carbon).
- **Story 1.5 (Potato News Agent):** As the farmer, I want a Featherless LLM-powered agent to automatically scrape and summarize KEPHIS/NPCK potato advisories relevant to my county, routing county-specific threats into `(:NewsAlert)` nodes.
- **Story 1.6 (Ground Truth Agent):** As the farmer, I want a Featherless VLM-powered agent (Llama-3.2-11B-Vision) to process my WhatsApp image uploads and text descriptions, classifying field observations into `(:FarmerLog)` nodes.

### Epic 2: Native Graph Processing & Holistic Farmer Insights

**Objective:** Compute critical agronomic calculations directly within Neo4j, cross-referencing a knowledge graph of potato growth stages, pest/disease profiles, and intervention protocols to deliver one actionable recommendation per farmer per day.

- **Story 2.1 (Automated Canopy Stress Alerts):** As the farmer, I want the system to analyze my plot's 14-day trailing NDVI baseline natively in Cypher and trigger an immediate SMS if a drop greater than 15% indicates canopy stress — bypassing the daily batch.
- **Story 2.2 (Potato Growth Stage Tracking):** As the system, I need a traversable `(:GrowthStage)` node chain (emergence → tuber initiation → tuber bulking → maturation) linked by `[:NEXT_STAGE]`, with `[:HAS_RISK]` relationships to known threats at each stage, so every plot's current crop stage is always known.
- **Story 2.3 (Pest & Disease Graph Diagnosis):** As the system, I need a `(:Pest)-[:AFFECTS_STAGE|THRIVES_IN|DETECTED_BY]->(...)` knowledge graph so that when NDVI drops combined with weather conditions match a pest profile, the graph diagnoses the likely cause and traverses to a `(:Intervention)` node with the recommended action.
- **Story 2.4 (Regional Disease Spread Detection):** As the system, I need spatial clustering of `(:StressEvent)` nodes across plots to detect when 3+ plots within 5km share the same pest match within 3 days, triggering a regional epidemic alert.
- **Story 2.5 (Predictive Yield Forecasting):** As the farmer, I want my running yield forecast calculated via Neo4j GDS node regression from accumulated growing degree days and soil baselines, allowing me to plan harvesting logistics.
- **Story 2.6 (Harvest Window Optimization):** As the farmer, I want the graph to traverse my `(:GrowthStage)` chain + accumulated GDD to determine my optimal 10-day harvest window and surface it as part of my daily recommendation.
- **Story 2.7 (Soil Amendment Gap Detection):** As the farmer, I want the graph to compare my plot's soil baseline against `(:SoilRequirement)` nodes for the current growth stage, surfacing pH or nitrogen gaps as part of my daily insight.
- **Story 2.8 (Daily Batch Diagnostic Synthesis):** As the system, I need a cron job running at 4am EAT that extracts the full connected subgraph (satellite, weather, soil, growth stage, news, farmer logs) for every active plot, feeds it to a Featherless LLM via GraphRAG, and stores the resulting actionable recommendation as a `(:DailyRecommendation)` node so farmers get instant USSD/SMS responses.

### Epic 3: Verifiable Farmer Production Record & Market Access

**Objective:** Transform each farmer's plot history into a portable, verifiable production record they can present to any buyer, processor, or financial partner.

- **Story 3.1 (Farmer Production Certificate):** As the farmer, I want a downloadable production certificate summarizing my verified yield history, stress event count, and ground-truth submission log — backed by Masumi/Cardano cryptographic hashes — that I can share via link or SMS with any buyer or lender.
- **Story 3.2 (Compliance Credit Profile):** As a financial partner, I want to access a credit risk profile built on cryptographically signed data from the Masumi Compliance Agent, with every data point traceable to its source Neo4j node and Cardano transaction hash.
- **Story 3.3 (Audit Trail as Graph Path):** As any stakeholder, I want to verify the full traceability chain from `(:Farmer) → (:Plot) → (:Observation) → (:StressEvent) → (:MasumiTxHash)` as a single traversable graph path.

### Epic 4: Omni-Channel Action Delivery

**Objective:** Deliver one clear, actionable recommendation per farmer per day via PWA mobile app, WhatsApp (text + voice), SMS, and email — meeting farmers where they are without surfacing raw metrics.

- **Story 4.1 (PWA Mobile App Onboarding & Home):** As a farmer, I can register via the PWA app (phone OTP, farm form, channel preferences) and immediately see today's single actionable sentence on my home screen, read from a pre-computed Neo4j node.
- **Story 4.2 (WhatsApp Text Delivery):** As a farmer, I receive my daily actionable sentence via Twilio WhatsApp in my preferred language (English or Swahili), pushed automatically.
- **Story 4.3 (WhatsApp Voice Note via Featherless TTS):** As a farmer, I can opt into receiving my daily recommendation as a Swahili voice note on WhatsApp, generated by a Featherless TTS model.
- **Story 4.4 (Proactive Critical Push Alerts):** As a farmer, I want graph-detected critical events (NDVI drop >15%, disease match, harvest window opening) pushed instantly via Twilio SMS, bypassing the daily batch.
- **Story 4.5 (PWA Dashboard Graphs):** As a farmer, I can view my plot health (NDVI chart), growth timeline, yield forecast, daily recommendation history, and action tracker within the PWA app.
- **Story 4.6 (Farmer Production Certificate):** As the farmer, I can download a production certificate with my verified monitoring history, stress events, yield forecast, and Masumi Cardano transaction hash links — shareable with any buyer or lender.
- **Story 4.7 (Stakeholder Market Confidence Report):** As a buyer or processor, I receive a weekly report of expected harvest volumes and verified production records across the farmer network. (Slide only for demo.)

(End of file)
