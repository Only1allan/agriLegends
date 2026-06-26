from twilio.rest import Client
from config import settings

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_whatsapp_text(to: str, body: str):
    return client.messages.create(
        from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
        to=f"whatsapp:{to}",
        body=body,
    )


def send_whatsapp_audio(to: str, audio_url: str):
    return client.messages.create(
        from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
        to=f"whatsapp:{to}",
        media_url=[audio_url],
    )


def send_sms(to: str, body: str):
    return client.messages.create(
        from_=settings.TWILIO_PHONE_NUMBER,
        to=to,
        body=body,
    )


def verify_send_otp(phone: str) -> dict:
    """Send OTP via Twilio Verify. Requires TWILIO_VERIFY_SERVICE_SID in .env."""
    verification = client.verify.v2.services(
        settings.TWILIO_VERIFY_SERVICE_SID
    ).verifications.create(to=phone, channel="sms")
    return {"status": verification.status, "sid": verification.sid}


def verify_check_otp(phone: str, code: str) -> dict:
    """Check OTP code via Twilio Verify."""
    check = client.verify.v2.services(
        settings.TWILIO_VERIFY_SERVICE_SID
    ).verification_checks.create(to=phone, code=code)
    return {"status": check.status, "sid": check.sid}
