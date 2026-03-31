# Deployment Workflow Guide

Complete guide for deploying and updating the RAG API in production.

---

## Overview

This project uses a **Git-based deployment workflow** with automated CI/CD:

```
Developer → GitHub → CI/CD (Docker Build) → Docker Hub → Production Server
```

**Key Components:**
- **GitHub Actions**: Automated Docker image builds
- **Docker Hub**: Image registry (public)
- **Server Git Pull**: Direct code updates from GitHub
- **Automated Backups**: Pre-update backups for safety

---

## First-Time Deployment

### Prerequisites

- [ ] VPS running Ubuntu 22.04/24.04 (minimum 2GB RAM, 1 CPU)
- [ ] SSH access to server
- [ ] Anthropic API key
- [ ] Domain name (optional, for SSL)
- [ ] Docker Hub account (for CI/CD)

### Step 1: Prepare Locally

```bash
cd ai-sandbox

# 1. Create environment file
cp .env.example .env
nano .env  # Add your ANTHROPIC_API_KEY

# 2. Index documentation (create vector database)
make ingest
# Output: data/chroma_db/ (~25 MB, 2,388 embeddings)

# 3. Test locally
make api  # Start API on http://localhost:8000
# In another terminal:
make query  # Test query

# 4. Build and test Docker image
make docker-build
docker run -p 8000:8000 --env-file .env \
  -v $(pwd)/data/chroma_db:/app/data/chroma_db \
  rag-api:latest
# Test: curl http://localhost:8000/health
```

### Step 2: Configure CI/CD (One-Time Setup)

```bash
# 1. Create Docker Hub account at https://hub.docker.com
# 2. Generate access token: Account Settings → Security → New Access Token

# 3. Add GitHub secrets (repo Settings → Secrets → Actions):
#    - DOCKERHUB_USERNAME: your Docker Hub username
#    - DOCKERHUB_TOKEN: your access token

# 4. Update workflow with your username
nano .github/workflows/docker-publish.yml
# Change: IMAGE_NAME: ${{ secrets.DOCKERHUB_USERNAME }}/rag-api

# 5. Commit and push (triggers first build)
git add .github/workflows/docker-publish.yml
git commit -m "Configure CI/CD with Docker Hub credentials"
git push origin main

# 6. Verify build: https://github.com/YOUR_USERNAME/ai-sandbox/actions
# Wait for "Docker Build and Publish" to complete (~10-15 min)
```

### Step 3: Deploy to Server

**Option A: Quick Deploy (Recommended)**

```bash
./deploy/quick-deploy.sh
# Follow interactive prompts:
# - Enter server IP: YOUR_SERVER_IP
# - Enter SSH user: root
# - Pull from Docker Hub? Yes
# - Configure domain? (optional)
```

**Option B: Manual Deploy**

```bash
# 1. Set up server
ssh root@YOUR_SERVER_IP
curl -fsSL https://raw.githubusercontent.com/jnzm02/ai-sandbox/main/deploy/server-setup.sh | bash

# 2. Upload vector database (from local machine)
rsync -avz data/chroma_db/ root@YOUR_SERVER_IP:/opt/rag-api/data/chroma_db/

# 3. Configure environment (on server)
ssh root@YOUR_SERVER_IP
cd /opt/rag-api
nano .env  # Add ANTHROPIC_API_KEY

# 4. Initialize Git repository
git init
git remote add origin https://github.com/YOUR_USERNAME/ai-sandbox.git
git fetch origin main
git reset --hard origin/main
chmod +x deploy/*.sh

# 5. Deploy application
./deploy/deploy.sh --pull

# 6. Verify
curl http://localhost:8000/health
```

### Step 4: Configure Nginx + SSL (Optional)

```bash
# On server
ssh root@YOUR_SERVER_IP

# 1. Update domain in Nginx config
nano /etc/nginx/sites-available/rag-api
# Replace 'your-domain.com' with your actual domain

# 2. Enable site
ln -s /etc/nginx/sites-available/rag-api /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# 3. Obtain SSL certificate
certbot --nginx -d your-domain.com

# 4. Verify
curl https://your-domain.com/health
```

---

## Updating Production

### Standard Update Workflow

```
Local Changes → Git Push → CI/CD Build → Server Update
```

**Step 1: Make Changes Locally**

```bash
# Example: Update prompt template
nano src/rag.py

# Test changes
make api
make query

# Commit and push
git add .
git commit -m "Improve prompt template for technical questions"
git push origin main
```

**Step 2: CI/CD Builds Docker Image**

GitHub Actions automatically:
1. Runs tests (`.github/workflows/test.yml`)
2. Builds Docker image (`.github/workflows/docker-publish.yml`)
3. Pushes to Docker Hub as `yourname/rag-api:latest`

Monitor: `https://github.com/YOUR_USERNAME/ai-sandbox/actions`

**Step 3: Update Server**

```bash
# SSH to server
ssh root@YOUR_SERVER_IP
cd /opt/rag-api

# Check for updates
./deploy/update-from-git.sh --check

# Pull and deploy
./deploy/update-from-git.sh
# Script will:
# - Create pre-update backup
# - Pull latest code from GitHub
# - Pull latest Docker image from Docker Hub
# - Restart container
# - Verify health

# Verify update
curl http://localhost:8000/health
docker logs rag-api --tail=50
```

### Update Vector Database

When you add/update documentation:

```bash
# Local machine
python src/ingest.py  # Re-index documentation
ls -lh data/chroma_db/  # Verify new database

# Push to server
./deploy/update-vector-db.sh --host YOUR_SERVER_IP

# Script will:
# - Backup current database on server
# - Stop API container
# - Upload new database (rsync)
# - Restart API
# - Verify health

# Test new content
curl -X POST https://your-domain.com/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Ask about newly indexed content"}'
```

### Rebuild Docker Image on Server

For Dockerfile changes (rare):

```bash
# On server
ssh root@YOUR_SERVER_IP
cd /opt/rag-api

# Pull code and rebuild
./deploy/update-from-git.sh --build
# Takes ~10-15 minutes to build image on server
```

---

## Rollback Procedures

### Rollback Application Code

```bash
# On server
ssh root@YOUR_SERVER_IP
cd /opt/rag-api

# Option 1: Restore from automated backup
ls -lh backups/
./restore-backup.sh rag-api-backup-YYYYMMDD_HHMMSS

# Option 2: Git rollback
git log --oneline -10  # Find previous commit
git reset --hard COMMIT_SHA
./deploy/deploy.sh --pull

# Verify
curl http://localhost:8000/health
```

### Rollback Vector Database

```bash
# On server
ssh root@YOUR_SERVER_IP
cd /opt/rag-api/backups

# List backups
ls -lh

# Restore previous database
tar -xzf rag-api-backup-20260330_162320/chroma_db.tar.gz -C /tmp/
docker stop rag-api
rm -rf data/chroma_db/*
mv /tmp/chroma_db/* data/chroma_db/
docker start rag-api

# Verify
curl http://localhost:8000/health
```

---

## Monitoring & Maintenance

### Daily Checks

```bash
# On server
ssh root@YOUR_SERVER_IP

# Check API health
curl http://localhost:8000/health

# Check container status
docker ps
docker stats rag-api --no-stream

# Check logs
docker logs rag-api --tail=100

# Check backups
ls -lh /opt/rag-api/backups/
```

### Automated Monitoring

**Already configured:**
- **RAG API Health**: Every 5 minutes (auto-restarts if down)
- **CPU Monitoring**: Every 5 minutes (alerts if >80%)
- **Backup Monitoring**: Every 6 hours (alerts if backup >30h old)
- **Backup Creation**: Daily at 2 AM UTC (14-day retention)

**Check monitoring status:**

```bash
# View cron jobs
crontab -l

# Check monitoring logs
tail -f /var/log/rag-api/monitor.log
tail -f /var/log/rag-api/cpu-monitor.log
tail -f /var/log/rag-api/backup-monitor.log
```

### Manual Security Audit

```bash
# On server
/usr/local/bin/security-audit.sh

# Checks:
# - Firewall (UFW)
# - SSH hardening
# - Fail2Ban status
# - Resource usage
# - Docker security
# - Suspicious processes
# - Open ports
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
cat /opt/rag-api/.env | grep ANTHROPIC_API_KEY

# 2. Missing vector database
ls -la /opt/rag-api/data/chroma_db/

# 3. Port conflict
sudo netstat -tulpn | grep 8000

# 4. Resource limits
docker stats rag-api --no-stream
```

### Health Check Failing

```bash
# Check API logs
docker logs rag-api --tail=100

# Check embeddings loaded
docker logs rag-api | grep "embeddings loaded"

# Test directly
docker exec rag-api curl -sf http://localhost:8000/health
```

### Slow Responses

```bash
# Check resource usage
docker stats rag-api --no-stream

# Check Anthropic API status
curl https://status.anthropic.com/

# Check container logs for errors
docker logs rag-api | grep -i error

# Increase memory if needed
# Edit deploy/deploy.sh: --memory='2500m'
./deploy/deploy.sh
```

### CI/CD Build Failing

```bash
# View workflow logs
# Go to: https://github.com/YOUR_USERNAME/ai-sandbox/actions

# Common issues:
# 1. Docker Hub credentials expired
#    → Regenerate token, update GitHub secrets

# 2. Test failures
#    → Fix tests locally, push again

# 3. Docker build errors
#    → Test locally: make docker-build
```

---

## Workflow Examples

### Example 1: Add New Feature

```bash
# === LOCAL ===
cd ai-sandbox

# 1. Create feature branch
git checkout -b feature/streaming-responses

# 2. Implement feature
nano src/api.py

# 3. Test locally
make api
# Test in browser: http://localhost:8000/docs

# 4. Commit and push
git add .
git commit -m "Add streaming response support"
git push origin feature/streaming-responses

# 5. Create PR on GitHub, merge after review
# (CI/CD builds and pushes Docker image automatically)

# === SERVER ===
ssh root@YOUR_SERVER_IP
cd /opt/rag-api

# Pull and deploy update
./deploy/update-from-git.sh

# Verify feature works
curl https://your-domain.com/health
```

### Example 2: Update Documentation

```bash
# === LOCAL ===
cd ai-sandbox

# 1. Update source docs
cp ~/new_docs/* data/fastapi_repo/

# 2. Re-index
python src/ingest.py
# Output: Indexed 3,245 embeddings (was 2,388)

# 3. Push to server
./deploy/update-vector-db.sh --host YOUR_SERVER_IP

# 4. Verify new content
curl -X POST https://your-domain.com/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about the new feature X"}'
```

### Example 3: Emergency Rollback

```bash
# === SERVER ===
ssh root@YOUR_SERVER_IP
cd /opt/rag-api

# 1. Check issue
docker logs rag-api --tail=100
# Error: "AttributeError: module 'langchain' has no attribute 'X'"

# 2. Quick rollback to yesterday's backup
ls -lh backups/
./restore-backup.sh rag-api-backup-20260330_020000

# 3. Verify service restored
curl http://localhost:8000/health

# 4. Fix issue locally, redeploy when ready
```

---

## Cost Estimates

### Infrastructure (Monthly)

- **VPS Hosting**: $10-30/month
  - Hetzner CPX21 (4GB): ~$10
  - DigitalOcean (4GB): ~$24
  - Linode (4GB): ~$24

- **Domain**: $10-15/year (optional)

- **SSL Certificate**: Free (Let's Encrypt)

### API Usage (Variable)

- **Claude 3 Haiku**: ~$0.001/query
  - 1,000 queries/month: ~$1-2
  - 10,000 queries/month: ~$10-20

- **Embeddings**: $0 (local sentence-transformers model)

**Total**: $10-50/month depending on traffic

---

## Production Checklist

Before going live:

- [ ] All tests passing locally
- [ ] Docker image built and tested
- [ ] CI/CD pipeline configured and passing
- [ ] Environment variables secured (chmod 600)
- [ ] Firewall configured (UFW)
- [ ] SSH hardened (key-only authentication)
- [ ] Fail2Ban installed and active
- [ ] Nginx configured with rate limiting
- [ ] SSL certificate obtained (if using domain)
- [ ] Backups automated (daily at 2 AM)
- [ ] Monitoring scripts active (5-min health checks)
- [ ] Server update workflow tested
- [ ] Rollback procedure documented and tested
- [ ] Logs configured and rotating
- [ ] Resource limits appropriate (CPU, memory)
- [ ] API keys not exposed in logs/code
- [ ] Documentation complete

---

## Next Steps: Production Enhancements

For high-traffic production:

1. **Caching Layer**
   - Add Redis for query result caching
   - Cache embeddings in memory
   - Reduce Anthropic API costs

2. **Authentication**
   - Add API key authentication
   - Implement rate limiting per user
   - JWT token support

3. **Observability**
   - Prometheus + Grafana dashboards
   - Distributed tracing (Jaeger)
   - Error tracking (Sentry)

4. **Scalability**
   - Load balancer (Nginx upstream)
   - Multiple API instances
   - Auto-scaling based on CPU/memory

5. **Advanced Monitoring**
   - Uptime monitoring (UptimeRobot, Pingdom)
   - Slack/Discord alerts
   - Log aggregation (ELK stack)

---

## Getting Help

- **Deployment Issues**: See `DEPLOYMENT_VPS.md`
- **Checklist**: See `DEPLOYMENT_CHECKLIST.md`
- **Scripts Reference**: See `deploy/README.md`
- **Security**: See `/root/SECURITY_SUMMARY.md` (on server)
- **Backup/Restore**: See `/root/BACKUP_GUIDE.md` (on server)
- **GitHub Issues**: File bug reports/feature requests

---

**Last Updated**: 2026-03-31
**Deployment Status**: ✅ Production-Ready
**Current Version**: commit 8f968dc
**Production Server**: YOUR_SERVER_IP
