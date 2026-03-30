# Deployment Guide

This guide covers deploying the RAG API in different environments.

## Architecture Overview

The Docker image is designed to work in multiple environments:
- **CI/CD**: Build-only validation (no runtime data required)
- **Local Development**: Docker Compose with volume mounts
- **Production**: Kubernetes/cloud with external volumes

## Prerequisites

1. **Vector Database**: Must be pre-indexed before deployment
   ```bash
   python3 src/ingest.py
   # Creates: data/chroma_db/ with 2,388 embeddings
   ```

2. **API Key**: Get from https://console.anthropic.com/

## Local Development with Docker Compose

### Step 1: Prepare Environment

```bash
# Create .env file
echo "ANTHROPIC_API_KEY=your_actual_key_here" > .env

# Index documents (one-time setup)
python3 src/ingest.py
```

### Step 2: Start Services

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Test health
curl http://localhost:8000/health
```

### Step 3: Use the API

```bash
# Stateless query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I handle CORS in FastAPI?"}'

# Stateful chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user-123", "question": "What is dependency injection?"}'
```

### Step 4: Stop Services

```bash
docker-compose down
```

## Production Deployment

### Option 1: Docker with Volume Mounts

```bash
# 1. Build image
docker build -t rag-api:v1.0 .

# 2. Run with environment variables and volume
docker run -d \
  --name rag-api \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_key_here \
  -v $(pwd)/data/chroma_db:/app/data/chroma_db:ro \
  --restart unless-stopped \
  rag-api:v1.0

# 3. Health check
docker logs rag-api
curl http://localhost:8000/health
```

### Option 2: Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-api
  template:
    metadata:
      labels:
        app: rag-api
    spec:
      containers:
      - name: rag-api
        image: your-registry/rag-api:v1.0
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: anthropic-secret
              key: api-key
        volumeMounts:
        - name: vector-db
          mountPath: /app/data/chroma_db
          readOnly: true
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
      volumes:
      - name: vector-db
        persistentVolumeClaim:
          claimName: chroma-db-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: rag-api-service
spec:
  selector:
    app: rag-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

**Deploy:**
```bash
# Create secret for API key
kubectl create secret generic anthropic-secret \
  --from-literal=api-key=your_actual_key_here

# Create PVC for vector DB (copy data first)
kubectl apply -f k8s-pvc.yaml

# Deploy application
kubectl apply -f k8s-deployment.yaml

# Get external IP
kubectl get service rag-api-service
```

### Option 3: Cloud Run (Serverless)

**Important**: Cloud Run has cold start issues. Not recommended for this use case due to large embedding model loading time.

## CI/CD Pipeline

The GitHub Actions workflow tests:
1. **Python tests**: Linting and type checking
2. **Docker build**: Validates image builds correctly
3. **Import tests**: Ensures all dependencies are installed

**Note**: Full API tests require:
- Indexed vector database
- Valid Anthropic API key
- Run these in staging environment, not CI

## Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key | `sk-ant-...` |
| `HOST` | No | API bind address | `0.0.0.0` (default) |
| `PORT` | No | API port | `8000` (default) |

## Data Requirements

### Vector Database Location
The API expects the vector database at: `/app/data/chroma_db/`

**Production options:**
1. **Persistent Volume**: Mount pre-indexed DB as read-only volume
2. **Init Container**: Run indexing as Kubernetes init container
3. **Sidecar**: Separate service that updates DB periodically

### Storage Requirements
- Vector DB: ~500 MB (for FastAPI docs)
- Embedding model cache: ~100 MB
- Total: ~600 MB persistent storage

## Scaling Considerations

### Horizontal Scaling
```bash
# Docker Compose
docker-compose up -d --scale rag-api=3

# Kubernetes
kubectl scale deployment rag-api --replicas=5
```

**Session management**:
- In-memory sessions (current implementation)
- For multi-instance: Use Redis for shared session storage

### Load Balancing
```nginx
# nginx.conf
upstream rag_api {
    least_conn;
    server rag-api-1:8000;
    server rag-api-2:8000;
    server rag-api-3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://rag_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Performance Tuning

### 1. Model Caching
```python
# Pre-load models in Dockerfile
RUN python3 -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
print('Model cached')
"
```

### 2. Resource Limits
```yaml
# docker-compose.yml
services:
  rag-api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 3. Connection Pooling
Already implemented via singleton RAGService pattern.

## Monitoring

### Health Checks
```bash
# Check API health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "vector_db_count": 2388,
  "active_sessions": 0,
  "timestamp": "2026-03-30T..."
}
```

### Metrics to Track
- Request latency (p50, p95, p99)
- Active sessions count
- Memory usage
- API error rate
- LLM token usage

### Logging
```python
# Structured logging (add to api.py)
import structlog

logger = structlog.get_logger()

@app.post("/query")
async def query_stateless(request: QueryRequest):
    start = time.time()
    # ... process request ...
    logger.info("query_processed",
                question=request.question,
                latency_ms=(time.time() - start) * 1000,
                source_count=len(sources))
```

## Security Checklist

- [ ] API key stored in secrets manager (not .env in production)
- [ ] HTTPS enabled (use reverse proxy)
- [ ] CORS configured for allowed origins only
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] Vector DB mounted read-only
- [ ] Container runs as non-root user
- [ ] Security scanning in CI/CD

## Troubleshooting

### Issue: "Vector DB not found"
```bash
# Check volume mount
docker inspect rag-api | grep -A 10 Mounts

# Verify DB exists
ls -lh data/chroma_db/
```

### Issue: "Out of memory"
```bash
# Increase container memory
docker run -m 4g ...

# Or in docker-compose.yml
services:
  rag-api:
    mem_limit: 4g
```

### Issue: "Slow cold starts"
- Pre-load embedding model in Dockerfile
- Use readiness probe to delay traffic until ready
- Keep at least 1 instance always running

### Issue: "Session data lost"
- Expected behavior (in-memory storage)
- For persistence: Implement Redis-backed session store

## Cost Estimation

**Compute** (AWS EC2 t3.medium, $0.0416/hour):
- ~$30/month for single instance
- ~$90/month for 3 instances (HA setup)

**Storage**:
- 1 GB EBS volume: ~$0.10/month

**LLM API** (Claude 3 Haiku):
- Input: $0.25 per million tokens
- Output: $1.25 per million tokens
- ~$0.001 per query
- 10,000 queries ≈ $10/month

**Total**: ~$40-100/month depending on scale

## Next Steps

1. Set up monitoring with Prometheus + Grafana
2. Implement Redis for distributed session storage
3. Add rate limiting with Redis
4. Set up log aggregation (ELK/Loki)
5. Add authentication/authorization
6. Implement caching layer for frequent queries
