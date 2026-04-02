# RAG API Usage Guide

Complete guide for interacting with your deployed RAG API.

---

## 🌐 API Endpoints Overview

**Base URL**: `http://YOUR_SERVER_IP:8000` (currently internal only)

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/` | GET | API info | None |
| `/health` | GET | Health check | None |
| `/query` | POST | Stateless Q&A | None |
| `/chat` | POST | Conversational (with memory) | None |
| `/sessions` | GET | List active sessions | None |
| `/sessions/{id}` | DELETE | Clear session | None |
| `/docs` | GET | Interactive API docs (Swagger UI) | None |

---

## 📖 API Documentation

### Interactive Docs (Swagger UI)

The easiest way to test your API:

**From server**:
```bash
ssh root@YOUR_SERVER_IP
# Open in browser (if you have GUI): http://localhost:8000/docs
# Or use curl to see endpoints
curl http://localhost:8000/docs
```

**Access from your local machine**:
Since the API is currently only listening on 127.0.0.1:8000, you need SSH port forwarding:

```bash
# Forward server's port 8000 to your local port 8000
ssh -L 8000:localhost:8000 root@YOUR_SERVER_IP

# Now open in your browser:
http://localhost:8000/docs
```

---

## 🔍 API Examples

### 1. Health Check

Check if API is running and see stats:

**Request**:
```bash
curl http://localhost:8000/health
```

**Response**:
```json
{
  "status": "healthy",
  "vector_db_count": 2388,
  "active_sessions": 1,
  "timestamp": "2026-04-02T13:39:50.453231"
}
```

**What it tells you**:
- `status`: API is up
- `vector_db_count`: Number of embeddings loaded
- `active_sessions`: Current chat sessions
- `timestamp`: Server time

---

### 2. Stateless Query (One-off Questions)

Ask a question without conversation history.

**Request**:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I handle CORS in FastAPI?"
  }'
```

**Response**:
```json
{
  "answer": "To handle CORS in FastAPI, you need to use CORSMiddleware...",
  "sources": [
    {
      "path": "tutorial/cors.md",
      "similarity": null
    },
    {
      "path": "advanced/middleware.md",
      "similarity": null
    }
  ],
  "session_id": null,
  "processing_time_ms": 1234.56
}
```

**Use case**: Search-like functionality, one-off questions

---

### 3. Conversational Chat (With Memory)

Multi-turn conversation with context awareness.

**First message**:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user-123",
    "question": "What is dependency injection in FastAPI?"
  }'
```

**Response**:
```json
{
  "answer": "Dependency injection in FastAPI is a system...",
  "sources": [...],
  "session_id": "user-123",
  "processing_time_ms": 1567.89
}
```

**Follow-up question** (uses context):
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user-123",
    "question": "Can you show me an example?"
  }'
```

The API remembers you asked about dependency injection!

**Use case**: Chatbots, conversational interfaces

---

### 4. List Active Sessions

See all ongoing conversations:

**Request**:
```bash
curl http://localhost:8000/sessions
```

**Response**:
```json
[
  {
    "session_id": "user-123",
    "message_count": 5,
    "created_at": "2026-04-02T10:00:00",
    "last_active": "2026-04-02T10:15:00"
  }
]
```

---

### 5. Clear Session

Reset conversation history:

**Request**:
```bash
curl -X DELETE http://localhost:8000/sessions/user-123
```

**Response**:
```json
{
  "message": "Session user-123 cleared"
}
```

---

## 🧪 Testing from Different Locations

### From the Server (SSH)

```bash
# SSH into server
ssh root@YOUR_SERVER_IP

# Health check
curl http://localhost:8000/health

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is FastAPI?"}'
```

### From Your Local Machine (SSH Tunnel)

```bash
# Terminal 1: Create SSH tunnel
ssh -L 8000:localhost:8000 root@YOUR_SERVER_IP
# Keep this terminal open

# Terminal 2: Use the API
curl http://localhost:8000/health

# Or open in browser
open http://localhost:8000/docs  # macOS
xdg-open http://localhost:8000/docs  # Linux
start http://localhost:8000/docs  # Windows
```

### From Public Internet (Requires Configuration)

**Current status**: ❌ Not accessible

**To enable public access**, you need to:

**Option A: Nginx Reverse Proxy** (Recommended)
```bash
# On server
ssh root@YOUR_SERVER_IP

# Configure Nginx to proxy port 80 → 8000
# Already have Nginx installed, just need configuration
```

**Option B: Docker Port Binding**
Change from `127.0.0.1:8000` to `0.0.0.0:8000`
(Less secure without Nginx rate limiting)

---

## 📊 Example Use Cases

### Use Case 1: Simple FAQ Bot

```python
import requests

def ask_fastapi(question):
    response = requests.post(
        "http://localhost:8000/query",
        json={"question": question}
    )
    return response.json()["answer"]

# Example
answer = ask_fastapi("How do I use path parameters?")
print(answer)
```

### Use Case 2: Chat Interface

```python
import requests

class FastAPIAssistant:
    def __init__(self, session_id):
        self.session_id = session_id
        self.base_url = "http://localhost:8000"

    def ask(self, question):
        response = requests.post(
            f"{self.base_url}/chat",
            json={
                "session_id": self.session_id,
                "question": question
            }
        )
        return response.json()["answer"]

    def reset(self):
        requests.delete(f"{self.base_url}/sessions/{self.session_id}")

# Usage
bot = FastAPIAssistant("user-456")
print(bot.ask("What is CORS?"))
print(bot.ask("How do I configure it?"))  # Remembers context!
bot.reset()  # Start fresh
```

### Use Case 3: Health Monitoring

```bash
#!/bin/bash
# health-check.sh

RESPONSE=$(curl -sf http://localhost:8000/health)

if [ $? -eq 0 ]; then
    echo "✅ API is healthy"
    echo $RESPONSE | python3 -m json.tool
else
    echo "❌ API is down!"
    # Send alert, restart service, etc.
fi
```

---

## 🚀 Making Your API Publicly Accessible

### Current Setup
- Port: 127.0.0.1:8000 (internal only)
- Firewall: Ports 22, 80, 443 open
- Nginx: Installed but not configured for API

### Option 1: Configure Nginx Proxy (Recommended)

**Benefits**:
- ✅ Rate limiting (100 req/min)
- ✅ SSL/HTTPS support
- ✅ Better security
- ✅ DDoS protection

**Configuration** (on server):
```bash
ssh root@YOUR_SERVER_IP

# Create Nginx config
cat > /etc/nginx/sites-available/rag-api << 'EOF'
server {
    listen 80;
    server_name YOUR_SERVER_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;  # Don't log health checks
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/rag-api /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# Now accessible at: http://YOUR_SERVER_IP/
```

### Option 2: Direct Port Binding (Quick but less secure)

**On server**, edit docker run command:
```bash
# Change from:
-p 127.0.0.1:8000:8000

# To:
-p 0.0.0.0:8000:8000

# Restart container
docker stop rag-api
./deploy/deploy.sh
```

Now accessible at: `http://YOUR_SERVER_IP:8000/`

---

## 🔒 Security Considerations

### Current Setup (Internal Only)
- ✅ **Secure**: Only accessible from server
- ✅ **No authentication needed**: Not exposed
- ❌ **Limited**: Can't use from outside

### If Making Public
- ⚠️ **Add rate limiting**: Prevent abuse
- ⚠️ **Add authentication**: API keys or OAuth
- ⚠️ **Monitor usage**: Track costs (Anthropic API)
- ⚠️ **Add HTTPS**: Use SSL certificate
- ⚠️ **Set up CORS**: Control which domains can access

---

## 📈 Monitoring Your API

### Already Configured
- ✅ Health checks every 5 minutes (auto-restart if down)
- ✅ CPU monitoring (prevent malware)
- ✅ Backup monitoring

### View Logs
```bash
# SSH to server
ssh root@YOUR_SERVER_IP

# Real-time logs
docker logs -f rag-api

# Last 100 lines
docker logs rag-api --tail=100

# Logs from last hour
docker logs rag-api --since 1h
```

### Check Performance
```bash
# Container stats
docker stats rag-api --no-stream

# API response time
time curl http://localhost:8000/health
```

---

## 🐛 Troubleshooting

### API Not Responding

```bash
# Check if container is running
docker ps | grep rag-api

# Check logs
docker logs rag-api --tail=50

# Restart if needed
docker restart rag-api
```

### Slow Responses

```bash
# Check system resources
docker stats rag-api --no-stream
free -h
df -h

# Check Anthropic API status
# (Your LLM provider might be slow)
```

### "Connection refused" from outside

```bash
# Check what's listening
ss -tlnp | grep 8000

# If shows 127.0.0.1:8000 → only internal access
# If shows 0.0.0.0:8000 → publicly accessible
```

---

## 💡 Next Steps

1. **Test the API** using SSH tunnel: `ssh -L 8000:localhost:8000 root@YOUR_SERVER_IP`
2. **Access Swagger UI**: http://localhost:8000/docs
3. **Try example queries** from this guide
4. **Optional**: Configure Nginx for public access
5. **Optional**: Add authentication if making public

---

**Current Status**: ✅ API Running, Internal Access Only
**To Test Now**: Use SSH tunnel or SSH into server

**Questions?** Check the interactive docs at http://localhost:8000/docs (via SSH tunnel)
