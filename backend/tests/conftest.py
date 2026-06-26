"""Shared test fixtures for FarmWise test suite."""
import uuid
import pytest
from services.neo4j import query


@pytest.fixture
def unique_id():
    return str(uuid.uuid4())


@pytest.fixture
def test_farmer(unique_id):
    fid = f"test-farmer-{unique_id[:8]}"
    query(
        "CREATE (f:Farmer {farmerId: $fid, phone: $phone, name: $name, "
        "preferredChannel: ['whatsapp_text'], preferredLanguage: 'en', "
        "registrationDate: date()})",
        {"fid": fid, "phone": "+254700000000", "name": "Test Farmer"},
    )
    yield fid
    query("MATCH (f:Farmer {farmerId: $fid}) DETACH DELETE f", {"fid": fid})


@pytest.fixture
def test_plot(unique_id):
    pid = f"test-plot-{unique_id[:8]}"
    query(
        "CREATE (p:Plot {plotId: $pid, name: 'Test Plot', latitude: -0.1833, "
        "longitude: 36.4333, sizeAcres: 1.5, variety: 'Shangi', "
        "plantingDate: date(), seasonDay: 67, soilBaseline_N: 0.18, "
        "soilBaseline_pH: 5.8, accumulatedGDD: 580, forecastedYieldKg: 7200})",
        {"pid": pid},
    )
    yield pid
    query(
        "MATCH (p:Plot {plotId: $pid}) "
        "OPTIONAL MATCH (p)-[:HAS_RECOMMENDATION]->(rec:DailyRecommendation) "
        "OPTIONAL MATCH (rec)-[:HAS_TX]->(tx:MasumiTxHash) "
        "DETACH DELETE tx, rec, p",
        {"pid": pid},
    )


@pytest.fixture
def test_county(unique_id):
    name = f"Test-County-{unique_id[:4]}"
    query(
        "MERGE (c:County {name: $name}) "
        "ON CREATE SET c.centroidLat = -0.3, c.centroidLon = 36.4",
        {"name": name},
    )
    yield name


@pytest.fixture
def test_growth_stage(test_plot):
    query(
        "MATCH (p:Plot {plotId: $pid}) "
        "MATCH (gs:GrowthStage {name: 'Tuber Bulking'}) "
        "MERGE (p)-[:AT_STAGE]->(gs)",
        {"pid": test_plot},
    )
    yield


@pytest.fixture
def test_observation_satellite(test_plot):
    ndvi = 0.72
    query(
        "MATCH (p:Plot {plotId: $pid}) "
        "MERGE (d:TimeDay {date: date()}) "
        "CREATE (obs:Observation_Satellite {ndvi: $ndvi, evi: $evi, "
        "cloudCover: $cloud, ndvi_std: 0.1, ndvi_min: 0.5, ndvi_max: 0.8, "
        "source: 'Sentinel-2', dc: 95}) "
        "CREATE (obs)-[:OCCURRED_ON]->(d) "
        "CREATE (p)-[:HAS_OBSERVATION]->(obs)",
        {"pid": test_plot, "ndvi": ndvi, "evi": round(ndvi * 0.82, 4), "cloud": 5.0},
    )
    yield


@pytest.fixture
def test_observation_weather(test_plot):
    query(
        "MATCH (p:Plot {plotId: $pid}) "
        "MERGE (d:TimeDay {date: date()}) "
        "CREATE (obs:Observation_Weather {tempMax: 24.0, tempMin: 12.0, "
        "precipitation: 3.0, humidity: 70}) "
        "CREATE (obs)-[:OCCURRED_ON]->(d) "
        "CREATE (p)-[:HAS_OBSERVATION]->(obs)",
        {"pid": test_plot},
    )
    yield


@pytest.fixture
def test_farmer_with_plot(test_farmer, test_plot):
    """Link a test farmer to a test plot with OWNS relationship."""
    query(
        "MATCH (f:Farmer {farmerId: $fid}) "
        "MATCH (p:Plot {plotId: $pid}) "
        "MERGE (f)-[:OWNS]->(p)",
        {"fid": test_farmer, "pid": test_plot},
    )
    yield test_farmer
