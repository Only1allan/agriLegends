// FarmWise Potato Knowledge Graph Seed — Dual-Graph Architecture
// AGRONOMIC GRAPH (Knowledge Layer) — hosted as Potato Agent on Masumi

// === CLEANUP — remove stale nodes from prior seed that lack a 'name' property ===
MATCH (wc:WeatherCondition) WHERE wc.name IS NULL DETACH DELETE wc;
MATCH (s:Symptom) WHERE s.description IS NULL DETACH DELETE s;
MATCH (i:Intervention) WHERE i.action = "spray_fungicide" AND i.urgencyHours = 48 DETACH DELETE i;
MATCH (i:Intervention) WHERE i.action = "remove_infected_plants" AND i.urgencyHours IS NULL DETACH DELETE i;
MATCH (i:Intervention) WHERE i.action = "apply_insecticide" AND i.urgencyHours IS NULL DETACH DELETE i;
MATCH (i:Intervention) WHERE i.action = "improve_ridging" AND i.method = "Ensure proper ridging to cover tubers. Apply neem cake to soil." DETACH DELETE i;
MATCH (i:Intervention) WHERE i.action = "irrigate" AND i.method CONTAINS "Avoid foliage wetting" DETACH DELETE i;
MATCH (i:Intervention) WHERE i.action = "monitor" AND i.method = "Continue regular monitoring. No immediate action required." DETACH DELETE i;
MATCH (sr:SoilRequirement) WHERE sr.nitrogenTarget < 0.5 DETACH DELETE sr;
MATCH (i:Intervention {action: "apply_insecticide"}) WHERE i.method CONTAINS "Introduce beneficial insects" DETACH DELETE i;
MATCH (i:Intervention {action: "spray_fungicide"}) WHERE i.method = "Apply chlorothalonil or mancozeb fungicide." DETACH DELETE i;

// === GROWTH STAGES (4) ===
MERGE (em:GrowthStage {name: "Emergence"})
SET em.dayStart = 0, em.dayEnd = 21,
    em.criticalActions = "Moisture, Weed control";
MERGE (ti:GrowthStage {name: "Tuber Initiation"})
SET ti.dayStart = 22, ti.dayEnd = 45,
    ti.criticalActions = "Soil moisture, scout for late blight, apply first fungicide";
MERGE (tb:GrowthStage {name: "Tuber Bulking"})
SET tb.dayStart = 46, tb.dayEnd = 80,
    tb.criticalActions = "Critical moisture, late blight vigilance, fertilizer top-dress, ridging";
MERGE (mt:GrowthStage {name: "Maturation"})
SET mt.dayStart = 81, mt.dayEnd = 110,
    mt.criticalActions = "Reduce irrigation, monitor skin set, prepare for harvest";

// NEXT_STAGE pipeline
MATCH (em:GrowthStage {name: "Emergence"})
MATCH (ti:GrowthStage {name: "Tuber Initiation"})
MERGE (em)-[:NEXT_STAGE]->(ti);
MATCH (ti:GrowthStage {name: "Tuber Initiation"})
MATCH (tb:GrowthStage {name: "Tuber Bulking"})
MERGE (ti)-[:NEXT_STAGE]->(tb);
MATCH (tb:GrowthStage {name: "Tuber Bulking"})
MATCH (mt:GrowthStage {name: "Maturation"})
MERGE (tb)-[:NEXT_STAGE]->(mt);

// === PESTS (5) ===
MERGE (lb:Pest {name: "Late Blight", scientificName: "Phytophthora infestans"});
MERGE (eb:Pest {name: "Early Blight", scientificName: "Alternaria solani"});
MERGE (bw:Pest {name: "Bacterial Wilt", scientificName: "Ralstonia solanacearum"});
MERGE (ap:Pest {name: "Aphids", scientificName: "Myzus persicae"});
MERGE (ptm:Pest {name: "Potato Tuber Moth", scientificName: "Phthorimaea operculella"});

// === WEATHER CONDITIONS (4) ===
MERGE (cool_wet:WeatherCondition {name: "cool_wet", tempMin: 10, tempMax: 22, humidityMin: 75});
MERGE (warm_wet:WeatherCondition {name: "warm_wet", tempMin: 15, tempMax: 28, humidityMin: 70});
MERGE (warm_dry:WeatherCondition {name: "warm_dry", tempMin: 18, tempMax: 32, humidityMin: 30});
MERGE (cool_dry:WeatherCondition {name: "cool_dry", tempMin: 8, tempMax: 20, humidityMin: 25});

// === SYMPTOMS (5) ===
MERGE (ndvi_15:Symptom {sensorType: "NDVI", threshold: 0.15, description: "NDVI drop >15% from baseline"});
MERGE (ndvi_10:Symptom {sensorType: "NDVI", threshold: 0.10, description: "NDVI drop >10% from baseline"});
MERGE (groundtruth:Symptom {sensorType: "GroundTruth", threshold: 0, description: "Visual confirmation by farmer"});
MERGE (temperature_22:Symptom {sensorType: "Temperature", threshold: 22, description: "Sustained temp above 22°C with humidity"});
MERGE (precipitation_5:Symptom {sensorType: "Precipitation", threshold: 5, description: "Rainfall >5mm for 3+ consecutive days"});

// === INTERVENTIONS (7) ===
MERGE (spray_lb_fungicide:Intervention {action: "spray_late_blight_fungicide", urgencyHours: 48, method: "Apply mancozeb-based or metalaxyl fungicide immediately"});
MERGE (spray_fungicide_72:Intervention {action: "spray_fungicide", urgencyHours: 72, method: "Apply chlorothalonil or mancozeb fungicide"});
MERGE (remove_plants:Intervention {action: "remove_infected_plants", urgencyHours: 24, method: "Uproot and destroy infected plants. Do not replant potatoes for 3 seasons."});
MERGE (apply_insecticide:Intervention {action: "apply_insecticide", urgencyHours: 72, method: "Apply neem-based or synthetic insecticide"});
MERGE (improve_ridging:Intervention {action: "improve_ridging", urgencyHours: 168, method: "Proper ridging to 30cm height. Apply neem cake at 250kg/ha."});
MERGE (irrigate:Intervention {action: "irrigate", urgencyHours: 72, method: "Apply 25-30mm irrigation"});
MERGE (monitor:Intervention {action: "monitor", urgencyHours: 168, method: "Continue regular monitoring. Report any changes."});

// === POTATO VARIETIES (5 — Kenya) ===
MERGE (shangi:PotatoVariety {name: "Shangi", maturity: 90, yieldPotential: 12000, blightResistance: "low", droughtTolerance: "medium"});
MERGE (kenya_mpya:PotatoVariety {name: "Kenya Mpya", maturity: 100, yieldPotential: 14000, blightResistance: "medium", droughtTolerance: "medium"});
MERGE (dutch_robjin:PotatoVariety {name: "Dutch Robjin", maturity: 110, yieldPotential: 16000, blightResistance: "medium", droughtTolerance: "low"});
MERGE (tigoni:PotatoVariety {name: "Tigoni", maturity: 100, yieldPotential: 13000, blightResistance: "low", droughtTolerance: "high"});
MERGE (asante:PotatoVariety {name: "Asante", maturity: 85, yieldPotential: 11000, blightResistance: "medium", droughtTolerance: "medium"});

// === PEST → WEATHER (THRIVES_IN) ===
MATCH (lb:Pest {name: "Late Blight"}) MATCH (wc:WeatherCondition {name: "cool_wet"}) MERGE (lb)-[:THRIVES_IN]->(wc);
MATCH (eb:Pest {name: "Early Blight"}) MATCH (wc:WeatherCondition {name: "warm_wet"}) MERGE (eb)-[:THRIVES_IN]->(wc);
MATCH (eb:Pest {name: "Early Blight"}) MATCH (wc:WeatherCondition {name: "warm_dry"}) MERGE (eb)-[:THRIVES_IN]->(wc);
MATCH (bw:Pest {name: "Bacterial Wilt"}) MATCH (wc:WeatherCondition {name: "warm_wet"}) MERGE (bw)-[:THRIVES_IN]->(wc);
MATCH (bw:Pest {name: "Bacterial Wilt"}) MATCH (wc:WeatherCondition {name: "warm_dry"}) MERGE (bw)-[:THRIVES_IN]->(wc);
MATCH (ap:Pest {name: "Aphids"}) MATCH (wc:WeatherCondition {name: "warm_dry"}) MERGE (ap)-[:THRIVES_IN]->(wc);
MATCH (ap:Pest {name: "Aphids"}) MATCH (wc:WeatherCondition {name: "cool_dry"}) MERGE (ap)-[:THRIVES_IN]->(wc);
MATCH (ptm:Pest {name: "Potato Tuber Moth"}) MATCH (wc:WeatherCondition {name: "warm_dry"}) MERGE (ptm)-[:THRIVES_IN]->(wc);

// === PEST → STAGE (AFFECTS_STAGE) ===
MATCH (lb:Pest {name: "Late Blight"}) MATCH (ti:GrowthStage {name: "Tuber Initiation"}) MERGE (lb)-[:AFFECTS_STAGE]->(ti);
MATCH (lb:Pest {name: "Late Blight"}) MATCH (tb:GrowthStage {name: "Tuber Bulking"}) MERGE (lb)-[:AFFECTS_STAGE]->(tb);
MATCH (lb:Pest {name: "Late Blight"}) MATCH (mt:GrowthStage {name: "Maturation"}) MERGE (lb)-[:AFFECTS_STAGE]->(mt);
MATCH (eb:Pest {name: "Early Blight"}) MATCH (tb:GrowthStage {name: "Tuber Bulking"}) MERGE (eb)-[:AFFECTS_STAGE]->(tb);
MATCH (eb:Pest {name: "Early Blight"}) MATCH (mt:GrowthStage {name: "Maturation"}) MERGE (eb)-[:AFFECTS_STAGE]->(mt);
MATCH (bw:Pest {name: "Bacterial Wilt"}) MATCH (ti:GrowthStage {name: "Tuber Initiation"}) MERGE (bw)-[:AFFECTS_STAGE]->(ti);
MATCH (bw:Pest {name: "Bacterial Wilt"}) MATCH (tb:GrowthStage {name: "Tuber Bulking"}) MERGE (bw)-[:AFFECTS_STAGE]->(tb);
MATCH (ap:Pest {name: "Aphids"}) MATCH (em:GrowthStage {name: "Emergence"}) MERGE (ap)-[:AFFECTS_STAGE]->(em);
MATCH (ap:Pest {name: "Aphids"}) MATCH (ti:GrowthStage {name: "Tuber Initiation"}) MERGE (ap)-[:AFFECTS_STAGE]->(ti);
MATCH (ptm:Pest {name: "Potato Tuber Moth"}) MATCH (tb:GrowthStage {name: "Tuber Bulking"}) MERGE (ptm)-[:AFFECTS_STAGE]->(tb);
MATCH (ptm:Pest {name: "Potato Tuber Moth"}) MATCH (mt:GrowthStage {name: "Maturation"}) MERGE (ptm)-[:AFFECTS_STAGE]->(mt);

// === STAGE → PEST (HAS_RISK — bidirectional reverse of AFFECTS_STAGE) ===
MATCH (em:GrowthStage {name: "Emergence"}) MATCH (ap:Pest {name: "Aphids"}) MERGE (em)-[:HAS_RISK]->(ap);
MATCH (ti:GrowthStage {name: "Tuber Initiation"}) MATCH (lb:Pest {name: "Late Blight"}) MERGE (ti)-[:HAS_RISK]->(lb);
MATCH (ti:GrowthStage {name: "Tuber Initiation"}) MATCH (bw:Pest {name: "Bacterial Wilt"}) MERGE (ti)-[:HAS_RISK]->(bw);
MATCH (ti:GrowthStage {name: "Tuber Initiation"}) MATCH (ap:Pest {name: "Aphids"}) MERGE (ti)-[:HAS_RISK]->(ap);
MATCH (tb:GrowthStage {name: "Tuber Bulking"}) MATCH (lb:Pest {name: "Late Blight"}) MERGE (tb)-[:HAS_RISK]->(lb);
MATCH (tb:GrowthStage {name: "Tuber Bulking"}) MATCH (eb:Pest {name: "Early Blight"}) MERGE (tb)-[:HAS_RISK]->(eb);
MATCH (tb:GrowthStage {name: "Tuber Bulking"}) MATCH (bw:Pest {name: "Bacterial Wilt"}) MERGE (tb)-[:HAS_RISK]->(bw);
MATCH (tb:GrowthStage {name: "Tuber Bulking"}) MATCH (ptm:Pest {name: "Potato Tuber Moth"}) MERGE (tb)-[:HAS_RISK]->(ptm);
MATCH (mt:GrowthStage {name: "Maturation"}) MATCH (lb:Pest {name: "Late Blight"}) MERGE (mt)-[:HAS_RISK]->(lb);
MATCH (mt:GrowthStage {name: "Maturation"}) MATCH (eb:Pest {name: "Early Blight"}) MERGE (mt)-[:HAS_RISK]->(eb);
MATCH (mt:GrowthStage {name: "Maturation"}) MATCH (ptm:Pest {name: "Potato Tuber Moth"}) MERGE (mt)-[:HAS_RISK]->(ptm);

// === PEST → SYMPTOM (DETECTED_BY) ===
MATCH (lb:Pest {name: "Late Blight"}) MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.15}) MERGE (lb)-[:DETECTED_BY]->(s);
MATCH (lb:Pest {name: "Late Blight"}) MATCH (s:Symptom {sensorType: "Temperature", threshold: 22}) MERGE (lb)-[:DETECTED_BY]->(s);
MATCH (lb:Pest {name: "Late Blight"}) MATCH (s:Symptom {sensorType: "Precipitation", threshold: 5}) MERGE (lb)-[:DETECTED_BY]->(s);
MATCH (eb:Pest {name: "Early Blight"}) MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.15}) MERGE (eb)-[:DETECTED_BY]->(s);
MATCH (eb:Pest {name: "Early Blight"}) MATCH (s:Symptom {sensorType: "GroundTruth", threshold: 0}) MERGE (eb)-[:DETECTED_BY]->(s);
MATCH (bw:Pest {name: "Bacterial Wilt"}) MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.10}) MERGE (bw)-[:DETECTED_BY]->(s);
MATCH (bw:Pest {name: "Bacterial Wilt"}) MATCH (s:Symptom {sensorType: "GroundTruth", threshold: 0}) MERGE (bw)-[:DETECTED_BY]->(s);
MATCH (ap:Pest {name: "Aphids"}) MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.10}) MERGE (ap)-[:DETECTED_BY]->(s);
MATCH (ptm:Pest {name: "Potato Tuber Moth"}) MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.15}) MERGE (ptm)-[:DETECTED_BY]->(s);

// === SYMPTOM → INTERVENTION (TREATED_BY) ===
MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.15}) MATCH (i:Intervention {action: "spray_late_blight_fungicide"}) MERGE (s)-[:TREATED_BY]->(i);
MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.15}) MATCH (i:Intervention {action: "spray_fungicide", urgencyHours: 72}) MERGE (s)-[:TREATED_BY]->(i);
MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.15}) MATCH (i:Intervention {action: "improve_ridging"}) MERGE (s)-[:TREATED_BY]->(i);
MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.15}) MATCH (i:Intervention {action: "monitor"}) MERGE (s)-[:TREATED_BY]->(i);
MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.10}) MATCH (i:Intervention {action: "apply_insecticide"}) MERGE (s)-[:TREATED_BY]->(i);
MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.10}) MATCH (i:Intervention {action: "remove_infected_plants"}) MERGE (s)-[:TREATED_BY]->(i);
MATCH (s:Symptom {sensorType: "NDVI", threshold: 0.10}) MATCH (i:Intervention {action: "monitor"}) MERGE (s)-[:TREATED_BY]->(i);
MATCH (s:Symptom {sensorType: "GroundTruth", threshold: 0}) MATCH (i:Intervention {action: "spray_fungicide", urgencyHours: 72}) MERGE (s)-[:TREATED_BY]->(i);
MATCH (s:Symptom {sensorType: "GroundTruth", threshold: 0}) MATCH (i:Intervention {action: "remove_infected_plants"}) MERGE (s)-[:TREATED_BY]->(i);
MATCH (s:Symptom {sensorType: "Temperature", threshold: 22}) MATCH (i:Intervention {action: "spray_late_blight_fungicide"}) MERGE (s)-[:TREATED_BY]->(i);
MATCH (s:Symptom {sensorType: "Precipitation", threshold: 5}) MATCH (i:Intervention {action: "spray_late_blight_fungicide"}) MERGE (s)-[:TREATED_BY]->(i);

// === SOIL REQUIREMENTS PER STAGE ===
MERGE (sr_em:SoilRequirement {stage: "Emergence", nitrogenTarget: 1.5, phTarget: 6.0});
MERGE (sr_ti:SoilRequirement {stage: "Tuber Initiation", nitrogenTarget: 2.0, phTarget: 5.8});
MERGE (sr_tb:SoilRequirement {stage: "Tuber Bulking", nitrogenTarget: 2.5, phTarget: 5.5});
MERGE (sr_mt:SoilRequirement {stage: "Maturation", nitrogenTarget: 1.5, phTarget: 6.0});

RETURN "Knowledge graph seeded successfully";
