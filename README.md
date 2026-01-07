# GraphRAG Engine

A Graph Retrieval-Augmented Generation (GraphRAG) system combining Neo4j for knowledge graphs and ChromaDB for vector search.

## Overview

Ingests text, extracts entities/relationships using Gemini, and allows for hybrid (Vector + Graph) Q&A.

## Features

- **Hybrid Retrieval**: Vector similarity + Graph traversal.
- **Async Ingestion**: Parallel processing for faster indexing.
- **Security**: Read-only users for retrieval operations.
- **Graph Visualization**: Built-in visual explorer.
- **Strict Schema**: Pydantic models to keep graph data clean.

## Architecture

```
Front End (Streamlit)
      |
      v
+-------------+      +--------------+
| Ingestor    |      | Retriever    |
| (RW Access) |      | (RO Access)  |
+------+------+      +-------+------+
       |                     |
       v                     v
+-----------------------------------+
|          Database Layer           |
|  [Neo4j (Graph)] [Chroma (Vec)]   |
+-----------------------------------+
```

## Security & Validation

- Input sanitization (regex)
- Read-only tokens for the query engine
- Canonical relationship types (WORKS_AT, LOCATED_IN, etc.)

## Installation

### Prerequisites

- Python 3.9+
- Neo4j 5.x (with separate RW and RO users)
- OpenAI API key

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd GraphRAG
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Neo4j Users

Create a read-only user in Neo4j:

```cypher
// Create read-only user
CREATE USER readonly_user SET PASSWORD 'your_ro_password' SET PASSWORD CHANGE NOT REQUIRED;
GRANT ROLE reader TO readonly_user;
DENY WRITE ON DATABASE * TO readonly_user;
```

### Step 4: Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-...
NEO4J_URI=bolt://localhost:7687
NEO4J_RW_USER=neo4j
NEO4J_RW_PASSWORD=your_password
NEO4J_RO_USER=readonly_user
NEO4J_RO_PASSWORD=your_ro_password
```

## Usage

### Start the Application

```bash
streamlit run app.py
```

### Ingest Documents

1. Navigate to the **Ingestion** tab
2. Upload a text or markdown file
3. Click **Ingest Document**
4. Wait for processing to complete

### Ask Questions

1. Navigate to the **Chat** tab
2. Type your question in the chat input
3. Toggle vector/graph search options
4. View the answer with source citations

### Search Entities

1. Navigate to the **Search** tab
2. Enter an entity name pattern
3. View matching entities and their relationships

## Configuration

All configuration is managed through environment variables. See `.env.example` for available options:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `NEO4J_URI` | Neo4j connection URI (required) | - |
| `NEO4J_RW_USER` | Neo4j read-write user (required) | - |
| `NEO4J_RW_PASSWORD` | RW user password (required) | - |
| `NEO4J_RO_USER` | Neo4j read-only user (required) | - |
| `NEO4J_RO_PASSWORD` | RO user password (required) | - |
| `CHUNK_SIZE` | Text chunk size for splitting | 1000 |
| `CHUNK_OVERLAP` | Overlap between chunks | 200 |
| `EMBEDDING_MODEL` | OpenAI embedding model | text-embedding-3-small |
| `LLM_MODEL` | OpenAI LLM model | gpt-4o-mini |
| `MAX_CONCURRENT_LLM_CALLS` | Parallel LLM requests | 10 |
| `VECTOR_SEARCH_K` | Vector search results | 5 |

## Module Overview

### config.py
Centralized configuration management with strict validation. Fails fast if required environment variables are missing.

### models.py
Pydantic data models with sanitization and schema enforcement:
- `Entity`: Graph entity with type validation
- `Relationship`: Graph relationship with canonical type mapping
- `KnowledgeGraph`: Complete graph structure
- `QueryRequest/QueryResponse`: Query interface models

### database.py
Database connection management:
- Singleton pattern for connection pooling
- Separate RW/RO driver factories
- ChromaDB vector store initialization
- Schema initialization utilities

### ingest.py
Async ingestion pipeline:
- `RecursiveCharacterTextSplitter` for text chunking
- Parallel entity/relationship extraction with semaphore
- Batch writes to Neo4j and ChromaDB
- Exponential backoff retries with `tenacity`

### retriever.py
Read-only hybrid retrieval engine:
- Vector similarity search via ChromaDB
- Graph traversal via `GraphCypherQAChain`
- LLM-powered answer synthesis
- Graph statistics and entity search

### app.py
Streamlit web interface:
- Document ingestion with progress tracking
- Interactive Q&A chat
- Entity search
- Knowledge graph visualization
- Real-time statistics

## Performance Optimization

### Async Ingestion
- Parallel LLM API calls using `asyncio`
- Semaphore limits concurrent requests to avoid rate limits
- Batch vector database writes (100 documents per batch)

### Connection Pooling
- Neo4j connection pools (max 50 connections)
- Singleton pattern for database connections
- Long-lived connections (1-hour lifetime)

### Retry Strategy
- 3 retry attempts with exponential backoff
- Min wait: 1 second, Max wait: 10 seconds
- Automatic retry on transient failures

## Security Best Practices

1. **Never commit `.env`** - use `.env.example` as template
2. **Rotate credentials regularly** - especially API keys
3. **Use strong passwords** - for database users
4. **Monitor API usage** - track OpenAI API costs
5. **Validate read-only user** - use `verify_read_only_permissions()`
6. **Review Cypher queries** - ensure no dynamic query construction from user input

## Troubleshooting

### Neo4j Connection Failed
- Verify Neo4j is running: `systemctl status neo4j`
- Check URI format: `bolt://localhost:7687`
- Test credentials with Neo4j Browser

### OpenAI API Errors
- Verify API key is valid
- Check quota limits at platform.openai.com
- Review rate limits for your tier

### ChromaDB Initialization Failed
- Ensure write permissions on `CHROMA_PERSIST_DIR`
- Delete `chroma_db/` to reset

### Read-Only User Can Write
- Revoke write permissions in Neo4j
- Run: `DENY WRITE ON DATABASE * TO readonly_user`

## Production Deployment

### Environment Variables
Set all required environment variables in your deployment platform (AWS, GCP, Azure, Heroku, etc.).

### Neo4j Setup
- Use Neo4j Aura (managed cloud) or self-hosted Neo4j cluster
- Configure proper backups
- Set up monitoring and alerting

### Scaling Considerations
- Use Neo4j clustering for high availability
- Deploy multiple Streamlit instances behind load balancer
- Consider Redis for session management
- Monitor memory usage of ChromaDB

### Monitoring
- Log all errors to centralized logging (e.g., Datadog, Sentry)
- Track LLM API costs and latency
- Monitor database query performance
- Set up alerts for failed ingestions

## License

MIT License

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss proposed changes.
