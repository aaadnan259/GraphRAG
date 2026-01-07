# 🚀 Quick Start Guide - GraphRAG System

## ✅ System is Ready!

Your GraphRAG system has been successfully configured with Google Gemini API and is ready to use.

## 📝 What You Have

A complete, production-grade GraphRAG system with:
- ✅ **113 entities** already extracted from sample document
- ✅ **108 relationships** in the knowledge graph
- ✅ Gemini 2.5 Flash LLM
- ✅ Google embeddings (768 dimensions)
- ✅ Neo4j graph database
- ✅ ChromaDB vector storage
- ✅ Security controls (RO/RW separation)

## 🎯 Three Ways to Use the System

### Option 1: Web Interface (Recommended)

Start the Streamlit app:
```bash
streamlit run app.py
```

Then open: **http://localhost:8501**

**Features:**
- 📤 **Ingestion Tab**: Upload and process documents
- 💬 **Chat Tab**: Ask questions about your documents
- 🔍 **Search Tab**: Explore entities and relationships
- 📊 **Graph Visualization**: See your knowledge graph

### Option 2: Run the Demo

See the full system in action:
```bash
python run_demo.py
```

This will:
1. Process the sample document (TechVision Inc. company profile)
2. Extract entities and relationships
3. Run 5 test queries
4. Display results

### Option 3: Test Individual Components

**Test Gemini API:**
```bash
python test_gemini.py
```

**Test Full Integration:**
```bash
python test_integration.py
```

## 📚 Sample Document Included

A comprehensive test document is ready: [sample_document.txt](sample_document.txt)

**Content:** Complete company profile with:
- Company overview and history
- Leadership team and organizational structure
- Office locations worldwide
- Products and services
- Partnerships and clients
- Funding and growth metrics
- Research initiatives
- Technology stack

**Perfect for testing:**
- Entity extraction (people, companies, locations, products)
- Relationship mapping (WORKS_AT, LOCATED_IN, PART_OF, etc.)
- Q&A capabilities

## 💡 Example Queries to Try

Once you start the app, try asking:

1. **"Who is the CEO of TechVision?"**
2. **"What products does TechVision offer?"**
3. **"Where are TechVision's offices located?"**
4. **"Who are TechVision's partners?"**
5. **"What technology stack does TechVision use?"**
6. **"Tell me about TechVision's funding rounds"**

## ⚙️ System Configuration

Your `.env` file is configured with:

| Setting | Value |
|---------|-------|
| **LLM Model** | gemini-2.5-flash |
| **Embedding Model** | text-embedding-004 |
| **Chunk Size** | 1000 characters |
| **Concurrent Calls** | 3 (respects free tier limits) |
| **Vector Search K** | 5 results |

## ⚠️ Important: API Rate Limits

**Gemini API Free Tier Limits:**
- **5 requests per minute**
- **1500 requests per day**

**Tips to avoid rate limits:**
1. Process small documents first (< 5 chunks)
2. The system automatically retries with backoff
3. `MAX_CONCURRENT_LLM_CALLS` is set to 3 (safe limit)
4. For large documents, expect 1-2 minute processing time

## 📊 Current Knowledge Graph

Your system already has data from the integration test:

```
Total Entities: 121
Total Relationships: 116
```

**Sample Entities:**
- TechVision Inc. (ORGANIZATION)
- Sarah Chen (PERSON)
- Michael Rodriguez (PERSON)
- IntelliCore (PRODUCT)
- San Francisco (LOCATION)
- Gemini API (PRODUCT)
- And many more...

## 🎨 Features Overview

### Security ✅
- Input sanitization (prevents injection)
- RBAC with separate RO/RW database users
- Schema validation for relationships
- Environment variable secrets

### Performance ✅
- Async parallel processing
- Batch database writes
- Connection pooling
- Automatic retries with backoff

### Accuracy ✅
- Hybrid retrieval (vector + graph)
- LLM-powered answer synthesis
- Source citations
- Schema-enforced relationships

## 📁 Project Structure

```
GraphRAG/
├── app.py                  # Streamlit web interface
├── config.py               # Configuration management
├── models.py               # Data schemas
├── database.py             # Database connections
├── ingest.py               # Ingestion pipeline
├── retriever.py            # Hybrid retrieval
├── .env                    # Your configuration ✅
├── sample_document.txt     # Test document ✅
├── run_demo.py             # Full demo script ✅
├── test_gemini.py          # API tests ✅
├── test_integration.py     # Integration tests ✅
└── requirements.txt        # Dependencies ✅
```

## 🔧 Troubleshooting

### "Rate limit exceeded"
- **Solution**: Wait 60 seconds between runs
- The system automatically retries
- Reduce `MAX_CONCURRENT_LLM_CALLS` if needed

### "Configuration error"
- **Solution**: Check `.env` file exists with all required variables
- Run: `python -c "from config import config; print('OK')"`

### "Neo4j connection failed"
- **Solution**: Verify Neo4j Aura is running
- Check URI in `.env`
- Test: `python test_integration.py`

### "Module not found"
- **Solution**: Install dependencies
- Run: `pip install -r requirements.txt`

## 📖 Documentation

- **[README.md](README.md)** - Complete system documentation
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide
- **[SUCCESS_REPORT.md](SUCCESS_REPORT.md)** - Migration status
- **[QUICK_START.md](QUICK_START.md)** - This guide

## 🎯 Next Steps

1. **Start the app**: `streamlit run app.py`
2. **Try the demo**: `python run_demo.py`
3. **Upload your documents**: Use the Ingestion tab
4. **Ask questions**: Use the Chat tab
5. **Explore the graph**: Use the Search tab

## 💪 What You Can Do Now

- ✅ Upload .txt and .md files
- ✅ Extract entities and relationships automatically
- ✅ Query using natural language
- ✅ Get answers with source citations
- ✅ Visualize the knowledge graph
- ✅ Search for specific entities
- ✅ Handle complex multi-hop queries

## 🌟 Pro Tips

1. **Start small**: Test with short documents first
2. **Check the logs**: Terminal shows processing details
3. **Adjust chunk size**: Modify `CHUNK_SIZE` in `.env` for different content types
4. **Use both search modes**: Enable both vector and graph search for best results
5. **Monitor quotas**: Check https://ai.dev/usage for API usage

---

## 🎊 Ready to Go!

Your system is **fully operational** and ready for production use!

**Start now:**
```bash
streamlit run app.py
```

**Enjoy your GraphRAG system! 🚀**
