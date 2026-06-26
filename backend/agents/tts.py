"""
TTS Agent: Translates English agricultural advice to Swahili using Featherless LLM.
Audio generation is disabled (Featherless doesn't provide TTS endpoint).
Returns Swahili text only for the demo.
"""
from services.featherless import chat, safe_content
from config import settings


async def translate_to_swahili(english_text: str) -> str:
    """Translate English agricultural advice to Kiswahili using Featherless."""
    result = await chat(
        model=settings.FEATHERLESS_CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Translate the following agricultural advice to Kiswahili. "
                    "Use clear, simple language a farmer would understand. "
                    "Output ONLY the Swahili text, no commentary, no quotation marks."
                ),
            },
            {"role": "user", "content": english_text},
        ],
    )

    return safe_content(result, "Tafadhali fuata ushauri wa shamba lako.").strip()


async def generate_swahili_audio(english_text: str) -> dict:
    """Translate English → Swahili using Featherless LLM.
    Audio file generation is skipped — Featherless has no /audio/speech endpoint.
    Returns Swahili text and a null audioUrl for the demo.
    """
    swahili = await translate_to_swahili(english_text)

    return {
        "swahiliText": swahili,
        "audioUrl": None,  # TTS not available on Featherless
        "note": "Swahili text ready. Audio generation requires a TTS service.",
    }
