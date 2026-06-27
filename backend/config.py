import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", os.getenv("NEO4J_USERNAME", "neo4j"))
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")

    AGROMONITORING_API_KEY: str = os.getenv("AGROMONITORING_API_KEY", "")
    ISDA_USERNAME: str = os.getenv("ISDA_USERNAME", "")
    ISDA_PASSWORD: str = os.getenv("ISDA_PASSWORD", "")

    FEATHERLESS_API_KEY: str = os.getenv("FEATHERLESS_API_KEY", "")
    FEATHERLESS_VISION_MODEL: str = os.getenv("FEATHERLESS_VISION_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct")
    FEATHERLESS_CHAT_MODEL: str = os.getenv("FEATHERLESS_CHAT_MODEL", "deepseek-ai/DeepSeek-V4-Pro")
    FEATHERLESS_TTS_MODEL: str = os.getenv("FEATHERLESS_TTS_MODEL", "deepseek-ai/DeepSeek-V4-Pro")

    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_VERIFY_SERVICE_SID: str = os.getenv("TWILIO_VERIFY_SERVICE_SID", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")

    AT_API_KEY: str = os.getenv("AT_API_KEY", "")
    AT_USERNAME: str = os.getenv("AT_USERNAME", "")
    AT_SENDER_ID: str = os.getenv("AT_SENDER_ID", "FarmWise")

    OWM_API_KEY: str = os.getenv("OWM_API_KEY", "")

    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

    MASUMI_PAYMENT_SERVICE_URL: str = os.getenv("MASUMI_PAYMENT_SERVICE_URL", "http://localhost:3001/api/v1")
    MASUMI_PAYMENT_API_KEY: str = os.getenv("MASUMI_PAYMENT_API_KEY", "")
    MASUMI_AGENT_IDENTIFIER: str = os.getenv("MASUMI_AGENT_IDENTIFIER", "farmwise-daily-diagnostic")
    MASUMI_NETWORK: str = os.getenv("MASUMI_NETWORK", "Preprod")

    MASUMI_AGENT_NAME: str = os.getenv("MASUMI_AGENT_NAME", "PotatoNewsAgent")
    MASUMI_AGENT_DESCRIPTION: str = os.getenv("MASUMI_AGENT_DESCRIPTION", "Monitors and broadcasts potato crop advisories for Kenyan smallholders")

    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")


settings = Settings()
