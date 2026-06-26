from neo4j import GraphDatabase
from config import settings

driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
)


def query(cypher: str, params: dict | None = None) -> list[dict]:
    records = []
    with driver.session() as session:
        result = session.run(cypher, params or {})
        for record in result:
            records.append(record.data())
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
