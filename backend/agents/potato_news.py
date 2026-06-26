"""
Potato News Agent: Scrapes and summarizes KEPHIS/NPCK potato advisories
using Featherless LLM. Routes county-specific threats to NewsAlert nodes.
"""
import json
from datetime import datetime
from services.featherless import chat, safe_content
from services.neo4j import query
from config import settings


async def summarize_bulletin(raw_text: str, county: str) -> dict:
    """Summarize a KEPHIS/NPCK bulletin for a specific county."""
    result = await chat(
        model=settings.FEATHERLESS_CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an agricultural news parser for Kenya. "
                    "Given a raw advisory bulletin, extract threats relevant to potato farming. "
                    'Return ONLY a JSON object: {"headline": "summary", "threats": ["pest1", "pest2"], "urgency": "low|medium|high|critical", "action": "recommended action"}. '
                    "Do not include markdown or text outside the JSON."
                ),
            },
            {"role": "user", "content": f"County: {county}\n\nBulletin: {raw_text}"},
        ],
    )

    content = safe_content(result, '{"headline": "No threats detected", "threats": [], "urgency": "low", "action": "monitor"}')
    content = content.strip().removeprefix("```json").removesuffix("```").strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"headline": raw_text[:200], "threats": [], "urgency": "low", "action": "monitor"}


async def ingest_news(county: str, raw_bulletin: str, source: str = "KEPHIS") -> dict:
    """Summarize a bulletin and store as NewsAlert linked to the county."""
    summary = await summarize_bulletin(raw_bulletin, county)

    query(
        """
        MATCH (c:County {name: $county})
        CREATE (na:NewsAlert {
            headline: $headline,
            summary: $headline,
            county: $county,
            source: $source,
            urgency: $urgency,
            action: $action,
            timestamp: datetime()
        })
        CREATE (na)-[:RELEVANT_TO]->(c)
        """,
        {
            "county": county,
            "headline": summary["headline"],
            "source": source,
            "urgency": summary.get("urgency", "low"),
            "action": summary.get("action", "monitor"),
        },
    )

    return summary
