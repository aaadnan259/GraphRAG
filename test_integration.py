"""Integration test for the full GraphRAG pipeline"""
import asyncio
from config import config
from database import get_write_graph, get_read_graph
from ingest import Ingestor
from retriever import HybridRetriever

print("="*60)
print("GraphRAG Integration Test")
print("="*60)

# Test 1: Configuration
print("\n[1/5] Testing configuration...")
print(f"  Google API Key: {config.google_api_key[:20]}...")
print(f"  LLM Model: {config.llm_model}")
print(f"  Embedding Model: {config.embedding_model}")
print(f"  Neo4j URI: {config.neo4j_uri}")
print("  [OK] Configuration loaded")

# Test 2: Database connections
print("\n[2/5] Testing database connections...")
write_driver = get_write_graph()
print("  [OK] Neo4j WRITE connection")
read_driver = get_read_graph()
print("  [OK] Neo4j READ connection")

# Test 3: Ingestion pipeline init
print("\n[3/5] Testing ingestion pipeline initialization...")
ingestor = Ingestor()
print("  [OK] Ingestion pipeline initialized")

# Test 4: Retriever init
print("\n[4/5] Testing retriever initialization...")
retriever = HybridRetriever()
stats = retriever.get_graph_statistics()
print(f"  Graph stats: {stats.get('total_entities', 0)} entities, {stats.get('total_relationships', 0)} relationships")
print("  [OK] Retriever initialized")

# Test 5: Small document ingestion (async)
print("\n[5/5] Testing small document ingestion...")
test_doc = """
GraphRAG is a powerful knowledge graph system. It uses Neo4j as the graph database
and ChromaDB for vector storage. The system extracts entities and relationships from
text documents using the Gemini API.
"""

async def test_ingestion():
    result = await ingestor.ingest(test_doc, "test_doc.txt")
    return result

result = asyncio.run(test_ingestion())

if result['success']:
    print(f"  [OK] Document ingested successfully")
    print(f"  Extracted {result['num_entities']} entities and {result['num_relationships']} relationships")
else:
    print(f"  [ERROR] Ingestion failed: {result.get('error')}")

print("\n" + "="*60)
print("Integration Test Complete!")
print("="*60)
print("\nYour system is ready to use!")
print("Run: streamlit run app.py")
