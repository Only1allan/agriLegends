import asyncio
import json
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


async def chat(model: str, messages: list[dict], temperature: float = 0.3) -> dict:
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(
                    f"{FEATHERLESS_URL}/chat/completions",
                    headers=HEADERS,
                    json={"model": model, "messages": messages, "temperature": temperature},
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
    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return default


async def structured_completion(system: str, user: str, schema: dict) -> dict:
    schema_text = json.dumps(schema, indent=2)
    full_system = f"{system}\n\nRespond ONLY with valid JSON matching this schema:\n{schema_text}"
    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": user},
    ]
    result = await chat(settings.FEATHERLESS_CHAT_MODEL, messages, temperature=0.2)
    content = safe_content(result, "{}")
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Structured completion: failed to parse JSON, raw: %s", content[:300])
        return {}


async def chat_completion(system: str, messages: list) -> str:
    all_messages = [{"role": "system", "content": system}] + messages
    result = await chat(settings.FEATHERLESS_CHAT_MODEL, all_messages, temperature=0.7)
    return safe_content(result, "")


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

