"""
Seed script: Single farmer demo data.
Creates 1 farmer, 1 plot, 1 active season, 30 days of DailySnapshots,
and sample alerts, observations, interventions, and a yield forecast.
"""
import os
import uuid
import random
from datetime import datetime, timedelta
from config import settings
from neo4j import GraphDatabase

FARMER_ID = "demo-farmer-01"
FARMER_PHONE = "+254712345678"
FARMER_NAME = "John Mwangi"
FARMER_PASSWORD = "demo123"
PLOT_ID = "demo-plot-01"
COUNTY = "Nyandarua"
LAT, LON = -0.1833, 36.4333
VARIETY = "Shangi"
PLANTING_DATE = (datetime.now() - timedelta(days=67)).strftime("%Y-%m-%d")
HARVEST_DATE = (datetime.now() + timedelta(days=23)).strftime("%Y-%m-%d")


def ndvi_curve(day: int) -> float:
    if day < 22:
        return round(0.35 + (day / 22) * 0.43 + random.uniform(-0.02, 0.02), 4)
    elif day == 22:
        return 0.30
    elif day < 30:
        return round(0.30 + ((day - 22) / 8) * 0.41 + random.uniform(-0.01, 0.01), 4)
    else:
        return round(0.70 + random.uniform(-0.03, 0.03), 4)


def seed():
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )

    import bcrypt
    password_hash = bcrypt.hashpw(FARMER_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    SEASON_ID = str(uuid.uuid4())

    with driver.session() as session:
        session.run("""
            MERGE (c:County {name: $county})
            ON CREATE SET c.centroidLat = $lat, c.centroidLon = $lon
        """, {"county": COUNTY, "lat": LAT, "lon": LON})

        session.run("""
            MERGE (f:Farmer {farmerId: $fid})
            SET f.name = $name, f.phone = $phone,
                f.passwordHash = $hash,
                f.preferredChannel = ['whatsapp_text', 'sms'],
                f.preferredLanguage = 'sw',
                f.registrationDate = date()
        """, {
            "fid": FARMER_ID, "name": FARMER_NAME,
            "phone": FARMER_PHONE, "hash": password_hash,
        })

        session.run("""
            MATCH (f:Farmer {farmerId: $fid})
            MATCH (c:County {name: $county})
            CREATE (p:Plot {
                plotId: $pid, name: $pname,
                county: $county, areaHa: 0.61,
                soilType: 'Clay Loam',
                location: '{lat: $lat, lng: $lon}',
                stakeholdersToken: $token
            })
            CREATE (f)-[:OWNS]->(p)
            CREATE (p)-[:LOCATED_IN]->(c)
        """, {
            "fid": FARMER_ID, "county": COUNTY,
            "pid": PLOT_ID, "pname": "Shamba ya Demo",
            "lat": LAT, "lon": LON,
            "token": str(uuid.uuid4()),
        })

        session.run("""
            MATCH (p:Plot {plotId: $pid})
            MERGE (v:PotatoVariety {name: $variety})
            CREATE (s:Season {
                seasonId: $sid, plantingDate: date($pdate),
                expectedHarvestDate: date($hdate),
                status: 'ACTIVE', varietyName: $variety
            })
            CREATE (p)-[:HAS_SEASON]->(s)
            CREATE (s)-[:PLANTED_WITH]->(v)
        """, {
            "pid": PLOT_ID, "sid": SEASON_ID,
            "pdate": PLANTING_DATE, "hdate": HARVEST_DATE,
            "variety": VARIETY,
        })

        for day_offset in range(30):
            date = (datetime.now() - timedelta(days=30 - day_offset)).strftime("%Y-%m-%d")
            ndvi = ndvi_curve(day_offset)
            temp = round(random.uniform(14, 28), 1)
            precip = round(random.uniform(0, 15), 1)
            humidity = round(random.uniform(50, 85), 0)
            cloud_cover = round(random.uniform(0, 40), 1)
            has_sat = cloud_cover < 15

            all_precip = [precip] + [round(random.uniform(0, 15), 1) for _ in range(14)]
            all_temp = [temp] + [round(random.uniform(14, 28), 1) for _ in range(5)]

            session.run("""
                MATCH (s:Season {seasonId: $sid})
                MERGE (d:DailySnapshot {snapshotId: $snapid})
                ON CREATE SET
                    d.date = $date,
                    d.daily_precip_mm = $precip,
                    d.daily_avg_temp_c = $temp,
                    d.daily_avg_humidity = $hum,
                    d.rolling_5d_precip = $r5p,
                    d.rolling_10d_precip = $r10p,
                    d.rolling_14d_precip = $r14p,
                    d.rolling_5d_temp_avg = $r5t,
                    d.rolling_5d_humidity_avg = $r5h,
                    d.has_satellite_data = $has_sat,
                    d.cloud_cover_percentage = $cloud,
                    d.mean_ndvi = $ndvi,
                    d.mean_evi = $evi,
                    d.mean_ndre = $ndre,
                    d.mean_ndwi = $ndwi,
                    d.mean_savi = $savi,
                    d.mean_msi = $msi
                MERGE (s)-[:HAS_SNAPSHOT]->(d)
            """, {
                "sid": SEASON_ID,
                "snapid": str(uuid.uuid4()),
                "date": date,
                "precip": precip, "temp": temp, "hum": humidity,
                "r5p": round(sum(all_precip[:5]), 1),
                "r10p": round(sum(all_precip[:10]), 1),
                "r14p": round(sum(all_precip[:14]), 1),
                "r5t": round(sum(all_temp[:5]) / 5, 1),
                "r5h": humidity,
                "has_sat": has_sat,
                "cloud": cloud_cover,
                "ndvi": ndvi, "evi": round(ndvi * 0.82, 4),
                "ndre": round(ndvi * 0.9, 4),
                "ndwi": round(0.3 + random.uniform(-0.05, 0.05), 4),
                "savi": round(ndvi * 0.8, 4),
                "msi": round(0.4 + random.uniform(-0.1, 0.1), 4),
            })

        alert_id = str(uuid.uuid4())
        session.run("""
            MATCH (s:Season {seasonId: $sid})
            MATCH (d:DailySnapshot) WHERE d.date = $alert_date
            WITH s, d LIMIT 1
            CREATE (a:Alert {
                alertId: $aid, detected_condition: 'Warm & Humid',
                confidence: 0.82, urgency: 'MEDIUM', status: 'ACTIVE',
                explanation: 'Recent warm and humid conditions create favorable environment for late blight development. Your Shangi variety has low resistance to late blight.',
                recommendation: 'Apply fungicide spray within 48 hours. Monitor fields for dark spots on leaves. Consider Ridomil or Mancozeb application.',
                sms_english: 'Late blight risk for your Shangi plot. Warm humid weather detected. Apply fungicide within 48h. Check FarmWise for details.',
                sms_swahili: 'Hatari ya ugonjwa wa late blight shambani kwako. Hali ya hewa ya joto na unyevu imegunduliwa. Weka dawa ndani ya masaa 48. Angalia FarmWise kwa maelezo.',
                createdAt: $now, retryCount: 0
            })
            CREATE (s)-[:GENERATED]->(a)
            CREATE (a)-[:TRIGGERED_BY]->(d)
        """, {
            "sid": SEASON_ID, "aid": alert_id,
            "alert_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
            "now": int(datetime.now().timestamp() * 1000),
        })

        obs_id = str(uuid.uuid4())
        session.run("""
            MATCH (s:Season {seasonId: $sid})
            CREATE (o:FarmerObservation {
                observationId: $oid, date: date(),
                notes: 'Majani yanageuka njano kwa doa doa nyeusi. Sehemu ya chini ya mmea imeathirika zaidi.',
                imageUrl: '', interpretationStatus: 'PENDING'
            })
            CREATE (s)-[:HAS_OBSERVATION]->(o)
        """, {"sid": SEASON_ID, "oid": obs_id})

        inter_id = str(uuid.uuid4())
        session.run("""
            MATCH (a:Alert {alertId: $aid})
            MATCH (f:Farmer {farmerId: $fid})
            CREATE (i:Intervention {
                interventionId: $iid, actionTaken: 'Applied Ridomil fungicide spray',
                date: $date
            })
            CREATE (f)-[:APPLIED]->(i)
            CREATE (i)-[:ADDRESSES]->(a)
        """, {
            "aid": alert_id, "fid": FARMER_ID, "iid": inter_id,
            "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        })

        exp_id = str(uuid.uuid4())
        session.run("""
            MATCH (i:Intervention {interventionId: $iid})
            CREATE (e:Expense {
                expenseId: $eid, category: 'Pesticide',
                description: 'Ridomil fungicide 500g',
                amount: 850, date: $date
            })
            CREATE (i)-[:HAS_EXPENSE]->(e)
        """, {"iid": inter_id, "eid": exp_id,
              "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")})

        fc_id = str(uuid.uuid4())
        session.run("""
            MATCH (s:Season {seasonId: $sid})
            CREATE (f:YieldForecast {
                forecastId: $fid, date: date(),
                predictedYield: 7200, confidenceLow: 5800,
                confidenceHigh: 8600,
                basis: 'Based on 30-day NDVI trend averaging 0.58, adequate precipitation, Shangi variety yield potential for 0.61 ha in Nyandarua county.'
            })
            CREATE (s)-[:HAS_FORECAST]->(f)
        """, {"sid": SEASON_ID, "fid": fc_id})

        sale_id = str(uuid.uuid4())
        session.run("""
            MATCH (s:Season {seasonId: $sid})
            CREATE (sa:Sale {
                saleId: $said, quantity_kg: 250, unit_price: 45,
                total_amount: 11250, buyer: 'Nairobi Wholesale Market',
                sale_date: $date
            })
            CREATE (s)-[:HAS_SALE]->(sa)
        """, {"sid": SEASON_ID, "said": sale_id,
              "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")})

        print(f"""
Seed complete:
  Farmer:    {FARMER_ID} ({FARMER_NAME}, {FARMER_PHONE})
  Plot:      {PLOT_ID} (Shamba ya Demo, {COUNTY})
  Season:    {SEASON_ID} (Shangi, planted {PLANTING_DATE})
  Snapshots: 30 days of telemetry
  Alerts:    1 (Warm & Humid → Late Blight)
  Observations: 1
  Interventions: 1 (Ridomil spray)
  Expenses:  1 (KES 850 Pesticide)
  Forecast:  1 (7,200 kg estimated)
  Sales:     1 (250 kg @ KES 45)
        """)

    driver.close()


if __name__ == "__main__":
    seed()
