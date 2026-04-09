# DNS Setup Guide - Squarespace to VPS

Complete guide for pointing your Squarespace domain to your VPS server.

---

## Prerequisites

- ✅ Domain purchased from Squarespace
- ✅ VPS server running (your server IP)
- ✅ Access to Squarespace account

---

## Step 1: Get Your Server IP Address

You need to know your server's IP address. You already have it in `.server-config`, but here's how to verify:

```bash
# From local machine
cat .server-config | grep SERVER_IP

# Or SSH to server and check
ssh root@YOUR_SERVER_IP 'curl -s ifconfig.me'
```

**Your server IP**: Write it down, you'll need it in Step 2.

---

## Step 2: Configure DNS at Squarespace

### 2.1 Log into Squarespace Domains

1. Go to: **https://domains.squarespace.com**
2. Sign in with your Squarespace account
3. You should see your domain listed

### 2.2 Access DNS Settings

1. Click on **your domain name**
2. Look for **"DNS Settings"** or **"Advanced DNS"** tab
3. Click on it

### 2.3 Add A Record for Subdomain (Recommended)

**For API subdomain** (e.g., `api.yourdomain.com`):

```
Click "Add Record" or "Add Custom Record"

Record Type: A
Host: api
Points to: YOUR_SERVER_IP (e.g., 206.81.22.71)
TTL: 3600 (default is fine)

Click "Save" or "Add"
```

**Example**:
```
Type: A
Host: api
Data: 206.81.22.71
TTL: 3600
```

This creates: `api.yourdomain.com` → Your server

### 2.4 Alternative: Root Domain

**If you want to use the root domain** (e.g., `yourdomain.com`):

```
Record Type: A
Host: @ (or leave blank, depending on Squarespace interface)
Points to: YOUR_SERVER_IP
TTL: 3600
```

**Note**: If you have a website on Squarespace, DON'T do this as it will override your website!

### 2.5 Optional: Add www Subdomain

If you want `www.yourdomain.com` to also work:

```
Record Type: CNAME
Host: www
Points to: yourdomain.com
TTL: 3600
```

---

## Step 3: Verify DNS Settings in Squarespace

Before saving, your DNS records should look like this:

**Example for api.example.com**:
```
Type    Host    Data                TTL
────────────────────────────────────────
A       api     206.81.22.71       3600
```

**Click "Save" or "Apply Changes"**

---

## Step 4: Wait for DNS Propagation

DNS changes take time to propagate across the internet:
- **Minimum**: 5-10 minutes
- **Average**: 30-60 minutes
- **Maximum**: 24-48 hours (rare with Squarespace)

### 4.1 Check DNS Propagation

**Method 1: Command Line** (from your computer)
```bash
# Replace with your actual domain
dig api.yourdomain.com

# Should show your server IP in the ANSWER section
# Look for: api.yourdomain.com. 3600 IN A YOUR_SERVER_IP
```

**Method 2: Online Tool**
```
Go to: https://dnschecker.org
Enter: api.yourdomain.com
Check if it shows your server IP across different locations
```

**Method 3: Simple ping**
```bash
ping api.yourdomain.com

# Should show your server IP
```

### 4.2 What Success Looks Like

```bash
$ dig api.yourdomain.com

;; ANSWER SECTION:
api.yourdomain.com.  3600  IN  A  206.81.22.71
```

The IP should match your server!

---

## Step 5: Configure Server (After DNS Propagates)

Once DNS is working, you need to configure your server to respond to the domain.

### 5.1 Configure Nginx for Your Domain

SSH to your server:
```bash
ssh root@YOUR_SERVER_IP
```

Create Nginx configuration:
```bash
# Replace 'yourdomain.com' with your actual domain
DOMAIN="api.yourdomain.com"

cat > /etc/nginx/sites-available/rag-api << EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=100r/m;
    limit_req zone=api_limit burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Health check (no rate limit)
    location /health {
        limit_req off;
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF
```

Enable the site:
```bash
ln -s /etc/nginx/sites-available/rag-api /etc/nginx/sites-enabled/

# Test configuration
nginx -t

# If OK, reload
systemctl reload nginx
```

### 5.2 Test HTTP Access

```bash
# From your computer
curl http://api.yourdomain.com/health

# Should return your API health check
```

---

## Step 6: Add SSL Certificate (HTTPS)

Once HTTP is working, add free SSL certificate with Let's Encrypt:

```bash
# On server
ssh root@YOUR_SERVER_IP

# Install certbot if not already installed
apt install -y certbot python3-certbot-nginx

# Get certificate (replace with your domain)
certbot --nginx -d api.yourdomain.com

# Follow prompts:
# - Enter email address
# - Agree to terms
# - Choose whether to redirect HTTP to HTTPS (recommend: Yes)
```

**Certbot will automatically**:
- Obtain SSL certificate
- Configure Nginx for HTTPS
- Set up auto-renewal

### 6.1 Test HTTPS

```bash
# From your computer
curl https://api.yourdomain.com/health

# Should work with HTTPS!
```

### 6.2 Verify Auto-Renewal

```bash
# On server
certbot renew --dry-run

# Should show: Congratulations, all simulated renewals succeeded
```

---

## Step 7: Test Your API

Now your API is accessible via HTTPS!

### From Browser
```
https://api.yourdomain.com/docs
```

### From Command Line
```bash
# Health check
curl https://api.yourdomain.com/health

# Query
curl -X POST https://api.yourdomain.com/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is FastAPI?"}'
```

---

## Troubleshooting

### DNS Not Propagating

**Symptoms**: `dig` doesn't show your IP
**Solutions**:
1. Wait longer (up to 24 hours)
2. Clear DNS cache: `sudo dscacheutil -flushcache` (macOS)
3. Try different DNS server: `dig @8.8.8.8 api.yourdomain.com`
4. Check Squarespace DNS settings are saved

### Nginx "Welcome to nginx" Page

**Symptoms**: See default Nginx page instead of API
**Solutions**:
1. Check Nginx config: `nginx -t`
2. Verify site is enabled: `ls -la /etc/nginx/sites-enabled/`
3. Check server_name matches domain: `grep server_name /etc/nginx/sites-available/rag-api`
4. Reload Nginx: `systemctl reload nginx`

### Certbot Fails

**Symptoms**: Can't obtain SSL certificate
**Solutions**:
1. Ensure HTTP (port 80) works first
2. Check firewall: `ufw status`
3. Verify domain points to server: `dig api.yourdomain.com`
4. Check Nginx is running: `systemctl status nginx`

### "Connection Refused"

**Symptoms**: Can't connect to domain
**Solutions**:
1. Check if RAG API is running: `docker ps | grep rag-api`
2. Check Nginx is running: `systemctl status nginx`
3. Check firewall: `ufw status` (port 80 and 443 should be open)
4. Test locally on server: `curl http://localhost:8000/health`

---

## Common Squarespace DNS Gotchas

### 1. Squarespace Website Conflict

If you're using Squarespace for your website:
- **DON'T** point root domain (@) to your VPS
- **DO** use subdomain (api.yourdomain.com)

### 2. DNS Record Types

Squarespace supports:
- **A Record**: For pointing to IP address (use this)
- **CNAME**: For pointing to another domain
- **TXT**: For verification (not needed for basic setup)

### 3. Propagation Time

Squarespace DNS is usually fast (30-60 min) but can take longer:
- Check multiple DNS servers
- Use https://dnschecker.org to see global propagation

---

## Quick Reference

### Squarespace DNS Settings

```
For api.yourdomain.com:
  Type: A
  Host: api
  Data: YOUR_SERVER_IP
  TTL: 3600
```

### Check DNS
```bash
dig api.yourdomain.com
# or
nslookup api.yourdomain.com
```

### Server Configuration Commands
```bash
# Enable Nginx site
ln -s /etc/nginx/sites-available/rag-api /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# Get SSL certificate
certbot --nginx -d api.yourdomain.com
```

---

## Summary Checklist

- [ ] Get server IP address
- [ ] Log into Squarespace Domains
- [ ] Add A Record (api → YOUR_SERVER_IP)
- [ ] Save DNS settings
- [ ] Wait for DNS propagation (check with `dig`)
- [ ] SSH to server
- [ ] Configure Nginx with your domain
- [ ] Test HTTP access
- [ ] Run Certbot for SSL
- [ ] Test HTTPS access
- [ ] Update documentation with your domain

---

## What Happens After Setup

Once complete:
- ✅ API accessible at: `https://api.yourdomain.com`
- ✅ Interactive docs: `https://api.yourdomain.com/docs`
- ✅ Automatic HTTPS (SSL certificate)
- ✅ Auto-renewal of SSL (every 90 days)
- ✅ Rate limiting (100 req/min)
- ✅ Professional domain instead of IP address

---

## Need Help?

If you get stuck:
1. Check the troubleshooting section above
2. Verify each step was completed correctly
3. Check server logs: `docker logs rag-api`
4. Check Nginx logs: `tail -f /var/log/nginx/error.log`

**When asking for help, provide**:
- Your domain name
- Output of: `dig yourdomain.com`
- Output of: `nginx -t`
- Output of: `docker ps`

---

**Next Steps After DNS Setup**:
- Come back and let me know your domain is configured
- I'll help verify DNS propagation
- We'll configure the server together
- Get HTTPS working in 10 minutes!

**Your domain**: __________________ (fill in after purchase)
**DNS configured**: [ ] Yes [ ] No
**DNS propagated**: [ ] Yes [ ] No [ ] Checking