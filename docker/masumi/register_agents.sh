#!/bin/bash
# Register 3 FarmWise agents on Masumi
# Usage: ADMIN_KEY="your_key" bash register_agents.sh

set -e

API="http://localhost:3100/api/v1/agents"

echo "=== Registering Agent 1: Daily Diagnostic ==="
curl -X POST "$API" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ADMIN_KEY" \
  -d '{
    "name": "FarmWise Daily Diagnostic",
    "description": "GraphRAG-based potato crop diagnostic agent. Synthesizes satellite, weather, soil, and knowledge graph data into daily recommendations.",
    "network": "Preprod",
    "pricing": { "amount": "0", "currency": "ADA", "period": "per_request" }
  }'
echo ""

echo "=== Registering Agent 2: Ground Truth ==="
curl -X POST "$API" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ADMIN_KEY" \
  -d '{
    "name": "FarmWise Ground Truth",
    "description": "VLM-based image classification agent. Classifies farmer-submitted potato crop photos for disease and pest detection.",
    "network": "Preprod",
    "pricing": { "amount": "0", "currency": "ADA", "period": "per_request" }
  }'
echo ""

echo "=== Registering Agent 3: Potato News ==="
curl -X POST "$API" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ADMIN_KEY" \
  -d '{
    "name": "FarmWise Potato News",
    "description": "LLM-based agricultural news summarization agent. Summarizes KEPHIS/NPCK potato advisories into county-specific alerts.",
    "network": "Preprod",
    "pricing": { "amount": "0", "currency": "ADA", "period": "per_request" }
  }'
echo ""

echo "Done. Copy the 3 agent IDs from the responses above."
