import logging
from datetime import datetime, timezone
from services.neo4j import query
from services.at_service import send_sms, send_whatsapp

logger = logging.getLogger("farmwise.pipeline_c")


async def run_pipeline_c():
    logger.info("Pipeline C: Morning alert dispatcher starting")

    alerts = query("""
        MATCH (p:Plot)<-[:OWNS]-(f:Farmer)
        MATCH (p)-[:HAS_SEASON]->(s:Season)-[:GENERATED]->(a:Alert {status: "ACTIVE"})
        WHERE a.retryCount IS NULL OR a.retryCount < 3
        RETURN f.phone AS phone, f.name AS farmerName,
               p.name AS plotName, a.alertId AS alertId,
               a.sms_swahili AS smsSwahili, a.sms_english AS smsEnglish,
               a.urgency AS urgency, coalesce(a.retryCount, 0) AS retryCount
    """)

    logger.info("Pipeline C: %d alerts to dispatch", len(alerts))

    for alert in alerts:
        alert_id = alert["alertId"]
        phone = alert.get("phone", "")
        message = alert.get("smsSwahili") or alert.get("smsEnglish") or "Angalia shamba lako. Tafadhali fungua FarmWise kwa maelezo zaidi."

        if not phone:
            logger.warning("Pipeline C: No phone for alert %s", alert_id)
            continue

        try:
            sms_ok = await send_sms(phone, message)
            wa_ok = await send_whatsapp(phone, message)
            success = sms_ok or wa_ok

            now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
            if success:
                query("""
                    MATCH (a:Alert {alertId: $aid})
                    SET a.status = 'SENT', a.dispatchedAt = $ts
                """, {"aid": alert_id, "ts": now_ts})
                logger.info("Pipeline C: Alert %s dispatched to %s", alert_id, phone)
            else:
                retry = alert.get("retryCount", 0) + 1
                if retry >= 3:
                    query("""
                        MATCH (a:Alert {alertId: $aid})
                        SET a.status = 'FAILED', a.retryCount = $rc
                    """, {"aid": alert_id, "rc": retry})
                else:
                    query("""
                        MATCH (a:Alert {alertId: $aid})
                        SET a.retryCount = $rc
                    """, {"aid": alert_id, "rc": retry})
                logger.warning("Pipeline C: Dispatch failed for %s (retry %d/3)", alert_id, retry)

        except Exception as e:
            logger.exception("Pipeline C: Exception dispatching alert %s", alert_id)

    logger.info("Pipeline C: Complete")
