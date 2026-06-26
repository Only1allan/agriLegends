# Masumi Agent Registration — FarmWise Potato Diagnostic Agent

## Architecture

The FarmWise Potato Diagnostic Agent uses the Potato Agronomic Graph (Neo4j) as its
knowledge base, synthesizing satellite NDVI, weather, and soil data into daily
recommendations logged on Cardano via Masumi.

## Registration Steps

1. The Potato Agronomic Graph is the agent's knowledge base
2. Agent endpoint: `http://localhost:8000/api/diagnostic` (MIP-003 compliant)
3. Register via Masumi Registry on-chain NFT minting
4. Use masumi-connector proxy to expose local agent to registry health checks

## Agent Registration Payload

```json
{
  "name": "FarmWise Potato Diagnostic Agent",
  "apiBaseUrl": "https://connector.masumi.network/mip003/farmwise-potato-agent",
  "description": "AI-powered potato crop diagnostic agent for Kenyan farmers. Uses satellite NDVI, weather data, and soil analysis to generate daily recommendations logged on Cardano via Masumi.",
  "authorName": "FarmWise Team",
  "authorOrganization": "FarmWise",
  "authorContactEmail": "farmwise@example.com",
  "paymentType": "Web3CardanoV1",
  "network": "Preprod",
  "tags": ["agriculture", "potato", "kenya", "satellite", "ndvi", "diagnostic"],
  "capability": {
    "name": "Custom Agent",
    "version": "1.0.0"
  },
  "pricing": {
    "amount": "0",
    "currency": "ADA",
    "period": "per_request"
  }
}
```

## MIP-003 API Compliance

The agent exposes these endpoints for Masumi health checks:

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/api/diagnostic/mip003/availability` | `{"status": "available"}` |
| GET | `/api/diagnostic/mip003/input_schema` | `{"type": "object", "properties": {"plotId": "string"}}` |

## Registration via CLI

```bash
ADMIN_KEY="your_admin_key"

curl -X POST http://localhost:3100/api/v1/agents \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ADMIN_KEY" \
  -d '{
    "name": "FarmWise Potato Diagnostic Agent",
    "apiBaseUrl": "http://localhost:8000/api/diagnostic",
    "description": "AI-powered potato crop diagnostic agent for Kenyan farmers.",
    "authorName": "FarmWise Team",
    "authorOrganization": "FarmWise",
    "authorContactEmail": "farmwise@example.com",
    "paymentType": "Web3CardanoV1",
    "network": "Preprod",
    "tags": ["agriculture", "potato", "kenya"],
    "capability": { "name": "Custom Agent", "version": "1.0.0" },
    "pricing": { "amount": "0", "currency": "ADA", "period": "per_request" }
  }'
```

## On-Chain Verification

Every diagnostic recommendation creates a complete input→output→tx hash audit trail:
- **inputHash**: SHA-256 of canonical input JSON
- **outputHash**: SHA-256 of canonical output JSON
- **txHash**: Cardano Preprod transaction hash
- **onChainState**: Current Masumi state (CREATED → FundsLocked → ResultSubmitted)
- **agentIdentifier**: Full agent DID on Cardano
- **purchaserIdentifier**: Hex purchaser ID
