---
name: farmwise-neo4j-patterns
description: Neo4j Cypher patterns for FarmWise knowledge graph. Use when writing Cypher queries, graph processing, GDS operations, or seed scripts. Triggers on database tasks, graph queries, or Cypher work.
---

# FarmWise Neo4j Patterns

Cypher query patterns for the potato crop monitoring graph database.

## Core Queries

### Stress Detection (14-day rolling NDVI baseline)
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

### Pest Diagnosis (knowledge graph traversal)
```cypher
MATCH (p:Plot {plotId: $plot_id})-[:AT_STAGE]->(gs:GrowthStage)
MATCH (p)-[:HAS_OBSERVATION]->(w:Observation_Weather)-[:OCCURRED_ON]->(d:TimeDay {date: date()})
MATCH (gs)-[:HAS_RISK]->(pest:Pest)-[:THRIVES_IN]->(wc:WeatherCondition)
WHERE w.tempMin >= wc.tempMin AND w.tempMax <= wc.tempMax
MATCH (pest)-[:DETECTED_BY]->(s:Symptom)-[:TREATED_BY]->(i:Intervention)
RETURN pest.name AS cause, i.action, i.urgencyHours, gs.name AS stage;
```

### Regional Disease Spread
```cypher
MATCH (p1:Plot)-[:EXPERIENCED_STRESS]->(se1:StressEvent {type: $type})
MATCH (p2:Plot)-[:EXPERIENCED_STRESS]->(se2:StressEvent {type: $type})
WHERE point.distance(
  point({latitude: p1.latitude, longitude: p1.longitude}),
  point({latitude: p2.latitude, longitude: p2.longitude})
) < 5000
AND abs(duration.between(se1.detectedAt, se2.detectedAt).days) <= 3
WITH p1, count(DISTINCT p2) AS nearby WHERE nearby >= 2
RETURN p1.plotId, nearby + 1 AS clusterSize;
```

### GraphRAG Subgraph Extraction
```cypher
MATCH (p:Plot {plotId: $plot_id})-[:AT_STAGE]->(gs:GrowthStage)
MATCH (p)-[:HAS_OBSERVATION]->(obs)-[:OCCURRED_ON]->(d:TimeDay {date: date()})
OPTIONAL MATCH (p)-[:LOCATED_IN]->(c:County)<-[:RELEVANT_TO]-(na:NewsAlert)
OPTIONAL MATCH (p)-[:EXPERIENCED_STRESS]->(se:StressEvent)
  WHERE se.detectedAt >= datetime() - duration('P1D')
OPTIONAL MATCH (gs)-[:HAS_RISK]->(pest:Pest)
RETURN {plot: properties(p), stage: gs.name, ...} AS ctx;
```

### Production Certificate (audit path)
```cypher
MATCH (f:Farmer {farmerId: $id})-[:OWNS]->(p:Plot)
OPTIONAL MATCH (p)-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation)
OPTIONAL MATCH (p)-[:EXPERIENCED_STRESS]->(se:StressEvent)
RETURN {farmerId: f.farmerId, plots: collect({...})} AS certificate;
```

### GDD Accumulation
```cypher
MATCH (p:Plot)-[:HAS_OBSERVATION]->(w:Observation_Weather)
WITH p, sum(CASE WHEN ((w.tempMax + w.tempMin)/2) - 8 > 0
  THEN ((w.tempMax + w.tempMin)/2) - 8 ELSE 0 END) AS gdd
SET p.accumulatedGDD = gdd;
```

## Seed Patterns
- Use `MERGE` for idempotent seeding
- Use `randomUUID()` for unique IDs
- Always set timestamps with `datetime()`
- Group related writes in single transactions
