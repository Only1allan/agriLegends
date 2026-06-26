"""
Seed script: Farmer network (scale proof).
Creates 50 farmers, 80 plots across 3 counties with 30 days of observations.
Varied stress patterns for spatial clustering demo.
"""
import uuid
import random
from datetime import datetime, timedelta
from config import settings
from neo4j import GraphDatabase

def seed_network():
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    COUNTIES = [
    ("Nyandarua", -0.1833, 36.4333, 25),
    ("Nakuru", -0.3031, 36.0800, 35),
    ("Kiambu", -1.1714, 36.8356, 20),
]

VARIETIES = ["Shangi", "Kenya Mpya", "Dutch Robjin", "Tigoni", "Asante"]
FIRST_NAMES = ["John", "Mary", "Peter", "Jane", "David", "Sarah", "James", "Grace",
               "Michael", "Esther", "Samuel", "Ruth", "Joseph", "Naomi", "Daniel"]
LAST_NAMES = ["Mwangi", "Wanjiku", "Kamau", "Akinyi", "Ochieng", "Njuguna",
              "Chebet", "Kiprotich", "Wambui", "Omondi", "Ndungu", "Mutua"]


def random_ndvi_curve(day: int, has_stress: bool, stress_day: int) -> float:
    if has_stress and day == stress_day:
        return round(random.uniform(0.45, 0.62), 4)
    elif has_stress and stress_day < day <= stress_day + 7:
        recovery = (day - stress_day) / 7
        return round(0.60 + recovery * 0.10 + random.uniform(-0.02, 0.02), 4)
    else:
        return round(0.35 + (day / 30) * 0.40 + random.uniform(-0.03, 0.03), 4)


def seed_network():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    plot_count = 0
    farmer_count = 0

    with driver.session() as session:
        for county_name, county_lat, county_lon, num_plots in COUNTIES:
            session.run(
                """
                MERGE (c:County {name: $name})
                ON CREATE SET c.centroidLat = $lat, c.centroidLon = $lon
                """,
                {"name": county_name, "lat": county_lat, "lon": county_lon},
            )

            for i in range(num_plots):
                farmer_id = str(uuid.uuid4())
                plot_id = str(uuid.uuid4())
                farmer_count += 1
                plot_count += 1
                has_stress = i % 3 == 0
                stress_day = random.randint(15, 25)

                lat = county_lat + random.uniform(-0.05, 0.05)
                lon = county_lon + random.uniform(-0.05, 0.05)
                planting_offset = random.randint(0, 60)
                planting_date = (datetime.now() - timedelta(days=30 + planting_offset)).strftime("%Y-%m-%d")
                season_day = 30 + planting_offset
                farmer_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                phone = f"+2547{random.randint(10000000, 99999999)}"
                variety = random.choice(VARIETIES)
                acres = round(random.uniform(0.25, 5.0), 2)

                session.run(
                    """
                    CREATE (f:Farmer {
                        farmerId: $fid, name: $name, phone: $phone,
                        preferredChannel: ['whatsapp_text'], preferredLanguage: 'sw',
                        registrationDate: date()
                    })
                    WITH f
                    MATCH (c:County {name: $county})
                    MERGE (gs:GrowthStage {name: $stage})
                    CREATE (p:Plot {
                        plotId: $pid, name: $pname, latitude: $lat, longitude: $lon,
                        sizeAcres: $acres, variety: $variety,
                        plantingDate: date($pdate), seasonDay: $sday,
                        soilBaseline_N: $soil_n, soilBaseline_pH: $soil_ph,
                        accumulatedGDD: $gdd, forecastedYieldKg: $yield
                    })
                    CREATE (f)-[:OWNS]->(p)
                    CREATE (p)-[:LOCATED_IN]->(c)
                    CREATE (p)-[:AT_STAGE]->(gs)
                    """,
                    {
                        "fid": farmer_id, "name": farmer_name, "phone": phone,
                        "county": county_name,
                        "pid": plot_id, "pname": f"Shamba {i + 1}",
                        "lat": lat, "lon": lon, "acres": acres,
                        "variety": variety, "pdate": planting_date, "sday": season_day,
                        "soil_n": round(random.uniform(0.12, 0.25), 2),
                        "soil_ph": round(random.uniform(4.8, 6.5), 1),
                        "gdd": round(random.uniform(300, 700), 0),
                        "yield": round(random.uniform(3000, 12000), 0),
                        "stage": "Tuber Bulking" if season_day > 45 else "Tuber Initiation",
                    },
                )

                for day_offset in range(30):
                    date = (datetime.now() - timedelta(days=30 - day_offset)).strftime("%Y-%m-%d")
                    ndvi = random_ndvi_curve(day_offset, has_stress, stress_day)
                    session.run(
                        """
                        MATCH (p:Plot {plotId: $pid})
                        MERGE (d:TimeDay {date: date($date)})
                        CREATE (obs:Observation_Satellite {
                            ndvi: $ndvi, evi: $evi, cloudCover: $cloud,
                            ndvi_std: $std, ndvi_min: $min, ndvi_max: $max,
                            source: 'Sentinel-2', dc: 95
                        })
                        CREATE (obs)-[:OCCURRED_ON]->(d)
                        CREATE (p)-[:HAS_OBSERVATION]->(obs)
                        """,
                        {
                            "pid": plot_id, "date": date, "ndvi": ndvi,
                            "evi": round(ndvi * 0.82, 4),
                            "cloud": round(random.uniform(0, 35), 1),
                            "std": round(random.uniform(0.05, 0.18), 4),
                            "min": round(ndvi - random.uniform(0.05, 0.15), 4),
                            "max": round(ndvi + random.uniform(0.03, 0.10), 4),
                        },
                    )

                if has_stress:
                    session.run(
                        """
                        MATCH (p:Plot {plotId: $pid})
                        CREATE (se:StressEvent {
                            eventId: $evid, type: 'CANOPY_NDVI_DROP',
                            severity: $sev, detectedAt: datetime() - duration('P7D')
                        })
                        CREATE (p)-[:EXPERIENCED_STRESS]->(se)
                        """,
                        {
                            "pid": plot_id,
                            "evid": str(uuid.uuid4()),
                            "sev": round(random.uniform(0.15, 0.30), 2),
                        },
                    )

        summary = session.run(
            """
            MATCH (f:Farmer) OPTIONAL MATCH (p:Plot) OPTIONAL MATCH (obs:Observation_Satellite)
            OPTIONAL MATCH (se:StressEvent)
            RETURN count(DISTINCT f) AS farmers, count(DISTINCT p) AS plots,
                   count(DISTINCT obs) AS observations, count(DISTINCT se) AS stressEvents
            """
        ).single().data()

        print(f"Network seeded: {summary}")

    driver.close()


if __name__ == "__main__":
    seed_network()
