# Production Deployment Guide

This guide covers deploying GraphRAG Engine to production environments.

## Pre-Deployment Checklist

- [ ] All environment variables configured
- [ ] Neo4j read-only user created and verified
- [ ] Security tests passed (`python test_security.py`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Database backups configured
- [ ] Monitoring and logging set up

## Security Verification

Before deploying, run the security test suite:

```bash
python test_security.py
```

Expected output:
```
✓ PASS - Configuration
✓ PASS - Neo4j Connectivity
✓ PASS - Read-Only Permissions
✓ PASS - Relationship Schema
✓ PASS - Input Sanitization

✓ ALL TESTS PASSED - System is secure and ready for deployment
```

## Neo4j Setup

### Option 1: Neo4j Aura (Managed Cloud)

1. Create account at https://neo4j.com/cloud/aura/
2. Create new database instance
3. Note connection URI and credentials
4. Create read-only user:

```cypher
CREATE USER readonly_user SET PASSWORD 'strong_password' SET PASSWORD CHANGE NOT REQUIRED;
GRANT ROLE reader TO readonly_user;
DENY WRITE ON DATABASE * TO readonly_user;
```

### Option 2: Self-Hosted Neo4j

1. Install Neo4j 5.x from https://neo4j.com/download/
2. Configure authentication in `neo4j.conf`
3. Run setup script:

```bash
cypher-shell -u neo4j -p password < setup_neo4j.cypher
```

4. Verify permissions:

```bash
# Should fail with permission error
cypher-shell -u readonly_user -p ro_password \
  "CREATE (test:TestNode {name: 'check'})"
```

## Environment Configuration

### Production .env Template

```env
# OpenAI
OPENAI_API_KEY=sk-proj-...

# Neo4j (Production)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_RW_USER=neo4j
NEO4J_RW_PASSWORD=<strong-password>
NEO4J_RO_USER=readonly_user
NEO4J_RO_PASSWORD=<strong-ro-password>

# Performance Tuning
MAX_CONCURRENT_LLM_CALLS=20
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Monitoring
LOG_LEVEL=INFO
```

## Deployment Platforms

### AWS (EC2 + RDS/DocumentDB)

```bash
# Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv

# Clone repository
git clone <repo-url>
cd GraphRAG

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="sk-..."
export NEO4J_URI="bolt://..."
# ... (set all required vars)

# Run application
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:

```bash
docker build -t graphrag-engine .
docker run -p 8501:8501 --env-file .env graphrag-engine
```

### Docker Compose (with Neo4j)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15
    environment:
      NEO4J_AUTH: neo4j/your_password
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data

  graphrag:
    build: .
    ports:
      - "8501:8501"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_RW_USER=neo4j
      - NEO4J_RW_PASSWORD=your_password
      - NEO4J_RO_USER=readonly_user
      - NEO4J_RO_PASSWORD=ro_password
    depends_on:
      - neo4j

volumes:
  neo4j_data:
```

Run:

```bash
docker-compose up -d
```

### Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: graphrag-secrets
type: Opaque
stringData:
  openai-api-key: "sk-..."
  neo4j-rw-password: "password"
  neo4j-ro-password: "ro_password"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: graphrag-engine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: graphrag
  template:
    metadata:
      labels:
        app: graphrag
    spec:
      containers:
      - name: graphrag
        image: your-registry/graphrag-engine:latest
        ports:
        - containerPort: 8501
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: graphrag-secrets
              key: openai-api-key
        - name: NEO4J_URI
          value: "bolt://neo4j-service:7687"
        - name: NEO4J_RW_USER
          value: "neo4j"
        - name: NEO4J_RW_PASSWORD
          valueFrom:
            secretKeyRef:
              name: graphrag-secrets
              key: neo4j-rw-password
        - name: NEO4J_RO_USER
          value: "readonly_user"
        - name: NEO4J_RO_PASSWORD
          valueFrom:
            secretKeyRef:
              name: graphrag-secrets
              key: neo4j-ro-password

---
apiVersion: v1
kind: Service
metadata:
  name: graphrag-service
spec:
  selector:
    app: graphrag
  ports:
  - port: 80
    targetPort: 8501
  type: LoadBalancer
```

Deploy:

```bash
kubectl apply -f k8s-deployment.yaml
```

### Heroku Deployment

```bash
# Install Heroku CLI
heroku login

# Create app
heroku create graphrag-engine

# Set environment variables
heroku config:set OPENAI_API_KEY="sk-..."
heroku config:set NEO4J_URI="neo4j+s://..."
heroku config:set NEO4J_RW_USER="neo4j"
heroku config:set NEO4J_RW_PASSWORD="password"
heroku config:set NEO4J_RO_USER="readonly_user"
heroku config:set NEO4J_RO_PASSWORD="ro_password"

# Deploy
git push heroku main
```

Create `Procfile`:

```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

## Performance Tuning

### Neo4j Optimization

```cypher
// Create additional indexes
CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE FULLTEXT INDEX entity_search IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.description];

// Configure database settings in neo4j.conf
dbms.memory.heap.initial_size=2G
dbms.memory.heap.max_size=4G
dbms.memory.pagecache.size=2G
```

### Application Tuning

```env
# Increase concurrency for large documents
MAX_CONCURRENT_LLM_CALLS=50

# Optimize chunk size based on document type
CHUNK_SIZE=1500
CHUNK_OVERLAP=300

# Increase vector search results
VECTOR_SEARCH_K=10
```

### Load Balancing

Use nginx as reverse proxy:

```nginx
upstream graphrag {
    server 127.0.0.1:8501;
    server 127.0.0.1:8502;
    server 127.0.0.1:8503;
}

server {
    listen 80;
    server_name graphrag.example.com;

    location / {
        proxy_pass http://graphrag;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## Monitoring

### Application Metrics

```python
# Add to app.py
import prometheus_client
from prometheus_client import Counter, Histogram

ingestion_counter = Counter('graphrag_ingestions_total', 'Total document ingestions')
query_counter = Counter('graphrag_queries_total', 'Total queries')
query_duration = Histogram('graphrag_query_duration_seconds', 'Query duration')
```

### Neo4j Monitoring

```cypher
// Active connections
CALL dbms.listConnections();

// Query performance
CALL dbms.listQueries();

// Database statistics
CALL apoc.meta.stats();
```

### Logging

Configure centralized logging:

```python
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler('graphrag.log', maxBytes=10000000, backupCount=5)
logging.basicConfig(handlers=[handler], level=logging.INFO)
```

## Backup and Recovery

### Neo4j Backup

```bash
# Online backup (Enterprise Edition)
neo4j-admin backup --from=bolt://localhost:7687 --backup-dir=/backups

# Dump database
neo4j-admin dump --database=neo4j --to=/backups/neo4j-backup.dump

# Restore from dump
neo4j-admin load --from=/backups/neo4j-backup.dump --database=neo4j --force
```

### ChromaDB Backup

```bash
# Backup vector database
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz ./chroma_db/

# Restore
tar -xzf chroma_backup_20240115.tar.gz
```

## Security Hardening

### HTTPS Configuration

Use Let's Encrypt for SSL certificates:

```bash
sudo apt install certbot
sudo certbot --nginx -d graphrag.example.com
```

### Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### Rate Limiting

```python
# Add to app.py
from streamlit_ratelimit import rate_limit

@rate_limit(max_calls=100, period=3600)
def process_query(query):
    # ... implementation
    pass
```

## Troubleshooting

### High Memory Usage

- Reduce `MAX_CONCURRENT_LLM_CALLS`
- Decrease `CHUNK_SIZE`
- Implement pagination for large results

### Slow Queries

- Add Neo4j indexes for frequently queried properties
- Optimize Cypher queries with `EXPLAIN` and `PROFILE`
- Increase Neo4j heap size

### API Rate Limits

- Implement request queuing
- Use exponential backoff (already implemented)
- Upgrade OpenAI tier

## Maintenance

### Regular Tasks

- Weekly: Review logs for errors
- Monthly: Update dependencies (`pip list --outdated`)
- Quarterly: Rotate API keys and passwords
- Annually: Review and update security policies

### Updates

```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Update Neo4j
# Follow Neo4j upgrade guide for version migrations

# Restart application
systemctl restart graphrag
```

## Support

For issues and questions:
- GitHub Issues: <repository-url>/issues
- Documentation: README.md
- Security Issues: Report via security@example.com
