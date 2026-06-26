from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from services.neo4j import query_one, query

router = APIRouter()


class RecommendationResponse(BaseModel):
    action: str
    cause: str
    urgencyHours: int
    narrative: str
    date: str
    dataFreshness: int
    masumiTxHash: str | None = None
    masumiStatus: str | None = None


class CertificateResponse(BaseModel):
    farmerId: str
    plotId: str
    plotName: str
    variety: str
    seasonDay: int
    recommendationAction: str
    recommendationCause: str
    recommendationNarrative: str
    recommendationDate: str
    monitoringDays: int
    stressEventsResolved: int
    currentYieldForecastKg: float
    masumiTxHash: str | None
    masumiStatus: str | None
    verified: bool
    audit_verified: bool


@router.get("/{plot_id}/recommendation")
async def get_recommendation(
    plot_id: str, date: str | None = Query(None, description="Date YYYY-MM-DD, defaults to today")
) -> RecommendationResponse:
    target_date = date or "date()"
    result = query_one(
        f"""
        MATCH (p:Plot {{plotId: $pid}})-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation {{date: {target_date}}})
        OPTIONAL MATCH (rec)-[:HAS_TX]->(tx:MasumiTxHash)
        RETURN rec {{.action, .cause, .urgencyHours, .narrative, .dataFreshness, date: toString(rec.date), masumiTxHash: tx.hash, masumiStatus: tx.status}} AS rec
        """,
        {"pid": plot_id},
    )
    if not result:
        raise HTTPException(status_code=404, detail="No recommendation found for today")
    return RecommendationResponse(**result["rec"])


@router.get("/{plot_id}/observations")
async def get_observations(plot_id: str, days: int = Query(30, ge=1, le=365)) -> list[dict]:
    results = query(
        """
        MATCH (p:Plot {plotId: $pid})-[:HAS_OBSERVATION]->(obs:Observation_Satellite)-[:OCCURRED_ON]->(d:TimeDay)
        WHERE d.date >= date() - duration({days: $days})
        RETURN obs.ndvi AS ndvi, obs.evi AS evi, obs.cloudCover AS cloudCover,
               obs.source AS source, toString(d.date) AS date
        ORDER BY d.date
        """,
        {"pid": plot_id, "days": days},
    )
    return results


@router.get("/{plot_id}/certificate")
@router.get("/{plot_id}/certificate/{recommendation_date}")
async def get_certificate(plot_id: str, recommendation_date: str | None = None) -> CertificateResponse:
    target_date = f"date($rec_date)" if recommendation_date else "date()"

    result = query_one(
        f"""
        MATCH (p:Plot {{plotId: $pid}})
        OPTIONAL MATCH (f:Farmer)-[:OWNS]->(p)
        OPTIONAL MATCH (p)-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation {{date: {target_date}}})
        OPTIONAL MATCH (rec)-[:HAS_TX]->(tx:MasumiTxHash)
        OPTIONAL MATCH (p)-[:EXPERIENCED_STRESS]->(se:StressEvent)
        RETURN coalesce(f.farmerId, 'unknown') AS farmerId,
               p.plotId AS plotId,
               p.name AS plotName,
               p.variety AS variety,
               p.seasonDay AS seasonDay,
               rec.action AS recommendationAction,
               rec.cause AS recommendationCause,
               rec.narrative AS recommendationNarrative,
               toString(rec.date) AS recommendationDate,
               count(DISTINCT se) AS stressEventsResolved,
               p.forecastedYieldKg AS currentYieldForecastKg,
               tx.hash AS masumiTxHash,
               tx.status AS masumiStatus,
               tx.inputHash AS inputHash,
               tx.outputHash AS outputHash
        """,
        {"pid": plot_id, "rec_date": recommendation_date or ""},
    )
    if not result:
        raise HTTPException(status_code=404, detail="Plot not found")

    tx_hash = result["masumiTxHash"]
    tx_status = result.get("masumiStatus")
    input_hash = result.get("inputHash")
    output_hash = result.get("outputHash")

    verified = bool(tx_hash) and tx_status == "VERIFIED_ON_CHAIN"
    audit_verified = (
        verified
        and bool(tx_hash)
        and bool(input_hash)
        and bool(output_hash)
        and tx_status == "VERIFIED_ON_CHAIN"
    )

    return CertificateResponse(
        farmerId=result["farmerId"],
        plotId=result["plotId"],
        plotName=result["plotName"] or "Unknown",
        variety=result["variety"] or "Unknown",
        seasonDay=result["seasonDay"] or 0,
        recommendationAction=result["recommendationAction"] or "",
        recommendationCause=result["recommendationCause"] or "",
        recommendationNarrative=result["recommendationNarrative"] or "",
        recommendationDate=result["recommendationDate"] or "",
        monitoringDays=0,
        stressEventsResolved=result["stressEventsResolved"] or 0,
        currentYieldForecastKg=result["currentYieldForecastKg"] or 0,
        masumiTxHash=tx_hash,
        masumiStatus=tx_status,
        verified=verified,
        audit_verified=audit_verified,
    )


@router.get("/{plot_id}/recommendations")
async def get_recommendations(plot_id: str) -> list[dict]:
    results = query(
        """
        MATCH (p:Plot {plotId: $pid})-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation)
        OPTIONAL MATCH (rec)-[:HAS_TX]->(tx:MasumiTxHash)
        RETURN rec.action AS action, rec.cause AS cause,
               rec.narrative AS narrative, rec.urgencyHours AS urgency,
               toString(rec.date) AS date, rec.dataFreshness AS dataFreshness,
               tx.hash AS txHash, tx.status AS masumiStatus
        ORDER BY rec.date DESC
        """,
        {"pid": plot_id},
    )
    return results


@router.get("/{plot_id}/audit-trail")
async def get_audit_trail(plot_id: str) -> list[dict]:
    """Return full Masumi audit trail for all recommendations on this plot."""
    results = query(
        """
        MATCH (p:Plot {plotId: $pid})-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation)
        OPTIONAL MATCH (rec)-[:HAS_TX]->(tx:MasumiTxHash)
        RETURN rec.action AS action, rec.cause AS cause,
               rec.narrative AS narrative, toString(rec.date) AS date,
               rec.urgencyHours AS urgencyHours,
               tx.hash AS txHash, tx.inputHash AS inputHash,
               tx.outputHash AS outputHash, tx.status AS status,
               tx.onChainState AS onChainState,
               tx.agentIdentifier AS agentIdentifier,
               tx.verifiedAt AS verifiedAt
        ORDER BY rec.date DESC
        """,
        {"pid": plot_id},
    )
    return results


@router.get("/{plot_id}/weather")
async def get_weather(plot_id: str, days: int = Query(14, ge=1, le=365)) -> list[dict]:
    results = query(
        """
        MATCH (p:Plot {plotId: $pid})-[:HAS_OBSERVATION]->(obs:Observation_Weather)-[:OCCURRED_ON]->(d:TimeDay)
        WHERE d.date >= date() - duration({days: $days})
        RETURN obs.tempMax AS tempMax, obs.tempMin AS tempMin,
               obs.precipitation AS precipitation, obs.humidity AS humidity,
               toString(d.date) AS date
        ORDER BY d.date
        """,
        {"pid": plot_id, "days": days},
    )
    return results


@router.get("/{plot_id}/growth")
async def get_growth_stage(plot_id: str):
    result = query_one(
        """
        MATCH (p:Plot {plotId: $pid})-[:AT_STAGE]->(gs:GrowthStage)
        RETURN gs.name AS stage, p.seasonDay AS day,
               gs.dayStart AS stageStart, gs.dayEnd AS stageEnd
        """,
        {"pid": plot_id},
    )
    if not result:
        raise HTTPException(status_code=404, detail="Plot not found")

    result["progress"] = min(
        100,
        max(0, (result["day"] - result["stageStart"]) / max(1, result["stageEnd"] - result["stageStart"]) * 100),
    )
    return result


@router.get("/{plot_id}/soil")
async def get_soil_data(plot_id: str):
    result = query_one(
        """
        MATCH (p:Plot {plotId: $pid})
        RETURN p.soilBaseline_N AS nitrogen_total,
               p.soilBaseline_pH AS ph,
               p.soilBaseline_C AS carbon_total,
               p.latitude AS latitude,
               p.longitude AS longitude
        """,
        {"pid": plot_id},
    )
    if not result:
        raise HTTPException(status_code=404, detail="Plot not found")
    return result


@router.get("/{plot_id}/stress")
async def get_stress_events(plot_id: str):
    results = query(
        """
        MATCH (p:Plot {plotId: $pid})-[:EXPERIENCED_STRESS]->(se:StressEvent)
        RETURN se.type AS type,
               se.detectedAt AS detectedAt,
               se.baselineNdvi AS baselineNdvi,
               se.currentNdvi AS currentNdvi,
               toString(se.detectedAt) AS date
        ORDER BY se.detectedAt DESC
        """,
        {"pid": plot_id},
    )
    return results
