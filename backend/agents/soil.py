"""
Soil Baseline Agent: Fetches soil properties from iSDAsoil API
at 30m resolution and writes to Plot node properties.
Auth: username/password login → Bearer token (60-min TTL).
"""
import time
import httpx
from config import settings
from services.neo4j import query

ISDA_BASE = "https://api.isda-africa.com"
SOIL_PROPERTIES = ["ph", "nitrogen_total", "carbon_total", "aluminium_extractable", "carbon_organic"]

_token_cache: dict | None = None
_token_expiry: float = 0.0


async def login() -> str:
    """Login to iSDAsoil and return access token. Cached for 55 minutes."""
    global _token_cache, _token_expiry

    if _token_cache and time.time() < _token_expiry:
        return _token_cache["access_token"]

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{ISDA_BASE}/login",
            data={
                "username": settings.ISDA_USERNAME,
                "password": settings.ISDA_PASSWORD,
            },
        )
        res.raise_for_status()
        _token_cache = res.json()
        _token_expiry = time.time() + 3300  # Re-login at 55 min (token expires 60 min)
        return _token_cache["access_token"]


async def fetch_property(lat: float, lon: float, prop: str, depth: str = "0-20") -> float | None:
    """Fetch a single soil property value for a coordinate."""
    token = await login()

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{ISDA_BASE}/isdasoil/v2/soilproperty",
            params={
                "lat": lat,
                "lon": lon,
                "property": prop,
                "depth": depth,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        res.raise_for_status()
        data = res.json()

    try:
        values = data["property"][prop]
        if values and len(values) > 0:
            return values[0]["value"]["value"]
    except (KeyError, IndexError, TypeError):
        pass

    return None


async def get_soil_baseline(lat: float, lon: float) -> dict:
    """Fetch all soil properties for plot coordinates."""
    results = {}

    for prop in SOIL_PROPERTIES:
        try:
            value = await fetch_property(lat, lon, prop)
            if value is not None:
                results[prop] = value
        except Exception:
            continue

    return results


async def ingest_soil(lat: float, lon: float, plot_id: str) -> dict:
    """Fetch soil baseline and update plot properties in Neo4j."""
    soil = await get_soil_baseline(lat, lon)

    n_value = soil.get("nitrogen_total", 0)
    ph_value = soil.get("ph", 7)
    carbon_value = soil.get("carbon_total", 0)
    al_value = soil.get("aluminium_extractable", 0)
    oc_value = soil.get("carbon_organic", 0)

    query(
        """
        MATCH (p:Plot {plotId: $plot_id})
        SET p.soilBaseline_N = $n,
            p.soilBaseline_pH = $ph,
            p.soilBaseline_C = $carbon,
            p.soilBaseline_Al = $al,
            p.soilBaseline_OC = $oc
        """,
        {
            "plot_id": plot_id,
            "n": n_value,
            "ph": ph_value,
            "carbon": carbon_value,
            "al": al_value,
            "oc": oc_value,
        },
    )

    return {
        "nitrogen_total": n_value,
        "ph": ph_value,
        "carbon_total": carbon_value,
        "aluminium_extractable": al_value,
        "carbon_organic": oc_value,
    }


async def check_soil_amendment(plot_id: str) -> list[str]:
    """Compare plot soil against stage-specific soil requirements.

    Resolves SoilRequirement by stage name directly — no pre-existing
    SOIL_COMPARED_TO edge required.  Comparison happens in Python so
    that fresh plots work without a prior seed run tying edges.
    """
    result = query(
        """
        MATCH (p:Plot {plotId: $plot_id})-[:AT_STAGE]->(gs:GrowthStage)
        MATCH (sr:SoilRequirement {stage: gs.name})
        RETURN p.soilBaseline_pH AS currentPH,
               p.soilBaseline_N AS currentN,
               sr.nitrogenTarget AS targetN,
               sr.phTarget AS targetPH
        """,
        {"plot_id": plot_id},
    )

    actions: list[str] = []
    for record in result:
        if record.get("currentPH") is not None and record.get("targetPH") is not None:
            if record["currentPH"] < record["targetPH"]:
                actions.append("pH below target — apply lime")
        if record.get("currentN") is not None and record.get("targetN") is not None:
            if record["currentN"] < record["targetN"]:
                actions.append("N below target — apply nitrogen top-dress")
    return actions
