from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.neo4j import query, query_one
from services.featherless import chat_completion
from routers.auth import get_current_farmer

router = APIRouter()


class AlertStatusUpdate(BaseModel):
    status: str


class ChatMessage(BaseModel):
    role: str
    content: str


class AlertChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] | None = None


@router.get("/seasons/{season_id}/alerts")
async def get_alerts(season_id: str, farmer: dict = Depends(get_current_farmer)) -> list[dict]:
    return query("""
        MATCH (s:Season {seasonId: $sid})-[:GENERATED]->(a:Alert)
        OPTIONAL MATCH (a)-[:TRIGGERED_BY]->(d:DailySnapshot)
        RETURN a.alertId AS alertId, a.detected_condition AS detectedCondition,
               a.confidence AS confidence, a.explanation AS explanation,
               a.recommendation AS recommendation, a.urgency AS urgency,
               a.status AS status, a.createdAt AS createdAt,
               a.dispatchedAt AS dispatchedAt, a.sms_english AS smsEnglish,
               a.sms_swahili AS smsSwahili, d.date AS snapshotDate
        ORDER BY a.createdAt DESC
    """, {"sid": season_id})


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str, farmer: dict = Depends(get_current_farmer)):
    result = query_one("""
        MATCH (a:Alert {alertId: $aid})
        OPTIONAL MATCH (a)-[:TRIGGERED_BY]->(d:DailySnapshot)
        RETURN a, d AS snapshot
    """, {"aid": alert_id})
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return result


@router.patch("/alerts/{alert_id}/status")
async def update_alert_status(alert_id: str, req: AlertStatusUpdate, farmer: dict = Depends(get_current_farmer)):
    if req.status not in ("RESOLVED", "IGNORED", "ACTIVE"):
        raise HTTPException(status_code=400, detail="Invalid status. Use RESOLVED, IGNORED, or ACTIVE")
    query("""
        MATCH (a:Alert {alertId: $aid})
        SET a.status = $status
    """, {"aid": alert_id, "status": req.status})
    return {"alertId": alert_id, "status": req.status}


@router.post("/alerts/{alert_id}/chat")
async def chat_with_alert(alert_id: str, req: AlertChatRequest, farmer: dict = Depends(get_current_farmer)):
    alert = query_one("""
        MATCH (a:Alert {alertId: $aid})
        OPTIONAL MATCH (a)-[:TRIGGERED_BY]->(d:DailySnapshot)
        RETURN a.detected_condition AS condition, a.explanation AS explanation,
               a.recommendation AS recommendation, d.daily_avg_temp_c AS temp,
               d.daily_precip_mm AS precip, d.mean_ndvi AS ndvi
    """, {"aid": alert_id})

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    system = (
        f"You are a potato farming advisor. The farmer has a '{alert.get('condition', '')}' alert. "
        f"Context: {alert.get('explanation', '')}. Recommendation: {alert.get('recommendation', '')}. "
        f"Temperature: {alert.get('temp', 'N/A')}°C, Precipitation: {alert.get('precip', 'N/A')}mm. "
        f"Respond helpfully in English or Swahili."
    )

    messages = []
    if req.history:
        messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    reply = await chat_completion(system, messages)
    return {"reply": reply}
