"""
Seed script: Single farmer demo data.
Creates 1 farmer, 1 plot in Nyandarua, 30 days of satellite/weather observations,
with an NDVI stress dip at day 22 to trigger late blight detection.
"""
import os
import uuid
import random
from datetime import datetime, timedelta
from config import settings
from neo4j import GraphDatabase

def seed():
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
FARMER_ID = "demo-farmer-01"
FARMER_PHONE = "+254712345678"
PLOT_ID = "demo-plot-01"
COUNTY = "Nyandarua"
LAT, LON = -0.1833, 36.4333
PLANTING_DATE = (datetime.now() - timedelta(days=67)).strftime("%Y-%m-%d")


def ndvi_curve(day: int) -> float:
    """Generate NDVI values with a stress dip at day 22."""
    if day < 22:
        return round(0.35 + (day / 22) * 0.43 + random.uniform(-0.02, 0.02), 4)
    elif day == 22:
        return 0.62  # Stress dip
    elif day < 30:
        return round(0.62 + ((day - 22) / 8) * 0.09 + random.uniform(-0.01, 0.01), 4)
    else:
        return round(0.70 + random.uniform(-0.03, 0.03), 4)


def seed():
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )

    with driver.session() as session:
        session.run(
            """
            MERGE (c:County {name: $county})
            ON CREATE SET c.centroidLat = $lat, c.centroidLon = $lon
            """,
            {"county": COUNTY, "lat": LAT, "lon": LON},
        )

        session.run(
            """
            MERGE (f:Farmer {farmerId: $fid})
            SET f.name = $name, f.phone = $phone,
                f.preferredChannel = $channels, f.preferredLanguage = 'sw',
                f.registrationDate = date()
            """,
            {
                "fid": FARMER_ID,
                "name": "John Mwangi",
                "phone": FARMER_PHONE,
                "channels": ["whatsapp_text", "whatsapp_audio"],
            },
        )

        session.run(
            """
            MATCH (f:Farmer {farmerId: $fid})
            MATCH (c:County {name: $county})
            MERGE (gs:GrowthStage {name: 'Tuber Bulking'})
            MERGE (p:Plot {plotId: $pid})
            SET p.name = $pname, p.latitude = $lat, p.longitude = $lon,
                p.sizeAcres = 1.5, p.variety = 'Shangi',
                p.plantingDate = date($pdate), p.seasonDay = $season_day,
                p.soilBaseline_N = 0.18, p.soilBaseline_pH = 5.8,
                p.accumulatedGDD = 580, p.forecastedYieldKg = 7200
            MERGE (f)-[:OWNS]->(p)
            MERGE (p)-[:LOCATED_IN]->(c)
            MERGE (p)-[:AT_STAGE]->(gs)
            """,
            {
                "fid": FARMER_ID,
                "county": COUNTY,
                "pid": PLOT_ID,
                "pname": "Shamba ya Demo",
                "lat": LAT,
                "lon": LON,
                "pdate": PLANTING_DATE,
                "season_day": 67,
            },
        )

        for day_offset in range(30):
            date = (datetime.now() - timedelta(days=30 - day_offset)).strftime("%Y-%m-%d")
            ndvi = ndvi_curve(day_offset)
            evi = round(ndvi * 0.82 + random.uniform(-0.02, 0.02), 4)
            cloud = round(random.uniform(0, 30), 1)
            temp_max = round(random.uniform(18, 26), 1)
            temp_min = round(random.uniform(8, 14), 1)
            precip = round(random.uniform(0, 12), 1)

            session.run(
                """
                MATCH (p:Plot {plotId: $pid})
                MERGE (d:TimeDay {date: date($date)})
                CREATE (obs_sat:Observation_Satellite {
                    ndvi: $ndvi, evi: $evi, cloudCover: $cloud,
                    ndvi_std: $std, ndvi_min: $min, ndvi_max: $max,
                    source: 'Sentinel-2', dc: 95
                })
                CREATE (obs_sat)-[:OCCURRED_ON]->(d)
                CREATE (p)-[:HAS_OBSERVATION]->(obs_sat)

                CREATE (obs_w:Observation_Weather {
                    tempMax: $tmax, tempMin: $tmin, precipitation: $precip,
                    humidity: $humidity
                })
                CREATE (obs_w)-[:OCCURRED_ON]->(d)
                CREATE (p)-[:HAS_OBSERVATION]->(obs_w)
                """,
                {
                    "pid": PLOT_ID,
                    "date": date,
                    "ndvi": ndvi,
                    "evi": evi,
                    "cloud": cloud,
                    "std": round(random.uniform(0.05, 0.15), 4),
                    "min": round(ndvi - 0.1, 4),
                    "max": round(ndvi + 0.08, 4),
                    "tmax": temp_max,
                    "tmin": temp_min,
                    "precip": precip,
                    "humidity": round(random.uniform(55, 85), 0),
                },
            )

        session.run(
            """
            MATCH (p:Plot {plotId: $pid})
            WHERE duration.between(p.plantingDate, date()).days < 90
            CREATE (se:StressEvent {
                eventId: $evid, type: 'CANOPY_NDVI_DROP',
                severity: 0.22, detectedAt: datetime() - duration('P5D')
            })
            CREATE (p)-[:EXPERIENCED_STRESS]->(se)
            """,
            {"pid": PLOT_ID, "evid": str(uuid.uuid4())},
        )

        session.run(
            """
            MATCH (p:Plot {plotId: $pid})
            CREATE (rec:DailyRecommendation {
                date: date(), action: 'spray_fungicide',
                cause: 'late_blight', urgencyHours: 48,
                narrative: 'Apply mancozeb fungicide within 48 hours. Late blight risk is elevated at tuber bulking stage.',
                dataFreshness: 1
            })
            CREATE (p)-[:HAS_RECOMMENDATION]->(rec)
            CREATE (tx:MasumiTxHash {
                hash: $tx_hash, blockNumber: 0, timestamp: datetime()
            })
            CREATE (rec)-[:HAS_TX]->(tx)
            """,
            {"pid": PLOT_ID, "tx_hash": "demo_tx_" + str(uuid.uuid4())[:8]},
        )

        print(f"Single farmer seeded: farmer={FARMER_ID}, plot={PLOT_ID}")

    driver.close()


if __name__ == "__main__":
    seed()
