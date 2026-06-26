---
name: farmwise-featherless-patterns
description: Featherless AI API patterns for FarmWise. Use when calling LLM, VLM, or TTS APIs via Featherless. Triggers on AI agent code, chat completions, image classification, or TTS generation.
---

# FarmWise Featherless API Patterns

## Chat Completion
```python
import httpx
FEATHERLESS_URL = "https://api.featherless.ai/v1"

async def chat(model: str, messages: list[dict]) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{FEATHERLESS_URL}/chat/completions",
            headers={"Authorization": f"Bearer {settings.FEATHERLESS_API_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.3},
        )
        return res.json()
```

## Models
- Vision: `Llama-3.2-11B-Vision` (farmer photo classification)
- Chat: `Llama-3-8B-Instruct` (news summarization, translation)
- TTS: `AfriqueGemma-12B` (Swahili speech generation)

## Translation Pipeline
1. English text → chat(model, [{system: "Translate to Kiswahili. Output ONLY the Swahili text."}, {user: english_text}])
2. Swahili text → text_to_speech(swahili_text)
3. .ogg file → save to static/audio/ → return URL

## Diagnostic LLM Prompt
System: "You are an agricultural diagnostic translator. Given structured crop data, return JSON: {action, cause, urgencyHours, narrative, dataFreshness}. Translate data into one clear farmer-facing sentence. If data >1 day old, note dataFreshness."
User: json.dumps(subgraph_context)
