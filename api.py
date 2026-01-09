
"""
FastAPI Backend for GraphRAG.
Handles API requests for querying, ingestion, and graph statistics.
"""

import logging
import shutil
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import config
from models import QueryRequest, QueryResponse
from ingest import Ingestor
from retriever import HybridRetriever

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GraphRAG API", version="1.0.0")

# CORS Configuration
origins = [
    "http://localhost:5173",  # Vite Dev Server
    "http://localhost:3000",  # Fallback React port
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "GraphRAG API"}


@app.post("/query", response_model=QueryResponse)
async def query_knowledge_graph(request: QueryRequest):
    """
    Process a user query using hybrid retrieval (Vector + Graph).
    """
    try:
        retriever = HybridRetriever()
        response = await retriever.retrieve(request)
        return response
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingest a document (text or markdown) into the knowledge graph.
    """
    try:
        # Validate file type
        if not file.filename.endswith((".txt", ".md")):
             raise HTTPException(status_code=400, detail="Only .txt and .md files are supported")

        content = await file.read()
        text = content.decode("utf-8")

        ingestor = Ingestor()
        # Ensure schema exists before ingesting
        ingestor.init_schema()
        
        result = await ingestor.ingest(text, file.filename)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown ingestion error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_graph_stats():
    """
    Retrieve statistics about the knowledge graph.
    """
    try:
        retriever = HybridRetriever()
        stats = retriever.get_graph_statistics()
        return stats
    except Exception as e:
        logger.error(f"Stats fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/entities")
async def search_entities(query: str, limit: int = 10):
    """
    Search for entities in the graph by name.
    """
    try:
        retriever = HybridRetriever()
        entities = retriever.search_entities(query, limit)
        return {"entities": entities}
    except Exception as e:
        logger.error(f"Entity search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
