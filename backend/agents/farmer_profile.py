from services.neo4j import query


async def create_farmer_profile(farmer_id: str, data: dict) -> dict:
    """
    Store farmer-contributed data as ground truth.
    data can include: text description, image_urls, documents,
    pest sightings, yield history.
    """
    query(
        """
        MATCH (f:Farmer {farmerId: $fid})
        MERGE (fp:FarmerProfile {farmerId: $fid})
        SET fp += $data, fp.updatedAt = datetime()
        MERGE (f)-[:HAS_PROFILE]->(fp)
        """,
        {"fid": farmer_id, "data": data},
    )

    for key, value in data.items():
        if value:
            query(
                """
                MATCH (f:Farmer {farmerId: $fid})
                CREATE (log:FarmerLog {
                    textRecord: $text,
                    classification: $key,
                    confidence: 1.0,
                    timestamp: datetime()
                })
                CREATE (f)-[:HAS_LOG]->(log)
                """,
                {"fid": farmer_id, "text": f"{key}: {value}", "key": key},
            )

    return {"profile_created": True}
