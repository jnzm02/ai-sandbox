# VPS Deployment Guide - RAG API

Complete guide for deploying your RAG API to a VPS (DigitalOcean, Hetzner, Linode, etc.)

---

## Prerequisites

### 1. VPS Requirements

**Minimum Specifications:**
- **OS:** Ubuntu 22.04/24.04 LTS (recommended)
- **RAM:** 4 GB (2 GB minimum, but 4 GB recommended for embedding model)
- **CPU:** 2 vCPUs
- **Storage:** 20 GB SSD (50 GB recommended for logs/backups)
- **Network:** 1 TB transfer/month

**Recommended Providers:**
- **DigitalOcean:** $24/mo (4GB RAM, 2 vCPUs) - Droplet
- **Hetzner:** €9/mo (4GB RAM, 2 vCPUs) - CPX21
- **Linode:** $24/mo (4GB RAM, 2 vCPUs) - Linode 4GB

### 2. Domain & DNS

- Domain name (e.g., `api.yourdomain.com`)
- DNS A record pointing to your VPS IP

### 3. Local Prerequisites

- Docker Hub account (free tier is fine)
- Your `ANTHROPIC_API_KEY`
- Pre-indexed vector database (`data/chroma_db/` from running `ingest.py` locally)

---

## Deployment Steps

### Step 1: Provision VPS

1. **Create VPS instance** on your provider of choice
2. **SSH into server:**
   ```bash
   ssh root@YOUR_SERVER_IP
   ```

3. **Update root password** (if not done during provisioning):
   ```bash
   passwd
   ```

4. **(Optional) Create non-root user:**
   ```bash
   adduser deploy
   usermod -aG sudo deploy
   su - deploy
   ```

---

### Step 2: Initial Server Setup

Run the automated server setup script:

```bash
# Download and run server setup
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/ai-sandbox/main/deploy/server-setup.sh -o server-setup.sh
chmod +x server-setup.sh
sudo ./server-setup.sh
```

**This script installs:**
- Docker & Docker Compose
- Nginx (web server)
- Certbot (SSL certificates)
- UFW (firewall)
- Basic monitoring tools

**Manual alternative** (if you prefer step-by-step):
See `deploy/server-setup.sh` for individual commands.

---

### Step 3: Upload Vector Database

Your vector database was created locally by running `python src/ingest.py`. Now upload it to the server:

**Option A: Using SCP (from local machine):**
```bash
# From your local ai-sandbox directory
cd /Users/nizamijussupov/Desktop/AI/Sandbox/ai-sandbox
scp -r data/chroma_db root@YOUR_SERVER_IP:/opt/rag-api/data/
```

**Option B: Using rsync (faster, resumable):**
```bash
rsync -avz --progress data/chroma_db/ root@YOUR_SERVER_IP:/opt/rag-api/data/chroma_db/
```

**Verify upload:**
```bash
ssh root@YOUR_SERVER_IP
ls -lh /opt/rag-api/data/chroma_db/
# Should show ~24 MB of data
```

---

### Step 4: Configure Environment Variables

**On the server**, create `.env` file with your API key:

```bash
ssh root@YOUR_SERVER_IP
cd /opt/rag-api

# Create .env from template
cat > .env <<EOF
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
EOF

# Secure the file
chmod 600 .env
```

**Verify:**
```bash
cat .env
# Should show your API key (keep this secret!)
```

---

### Step 5: Build & Push Docker Image

**Option A: Build locally and push to Docker Hub** (recommended for faster deployment)

On your **local machine**:

```bash
cd /Users/nizamijussupov/Desktop/AI/Sandbox/ai-sandbox

# Login to Docker Hub
docker login

# Build image
docker build -t YOUR_DOCKERHUB_USERNAME/rag-api:latest .

# Push to registry
docker push YOUR_DOCKERHUB_USERNAME/rag-api:latest
```

**Option B: Build on server** (slower, uses server resources)

On the **server**:

```bash
cd /opt/rag-api
git clone https://github.com/YOUR_USERNAME/ai-sandbox.git .
docker build -t rag-api:latest .
```

---

### Step 6: Deploy Application

**On the server**, run the deployment script:

```bash
cd /opt/rag-api

# Download deployment script
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/ai-sandbox/main/deploy/deploy.sh -o deploy.sh
chmod +x deploy.sh

# Deploy (pulls from Docker Hub)
./deploy.sh --pull
```

**If you built locally on server:**
```bash
./deploy.sh --build
```

**Verify deployment:**
```bash
# Check container status
docker ps

# Check logs
docker logs rag-api

# Test health endpoint
curl http://localhost:8000/health
# Should return: {"status":"healthy"}

# Test query endpoint
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is FastAPI?"}'
```

---

### Step 7: Configure Nginx Reverse Proxy

**On the server:**

```bash
# Download Nginx config
sudo curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/ai-sandbox/main/deploy/nginx.conf \
  -o /etc/nginx/sites-available/rag-api

# Edit the config with your domain
sudo nano /etc/nginx/sites-available/rag-api
# Replace 'your-domain.com' with your actual domain (e.g., api.example.com)

# Enable site
sudo ln -s /etc/nginx/sites-available/rag-api /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

### Step 8: Obtain SSL Certificate

**Using Certbot (Let's Encrypt):**

```bash
# Obtain certificate (replace with your domain)
sudo certbot --nginx -d api.yourdomain.com

# Follow prompts:
# - Enter email address
# - Agree to Terms of Service
# - Choose redirect HTTP to HTTPS (option 2)
```

**Verify SSL:**
```bash
# Check certificate
sudo certbot certificates

# Test auto-renewal
sudo certbot renew --dry-run
```

**Access your API:**
```
https://api.yourdomain.com/health
```

---

### Step 9: Set Up Monitoring

**Run monitoring setup:**

```bash
cd /opt/rag-api
sudo curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/ai-sandbox/main/deploy/monitoring-setup.sh \
  -o monitoring-setup.sh
chmod +x monitoring-setup.sh
sudo ./monitoring-setup.sh
```

**Add health check to crontab:**

```bash
crontab -e
# Add this line to check every 5 minutes:
*/5 * * * * /opt/rag-api/monitor-health.sh
```

**Optional: Install Uptime Kuma (visual dashboard):**

```bash
docker run -d \
  --name uptime-kuma \
  --restart=unless-stopped \
  -p 3001:3001 \
  -v uptime-kuma:/app/data \
  louislam/uptime-kuma:1

# Access at: http://YOUR_SERVER_IP:3001
# Add monitor for https://api.yourdomain.com/health
```

---

### Step 10: Set Up Automated Backups

**Configure backup script:**

```bash
cd /opt/rag-api
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/ai-sandbox/main/deploy/backup.sh \
  -o backup.sh
chmod +x backup.sh

# Test backup
sudo ./backup.sh
```

**Add to crontab** (runs daily at 2 AM):

```bash
sudo crontab -e
# Add:
0 2 * * * /opt/rag-api/backup.sh >> /var/log/rag-api/backup.log 2>&1
```

**Verify backups:**
```bash
ls -lh /opt/rag-api/backups/
```

---

## Post-Deployment Tasks

### 1. Test All Endpoints

```bash
# Health check
curl https://api.yourdomain.com/health

# Query endpoint (stateless)
curl -X POST https://api.yourdomain.com/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is dependency injection in FastAPI?"}'

# Chat endpoint (stateful)
curl -X POST https://api.yourdomain.com/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain path parameters", "session_id": "test-session-1"}'

# Follow-up question
curl -X POST https://api.yourdomain.com/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Can you give me an example?", "session_id": "test-session-1"}'
```

### 2. Monitor Performance

```bash
# Container stats
docker stats rag-api

# Logs (real-time)
docker logs -f rag-api

# Nginx access logs
sudo tail -f /var/log/nginx/rag-api-access.log

# Health monitor logs
tail -f /var/log/rag-api/health-monitor.log
```

### 3. Set Up Alerts (Optional)

**Webhook alerts for downtime:**

Edit `/opt/rag-api/monitor-health.sh` and uncomment the webhook section:

```bash
# Send alert to Slack/Discord/Telegram
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"🚨 RAG API is down on $(hostname)!\"}"
```

---

## CI/CD: Automated Deployments

### Set Up Docker Hub Credentials in GitHub

1. **Create Docker Hub access token:**
   - Go to https://hub.docker.com/settings/security
   - Click "New Access Token"
   - Name: `github-actions`
   - Copy token

2. **Add secrets to GitHub repository:**
   - Go to your repo → Settings → Secrets and variables → Actions
   - Add secrets:
     - `DOCKERHUB_USERNAME`: your Docker Hub username
     - `DOCKERHUB_TOKEN`: the access token you just created

### Automated Workflow

Now, every push to `main` will:
1. Build Docker image
2. Push to Docker Hub as `latest`
3. Tag with commit SHA

**To deploy updates to your server:**

```bash
ssh root@YOUR_SERVER_IP
cd /opt/rag-api
./deploy.sh --pull
```

**Or automate with webhook** (advanced - requires additional setup).

---

## Updating the Application

### Update from Docker Hub (recommended)

```bash
ssh root@YOUR_SERVER_IP
cd /opt/rag-api
./deploy.sh --pull
```

### Update from Git (if building on server)

```bash
ssh root@YOUR_SERVER_IP
cd /opt/rag-api
git pull origin main
./deploy.sh --build
```

### Rollback to Previous Version

```bash
# If you tagged versions (e.g., v1.0.0)
docker pull YOUR_DOCKERHUB_USERNAME/rag-api:v1.0.0
docker tag YOUR_DOCKERHUB_USERNAME/rag-api:v1.0.0 YOUR_DOCKERHUB_USERNAME/rag-api:latest
./deploy.sh
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs rag-api

# Common issues:
# 1. Missing .env file
ls -la /opt/rag-api/.env

# 2. Missing vector database
ls -la /opt/rag-api/data/chroma_db/

# 3. Port already in use
sudo netstat -tulpn | grep 8000

# 4. Invalid API key
docker exec rag-api env | grep ANTHROPIC_API_KEY
```

### High Memory Usage

```bash
# Check memory
free -h
docker stats rag-api

# Solution: Increase VPS RAM or add swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Slow Responses

```bash
# Check if embedding model is cached
docker exec rag-api ls -lh /root/.cache/huggingface/

# Check Anthropic API latency
time curl -X POST https://api.yourdomain.com/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'
```

### SSL Certificate Issues

```bash
# Check certificate expiry
sudo certbot certificates

# Renew manually
sudo certbot renew

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

---

## Cost Estimate

### VPS Hosting (Monthly)

| Provider | Plan | RAM | Price |
|----------|------|-----|-------|
| Hetzner | CPX21 | 4 GB | €9 (~$10) |
| DigitalOcean | Droplet | 4 GB | $24 |
| Linode | Linode 4GB | 4 GB | $24 |

### API Costs (Per 1000 requests)

- **Claude 3 Haiku:** ~$1-2 (depends on context size)
- **Embeddings:** $0 (running locally with sentence-transformers)

**Total estimated monthly cost:** $10-30 (mostly VPS hosting)

---

## Security Checklist

- [x] Firewall configured (UFW)
- [x] SSL/TLS enabled (Let's Encrypt)
- [x] API key stored securely (not in git)
- [x] Rate limiting enabled (Nginx)
- [x] Non-root container user (Dockerfile)
- [x] Read-only vector database mount
- [ ] Add API authentication (optional, for future)
- [ ] Add request logging/audit trail (optional)
- [ ] Add DDoS protection (CloudFlare, optional)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│           Internet (HTTPS/443)              │
└────────────────┬────────────────────────────┘
                 │
         ┌───────▼──────────┐
         │   Nginx          │
         │   - SSL/TLS      │
         │   - Rate Limit   │
         │   - Reverse Proxy│
         └───────┬──────────┘
                 │
         ┌───────▼──────────┐
         │  rag-api:8000    │  ← Docker Container
         │  (FastAPI)       │
         │                  │
         │  Components:     │
         │  - RAGService    │
         │  - Embeddings    │
         │  - ChromaDB      │
         │  - Claude API    │
         └───────┬──────────┘
                 │
         ┌───────▼──────────┐
         │  Vector DB       │  ← Persistent Volume
         │  /opt/rag-api    │
         │  /data/chroma_db │
         │  (read-only)     │
         └──────────────────┘

┌──────────────────────────────────────────────┐
│          Monitoring Stack (Optional)         │
├──────────────────────────────────────────────┤
│  - Node Exporter (system metrics)            │
│  - cAdvisor (Docker metrics)                 │
│  - Uptime Kuma (visual dashboard)            │
│  - Health monitor (cron job)                 │
└──────────────────────────────────────────────┘
```

---

## Quick Reference Commands

```bash
# Start/Stop/Restart
docker start rag-api
docker stop rag-api
docker restart rag-api

# View logs
docker logs rag-api
docker logs -f rag-api --tail=100

# Container shell access
docker exec -it rag-api /bin/bash

# Update application
cd /opt/rag-api && ./deploy.sh --pull

# Nginx commands
sudo nginx -t              # Test config
sudo systemctl reload nginx
sudo systemctl status nginx

# SSL renewal
sudo certbot renew

# Backup manually
sudo /opt/rag-api/backup.sh

# Check disk space
df -h
du -sh /opt/rag-api/data/

# Monitor resources
htop
docker stats
```

---

## Next Steps: Production Hardening

For high-traffic production use, consider:

1. **Add Redis for session storage:**
   - Replace in-memory sessions with Redis
   - Enables horizontal scaling

2. **Implement API authentication:**
   - JWT tokens or API keys
   - Rate limiting per user

3. **Add comprehensive monitoring:**
   - Prometheus + Grafana
   - Structured logging (ELK stack)
   - APM (Application Performance Monitoring)

4. **Load balancing:**
   - Multiple API instances
   - HAProxy or Nginx load balancer
   - Auto-scaling based on CPU/memory

5. **Database replication:**
   - Read replicas for vector DB
   - Multi-region deployment

6. **CDN integration:**
   - CloudFlare for DDoS protection
   - Edge caching for static responses

---

## Support & Resources

- **Project Repo:** https://github.com/YOUR_USERNAME/ai-sandbox
- **Issues:** https://github.com/YOUR_USERNAME/ai-sandbox/issues
- **LangChain Docs:** https://docs.langchain.com
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Docker Docs:** https://docs.docker.com

---

**Deployment prepared by:** Claude Code (AI Systems Engineer)
**Date:** 2026-03-30
**Status:** Production-Ready ✅