import logging
from config import settings

logger = logging.getLogger("farmwise.at_service")

_at_initialized = False


def init_at():
    global _at_initialized
    if not settings.AT_API_KEY or not settings.AT_USERNAME:
        logger.warning("Africa's Talking not configured — SMS dispatch disabled")
        return
    try:
        import africastalking
        africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
        _at_initialized = True
        logger.info("Africa's Talking initialized")
    except Exception as e:
        logger.error("Failed to initialize Africa's Talking: %s", e)


async def send_sms(phone: str, message: str) -> bool:
    if not _at_initialized:
        logger.warning("AT not initialized, skipping SMS to %s", phone)
        return False
    try:
        import africastalking
        sms = africastalking.SMS
        recipients = [phone.replace("+", "")]
        response = sms.send(message, recipients, settings.AT_SENDER_ID)
        if not response or "SMSMessageData" not in response:
            logger.error("AT SMS unexpected response: %s", response)
            return False
        data = response["SMSMessageData"]
        recips = data.get("Recipients", [])
        if not recips:
            return False
        status = recips[0].get("status", "")
        success = status == "Success"
        if not success:
            logger.warning("AT SMS failed for %s: status=%s", phone, status)
        return success
    except Exception as e:
        logger.error("AT SMS exception for %s: %s", phone, e)
        return False


async def send_whatsapp(phone: str, message: str) -> bool:
    logger.info("AT WhatsApp send attempted for %s (channel stub)", phone)
    return await send_sms(phone, message)
