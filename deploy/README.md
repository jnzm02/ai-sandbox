# Deployment Scripts

Production deployment automation for RAG API on VPS.

---

## Quick Start

### First-Time Deployment

From your **local machine**:

```bash
# 1. Prepare locally
make deploy-init          # Initialize deployment files
make ingest              # Create vector database
make docker-build        # Build and test Docker image

# 2. Deploy to server (interactive)
./deploy/quick-deploy.sh
# Enter server IP when prompted
# Script will handle everything automatically
```

### Manual Deployment

If you prefer step-by-step control:

```bash
# 1. Set up fresh VPS
ssh root@YOUR_SERVER_IP
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/ai-sandbox/main/deploy/server-setup.sh | bash

# 2. Upload vector database (from local)
rsync -avz data/chroma_db/ root@YOUR_SERVER_IP:/opt/rag-api/data/chroma_db/

# 3. Configure environment (on server)
ssh root@YOUR_SERVER_IP
cd /opt/rag-api
nano .env  # Add ANTHROPIC_API_KEY

# 4. Deploy application
./deploy/deploy.sh --pull
```

### Updating Deployed Application

After initial deployment, update from Git:

```bash
# On server
ssh root@YOUR_SERVER_IP
cd /opt/rag-api

# Check for updates
./deploy/update-from-git.sh --check

# Pull and deploy updates
./deploy/update-from-git.sh

# Or pull and rebuild (if Dockerfile changed)
./deploy/update-from-git.sh --build
```

---

## Scripts Overview

### update-from-git.sh
**Purpose:** Update production application from GitHub
**Run on:** Server (after initial deployment)
**What it does:**
- Fetches latest code from GitHub
- Creates pre-update backup
- Pulls changes and redeploys
- Verifies health after update

**Usage:**
```bash
# Check for updates only
./deploy/update-from-git.sh --check

# Pull and deploy (uses Docker Hub image)
./deploy/update-from-git.sh

# Pull and rebuild (for Dockerfile changes)
./deploy/update-from-git.sh --build
```

**Prerequisites:**
- Initial deployment completed
- Git repository initialized on server
- Network access to GitHub

**Runtime:** ~2-5 minutes (pull), ~10-15 minutes (build)

---

### server-setup.sh
**Purpose:** One-time server initialization
**Run on:** Fresh Ubuntu 22.04/24.04 VPS
**What it does:**
- Installs Docker, Docker Compose, Nginx, Certbot
- Configures UFW firewall (ports 22, 80, 443)
- Creates application directories
- Sets up logging infrastructure

**Usage:**
```bash
# On server as root
curl -fsSL https://URL/server-setup.sh | bash
# or
./server-setup.sh
```

**Prerequisites:** Ubuntu 22.04/24.04, root access
**Runtime:** ~5-10 minutes
**Idempotent:** Yes (safe to re-run)

---

### deploy.sh
**Purpose:** Deploy or update the RAG API application
**Run on:** Server (after server-setup.sh)
**What it does:**
- Stops existing container (if running)
- Pulls or builds Docker image
- Starts new container with health checks
- Validates deployment
- Cleans up old images

**Usage:**
```bash
# Pull from Docker Hub (recommended)
./deploy.sh --pull

# Build locally on server
./deploy.sh --build

# Use existing local image
./deploy.sh
```

**Prerequisites:**
- `/opt/rag-api/.env` exists with API key
- `/opt/rag-api/data/chroma_db/` exists
- Docker running

**Runtime:** ~2-5 minutes (pull), ~10-15 minutes (build)

---

### monitoring-setup.sh
**Purpose:** Install monitoring and observability stack
**Run on:** Server (after server-setup.sh)
**What it does:**
- Installs Prometheus Node Exporter (system metrics)
- Installs cAdvisor (Docker metrics)
- Creates health check monitoring script
- Configures logrotate for application logs

**Usage:**
```bash
# On server as root
./monitoring-setup.sh
```

**Endpoints after installation:**
- Node Exporter: `http://localhost:9100/metrics`
- cAdvisor: `http://localhost:8080`

**Optional:** Add cron job for health monitoring:
```bash
crontab -e
# Add: */5 * * * * /opt/rag-api/monitor-health.sh
```

---

### backup.sh
**Purpose:** Backup vector database
**Run on:** Server (manual or cron)
**What it does:**
- Creates compressed backup of `/opt/rag-api/data/chroma_db/`
- Stores in `/opt/rag-api/backups/`
- Removes backups older than 7 days
- Optional: Upload to S3/cloud storage

**Usage:**
```bash
# Manual backup
./backup.sh

# Automated daily backup (cron)
sudo crontab -e
# Add: 0 2 * * * /opt/rag-api/backup.sh >> /var/log/rag-api/backup.log 2>&1
```

**Output:** `chroma_db_YYYYMMDD_HHMMSS.tar.gz`

**Restore from backup:**
```bash
cd /opt/rag-api/backups
tar -xzf chroma_db_20260330_020000.tar.gz -C /opt/rag-api/data/
docker restart rag-api
```

---

### update-vector-db.sh
**Purpose:** Update production vector database with new content
**Run on:** Local machine (pushes to server)
**What it does:**
- Creates backup on server
- Stops API container
- Uploads new vector database
- Restarts API
- Validates deployment

**Usage:**
```bash
# From local machine (after running 'make ingest')
./deploy/update-vector-db.sh --host YOUR_SERVER_IP --user root
```

**Prerequisites:**
- New vector DB created locally at `./data/chroma_db/`
- SSH access to server
- rsync installed locally

**Warning:** This replaces the entire production vector database!

---

### quick-deploy.sh
**Purpose:** Single-command deployment for experienced users
**Run on:** Local machine OR server
**What it does:**
- **On local:** Orchestrates full deployment to remote server
- **On server:** Runs server setup and deployment

**Usage:**
```bash
# From local machine (interactive)
./deploy/quick-deploy.sh
# Follow prompts for server IP, domain, etc.

# From server (automated)
curl -fsSL https://URL/quick-deploy.sh | bash
```

**What it automates:**
1. Server setup
2. Vector DB upload
3. Environment configuration
4. Application deployment
5. Nginx + SSL setup (optional)

**Runtime:** ~15-30 minutes (full deployment)

---

## Configuration Files

### nginx.conf
**Purpose:** Nginx reverse proxy configuration
**Location on server:** `/etc/nginx/sites-available/rag-api`

**Features:**
- HTTPS with Let's Encrypt SSL
- Rate limiting (100 req/min per IP)
- Security headers (HSTS, XSS protection)
- Health check endpoint (no rate limit)
- CORS support

**Setup:**
```bash
# Copy to server
sudo cp nginx.conf /etc/nginx/sites-available/rag-api

# Edit domain name
sudo nano /etc/nginx/sites-available/rag-api
# Replace 'your-domain.com' with your actual domain

# Enable site
sudo ln -s /etc/nginx/sites-available/rag-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

---

## Workflow Examples

### Example 1: Fresh Deployment

```bash
# === LOCAL MACHINE ===
cd ai-sandbox
make deploy-init
# Add API key to .env
make ingest
make docker-build

# Push to Docker Hub (optional)
DOCKER_USER=yourname make docker-push

# === DEPLOY ===
./deploy/quick-deploy.sh
# Enter server IP: 192.168.1.100
# Enter domain: api.example.com
# Script completes deployment

# === VERIFY ===
curl https://api.example.com/health
```

### Example 2: Update Application Code

```bash
# === LOCAL MACHINE ===
# Make code changes
git add .
git commit -m "Fix: improve prompt template"
git push

# CI/CD builds and pushes Docker image automatically
# (if .github/workflows/docker-publish.yml is configured)

# === SERVER ===
ssh root@YOUR_SERVER
cd /opt/rag-api
./deploy/deploy.sh --pull

# Verify
curl http://localhost:8000/health
```

### Example 3: Update Vector Database

```bash
# === LOCAL MACHINE ===
# Update source documents in data/fastapi_repo/
python src/ingest.py  # Re-index

# Push to production
./deploy/update-vector-db.sh --host YOUR_SERVER_IP

# Script handles:
# - Backup current DB
# - Upload new DB
# - Restart API
# - Verify health

# === VERIFY ===
curl -X POST https://api.example.com/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Ask about new content"}'
```

### Example 4: Rollback Deployment

```bash
# === SERVER ===
ssh root@YOUR_SERVER
cd /opt/rag-api

# Stop current version
docker stop rag-api && docker rm rag-api

# Pull previous version (if tagged)
docker pull yourname/rag-api:v1.0.0
docker tag yourname/rag-api:v1.0.0 yourname/rag-api:latest

# Or restore from backup DB
cd backups
tar -xzf chroma_db_20260329_020000.tar.gz -C /opt/rag-api/data/

# Redeploy
./deploy/deploy.sh
```

---

## Troubleshooting

### Script fails with "Permission denied"

```bash
# Make scripts executable
chmod +x deploy/*.sh

# Or run with explicit shell
bash deploy/server-setup.sh
```

### "Connection refused" during deployment

```bash
# Check SSH access
ssh -v root@YOUR_SERVER_IP

# Verify SSH key is added
ssh-copy-id root@YOUR_SERVER_IP
```

### Deploy script can't find .env file

```bash
# Create from template
cp .env.production /opt/rag-api/.env
nano /opt/rag-api/.env  # Add API key
chmod 600 /opt/rag-api/.env
```

### Vector DB upload is slow

```bash
# Use compression with rsync
rsync -avz --compress-level=9 data/chroma_db/ root@SERVER:/opt/rag-api/data/chroma_db/

# Or create tarball first
tar -czf chroma_db.tar.gz data/chroma_db/
scp chroma_db.tar.gz root@SERVER:/opt/rag-api/
ssh root@SERVER "cd /opt/rag-api && tar -xzf chroma_db.tar.gz && mv chroma_db/* data/chroma_db/"
```

### Container keeps restarting

```bash
# Check logs
docker logs rag-api

# Common issues:
# 1. Missing .env
ls -la /opt/rag-api/.env

# 2. Missing vector DB
ls -la /opt/rag-api/data/chroma_db/

# 3. Invalid API key
docker exec rag-api env | grep ANTHROPIC_API_KEY

# 4. Port already in use
sudo netstat -tulpn | grep 8000
```

---

## Security Notes

### Secrets Management
- Never commit `.env` files to Git
- Use `chmod 600` for `.env` on server
- Rotate API keys periodically
- Use environment variables, not hardcoded secrets

### Network Security
- Firewall configured by `server-setup.sh`
- Only ports 22, 80, 443 open
- Consider fail2ban for SSH protection
- Use CloudFlare for DDoS protection (optional)

### Container Security
- Containers run as non-root user
- Vector DB mounted read-only
- Resource limits enforced
- Regular image updates via CI/CD

---

## Maintenance

### Weekly Tasks
- Review logs: `docker logs rag-api --since 7d`
- Check disk space: `df -h`
- Verify backups exist: `ls -lh /opt/rag-api/backups/`
- Monitor API costs (Anthropic dashboard)

### Monthly Tasks
- Review and clear old logs
- Check SSL certificate expiry: `certbot certificates`
- Update system packages: `apt update && apt upgrade`
- Review resource usage trends

### Quarterly Tasks
- Test disaster recovery (restore from backup)
- Review and update dependencies
- Audit security settings
- Performance optimization review

---

## Cost Estimates

### VPS Hosting (Monthly)
- Hetzner CPX21 (4GB): €9 (~$10)
- DigitalOcean Droplet (4GB): $24
- Linode 4GB: $24

### API Usage (Variable)
- Claude 3 Haiku: ~$1-2 per 1000 requests
- Embeddings: $0 (local model)

**Total:** $10-30/month depending on traffic

---

## Getting Help

- **Full Guide:** See `DEPLOYMENT_VPS.md`
- **Checklist:** See `DEPLOYMENT_CHECKLIST.md`
- **Issues:** GitHub Issues
- **CI/CD:** See `.github/workflows/`

---

**Last Updated:** 2026-03-30
**Maintainer:** Your Name
**Status:** Production-Ready ✅
