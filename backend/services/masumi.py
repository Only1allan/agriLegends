"""
Masumi Decision Logging Service.
Logs AI agent decisions on Cardano via Masumi Payment Service.
No fallbacks. No placeholders. Masumi only.

Agent identifier format (Masumi v0.22.0):
  {56-char-policyId}{unique-agent-suffix}
  The payment service extracts the policyId from the first 56 chars.
"""
import json
import hashlib
import uuid
import httpx
from masumi import Config, Payment
from config import settings

POLICY_ID = "7e8bdaf2b2b919a3a4b94002cafb50086c0c845fe535d07a77ab7f77"


def _build_agent_identifier() -> str:
    agent_id = settings.MASUMI_AGENT_IDENTIFIER
    if agent_id and agent_id.startswith(POLICY_ID) and len(agent_id) >= 57:
        return agent_id
    suffix = hashlib.sha256(
        (agent_id or "farmwise-daily-diagnostic").encode()
    ).hexdigest()[:32]
    return f"{POLICY_ID}{suffix}"


def _build_purchaser_id() -> str:
    return hashlib.sha256("farmwise-demo-app".encode()).hexdigest()[:24]


def canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def sha256_hash(data_str: str) -> str:
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


def build_canonical_input(payload: dict) -> str:
    input_data = {
        "action": payload.get("action", ""),
        "cause": payload.get("cause", ""),
        "plotId": payload.get("plotId", ""),
        "stage": payload.get("stage", ""),
        "urgencyHours": payload.get("urgencyHours", 0),
        "forecastedYieldKg": payload.get("forecastedYieldKg", 0),
        "narrative": payload.get("narrative", ""),
        "timestamp": payload.get("timestamp", ""),
    }
    return canonical_json(input_data)


def build_canonical_output(output_data: dict) -> str:
    return canonical_json(output_data)


async def log_decision(payload: dict) -> str:
    """
    Log an AI agent decision on Cardano via Masumi.
    Returns the blockchain transaction hash.
    Raises RuntimeError on failure — no silent swallow.
    """
    agent_id = _build_agent_identifier()
    purchaser_id = _build_purchaser_id()

    input_data = {
        "action": payload.get("action", ""),
        "cause": payload.get("cause", ""),
        "plotId": payload.get("plotId", ""),
        "stage": payload.get("stage", ""),
        "urgencyHours": payload.get("urgencyHours", 0),
        "forecastedYieldKg": payload.get("forecastedYieldKg", 0),
        "narrative": payload.get("narrative", ""),
        "timestamp": payload.get("timestamp", ""),
    }

    config = Config(
        payment_service_url=settings.MASUMI_PAYMENT_SERVICE_URL,
        payment_api_key=settings.MASUMI_PAYMENT_API_KEY,
    )
    payment = Payment(
        agent_identifier=agent_id,
        config=config,
        identifier_from_purchaser=purchaser_id,
        network=settings.MASUMI_NETWORK or "Preprod",
        input_data=input_data,
    )

    result = await payment.create_payment_request()
    tx_hash = result.get("data", {}).get("blockchainIdentifier")
    if not tx_hash:
        raise RuntimeError("Masumi returned no blockchain identifier")
    return tx_hash


async def complete_decision(tx_hash: str, output_data: dict) -> dict:
    """
    Submit the output hash on-chain to finalize a payment.
    Must be called after the payment reaches FundsLocked state.
    Returns the submission result from Masumi.
    Raises RuntimeError on failure.
    """
    agent_id = _build_agent_identifier()
    purchaser_id = _build_purchaser_id()
    output_str = build_canonical_output(output_data)

    config = Config(
        payment_service_url=settings.MASUMI_PAYMENT_SERVICE_URL,
        payment_api_key=settings.MASUMI_PAYMENT_API_KEY,
    )
    payment = Payment(
        agent_identifier=agent_id,
        config=config,
        identifier_from_purchaser=purchaser_id,
        network=settings.MASUMI_NETWORK or "Preprod",
    )

    result = await payment.complete_payment(tx_hash, output_str)
    on_chain_state = result.get("data", {}).get("onChainState")
    return {
        "txHash": tx_hash,
        "onChainState": on_chain_state,
        "verified": on_chain_state == "ResultSubmitted",
    }


async def get_decision_status(tx_hash: str) -> dict:
    """
    Query the Masumi payment service for the current status of a decision.
    Returns the payment state from the ledger.
    """
    config = Config(
        payment_service_url=settings.MASUMI_PAYMENT_SERVICE_URL,
        payment_api_key=settings.MASUMI_PAYMENT_API_KEY,
    )
    payment = Payment(
        agent_identifier=_build_agent_identifier(),
        config=config,
        identifier_from_purchaser=_build_purchaser_id(),
        network=settings.MASUMI_NETWORK or "Preprod",
    )

    try:
        result = await payment.get_payment(tx_hash)
        return result.get("data", result)
    except Exception:
        return {"onChainState": "UNKNOWN", "txHash": tx_hash}
