from fastapi import APIRouter, Request, Form
from services.twilio import send_whatsapp_text
from config import settings

router = APIRouter()


@router.post("/whatsapp-webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
):
    farmer_phone = From.replace("whatsapp:", "")
    body_lower = Body.lower().strip()

    if body_lower in ("done", "yes", "ndio"):
        reply = "Asante! Tumerekodi kuwa umetekeleza ushauri wa leo. (Thank you! We've recorded that you completed today's advice.)"
    elif body_lower in ("no", "hapana", "couldn't"):
        reply = "Sawa. Tunaona haukuweza kutekeleza. Tutaboresha ushauri wa kesho. (Noted. We'll improve tomorrow's advice.)"
    else:
        reply = "Habari! Tumepokea ujumbe wako. Endelea kufuatilia ushauri wa kila siku. (We received your message. Continue checking your daily advice.)"

    send_whatsapp_text(farmer_phone, reply)
    return {"status": "ok"}


@router.post("/send-message")
async def send_message(
    to: str = Form(...),
    body: str = Form(...),
    channel: str = Form("whatsapp"),
):
    if channel == "whatsapp":
        send_whatsapp_text(to, body)
    elif channel == "sms":
        from services.twilio import send_sms
        send_sms(to, body)
    return {"status": "sent", "channel": channel}
