
"""
FastAPI Backend for GraphRAG.
Handles API requests for querying, ingestion, and graph statistics.
"""

import logging

import codecs
from typing import AsyncIterator

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import config
from models import QueryRequest, QueryResponse
from ingest import Ingestor
from retriever import HybridRetriever

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GraphRAG API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.exception("Global exception handler caught: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
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
    retriever = HybridRetriever()
    response = await retriever.retrieve(request)
    return response


@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingest a document (text or markdown) into the knowledge graph.
    """
    # Validate file type
    if not file.filename.endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail="Only .txt and .md files are supported")

    async def file_generator(file: UploadFile) -> AsyncIterator[str]:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        total_size = 0
        CHUNK_SIZE = 1024 * 1024  # 1MB

        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > config.max_file_size:
                raise ValueError(f"File too large. Maximum size is {config.max_file_size} bytes")
            yield decoder.decode(chunk, final=False)

        yield decoder.decode(b"", final=True)

    ingestor = Ingestor()
    # Ensure schema exists before ingesting
    ingestor.init_schema()

    result = await ingestor.ingest(file_generator(file), file.filename)

    if not result["success"]:
        error_msg = result.get("error", "Unknown ingestion error")
        if "File too large" in error_msg:
            raise HTTPException(status_code=413, detail=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

    return result


@app.get("/stats")
async def get_graph_stats():
    """
    Retrieve statistics about the knowledge graph.
    """
    retriever = HybridRetriever()
    stats = await retriever.get_graph_statistics()
    return stats


@app.get("/search/entities")
async def search_entities(query: str, limit: int = 10):
    """
    Search for entities in the graph by name.
    """
    retriever = HybridRetriever()
    entities = await retriever.search_entities(query, limit)
    return {"entities": entities}
