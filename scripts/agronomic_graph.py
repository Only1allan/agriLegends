import asyncio
import glob
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.experimental.components.data_loader import PdfLoader
from neo4j_graphrag.experimental.components.embedder import TextChunkEmbedder
from neo4j_graphrag.experimental.components.entity_relation_extractor import (
    LLMEntityRelationExtractor,
    OnError,
)
from neo4j_graphrag.experimental.components.kg_writer import Neo4jWriter
from neo4j_graphrag.experimental.components.resolver import (
    SinglePropertyExactMatchResolver,
)
from neo4j_graphrag.experimental.components.schema import (
    SchemaBuilder,
    NodeType,
    PropertyType,
    RelationshipType,
)
from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import (
    FixedSizeSplitter,
)
from neo4j_graphrag.indexes import create_vector_index
from neo4j_graphrag.llm import OpenAILLM

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

llm = OpenAILLM(
    model_name="deepseek-v4-flash",
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
    model_params={
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
        "temperature": 0,
    },
)

embedder = OpenAIEmbeddings(
    model="Qwen/Qwen3-Embedding-0.6B",
    api_key=FEATHERLESS_API_KEY,
    base_url="https://api.featherless.ai/v1",
)

NODE_TYPES = [
    NodeType(
        label="Variety",
        properties=[
            PropertyType(name="name", type="STRING"),
            PropertyType(name="maturity_period", type="STRING"),
            PropertyType(name="dormancy_period", type="STRING"),
            PropertyType(name="dry_matter_percentage", type="FLOAT"),
        ],
    ),
    NodeType(
        label="GrowthStage",
        properties=[
            PropertyType(name="stage_number", type="INTEGER"),
            PropertyType(name="name", type="STRING"),
        ],
    ),
    NodeType(
        label="WeatherCondition",
        properties=[
            PropertyType(name="name", type="STRING"),
            PropertyType(name="threshold_criteria", type="STRING"),
        ],
    ),
    NodeType(
        label="SoilCondition",
        properties=[
            PropertyType(name="name", type="STRING"),
            PropertyType(name="threshold_criteria", type="STRING"),
        ],
    ),
    NodeType(
        label="Disease",
        properties=[
            PropertyType(name="name", type="STRING"),
            PropertyType(name="scientific_name", type="STRING"),
            PropertyType(name="pathogen_type", type="STRING"),
            PropertyType(name="overwinters_in_soil", type="BOOLEAN"),
        ],
    ),
    NodeType(
        label="Pest",
        properties=[
            PropertyType(name="name", type="STRING"),
            PropertyType(name="scientific_name", type="STRING"),
            PropertyType(name="pest_type", type="STRING"),
        ],
    ),
    NodeType(
        label="Nutrient",
        properties=[
            PropertyType(name="name", type="STRING"),
            PropertyType(name="type", type="STRING"),
            PropertyType(name="optimal_ph_range", type="STRING"),
        ],
    ),
    NodeType(
        label="ObservableSymptom",
        properties=[
            PropertyType(name="name", type="STRING"),
            PropertyType(name="description", type="STRING"),
            PropertyType(name="plant_part_affected", type="STRING"),
        ],
    ),
    NodeType(
        label="Intervention",
        properties=[
            PropertyType(name="name", type="STRING"),
            PropertyType(name="description", type="STRING"),
        ],
    ),
    NodeType(
        label="Agrochemical",
        properties=[
            PropertyType(name="name", type="STRING"),
            PropertyType(name="type", type="STRING"),
        ],
    ),
]

RELATIONSHIP_TYPES = [
    RelationshipType(label="FAVORS"),
    RelationshipType(label="REDUCES"),
    RelationshipType(
        label="VECTORS",
        properties=[PropertyType(name="transmission_mode", type="STRING")],
    ),
    RelationshipType(
        label="CAUSES",
        properties=[PropertyType(name="severity_stage", type="STRING")],
    ),
    RelationshipType(label="DEFICIENCY_CAUSES"),
    RelationshipType(label="ANTAGONIZES"),
    RelationshipType(label="STIMULATES_DEMAND_FOR"),
    RelationshipType(
        label="RESISTANT_TO",
        properties=[PropertyType(name="resistance_level", type="STRING")],
    ),
    RelationshipType(label="PEAK_DEMAND_FOR"),
    RelationshipType(label="TIMED_FOR"),
    RelationshipType(
        label="MITIGATES",
        properties=[
            PropertyType(name="application_type", type="STRING"),
            PropertyType(name="application_rate", type="STRING"),
        ],
    ),
    RelationshipType(
        label="SUPPLIES",
        properties=[
            PropertyType(name="application_type", type="STRING"),
            PropertyType(name="composition_percentage", type="FLOAT"),
            PropertyType(name="standard_application_rate", type="STRING"),
        ],
    ),
]

PATTERNS = [
    ("WeatherCondition", "FAVORS", "Disease"),
    ("WeatherCondition", "FAVORS", "Pest"),
    ("SoilCondition", "REDUCES", "Disease"),
    ("Pest", "VECTORS", "Disease"),
    ("Disease", "CAUSES", "ObservableSymptom"),
    ("Pest", "CAUSES", "ObservableSymptom"),
    ("Nutrient", "DEFICIENCY_CAUSES", "ObservableSymptom"),
    ("Nutrient", "ANTAGONIZES", "Nutrient"),
    ("Nutrient", "STIMULATES_DEMAND_FOR", "Nutrient"),
    ("Variety", "RESISTANT_TO", "Disease"),
    ("Variety", "RESISTANT_TO", "Pest"),
    ("GrowthStage", "PEAK_DEMAND_FOR", "Nutrient"),
    ("Intervention", "TIMED_FOR", "GrowthStage"),
    ("Agrochemical", "MITIGATES", "Disease"),
    ("Agrochemical", "MITIGATES", "Pest"),
    ("Agrochemical", "SUPPLIES", "Nutrient"),
]

pdf_loader = PdfLoader()
text_splitter = FixedSizeSplitter(chunk_size=1000, chunk_overlap=100)
chunk_embedder = TextChunkEmbedder(embedder=embedder)
schema_builder = SchemaBuilder()
extractor = LLMEntityRelationExtractor(
    llm=llm,
    on_error=OnError.IGNORE,
)
writer = Neo4jWriter(driver)


async def process_file(file_path, file_idx, total_files):
    fname = os.path.basename(file_path)
    print(f"[{file_idx}/{total_files}] Processing: {fname}")

    print(f"  [1/5] Loading PDF...")
    loaded = await pdf_loader.run(filepath=Path(file_path))
    print(f"  [1/5] Loaded: {len(loaded.text)} chars")

    print(f"  [2/5] Splitting into chunks...")
    chunks = await text_splitter.run(text=loaded.text)
    print(f"  [2/5] Created {len(chunks.chunks)} chunks")

    print(f"  [3/5] Embedding chunks...")
    embedded_chunks = await chunk_embedder.run(text_chunks=chunks)
    print(f"  [3/5] Embedded {len(embedded_chunks.chunks)} chunks")

    print(f"  [4/5] Building schema...")
    schema = await schema_builder.run(
        node_types=NODE_TYPES,
        relationship_types=RELATIONSHIP_TYPES,
        patterns=PATTERNS,
    )
    print(f"  [4/5] Schema ready")

    print(f"  [5/5] Extracting entities & relations ({len(embedded_chunks.chunks)} chunks)...")
    graph = await extractor.run(
        chunks=embedded_chunks,
        document_info=loaded.document_info,
        schema=schema,
    )
    node_count = len(graph.nodes) if hasattr(graph, 'nodes') else '?'
    rel_count = len(graph.relationships) if hasattr(graph, 'relationships') else '?'
    print(f"  [5/5] Extracted ~{node_count} nodes, ~{rel_count} relationships")

    print(f"  Writing to Neo4j...")
    await writer.run(graph=graph)
    print(f"  Done: {fname}\n")


async def main():
    SOURCES_DIR = os.path.join(os.path.dirname(__file__), "sources")
    pdf_files = glob.glob(os.path.join(SOURCES_DIR, "*.pdf"))
    total = len(pdf_files)
    print(f"Found {total} PDF file(s) to process\n")

    for idx, pdf_file in enumerate(pdf_files, 1):
        await process_file(pdf_file, idx, total)

    print("Resolving duplicate entities...")
    resolver = SinglePropertyExactMatchResolver(driver)
    await resolver.run()
    print("Entity resolution complete")

    print("Creating vector index...")
    create_vector_index(
        driver,
        name="chunkEmbeddings",
        label="Chunk",
        embedding_property="embedding",
        dimensions=3072,
        similarity_fn="cosine",
    )
    print("Vector index created")

    driver.close()
    print("Done. Neo4j connection closed.")


asyncio.run(main())
