import httpx
from config import settings

FEATHERLESS_URL = "https://api.featherless.ai/v1"
HEADERS = {
    "Authorization": f"Bearer {settings.FEATHERLESS_API_KEY}",
    "Content-Type": "application/json",
}


async def chat(model: str, messages: list[dict]) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(
            f"{FEATHERLESS_URL}/chat/completions",
            headers=HEADERS,
            json={"model": model, "messages": messages, "temperature": 0.3},
        )
        res.raise_for_status()
        return res.json()


def safe_content(result: dict, default: str = "") -> str:
    """Safely extract LLM response content without crashing on unexpected shapes."""
    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return default


async def get_embedding(text: str, model: str = "openai/text-embedding-3-small") -> list[float] | None:
    result = await chat(model, [{"role": "user", "content": f"Embed: {text}"}])
    content = safe_content(result, "[]")
    content = content.strip()
    if content.startswith("[") and content.endswith("]"):
        try:
            return [float(x) for x in content.strip("[]").split(",")]
        except ValueError:
            pass
    return None


async def text_to_speech(text: str) -> bytes:
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(
            f"{FEATHERLESS_URL}/audio/speech",
            headers=HEADERS,
            json={
                "model": settings.FEATHERLESS_TTS_MODEL,
                "input": text,
                "voice": "swahili-female",
            },
        )
        res.raise_for_status()
        return res.content
