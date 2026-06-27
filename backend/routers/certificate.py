"""
Certificate endpoint: Aggregates verified production records for a plot/season,
including Masumi blockchain audit trail.
"""
from fastapi import APIRouter, Depends
from services.neo4j import query, query_one
from routers.auth import get_current_farmer

router = APIRouter()


@router.get("/plots/{plot_id}/certificate")
async def get_certificate(plot_id: str, farmer: dict = Depends(get_current_farmer)):
    """Generate a verifiable production certificate for a plot."""
    cert = query_one("""
        MATCH (f:Farmer {farmerId: $fid})-[:OWNS]->(p:Plot {plotId: $pid})
        OPTIONAL MATCH (p)-[:HAS_SEASON]->(s:Season {status: "ACTIVE"})
        OPTIONAL MATCH (s)-[:PLANTED_WITH]->(v:PotatoVariety)
        OPTIONAL MATCH (s)-[:HAS_SNAPSHOT]->(d:DailySnapshot)
        OPTIONAL MATCH (s)-[:GENERATED]->(a:Alert)
        OPTIONAL MATCH (s)-[:HAS_OBSERVATION]->(o:FarmerObservation)
        OPTIONAL MATCH (s)-[:HAS_EXPENSE]->(e:Expense)
        OPTIONAL MATCH (a)-[:ADDRESSED_BY]-(i:Intervention)
        OPTIONAL MATCH (s)-[:HAS_FORECAST]->(f:YieldForecast)
        OPTIONAL MATCH (s)-[:HAS_SALE]->(sa:Sale)
        RETURN p.plotId AS plotId, p.name AS plotName, p.county AS county,
               p.areaHa AS areaHa, p.soilType AS soilType,
               toString(s.plantingDate) AS plantingDate,
               toString(s.expectedHarvestDate) AS expectedHarvestDate,
               coalesce(v.name, 'Shangi') AS variety,
               count(DISTINCT d) AS monitoringDays,
               count(DISTINCT a) AS alertCount,
               count(DISTINCT i) AS interventionCount,
               count(DISTINCT o) AS observationCount,
               count(DISTINCT e) AS expenseCount,
               coalesce(sum(e.amount), 0) AS totalExpenses,
               count(DISTINCT f) AS forecastCount,
               count(DISTINCT sa) AS saleCount,
               coalesce(sum(sa.total_amount), 0) AS totalRevenue
    """, {"fid": farmer["farmerId"], "pid": plot_id})

    if not cert:
        return None

    # Get Masumi audit trail
    masumi_records = query("""
        MATCH (p:Plot {plotId: $pid})-[:HAS_SEASON]->(s:Season)-[:GENERATED]->(a:Alert)
        WHERE a.masumiTxHash IS NOT NULL
        RETURN a.alertId AS alertId, a.detected_condition AS condition,
               a.status AS alertStatus, a.masumiTxHash AS txHash,
               coalesce(a.masumiStatus, 'UNKNOWN') AS masumiStatus,
               a.urgency AS urgency
    """, {"pid": plot_id})

    interventions = query("""
        MATCH (p:Plot {plotId: $pid})-[:HAS_SEASON]->(s:Season)-[:GENERATED]->(a:Alert)
        MATCH (i:Intervention)-[:ADDRESSES]->(a)
        OPTIONAL MATCH (i)-[:HAS_EXPENSE]->(e:Expense)
        RETURN a.alertId AS alertId, a.detected_condition AS condition,
               i.actionTaken AS action, i.date AS date,
               collect({category: e.category, amount: e.amount}) AS expenses
    """, {"pid": plot_id})

    cert["verified"] = any(r.get("masumiStatus") == "VERIFIED_ON_CHAIN" for r in masumi_records)
    cert["masumiRecords"] = masumi_records
    cert["interventions"] = interventions
    cert["totalExpenses"] = float(cert.get("totalExpenses", 0) or 0)
    cert["totalRevenue"] = float(cert.get("totalRevenue", 0) or 0)

    return cert


@router.get("/seasons/{season_id}/audit-trail")
async def get_audit_trail(season_id: str, farmer: dict = Depends(get_current_farmer)):
    """Get full audit trail for a season."""
    alerts = query("""
        MATCH (s:Season {seasonId: $sid})-[:GENERATED]->(a:Alert)
        OPTIONAL MATCH (i:Intervention)-[:ADDRESSES]->(a)
        OPTIONAL MATCH (i)-[:HAS_EXPENSE]->(e:Expense)
        OPTIONAL MATCH (a)-[:TRIGGERED_BY]->(d:DailySnapshot)
        RETURN a.alertId AS alertId, a.detected_condition AS condition,
               a.confidence AS confidence, a.urgency AS urgency,
               a.status AS alertStatus, a.masumiTxHash AS txHash,
               coalesce(a.masumiStatus, 'NOT_LOGGED') AS masumiStatus,
               a.createdAt AS createdAt,
               i.interventionId AS interventionId, i.actionTaken AS action,
               i.date AS interventionDate,
               collect({category: e.category, description: e.description,
                        amount: e.amount}) AS expenses,
               d.date AS snapshotDate
        ORDER BY a.createdAt DESC
    """, {"sid": season_id})

    interventions = query("""
        MATCH (s:Season {seasonId: $sid})-[:GENERATED]->(a:Alert)
        MATCH (i:Intervention)-[:ADDRESSES]->(a)
        OPTIONAL MATCH (i)-[:HAS_EXPENSE]->(e:Expense)
        RETURN i.interventionId AS id, i.actionTaken AS action, i.date AS date,
               a.detected_condition AS forCondition,
               sum(e.amount) AS totalCost,
               collect(e.category) AS categories
    """, {"sid": season_id})

    observations = query("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_OBSERVATION]->(o:FarmerObservation)
        RETURN o.observationId AS id, o.date AS date, o.notes AS notes,
               o.interpretationStatus AS status, o.interpretation AS interpretation
        ORDER BY o.date DESC
    """, {"sid": season_id})

    return {
        "seasonId": season_id,
        "alerts": alerts,
        "interventions": interventions,
        "observations": observations,
        "totalAlerts": len(alerts),
        "totalInterventions": len(interventions),
        "totalObservations": len(observations),
        "verifiedOnChain": any(a.get("masumiStatus") == "VERIFIED_ON_CHAIN" for a in alerts),
    }
