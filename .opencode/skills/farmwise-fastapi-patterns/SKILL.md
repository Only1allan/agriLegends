---
name: farmwise-fastapi-patterns
description: FastAPI backend patterns for FarmWise. Use when building Python API routes, agents, services, or Pydantic models. Triggers on backend tasks, API endpoint creation, or Python service work.
---

# FarmWise FastAPI Backend Patterns

FastAPI backend serving the FarmWise potato monitoring platform.

## Project Structure
```
backend/
├── main.py              # FastAPI app + CORS
├── config.py            # Settings from .env
├── requirements.txt
├── routers/             # API route handlers
├── agents/              # Ingestion + AI agents
├── services/            # Neo4j, Featherless, Twilio, Masumi
└── seed/                # Cypher + Python seed scripts
```

## Route Pattern
```python
# routers/plot.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.neo4j import query_one

router = APIRouter()

class RecommendationResponse(BaseModel):
    action: str
    cause: str
    urgencyHours: int
    narrative: str
    date: str

@router.get("/{plot_id}/recommendation")
async def get_recommendation(plot_id: str) -> RecommendationResponse:
    result = query_one("""
        MATCH (p:Plot {plotId: $plot_id})-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation {date: date()})
        RETURN rec {.action, .cause, .urgencyHours, .narrative, .date} AS rec
    """, {"plot_id": plot_id})
    if not result:
        raise HTTPException(status_code=404, detail="No recommendation found")
    return result
```

## Service Pattern
```python
# services/neo4j.py
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

## Agent Pattern
```python
# agents/satellite.py
from services.neo4j import query

async def ingest_satellite(polygon_id: str, plot_id: str):
    ndvi_data = await fetch_ndvi(polygon_id)
    for entry in ndvi_data:
        query("""...""", {"plot_id": plot_id, ...})
```

## Error Handling
- All routes return Pydantic models
- NotFound → HTTPException(404)
- External API failures → HTTPException(502)
- Validation errors → HTTPException(422)
- Log all errors with traceback
