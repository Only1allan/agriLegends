"""
Ground Truth Agent: Classifies farmer WhatsApp photos using Featherless VLM.
Writes classified FarmerLog nodes to Neo4j.
"""
import json
from services.featherless import chat, safe_content
from services.neo4j import query
from config import settings


async def classify_farmer_image(image_url: str, caption: str = "") -> dict:
    """Classify farmer-submitted potato crop image using Vision LLM."""
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Classify this potato crop image. Return ONLY a JSON object with these fields: "
                        '{"classification": "one of: healthy, late_blight, early_blight, bacterial_wilt, '
                        'nutrient_deficiency, pest_damage, moisture_stress, other", '
                        '"confidence": float 0-1, "notes": "brief observation"}. '
                        "Do not include markdown, code blocks, or any text outside the JSON."
                    ),
                },
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]

    if caption:
        messages.insert(
            0,
            {
                "role": "user",
                "content": [{"type": "text", "text": f"Farmer note: {caption}"}],
            },
        )

    result = await chat(model=settings.FEATHERLESS_VISION_MODEL, messages=messages)
    content = safe_content(result, '{"classification": "other", "confidence": 0.5}')
    content = content.strip().removeprefix("```json").removesuffix("```").strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {"classification": "other", "confidence": 0.5, "notes": content[:200]}

    return parsed


async def ingest_ground_truth(
    farmer_id: str, plot_id: str, image_url: str, caption: str = ""
) -> dict:
    """Classify farmer image and store as FarmerLog node."""
    classification = await classify_farmer_image(image_url, caption)

    query(
        """
        MATCH (p:Plot {plotId: $plot_id})
        MATCH (f:Farmer {farmerId: $farmer_id})
        CREATE (log:FarmerLog {
            textRecord: $caption,
            mediaUrl: $url,
            classification: $class,
            confidence: $conf,
            timestamp: datetime()
        })
        CREATE (p)-[:HAS_OBSERVATION]->(log)
        CREATE (f)-[:HAS_LOG]->(log)
        """,
        {
            "plot_id": plot_id,
            "farmer_id": farmer_id,
            "caption": caption or classification.get("notes", ""),
            "url": image_url,
            "class": classification["classification"],
            "conf": classification["confidence"],
        },
    )

    return classification
