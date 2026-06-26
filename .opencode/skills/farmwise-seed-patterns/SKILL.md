---
name: farmwise-seed-patterns
description: Seed script patterns for FarmWise Neo4j database. Use when writing Python seed scripts that populate the graph database with demo data. Triggers on seed data tasks.
---

# FarmWise Seed Patterns

## Python Seed Script Pattern
```python
from neo4j import GraphDatabase
import os, uuid, random
from datetime import datetime, timedelta

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

def seed():
    with driver.session() as session:
        # Use MERGE for idempotency
        session.run("""
            CREATE (f:Farmer {farmerId: $id, name: $name, phone: $phone})
            CREATE (f)-[:OWNS]->(p:Plot {plotId: $pid, ...})
            CREATE (p)-[:LOCATED_IN]->(c:County {name: $county})
            CREATE (p)-[:AT_STAGE]->(gs:GrowthStage {name: 'Emergence'})
        """, params)

        # Generate 30 days of observations
        for day_offset in range(30):
            date = (datetime.now() - timedelta(days=30 - day_offset)).strftime('%Y-%m-%d')
            ndvi = generate_ndvi_curve(day_offset)  # Custom curve with dip at day 22
            session.run("""
                MATCH (p:Plot {plotId: $pid})
                MERGE (d:TimeDay {date: date($date)})
                CREATE (obs:Observation_Satellite {ndvi: $ndvi, evi: $evi, cloudCover: $cl})
                CREATE (obs)-[:OCCURRED_ON]->(d)
                CREATE (p)-[:HAS_OBSERVATION]->(obs)
            """, {"pid": plot_id, "date": date, "ndvi": ndvi, ...})
```

## NDVI Stress Curve
For the demo, generate an NDVI curve that drops at day 22 to simulate late blight:
- Days 1-21: NDVI rises from 0.35 → 0.78 (healthy growth)
- Day 22: drops to 0.62 (stress event trigger)
- Days 23-30: recovers slowly to 0.71

## Network Seed
50 farmers across 3 counties with varied:
- Planting dates (spread across 90 days)
- Plot sizes (0.25 — 5 acres)
- NDVI patterns (some healthy, some with stress dips in different weeks)
- Stress event distribution for spatial clustering demo
