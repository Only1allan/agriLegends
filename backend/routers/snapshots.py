from fastapi import APIRouter, Depends
from services.neo4j import query, query_one
from routers.auth import get_current_farmer

router = APIRouter()


@router.get("/seasons/{season_id}/snapshots")
async def get_snapshots(season_id: str, farmer: dict = Depends(get_current_farmer)) -> list[dict]:
    return query("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_SNAPSHOT]->(d:DailySnapshot)
        RETURN d.snapshotId AS snapshotId, d.date AS date,
               d.daily_precip_mm AS daily_precip_mm,
               d.daily_avg_temp_c AS daily_avg_temp_c,
               d.daily_avg_humidity AS daily_avg_humidity,
               d.rolling_5d_precip AS rolling_5d_precip,
               d.rolling_10d_precip AS rolling_10d_precip,
               d.rolling_14d_precip AS rolling_14d_precip,
               d.rolling_5d_temp_avg AS rolling_5d_temp_avg,
               d.rolling_5d_humidity_avg AS rolling_5d_humidity_avg,
               d.has_satellite_data AS has_satellite_data,
               d.cloud_cover_percentage AS cloud_cover_percentage,
               d.mean_ndvi AS mean_ndvi, d.mean_evi AS mean_evi,
               d.mean_ndre AS mean_ndre, d.mean_ndwi AS mean_ndwi,
               d.mean_savi AS mean_savi, d.mean_msi AS mean_msi
        ORDER BY d.date ASC
    """, {"sid": season_id})


@router.get("/seasons/{season_id}/snapshots/latest")
async def get_latest_snapshot(season_id: str, farmer: dict = Depends(get_current_farmer)):
    result = query_one("""
        MATCH (s:Season {seasonId: $sid})-[:HAS_SNAPSHOT]->(d:DailySnapshot)
        RETURN d.snapshotId AS snapshotId, d.date AS date,
               d.daily_precip_mm AS daily_precip_mm,
               d.daily_avg_temp_c AS daily_avg_temp_c,
               d.daily_avg_humidity AS daily_avg_humidity,
               d.rolling_5d_precip AS rolling_5d_precip,
               d.rolling_10d_precip AS rolling_10d_precip,
               d.rolling_14d_precip AS rolling_14d_precip,
               d.rolling_5d_temp_avg AS rolling_5d_temp_avg,
               d.rolling_5d_humidity_avg AS rolling_5d_humidity_avg,
               d.has_satellite_data AS has_satellite_data,
               d.cloud_cover_percentage AS cloud_cover_percentage,
               d.mean_ndvi AS mean_ndvi, d.mean_evi AS mean_evi,
               d.mean_ndre AS mean_ndre, d.mean_ndwi AS mean_ndwi,
               d.mean_savi AS mean_savi, d.mean_msi AS mean_msi
        ORDER BY d.date DESC LIMIT 1
    """, {"sid": season_id})
    return result
