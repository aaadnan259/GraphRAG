"""
Complete Demo Script for GraphRAG System
This script demonstrates the full capabilities of the system.
"""

import asyncio
import sys
from pathlib import Path

print("="*70)
print("  GraphRAG System - Complete Demo")
print("="*70)

# Import modules
print("\n[Step 1] Loading system modules...")
try:
    from config import config
    from ingest import IngestionPipeline
    from retriever import HybridRetriever
    from models import QueryRequest
    print("  [OK] All modules loaded successfully")
except Exception as e:
    print(f"  [ERROR] Failed to load modules: {e}")
    sys.exit(1)

# Verify configuration
print("\n[Step 2] Verifying configuration...")
print(f"  API Key: {config.google_api_key[:20]}...")
print(f"  LLM Model: {config.llm_model}")
print(f"  Embedding Model: {config.embedding_model}")
print(f"  Neo4j URI: {config.neo4j_uri}")
print("  [OK] Configuration verified")

# Read sample document
print("\n[Step 3] Reading sample document...")
doc_path = Path("sample_document.txt")
if not doc_path.exists():
    print(f"  [ERROR] {doc_path} not found!")
    sys.exit(1)

with open(doc_path, 'r', encoding='utf-8') as f:
    document_text = f.read()

print(f"  Document: {doc_path.name}")
print(f"  Size: {len(document_text)} characters")
print("  [OK] Document loaded")

# Initialize pipeline
print("\n[Step 4] Initializing ingestion pipeline...")
try:
    pipeline = IngestionPipeline()
    pipeline.initialize_schema()
    print("  [OK] Pipeline ready")
except Exception as e:
    print(f"  [ERROR] Pipeline initialization failed: {e}")
    sys.exit(1)

# Ingest document
print("\n[Step 5] Ingesting document (this may take 30-60 seconds)...")
print("  Processing with Gemini API...")

async def ingest_doc():
    return await pipeline.ingest_document(document_text, doc_path.name)

try:
    result = asyncio.run(ingest_doc())

    if result['success']:
        print("\n  [SUCCESS] Document ingested!")
        print(f"  - Document ID: {result['document_id']}")
        print(f"  - Text chunks: {result['num_chunks']}")
        print(f"  - Entities extracted: {result['num_entities']}")
        print(f"  - Relationships created: {result['num_relationships']}")
    else:
        print(f"\n  [ERROR] Ingestion failed: {result.get('error')}")
        sys.exit(1)
except Exception as e:
    print(f"\n  [ERROR] Ingestion error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Initialize retriever
print("\n[Step 6] Initializing retriever...")
try:
    retriever = HybridRetriever()
    stats = retriever.get_graph_statistics()
    print(f"  Knowledge Graph Stats:")
    print(f"  - Total entities: {stats.get('total_entities', 0)}")
    print(f"  - Total relationships: {stats.get('total_relationships', 0)}")
    print("  [OK] Retriever ready")
except Exception as e:
    print(f"  [ERROR] Retriever initialization failed: {e}")
    sys.exit(1)

# Run test queries
print("\n[Step 7] Running test queries...")
print("-" * 70)

test_queries = [
    "Who is the CEO of TechVision Inc?",
    "What products does TechVision offer?",
    "Where are TechVision's offices located?",
    "What partnerships does TechVision have?",
    "Who are the major clients of TechVision?",
]

async def run_query(query: str):
    request = QueryRequest(
        query=query,
        use_vector_search=True,
        use_graph_search=True
    )
    return await retriever.retrieve(request)

for i, query in enumerate(test_queries, 1):
    print(f"\nQuery {i}: {query}")
    print("-" * 70)

    try:
        response = asyncio.run(run_query(query))
        print(f"\nAnswer:")
        print(f"{response.answer}")
        print(f"\nSources: {', '.join(response.sources)}")

        if i < len(test_queries):
            print("\n" + "=" * 70)
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")

# Display graph sample
print("\n[Step 8] Sample entities from knowledge graph...")
print("-" * 70)

try:
    sample_entities = retriever.search_entities("TechVision", limit=5)
    if sample_entities:
        print("Found entities:")
        for entity in sample_entities:
            print(f"  - {entity['name']} ({entity['type']})")
    else:
        print("  No entities found")
except Exception as e:
    print(f"  [ERROR] Entity search failed: {e}")

# Summary
print("\n" + "="*70)
print("  Demo Complete!")
print("="*70)
print("\nNext Steps:")
print("  1. Run the web interface: streamlit run app.py")
print("  2. Upload your own documents via the Ingestion tab")
print("  3. Ask questions via the Chat tab")
print("  4. Explore the knowledge graph in the Search tab")
print("\nYour GraphRAG system is fully operational!")
print("="*70)
