import json
import uuid
import logging
from datetime import datetime, timedelta, timezone
from services.neo4j import query
from services.weather_service import fetch_daily_weather

logger = logging.getLogger("farmwise.pipeline_a")

_COUNTY_COORDS = {
    "Nyandarua": (-0.1833, 36.4333), "Nakuru": (-0.3031, 36.0800),
    "Nairobi": (-1.2921, 36.8219), "Kiambu": (-1.1714, 36.8356),
    "Meru": (0.0463, 37.6559), "Nyeri": (-0.4273, 36.9548),
    "Murang'a": (-0.7351, 37.1588), "Kirinyaga": (-0.4983, 37.2838),
    "Embu": (-0.5333, 37.4500), "Machakos": (-1.5177, 37.2634),
    "Kitui": (-1.3667, 38.0167), "Makueni": (-1.8000, 37.6167),
    "Kajiado": (-1.8500, 36.7833), "Narok": (-1.0833, 35.8667),
    "Bomet": (-0.7822, 35.3378), "Kericho": (-0.3679, 35.2860),
    "Uasin Gishu": (0.5143, 35.2698), "Nandi": (0.1767, 35.1167),
    "Trans Nzoia": (1.0167, 35.0000), "Bungoma": (0.5695, 34.5584),
    "Kakamega": (0.2827, 34.7519), "Vihiga": (0.0500, 34.7333),
    "Kisumu": (-0.1000, 34.7500), "Siaya": (0.0600, 34.2867),
    "Homa Bay": (-0.5273, 34.4571), "Migori": (-1.0634, 34.4731),
    "Kisii": (-0.6817, 34.7667), "Nyamira": (-0.6167, 34.9833),
    "Busia": (0.4633, 34.1050), "Baringo": (0.4667, 35.9667),
    "Elgeyo Marakwet": (0.5000, 35.5000), "West Pokot": (1.2500, 35.0833),
    "Turkana": (3.1167, 35.6000), "Samburu": (1.1667, 36.6667),
    "Laikipia": (0.3600, 36.7800), "Isiolo": (0.3500, 37.5833),
    "Marsabit": (2.3333, 37.9833), "Mandera": (3.9333, 41.8667),
    "Wajir": (1.7500, 40.0667), "Garissa": (-0.4500, 39.6500),
    "Tana River": (-1.5000, 40.0333), "Lamu": (-2.2667, 40.9000),
    "Taita Taveta": (-3.4167, 38.3333), "Kwale": (-4.1767, 39.4500),
    "Kilifi": (-3.6300, 39.8500), "Mombasa": (-4.0500, 39.6667),
    "Tharaka Nithi": (-0.3000, 37.9167),
}


def _parse_location(loc: any) -> tuple:
    if not loc:
        return None, None
    if isinstance(loc, dict):
        lat = loc.get("lat") or loc.get("latitude")
        lng = loc.get("lng") or loc.get("lon") or loc.get("longitude")
        if lat is not None and lng is not None:
            return float(lat), float(lng)
    if isinstance(loc, str):
        try:
            parsed = json.loads(loc)
            if isinstance(parsed, dict):
                lat = parsed.get("lat") or parsed.get("latitude")
                lng = parsed.get("lng") or parsed.get("lon") or parsed.get("longitude")
                if lat is not None and lng is not None:
                    return float(lat), float(lng)
        except Exception:
            import re
            m = re.match(r'\{.*?"lat"\s*:\s*([-\d.]+).*?"lng"\s*:\s*([-\d.]+).*?\}', loc)
            if not m:
                m = re.match(r'\{lat:\s*([-\d.]+),\s*lng:\s*([-\d.]+)\}', loc)
            if m:
                return float(m.group(1)), float(m.group(2))
    return None, None


async def run_pipeline_a(season_id: str = None):
    logger.info("Pipeline A: Nightly telemetry ingestion starting (season_id=%s)", season_id or "all")

    today = datetime.now(timezone.utc).date()
    yesterday = (today - timedelta(days=1)).isoformat()

    season_clause = ""
    params = {"today": today.isoformat(), "yesterday": yesterday}
    if season_id:
        season_clause = "WHERE s.seasonId = $season_id"
        params["season_id"] = season_id

    seasons = query(f"""
        MATCH (p:Plot)-[:HAS_SEASON]->(s:Season {{status: "ACTIVE"}})
        {season_clause}
        MATCH (p)-[:LOCATED_IN]->(c:County)
        OPTIONAL MATCH (s)-[:PLANTED_WITH]->(v:PotatoVariety)
        RETURN p.plotId AS plotId, p.boundaryPolygon AS boundaryPolygon,
               p.location AS location, s.seasonId AS seasonId,
               s.plantingDate AS plantingDate,
               coalesce(v.name, 'Shangi') AS variety,
               c.name AS county, c.centroidLat AS centroidLat,
               c.centroidLon AS centroidLon
    """, params)

    logger.info("Pipeline A: %d active seasons to process", len(seasons))

    for row in seasons:
        sid = row["seasonId"]
        pid = row["plotId"]
        county = row.get("county", "")
        try:
            loc = row.get("location") or {}
            lat, lng = _parse_location(loc)

            if lat is None or lng is None:
                fallback = _COUNTY_COORDS.get(county)
                c_lat = row.get("centroidLat")
                c_lng = row.get("centroidLon")
                if c_lat is not None and c_lng is not None:
                    lat, lng = float(c_lat), float(c_lng)
                elif fallback:
                    lat, lng = fallback
                else:
                    lat, lng = -1.2921, 36.8219
                logger.info("Pipeline A: Using fallback coords for %s/%s: (%.4f, %.4f)", sid, county, lat, lng)

            weather = await fetch_daily_weather(lat, lng, yesterday)

            sat_data = None
            polygon_id = row.get("boundaryPolygon")
            if polygon_id:
                try:
                    from agents.satellite import get_ndvi_history
                    ndvi_entries = await get_ndvi_history(polygon_id, days=1)
                    if ndvi_entries:
                        latest = ndvi_entries[0]
                        cloud_cover = latest.get("cl", 100)
                        if cloud_cover <= 95:
                            stats = latest.get("data", {})
                            sat_data = {
                                "cloud_cover_percentage": cloud_cover,
                                "mean_ndvi": stats.get("ndvi", stats.get("mean", 0)),
                                "mean_evi": 0,
                                "mean_ndre": 0,
                                "mean_ndwi": 0,
                                "mean_savi": 0,
                                "mean_msi": 0,
                            }
                except Exception as e:
                    logger.warning("Pipeline A: Satellite fetch failed for %s: %s", sid, e)

            fourteen_days_ago = (today - timedelta(days=14)).isoformat()
            history = query("""
                MATCH (s:Season {seasonId: $sid})-[:HAS_SNAPSHOT]->(d:DailySnapshot)
                WHERE d.date >= $since
                RETURN d.daily_precip_mm AS precip, d.daily_avg_temp_c AS temp,
                       d.daily_avg_humidity AS humidity
                ORDER BY d.date DESC
            """, {"sid": sid, "since": fourteen_days_ago})

            precip_vals = [d["precip"] for d in history]
            temp_vals = [d["temp"] for d in history]
            humidity_vals = [d["humidity"] for d in history]

            today_precip = weather["daily_precip_mm"]
            today_temp = weather["daily_avg_temp_c"]
            today_humidity = weather["daily_avg_humidity"]

            all_precip = [today_precip] + precip_vals
            all_temp = [today_temp] + temp_vals
            all_humidity = [today_humidity] + humidity_vals

            def rolling(series, n):
                return round(sum(series[:min(n, len(series))]), 1)

            def rolling_avg(series, n):
                subset = series[:min(n, len(series))]
                return round(sum(subset) / len(subset), 1) if subset else 0.0

            snapshot_id = str(uuid.uuid4())
            has_sat = sat_data is not None and sat_data.get("cloud_cover_percentage", 100) <= 10.0

            set_clauses = """
                SET d.date = $date, d.daily_precip_mm = $precip,
                    d.daily_avg_temp_c = $temp, d.daily_avg_humidity = $humidity,
                    d.rolling_5d_precip = $r5p, d.rolling_10d_precip = $r10p,
                    d.rolling_14d_precip = $r14p, d.rolling_5d_temp_avg = $r5t,
                    d.rolling_5d_humidity_avg = $r5h, d.has_satellite_data = $has_sat
            """
            params_snap = {
                "sid": sid, "snapid": snapshot_id, "date": yesterday,
                "precip": today_precip, "temp": today_temp, "humidity": today_humidity,
                "r5p": rolling(all_precip, 5), "r10p": rolling(all_precip, 10),
                "r14p": rolling(all_precip, 14), "r5t": rolling_avg(all_temp, 5),
                "r5h": rolling_avg(all_humidity, 5), "has_sat": has_sat,
            }

            sat_clauses = ""
            if has_sat and sat_data:
                sat_clauses = """
                    SET d.cloud_cover_percentage = $cloud, d.mean_ndvi = $ndvi,
                        d.mean_evi = $evi, d.mean_ndre = $ndre, d.mean_ndwi = $ndwi,
                        d.mean_savi = $savi, d.mean_msi = $msi
                """
                params_snap.update({
                    "cloud": sat_data.get("cloud_cover_percentage", 0),
                    "ndvi": sat_data.get("mean_ndvi", 0),
                    "evi": sat_data.get("mean_evi", 0),
                    "ndre": sat_data.get("mean_ndre", 0),
                    "ndwi": sat_data.get("mean_ndwi", 0),
                    "savi": sat_data.get("mean_savi", 0),
                    "msi": sat_data.get("mean_msi", 0),
                })

            query(f"""
                MATCH (s:Season {{seasonId: $sid}})
                MERGE (d:DailySnapshot {{snapshotId: $snapid}})
                ON CREATE {set_clauses} {sat_clauses}
                MERGE (s)-[:HAS_SNAPSHOT]->(d)
            """, params_snap)

            planting_date = row.get("plantingDate")
            if planting_date:
                try:
                    pd = datetime.fromisoformat(str(planting_date).replace("Z", "").split("+")[0].split("T")[0])
                    days_since = (today - pd.date()).days
                    stage_result = query("""
                        MATCH (v:PotatoVariety)-[:HAS_GROWTH_STAGE]->(g:GrowthStage)
                        WHERE g.startDaysAfterPlanting <= $days
                          AND g.endDaysAfterPlanting >= $days
                        RETURN g.name AS name, g.stageId AS stageId
                        LIMIT 1
                    """, {"days": days_since})
                    if stage_result:
                        stage_name = stage_result[0]["name"]
                        query("""
                            MATCH (s:Season {seasonId: $sid})
                            OPTIONAL MATCH (s)-[r:HAS_GROWTH_STAGE]->(:GrowthStage)
                            DELETE r
                            WITH s
                            MATCH (g:GrowthStage {name: $stage})
                            MERGE (s)-[:HAS_GROWTH_STAGE]->(g)
                        """, {"sid": sid, "stage": stage_name})
                except Exception as e:
                    logger.warning("Pipeline A: Growth stage check failed for %s: %s", sid, e)

            logger.info("Pipeline A: Ingested snapshot %s for season %s", snapshot_id, sid)

        except Exception as e:
            logger.exception("Pipeline A: Failed for season %s", sid)
            continue

    logger.info("Pipeline A: Complete")
