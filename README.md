# FastAPI Documentation RAG System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://github.com/jnzm02/ai-sandbox/actions/workflows/test.yml/badge.svg)](https://github.com/jnzm02/ai-sandbox/actions/workflows/test.yml)
[![Docker Build](https://github.com/jnzm02/ai-sandbox/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/jnzm02/ai-sandbox/actions/workflows/docker-publish.yml)
[![Production](https://img.shields.io/badge/status-deployed-success.svg)](https://github.com/jnzm02/ai-sandbox)

Production-ready **Retrieval-Augmented Generation (RAG)** system for querying FastAPI documentation. Built to demonstrate AI systems engineering best practices: from prototype to production in one weekend.

**🚀 Live Production Deployment** | [Deployment Guide](DEPLOYMENT_WORKFLOW.md) | [API Docs](#api-endpoints)

**🎯 Perfect for:** Backend engineers learning AI/ML systems • RAG architecture reference • Interview portfolio projects

> **Weekend Project → Production API**: This repo shows the complete journey from zero to a deployed RAG system with proper architecture, testing, and containerization.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI REST API                      │
│  (Multi-user, Session Management, CORS-enabled)          │
└──────────────┬──────────────────────────────────────────┘
               │
               ├─ GET  /health         (Health check)
               ├─ POST /query          (Stateless Q&A)
               ├─ POST /chat           (Conversational)
               └─ GET  /sessions       (Session mgmt)

               ↓
┌─────────────────────────────────────────────────────────┐
│              RAG Pipeline (LangChain)                    │
└──────────────┬──────────────────────────────────────────┘
               │
               ├─ Embedding Model: all-MiniLM-L6-v2 (local)
               ├─ Vector DB: ChromaDB (2,388 embeddings)
               └─ LLM: Claude 3 Haiku (Anthropic)
```

## Features

- ✅ **Stateless Query**: One-off questions without conversation memory
- ✅ **Stateful Chat**: Multi-turn conversations with context
- ✅ **Multi-User Support**: Isolated sessions per user
- ✅ **Source Attribution**: Every answer cites FastAPI docs
- ✅ **Production-Ready**: Docker, health checks, CORS, error handling
- ✅ **Local Embeddings**: No embedding API costs

## Quick Start

### 1. Prerequisites

```bash
# Python 3.10+
python3 --version

# Install dependencies
pip install -r requirements.txt
```

### 2. Index Documentation (One-time)

```bash
# Clone FastAPI docs & generate embeddings (~30 seconds)
python3 src/ingest.py
```

### 3. Run API Server

```bash
# Start server
python3 src/api.py

# Server runs on: http://localhost:8000
# API docs: http://localhost:8000/docs
```

### 4. Test API

```bash
# Run test suite
python3 test_api.py

# Or use curl
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I handle CORS?"}'
```

## API Endpoints

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "vector_db_count": 2388,
  "active_sessions": 0,
  "timestamp": "2026-03-30T..."
}
```

### Stateless Query
```http
POST /query
Content-Type: application/json

{
  "question": "How do I use path parameters?"
}
```

**Response:**
```json
{
  "answer": "To use path parameters in FastAPI...",
  "sources": [
    {"path": "tutorial/path-params.md"},
    {"path": "tutorial/first-steps.md"}
  ],
  "processing_time_ms": 1234.56
}
```

### Stateful Chat
```http
POST /chat
Content-Type: application/json

{
  "session_id": "user-123",
  "question": "What is CORS?"
}
```

**Response:**
```json
{
  "answer": "CORS stands for Cross-Origin Resource Sharing...",
  "sources": [...],
  "session_id": "user-123",
  "processing_time_ms": 1567.89
}
```

**Follow-up question:**
```http
POST /chat
Content-Type: application/json

{
  "session_id": "user-123",
  "question": "How do I configure it?"  # "it" = CORS from previous turn
}
```

### Session Management
```http
# List sessions
GET /sessions

# Clear session
DELETE /sessions/{session_id}
```

## Docker Deployment

### Local Development

```bash
# Build image
docker-compose build

# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

### Production Deployment (VPS)

This project includes **complete production deployment automation** with CI/CD, automated backups, and monitoring.

**📚 Full Deployment Guide**: See [DEPLOYMENT_WORKFLOW.md](DEPLOYMENT_WORKFLOW.md)

#### Quick Production Deploy

```bash
# 1. Prepare locally
make deploy-init          # Initialize deployment files
make ingest              # Create vector database
make docker-build        # Build and test Docker image

# 2. Deploy to server (automated)
./deploy/quick-deploy.sh  # Interactive deployment wizard
```

#### What's Included

- ✅ **Automated CI/CD**: GitHub Actions → Docker builds → Container Registry
- ✅ **Security Hardening**: Firewall, SSH, Fail2Ban, malware prevention
- ✅ **Automated Backups**: Daily backups (2.8 GB), 14-day retention
- ✅ **Git-based Updates**: Pull updates directly from GitHub
- ✅ **Health Monitoring**: CPU, API, backup validation (every 5 min)
- ✅ **Zero-Downtime Deploys**: Health checks, auto-restart
- ✅ **Production Docs**: Comprehensive guides, checklists, troubleshooting

#### Production Stack

```
GitHub Actions (CI/CD)
       ↓
GitHub Container Registry
       ↓
VPS Server (Ubuntu)
  ├─ Docker (Containerization)
  ├─ Nginx (Reverse proxy, rate limiting)
  ├─ Fail2Ban (Intrusion prevention)
  └─ Automated monitoring & backups
```

#### Update Production

```bash
# Local: Make changes
git add .
git commit -m "Your changes"
git push origin main

# Server: Pull and deploy
ssh root@YOUR_SERVER_IP
cd /opt/rag-api
./deploy/update-from-git.sh
```

**Production Status**: ✅ Deployed and Operational

**Live URLs**:
- **Landing Page**: https://aether-guard.com
- **API Endpoint**: `api.aether-guard.com` (pending DNS configuration)
- **API Documentation**: [API Usage Guide](API_USAGE_GUIDE.md)

**See**: [Deployment Checklist](DEPLOYMENT_CHECKLIST.md) | [VPS Guide](DEPLOYMENT_VPS.md) | [DNS Setup](DNS_SETUP_GUIDE.md)

## Project Structure

```
ai-sandbox/
├── src/
│   ├── ingest.py       # Phase 1: Document indexing
│   ├── query.py        # Phase 2: Stateless Q&A (CLI)
│   ├── chat.py         # Phase 3: Conversational (CLI)
│   └── api.py          # Phase 4: Production REST API
│
├── data/
│   ├── chroma_db/      # Vector database (persistent)
│   └── fastapi_repo/   # Cloned FastAPI docs
│
├── test_api.py         # API integration tests
├── test_rag.py         # RAG system tests
├── test_conversation.py # Stateless vs stateful demo
│
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container image
├── docker-compose.yml  # Orchestration
└── README.md           # This file
```

## Performance

| Metric | Value |
|--------|-------|
| Vector DB Size | 2,388 embeddings |
| Index Time | ~30 seconds |
| Query Latency | 1-3 seconds |
| Memory Usage | ~1.5 GB (embedding model + DB) |
| API Throughput | ~10 req/sec (single instance) |

## Cost Analysis

| Component | Cost |
|-----------|------|
| Embedding Model | $0 (local) |
| Vector DB | $0 (local) |
| LLM (Claude Haiku) | ~$0.001 per query |
| **Total for 1,000 queries** | **~$1** |

## Production Considerations

### 1. API Key Management
```python
# Use secrets manager in production
import os
from aws_secretsmanager import get_secret

ANTHROPIC_API_KEY = get_secret("anthropic-api-key")
```

### 2. Rate Limiting
```python
# Add to api.py
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/query")
@limiter.limit("10/minute")
async def query_stateless(...):
    ...
```

### 3. Observability
```python
# Structured logging
import structlog

logger = structlog.get_logger()
logger.info("query_processed",
            question=question,
            latency_ms=latency,
            sources=[...])
```

### 4. Caching
```python
# Cache frequent queries
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_answer(question_hash):
    ...
```

### 5. Load Balancing
```yaml
# Nginx upstream
upstream rag_api {
    server rag-api-1:8000;
    server rag-api-2:8000;
    server rag-api-3:8000;
}
```

## Troubleshooting

### Issue: "ModuleNotFoundError"
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Vector DB not found"
```bash
# Re-index documents
python3 src/ingest.py
```

### Issue: "API key invalid"
```bash
# Check .env file
cat .env
# Verify key at: https://console.anthropic.com/
```

### Issue: "Out of memory"
```bash
# Reduce model size or use smaller vector DB
# Alternative: Use quantized embeddings
```

## Next Steps

1. **Add Reranking**: Use cross-encoder to rerank top-10 chunks
2. **Hybrid Search**: Combine semantic + keyword (BM25)
3. **Evaluation**: Build test set with ground truth answers
4. **Streaming**: Stream LLM responses for better UX
5. **Multi-Modal**: Add diagram/image support

## License

MIT

## Author

Built by a Backend Engineer learning AI Systems Architecture.

**Stack**: Python • LangChain • FastAPI • ChromaDB • Claude • Docker
