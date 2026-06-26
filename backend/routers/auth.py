import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.neo4j import query, query_one
from services.twilio import verify_send_otp, verify_check_otp
from config import settings

router = APIRouter()


class SendOTPRequest(BaseModel):
    phone: str


class VerifyOTPRequest(BaseModel):
    phone: str
    code: str


class AuthResponse(BaseModel):
    farmerId: str
    token: str

MOCK_MODE = not settings.TWILIO_VERIFY_SERVICE_SID


@router.post("/send-otp")
async def send_otp(req: SendOTPRequest):
    if MOCK_MODE:
        return {"status": "pending", "phone": req.phone, "mock": True}
    try:
        result = verify_send_otp(req.phone)
        return {"status": result.get("status", "sent"), "phone": req.phone}
    except Exception as e:
        err = str(e)
        if "unverified" in err.lower() or "trial" in err.lower():
            return {"status": "pending", "phone": req.phone, "mock": True,
                    "note": "Trial account - OTP simulated"}
        raise HTTPException(status_code=502, detail=f"Failed to send OTP: {err}")


@router.post("/verify-otp")
async def verify_otp(req: VerifyOTPRequest) -> AuthResponse:
    if not MOCK_MODE:
        try:
            check = verify_check_otp(req.phone, req.code)
            if check.get("status") != "approved":
                raise HTTPException(status_code=401, detail="Invalid OTP code")
        except HTTPException:
            raise
        except Exception as e:
            err = str(e)
            if "unverified" not in err.lower() and "trial" not in err.lower() and "not found" not in err.lower():
                raise HTTPException(status_code=502, detail=f"OTP verification failed: {err}")
            # Fall through to mock mode on any Twilio error

    existing = query_one(
        "MATCH (f:Farmer {phone: $phone}) RETURN f.farmerId AS farmerId",
        {"phone": req.phone},
    )

    if existing:
        farmer_id = existing["farmerId"]
    else:
        farmer_id = str(uuid.uuid4())
        query(
            """
            CREATE (f:Farmer {
                farmerId: $id, phone: $phone, name: '',
                preferredChannel: ['whatsapp_text'], preferredLanguage: 'en',
                masumiDid: '', registrationDate: date()
            })
            """,
            {"id": farmer_id, "phone": req.phone},
        )

    return AuthResponse(farmerId=farmer_id, token=f"tok_{farmer_id[:8]}")
