# Farmer Onboarding

## Current Scope (Hackathon Demo)

All farmers assumed to have smartphones. Onboarding via mobile app with WhatsApp as the primary chat interface.

## Future Addition: USSD Feature Phone Flow

Out of scope for the demo. Dial `*384#` menu tree documented below for post-hackathon implementation.

---

## Smartphone Onboarding Flow

### Step 1: App Install & Phone Verification

Farmer downloads the FarmWise mobile app. First screen: phone number entry. Twilio Verify sends an OTP via SMS. Verification creates the `(:Farmer)` node in Neo4j.

```
CREATE (f:Farmer {
    farmerId: randomUUID(),
    phone: $phoneNumber,
    registrationDate: date(),
    preferredChannel: null,
    preferredLanguage: null,
    masumiDid: null
})
```

### Step 2: Farm Registration Form

Single-screen form collecting:

| Field | Source | Action |
|---|---|---|
| Full Name | Manual entry | Updates `farmer.name` |
| County | Dropdown (Kenya counties) | Creates `(:County)` node if not exists |
| Plot Name | Manual entry (e.g. "Shamba ya Mlima") | Creates `(:Plot)` node |
| Plot Size (acres) | Manual entry | `plot.sizeAcres` |
| Potato Variety | Dropdown (Shangi, Kenya Mpya, Dutch Robjin, etc.) | `plot.variety` |
| Planting Date | Date picker | Sets `plot.plantingDate`, calculates `seasonDay` |

On submit, the backend:
1. Geolocates the county centroid as approximate plot coordinates
2. Triggers iSDAsoil API fetch → populates `plot.soilBaseline_N`, `plot.soilBaseline_pH`
3. Creates `(:GrowthStage)` relationship to "Emergence" (first stage)
4. Creates `(:SoilRequirement)` comparison relationship
5. Silently creates Masumi DID for the farmer (background, invisible)

```cypher
MATCH (c:County {name: $county})
CREATE (f:Farmer {farmerId: $farmerId})-[:OWNS]->(p:Plot {
    plotId: randomUUID(),
    name: $plotName,
    latitude: c.centroidLat,
    longitude: c.centroidLon,
    sizeAcres: $sizeAcres,
    variety: $variety,
    plantingDate: $plantingDate,
    seasonDay: 1
})
CREATE (p)-[:LOCATED_IN]->(c)
CREATE (p)-[:AT_STAGE]->(gs:GrowthStage {name: "Emergence"})
```

### Step 3: Channel & Language Preferences

Farmer selects:

**Delivery channel (multi-select):**
- [ ] WhatsApp text
- [ ] WhatsApp audio (voice note in Swahili)

**Language for WhatsApp text:**
- Swahili
- English

**Language for WhatsApp audio:**
- Swahili (default, only option for demo)

```
SET f.preferredChannel = $channels,
    f.preferredLanguage = $language
```

If audio selected: daily recommendation text is sent to Featherless TTS model → Swahili voice note → delivered via WhatsApp audio message.

### Step 4: Confirmation & First Message

```
"Karibu FarmWise! Your farm 'Shamba ya Mlima' is registered.
 We are monitoring 0.5 acres of Shangi potatoes in Nyandarua.
 Your first daily advice arrives tomorrow at 6am EAT."
```

Farmer receives:
- WhatsApp confirmation (text)
- If audio opted in: voice note reading the same confirmation
- Option to add additional plots from the app dashboard

---

## Channel Delivery Logic (Post-Onboarding)

```
Daily cron 4am EAT:
  MATCH (f:Farmer)-[:OWNS]->(p:Plot)
  MATCH (p)-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation {date: date()})
  FOR EACH farmer:
    IF 'whatsapp_text'  IN f.preferredChannel → WhatsApp text message (f.preferredLanguage)
    IF 'whatsapp_audio' IN f.preferredChannel → Featherless TTS → WhatsApp voice note (Swahili)
```

### Featherless TTS Voice Pipeline

```
rec.narrative (English)
    │
    ▼
Featherless LLM translates to Swahili:
  "Apply mancozeb fungicide within 48 hours..."
  →
  "Paka dawa ya kuvu ya mancozeb ndani ya masaa 48..."
    │
    ▼
Featherless TTS model (e.g. OpenAI-compatible TTS endpoint on Featherless)
    │
    ▼
WhatsApp audio voice note (.ogg / .mp3)
    │
    ▼
Delivered to farmer's WhatsApp
```

No Africa's Talking Voice API dependency. Pure Featherless pipeline.

---

## Mobile App Dashboard Features

| Screen | Cypher Source | What Farmer Sees |
|---|---|---|
| **Home** | `MATCH (rec:DailyRecommendation {date: date()}) RETURN rec.narrative` | Today's single actionable sentence |
| **Action Tracker** | `MATCH (:Farmer)-[:LOGGED]->(al:ActionLog) WHERE al.date >= date() - duration('P7D')` | Calendar: green/red dots for done/missed |
| **Plot Health** | NDVI trend from `(:Observation_Satellite)` nodes, last 30 days | Line chart of vegetation health |
| **Growth Timeline** | Current `(:GrowthStage)` + stage progress bar | Visual: emergence → bulking → harvest |
| **Yield Forecast** | `p.forecastedYieldKg` from GDS regression | Gauge: current estimate + trend arrow |
| **History** | All `(:DailyRecommendation)` nodes for plot, scrollable | Card stack of past recommendations |
| **Production Certificate** | Full audit path query | Downloadable PDF + shareable link |
| **Settings** | n/a | Channel pref, language, add plot |

### Action Tracker Cypher

When farmer taps "Done / Couldn't / Partially":

```cypher
CREATE (f:Farmer {farmerId: $farmerId})-[:LOGGED]->(al:ActionLog {
    date: date(),
    recommendationId: $recId,
    status: $status,          // 'done' | 'missed' | 'partial'
    reason: $reason,          // NULL if done
    farmerNote: $note         // optional free text
})
CREATE (al)-[:REFERS_TO]->(:DailyRecommendation {date: date(), plotId: $plotId})
```

Action log rolled into production certificate: "112 of 120 recommendations completed (93% compliance)."

---

## Future: USSD Feature Phone Flow

Post-hackathon. Same `(:Farmer)`, `(:Plot)`, `(:DailyRecommendation)`, `(:ActionLog)` nodes — different input mechanism.

### Registration via USSD

```
Dial *384# (first session, unregistered number):
  "Welcome to FarmWise. You are not registered."
  1.Register  2.Exit

  Register:
  "Enter your county code:"
  1.Nyandarua  2.Nakuru  3.Kiambu  ...

  "Enter your plot name:"
  (free text input via multi-press keypad)

  "Enter number of acres:"
  (numeric input)

  "Choose potato variety:"
  1.Shangi  2.Kenya Mpya  3.Dutch Robjin  ...

  "Choose planting date (DD/MM/YYYY):"
  (numeric input)

  "Confirmed. Plot 'X' registered. Daily advice starts tomorrow via SMS.
   Reply YES to confirm SMS subscription."
```

### Daily USSD Menu (registered number)

```
Dial *384#:
  1.Today's Advice      → MATCH (:DailyRecommendation {date: date()})
  2.My Farm Summary     → Numeric text: day #, stage, stress count, yield
  3.Action Tracker      → Did/didn't/why (multi-select numbered options)
  4.Weekly Report       → SMS push on demand
  5.Settings            → Add plot, change county, unsubscribe
```

Numeric summaries replace visual dashboards. Same Cypher queries, output truncated to 160-char SMS constraints.

### Voice (future stretch)

Same Featherless TTS pipeline as smartphone audio. Delivered via Africa's Talking Voice API call-out instead of WhatsApp voice note. Farmer receives a phone call: "Habari. Ushauri wako wa leo: Paka dawa ya kuvu..." Same Swahili TTS output, different delivery transport.
