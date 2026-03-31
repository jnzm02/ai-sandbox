# Production Deployment Checklist

Complete checklist for deploying RAG API to production VPS.

---

## Pre-Deployment (Local Setup)

### 1. Code & Dependencies
- [ ] All code committed to Git
- [ ] GitHub repository created and pushed
- [ ] CI/CD pipeline passing (`.github/workflows/test.yml`)
- [ ] Requirements frozen and tested

### 2. Data Preparation
- [ ] Vector database indexed locally (`make ingest`)
- [ ] Verify vector DB size (~24 MB expected)
- [ ] Test queries locally work (`make query`)
- [ ] Backup vector DB (`make backup`)

### 3. Environment Configuration
- [ ] `.env` file created from `.env.example`
- [ ] `ANTHROPIC_API_KEY` added and tested
- [ ] API key has sufficient credits
- [ ] `.env` confirmed in `.gitignore`

### 4. Docker Registry
- [ ] Docker Hub account created (or other registry)
- [ ] Logged in: `docker login`
- [ ] Updated `docker-publish.yml` with your username
- [ ] Added GitHub secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`

### 5. Domain & DNS
- [ ] Domain purchased (optional but recommended)
- [ ] DNS A record created pointing to VPS IP
- [ ] DNS propagated (use `dig` or `nslookup` to verify)

---

## VPS Provisioning

### 1. Server Selection
- [ ] VPS provider chosen (Hetzner/DigitalOcean/Linode)
- [ ] Instance created (4GB RAM minimum recommended)
- [ ] Ubuntu 22.04/24.04 LTS selected
- [ ] SSH access configured
- [ ] Static IP assigned

### 2. Initial Access
- [ ] SSH key added to VPS
- [ ] Able to SSH: `ssh root@YOUR_SERVER_IP`
- [ ] Root password changed (if applicable)
- [ ] (Optional) Non-root sudo user created

---

## Server Setup

### 1. Base System Configuration
Run: `./deploy/server-setup.sh` or manually:

- [ ] System updated: `apt update && apt upgrade -y`
- [ ] Docker installed and running
- [ ] Docker Compose installed
- [ ] Nginx installed
- [ ] Certbot installed
- [ ] UFW firewall configured (ports 22, 80, 443 open)
- [ ] Application directory created: `/opt/rag-api/`

### 2. File Upload
- [ ] Vector database uploaded to `/opt/rag-api/data/chroma_db/`
- [ ] `.env` file uploaded to `/opt/rag-api/.env`
- [ ] `.env` permissions secured: `chmod 600 /opt/rag-api/.env`
- [ ] Deployment scripts uploaded to `/opt/rag-api/deploy/`
- [ ] Scripts made executable: `chmod +x deploy/*.sh`

### 3. Verify Prerequisites on Server
```bash
ssh root@YOUR_SERVER_IP
ls -lh /opt/rag-api/data/chroma_db/  # Should show ~24 MB
cat /opt/rag-api/.env | grep ANTHROPIC_API_KEY  # Should show key
docker --version  # Should show Docker version
nginx -v  # Should show Nginx version
```

---

## Application Deployment

### 1. Docker Image
Choose one:

**Option A: Pull from Docker Hub** (recommended)
- [ ] Image built and pushed from local or CI/CD
- [ ] Run: `./deploy/deploy.sh --pull`

**Option B: Build on server**
- [ ] Source code uploaded to `/opt/rag-api/`
- [ ] Run: `./deploy/deploy.sh --build`

### 2. Container Verification
- [ ] Container running: `docker ps | grep rag-api`
- [ ] Health check passing: `curl http://localhost:8000/health`
- [ ] Test query works locally on server
- [ ] Logs show no errors: `docker logs rag-api`

### 3. Test Endpoints
```bash
# Health
curl http://localhost:8000/health

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is FastAPI?"}'

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain routing", "session_id": "test-1"}'
```

---

## Nginx & SSL Configuration

### 1. Nginx Setup
- [ ] Nginx config downloaded to `/etc/nginx/sites-available/rag-api`
- [ ] Config edited with your domain name
- [ ] Symlink created: `ln -s /etc/nginx/sites-available/rag-api /etc/nginx/sites-enabled/`
- [ ] Config tested: `nginx -t`
- [ ] Nginx reloaded: `systemctl reload nginx`

### 2. SSL Certificate
- [ ] Certbot run: `certbot --nginx -d your-domain.com`
- [ ] Email provided for expiry notifications
- [ ] HTTPS redirect enabled
- [ ] Certificate obtained successfully
- [ ] Auto-renewal tested: `certbot renew --dry-run`

### 3. Public Access Verification
- [ ] HTTPS working: `https://your-domain.com/health`
- [ ] HTTP redirects to HTTPS
- [ ] API docs accessible: `https://your-domain.com/docs`
- [ ] SSL certificate valid (check browser)
- [ ] Rate limiting working (test 100+ requests)

---

## Monitoring & Logging

### 1. Monitoring Setup
Run: `./deploy/monitoring-setup.sh`

- [ ] Node Exporter installed (port 9100)
- [ ] cAdvisor installed (port 8080)
- [ ] Health monitor script created
- [ ] Health monitor added to crontab: `*/5 * * * * /opt/rag-api/monitor-health.sh`
- [ ] Logrotate configured for `/var/log/rag-api/`

### 2. (Optional) Uptime Kuma Dashboard
- [ ] Uptime Kuma container running
- [ ] Dashboard accessible: `http://YOUR_SERVER_IP:3001`
- [ ] Monitor added for API health endpoint
- [ ] Notifications configured (email/Slack/Discord)

### 3. Log Verification
- [ ] Application logs viewable: `docker logs rag-api`
- [ ] Nginx access logs: `/var/log/nginx/rag-api-access.log`
- [ ] Nginx error logs: `/var/log/nginx/rag-api-error.log`
- [ ] Health monitor logs: `/var/log/rag-api/health-monitor.log`

---

## Backup & Recovery

### 1. Backup Configuration
- [ ] Backup script tested: `./deploy/backup.sh`
- [ ] Backup directory created: `/opt/rag-api/backups/`
- [ ] Cron job added: `0 2 * * * /opt/rag-api/backup.sh`
- [ ] Retention policy configured (7 days default)

### 2. (Optional) Off-site Backups
- [ ] S3 bucket created or cloud storage configured
- [ ] Backup script updated with upload commands
- [ ] Test backup upload works
- [ ] Backup restore tested

### 3. Disaster Recovery Plan
- [ ] Document recovery steps
- [ ] Test restore from backup
- [ ] Verify restored DB works with API

---

## Security Hardening

### 1. Firewall
- [ ] UFW enabled and configured
- [ ] Only necessary ports open (22, 80, 443)
- [ ] SSH port changed (optional but recommended)
- [ ] Fail2ban installed for SSH protection (optional)

### 2. Secrets Management
- [ ] `.env` file has `chmod 600` permissions
- [ ] API key not in logs or error messages
- [ ] No secrets committed to Git repository

### 3. Container Security
- [ ] Container runs as non-root user (verified in Dockerfile)
- [ ] Vector DB mounted read-only
- [ ] Resource limits set (memory: 2GB, CPU: 1.5)
- [ ] Health checks configured

### 4. (Optional) Additional Security
- [ ] CloudFlare DDoS protection configured
- [ ] API authentication added (if required)
- [ ] Request rate limiting per IP/user
- [ ] Security headers verified (check Nginx config)

---

## Performance Testing

### 1. Load Testing
- [ ] Test single request latency
- [ ] Test concurrent requests (10, 50, 100)
- [ ] Verify response times acceptable (<2s for queries)
- [ ] Monitor resource usage during load

### 2. Cold Start Testing
- [ ] Restart container: `docker restart rag-api`
- [ ] Measure startup time (~30-60 seconds expected)
- [ ] Verify health check passes after startup
- [ ] Test first query after restart

### 3. Memory & CPU Monitoring
- [ ] Monitor container stats: `docker stats rag-api`
- [ ] Verify memory stays under limit (2GB)
- [ ] Check for memory leaks (monitor over 24h)
- [ ] CPU usage reasonable (<50% average)

---

## Documentation & Handoff

### 1. Internal Documentation
- [ ] Server IP and credentials documented (secure location)
- [ ] Domain registrar details saved
- [ ] API key storage location documented
- [ ] Deployment runbook created

### 2. User Documentation
- [ ] API endpoints documented
- [ ] Example requests/responses provided
- [ ] Rate limits communicated
- [ ] Support contact provided

### 3. Team Handoff
- [ ] Access credentials shared with team
- [ ] Deployment process demonstrated
- [ ] Monitoring dashboards shared
- [ ] On-call rotation established (if applicable)

---

## Post-Deployment Verification

### 1. Smoke Tests (24 hours after deployment)
- [ ] API still responding
- [ ] No error spikes in logs
- [ ] Memory/CPU stable
- [ ] Backup ran successfully
- [ ] SSL certificate valid
- [ ] Monitoring alerts working

### 2. Week 1 Checks
- [ ] Review logs for errors
- [ ] Check API usage metrics
- [ ] Verify backup schedule working
- [ ] Monitor costs (VPS + API usage)
- [ ] Review and adjust resource limits if needed

### 3. Continuous Monitoring
- [ ] Set up weekly log reviews
- [ ] Monitor API costs (Anthropic usage)
- [ ] Track response time trends
- [ ] Plan for scaling if needed

---

## Rollback Plan

In case of issues:

### Quick Rollback Steps
1. **Stop current container:**
   ```bash
   docker stop rag-api && docker rm rag-api
   ```

2. **Deploy previous version:**
   ```bash
   docker pull YOUR_USERNAME/rag-api:previous-tag
   docker tag YOUR_USERNAME/rag-api:previous-tag YOUR_USERNAME/rag-api:latest
   ./deploy/deploy.sh
   ```

3. **Restore vector DB from backup:**
   ```bash
   cd /opt/rag-api/backups
   tar -xzf chroma_db_YYYYMMDD_HHMMSS.tar.gz -C /opt/rag-api/data/
   ```

4. **Restart and verify:**
   ```bash
   ./deploy/deploy.sh
   curl http://localhost:8000/health
   ```

---

## Common Issues & Solutions

### Container won't start
- Check `.env` exists: `ls -la /opt/rag-api/.env`
- Check vector DB exists: `ls -la /opt/rag-api/data/chroma_db/`
- View logs: `docker logs rag-api`

### High memory usage
- Check current usage: `docker stats rag-api`
- Add swap if needed (see DEPLOYMENT_VPS.md)
- Consider upgrading VPS plan

### SSL certificate issues
- Check expiry: `certbot certificates`
- Renew manually: `certbot renew`
- Check Nginx logs: `tail -f /var/log/nginx/error.log`

### Slow responses
- Check Anthropic API status
- Monitor network latency
- Review embedding model loading time
- Consider caching layer (Redis)

---

## Next Steps: Production Hardening

For high-traffic production:
- [ ] Add Redis for session storage
- [ ] Implement API authentication (JWT)
- [ ] Set up Prometheus + Grafana
- [ ] Add distributed tracing (Jaeger)
- [ ] Configure load balancer for multi-instance
- [ ] Set up auto-scaling
- [ ] Add response caching
- [ ] Implement circuit breaker pattern

---

## Sign-off

### Deployment Team
- **Deployed by:** ___________________
- **Date:** ___________________
- **Version:** ___________________

### Verification
- **QA Verified:** [ ] Yes [ ] No
- **Security Review:** [ ] Yes [ ] No
- **Performance Acceptable:** [ ] Yes [ ] No

### Approval
- **Tech Lead:** ___________________ Date: ___________
- **Operations:** ___________________ Date: ___________

---

**Deployment Status:** ⏳ In Progress | ✅ Complete | ❌ Issues

**Last Updated:** 2026-03-30