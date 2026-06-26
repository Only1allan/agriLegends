import asyncio
import logging
import httpx
from config import settings

logger = logging.getLogger("farmwise.featherless")

FEATHERLESS_URL = "https://api.featherless.ai/v1"
HEADERS = {
    "Authorization": f"Bearer {settings.FEATHERLESS_API_KEY}",
    "Content-Type": "application/json",
}

MAX_RETRIES = 3
BASE_DELAY = 2.0
MAX_DELAY = 30.0


async def chat(model: str, messages: list[dict]) -> dict:
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    f"{FEATHERLESS_URL}/chat/completions",
                    headers=HEADERS,
                    json={"model": model, "messages": messages, "temperature": 0.3},
                )
                if res.status_code == 429:
                    retry_after = res.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    logger.warning("Featherless rate limited (429), attempt %d/%d, waiting %.1fs", attempt + 1, MAX_RETRIES, wait)
                    await asyncio.sleep(wait)
                    continue
                res.raise_for_status()
                return res.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                continue
            last_error = e
            logger.error("Featherless HTTP error: %s", e)
            if attempt < MAX_RETRIES - 1:
                wait = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                await asyncio.sleep(wait)
            else:
                raise
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_error = e
            logger.error("Featherless connection error: %s", e)
            if attempt < MAX_RETRIES - 1:
                wait = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                await asyncio.sleep(wait)
            else:
                raise
    if last_error:
        raise last_error
    raise RuntimeError("Featherless chat: max retries exhausted")


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
