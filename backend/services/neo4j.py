import logging
from datetime import date, datetime as dt
from neo4j import GraphDatabase
from neo4j.time import Date, DateTime, Time
from config import settings

logger = logging.getLogger("farmwise.neo4j")

driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
)


from neo4j.graph import Node, Relationship

def _serialize_value(val):
    if isinstance(val, Node):
        result = dict(val.items())
        return {k: _serialize_value(v) for k, v in result.items()}
    if isinstance(val, Relationship):
        return {"id": val.id, "type": val.type, "properties": _serialize_value(dict(val.items()))}
    if isinstance(val, (Date, DateTime, Time)):
        return str(val)
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, dt):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_serialize_value(v) for v in val]
    return val


def _serialize_record(record: dict) -> dict:
    result = {}
    for k, v in record.items():
        serialized = _serialize_value(v)
        if isinstance(serialized, dict) and not isinstance(v, (dict, Node)):
            result.update(serialized)
        else:
            result[k] = serialized
    return result


def query(cypher: str, params: dict | None = None) -> list[dict]:
    records = []
    with driver.session() as session:
        result = session.run(cypher, params or {})
        for record in result:
            records.append(_serialize_record(record.data()))
    return records


def query_one(cypher: str, params: dict | None = None) -> dict | None:
    records = query(cypher, params)
    return records[0] if records else None


def create_vector_index(index_name: str = "plot_embedding", dimension: int = 1536) -> bool:
    try:
        query(
            """
            CREATE VECTOR INDEX $index_name IF NOT EXISTS
            FOR (p:Plot) ON (p.embedding)
            OPTIONS {indexConfig: {
                `vector.dimensions`: $dim,
                `vector.similarity_function`: 'cosine'
            }}
            """,
            {"index_name": index_name, "dim": dimension},
        )
        return True
    except Exception:
        return False


async def apply_constraints():
    constraints = [
        ("season_id", "Season", "seasonId"),
        ("snapshot_id", "DailySnapshot", "snapshotId"),
        ("alert_id", "Alert", "alertId"),
        ("county_name", "County", "name"),
        ("obs_id", "FarmerObservation", "observationId"),
        ("intervention_id", "Intervention", "interventionId"),
        ("expense_id", "Expense", "expenseId"),
        ("sale_id", "Sale", "saleId"),
        ("forecast_id", "YieldForecast", "forecastId"),
    ]
    for constraint_name, label, prop in constraints:
        try:
            query(
                f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
            )
            logger.info("Constraint %s applied for :%s(%s)", constraint_name, label, prop)
        except Exception as e:
            logger.warning("Constraint %s skipped: %s", constraint_name, e)


async def close():
    driver.close()
