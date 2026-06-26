"""
Daily Diagnostic Agent: GraphRAG synthesis — extracts the full connected
subgraph for a plot, feeds it to Featherless LLM, stores as DailyRecommendation,
and logs the decision on Masumi with full lifecycle (create + complete).
"""
import json
from datetime import datetime, timezone
from services.neo4j import query_one, query
from services.featherless import chat, safe_content
from services.masumi import (
    log_decision,
    complete_decision,
    build_canonical_input,
    build_canonical_output,
    sha256_hash,
    _build_agent_identifier,
    _build_purchaser_id,
)
from config import settings


async def extract_subgraph(plot_id: str) -> dict:
    """Extract the connected subgraph for a plot's most recent observation day."""
    ctx = query_one(
        """
        MATCH (p:Plot {plotId: $plot_id})-[:AT_STAGE]->(gs:GrowthStage)
        MATCH (p)-[:HAS_OBSERVATION]->(obs)-[:OCCURRED_ON]->(d:TimeDay)
        WITH p, gs, d, obs
        ORDER BY d.date DESC
        WITH p, gs, collect(obs)[0..10] AS todayObs
        UNWIND todayObs AS obs
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(c:County)<-[:RELEVANT_TO]-(na:NewsAlert)
        OPTIONAL MATCH (p)-[:EXPERIENCED_STRESS]->(se:StressEvent)
            WHERE se.detectedAt >= datetime() - duration('P7D')
        OPTIONAL MATCH (gs)-[:HAS_RISK]->(pest:Pest)
        WITH p, gs,
             collect(DISTINCT properties(obs)) AS todayObsColl,
             collect(DISTINCT na.headline) AS alerts,
             collect(DISTINCT se.type) AS stressTypes,
             collect(DISTINCT pest.name) AS riskNames
        RETURN {
            plot: {
                plotId: p.plotId,
                name: p.name,
                latitude: p.latitude,
                longitude: p.longitude,
                sizeAcres: p.sizeAcres,
                variety: p.variety,
                plantingDate: toString(p.plantingDate),
                seasonDay: p.seasonDay,
                soilBaseline_N: p.soilBaseline_N,
                soilBaseline_pH: p.soilBaseline_pH,
                accumulatedGDD: p.accumulatedGDD,
                forecastedYieldKg: p.forecastedYieldKg
            },
            stage: gs.name,
            todayObservations: todayObsColl,
            activeAlerts: alerts,
            newStressEvents: stressTypes,
            stageRisks: riskNames,
            forecastedYieldKg: p.forecastedYieldKg
        } AS ctx
        """,
        {"plot_id": plot_id},
    )
    return ctx["ctx"] if ctx else {}


async def synthesize_diagnosis(subgraph: dict) -> dict:
    """Send subgraph to Featherless LLM for synthesis — LLM is translator, not decision-maker."""
    result = await chat(
        model=settings.FEATHERLESS_CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an agricultural diagnostic translator for potato farming in Kenya. "
                    "Given structured crop monitoring data, return ONLY a JSON object with these fields: "
                    '{"action": "what the farmer should do", '
                    '"cause": "why (pest/disease/stress name)", '
                    '"urgencyHours": number, '
                    '"narrative": "one clear sentence in English for the farmer", '
                    '"dataFreshness": number of days since latest satellite observation}. '
                    "Translate data into one actionable sentence. Do not invent actions. "
                    "If observations array is empty, set dataFreshness to 999. "
                    "Return ONLY valid JSON, no markdown, no explanation."
                ),
            },
            {"role": "user", "content": json.dumps(subgraph)},
        ],
    )

    content = safe_content(result)
    content = content.strip().removeprefix("```json").removesuffix("```").strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "action": "monitor_crop",
            "cause": "insufficient_data",
            "urgencyHours": 24,
            "narrative": "No data available for today. Continue monitoring your farm and check back tomorrow.",
            "dataFreshness": 999,
        }


async def store_recommendation(
    plot_id: str, diagnosis: dict, subgraph: dict
) -> tuple[str, str]:
    """
    Store recommendation in Neo4j and log decision on Masumi.
    Stores full audit trail: inputHash, outputHash, txHash, onChainState,
    agentIdentifier, purchaserIdentifier.
    Returns (tx_hash, masumi_status).
    """
    query(
        """
        MATCH (p:Plot {plotId: $plot_id})
        CREATE (rec:DailyRecommendation {
            date: date(),
            action: $action,
            cause: $cause,
            urgencyHours: $urgency,
            narrative: $narrative,
            dataFreshness: $freshness
        })
        CREATE (p)-[:HAS_RECOMMENDATION]->(rec)
        """,
        {
            "plot_id": plot_id,
            "action": diagnosis.get("action", "monitor_crop"),
            "cause": diagnosis.get("cause", "unknown"),
            "urgency": diagnosis.get("urgencyHours", 24),
            "narrative": diagnosis.get("narrative", ""),
            "freshness": diagnosis.get("dataFreshness", 0),
        },
    )

    agent_identifier = _build_agent_identifier()
    purchaser_identifier = _build_purchaser_id()

    masumi_payload = {
        "plotId": plot_id,
        "action": diagnosis.get("action", ""),
        "cause": diagnosis.get("cause", ""),
        "urgencyHours": diagnosis.get("urgencyHours", 0),
        "stage": subgraph.get("stage", "unknown"),
        "forecastedYieldKg": subgraph.get("forecastedYieldKg", 0),
        "narrative": diagnosis.get("narrative", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    canonical_input = build_canonical_input(masumi_payload)
    canonical_output = build_canonical_output(diagnosis)
    input_hash = sha256_hash(canonical_input)
    output_hash = sha256_hash(canonical_output)
    timestamp = datetime.now(timezone.utc).isoformat()

    masumi_status = "SUBMITTED"
    tx_hash = None
    on_chain_state = "CREATED"

    try:
        tx_hash = await log_decision(masumi_payload)
    except Exception as e:
        masumi_status = f"CREATE_FAILED: {str(e)}"

    if tx_hash:
        query(
            """
            MATCH (p:Plot {plotId: $plot_id})-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation {date: date()})
            CREATE (tx:MasumiTxHash {
                hash: $hash,
                inputHash: $input_hash,
                outputHash: $output_hash,
                status: $status,
                onChainState: $chain_state,
                agentIdentifier: $agent_id,
                purchaserIdentifier: $purchaser_id,
                verifiedAt: $timestamp,
                network: 'Preprod'
            })
            CREATE (rec)-[:HAS_TX]->(tx)
            """,
            {
                "plot_id": plot_id,
                "hash": tx_hash,
                "input_hash": input_hash,
                "output_hash": output_hash,
                "status": masumi_status,
                "chain_state": on_chain_state,
                "agent_id": agent_identifier,
                "purchaser_id": purchaser_identifier,
                "timestamp": timestamp,
            },
        )

        try:
            completion = await complete_decision(tx_hash, diagnosis)
            on_chain_state = completion.get("onChainState", "FundsLocked")
            if completion.get("verified"):
                masumi_status = "VERIFIED_ON_CHAIN"
            elif on_chain_state:
                masumi_status = on_chain_state
            query(
                """
                MATCH (tx:MasumiTxHash {hash: $hash})
                SET tx.status = $status, tx.onChainState = $chain_state
                """,
                {"hash": tx_hash, "status": masumi_status, "chain_state": on_chain_state},
            )
        except Exception as e:
            masumi_status = f"COMPLETE_PENDING: {str(e)}"
            query(
                """
                MATCH (tx:MasumiTxHash {hash: $hash})
                SET tx.status = $status, tx.onChainState = $chain_state
                """,
                {"hash": tx_hash, "status": masumi_status, "chain_state": on_chain_state},
            )

    return tx_hash or "", masumi_status


async def run_diagnostic(plot_id: str) -> dict:
    """Full diagnostic pipeline: extract → synthesize → store → log on Masumi."""
    subgraph = await extract_subgraph(plot_id)
    diagnosis = await synthesize_diagnosis(subgraph)
    tx_hash, masumi_status = await store_recommendation(plot_id, diagnosis, subgraph)

    return {
        "action": diagnosis.get("action"),
        "cause": diagnosis.get("cause"),
        "urgencyHours": diagnosis.get("urgencyHours"),
        "narrative": diagnosis.get("narrative"),
        "dataFreshness": diagnosis.get("dataFreshness"),
        "masumiTxHash": tx_hash,
        "masumiStatus": masumi_status,
    }


async def run_batch_diagnostics() -> list[dict]:
    """Run diagnostic for all plots — one Masumi tx per plot."""
    plots = query("MATCH (p:Plot) RETURN p.plotId AS plotId")
    results = []
    for p in plots:
        try:
            result = await run_diagnostic(p["plotId"])
            results.append(result)
        except Exception as e:
            results.append({"plotId": p["plotId"], "error": str(e)})
    return results


async def run_pest_diagnosis(plot_id: str) -> list[dict]:
    """Run knowledge graph pest diagnosis traversal."""
    results = query(
        """
        MATCH (p:Plot {plotId: $plot_id})-[:AT_STAGE]->(gs:GrowthStage)
        MATCH (p)-[:HAS_OBSERVATION]->(w:Observation_Weather)-[:OCCURRED_ON]->(d:TimeDay {date: date()})
        MATCH (gs)-[:HAS_RISK]->(pest:Pest)-[:THRIVES_IN]->(wc:WeatherCondition)
        WHERE w.tempMin >= wc.tempMin AND w.tempMax <= wc.tempMax
            AND w.precipitation >= COALESCE(wc.humidityMin, 0)
        MATCH (pest)-[:DETECTED_BY]->(s:Symptom)-[:TREATED_BY]->(i:Intervention)
        RETURN pest.name AS cause, pest.scientificName AS scientific,
               i.action, i.urgencyHours, i.method, gs.name AS stage
        """,
        {"plot_id": plot_id},
    )

    return results
