"""
Demo and utility endpoints: mailing list, WhatsApp test, demo credentials.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# In-memory mailing list (for demo)
_mailing_list: list[dict] = []


class MailingListRequest(BaseModel):
    email: str
    name: str = ""
    county: str = ""


class WhatsAppTestRequest(BaseModel):
    phone: str
    message: str = ""


@router.post("/mailing-list")
async def mailing_list(req: MailingListRequest):
    _mailing_list.append({"email": req.email, "name": req.name, "county": req.county})
    return {"status": "subscribed", "count": len(_mailing_list)}


@router.get("/mailing-list")
async def get_mailing_list():
    return {"subscribers": len(_mailing_list), "list": _mailing_list}


@router.post("/whatsapp-test")
async def whatsapp_test(req: WhatsAppTestRequest):
    """Send a test WhatsApp message to a phone number."""
    try:
        from services.twilio import send_whatsapp_text
        result = send_whatsapp_text(req.phone, req.message)
        return {"status": "sent", "to": req.phone, "sid": str(result.sid) if result else "unknown"}
    except Exception as e:
        return {"status": "failed", "error": str(e)[:200], "note": "Trial accounts cannot send WhatsApp messages without an approved sender."}
