#!/bin/bash
set -e

# Simple monitoring setup for RAG API
# Uses Prometheus Node Exporter + optional Uptime Kuma
# Run this after server-setup.sh

echo "=== Monitoring Setup ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Install Prometheus Node Exporter
echo "[1/3] Installing Prometheus Node Exporter..."
if ! systemctl is-active --quiet node_exporter; then
    # Download Node Exporter
    NODE_EXPORTER_VERSION="1.7.0"
    cd /tmp
    wget "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
    tar xvfz "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
    cp "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" /usr/local/bin/

    # Create systemd service
    cat > /etc/systemd/system/node_exporter.service <<EOF
[Unit]
Description=Prometheus Node Exporter
After=network.target

[Service]
Type=simple
User=nobody
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable node_exporter
    systemctl start node_exporter

    echo "Node Exporter installed on :9100"
else
    echo "Node Exporter already running"
fi

# Install Docker Stats Exporter (cAdvisor)
echo "[2/3] Installing cAdvisor for Docker metrics..."
if ! docker ps | grep -q cadvisor; then
    docker run -d \
        --name=cadvisor \
        --restart=unless-stopped \
        --volume=/:/rootfs:ro \
        --volume=/var/run:/var/run:ro \
        --volume=/sys:/sys:ro \
        --volume=/var/lib/docker/:/var/lib/docker:ro \
        --volume=/dev/disk/:/dev/disk:ro \
        --publish=127.0.0.1:8080:8080 \
        --detach=true \
        gcr.io/cadvisor/cadvisor:latest

    echo "cAdvisor installed on :8080"
else
    echo "cAdvisor already running"
fi

# Create health check monitoring script
echo "[3/3] Creating health check monitoring..."
cat > /opt/rag-api/monitor-health.sh <<'EOF'
#!/bin/bash

# Simple health check monitor
# Add to crontab: */5 * * * * /opt/rag-api/monitor-health.sh

LOG_FILE="/var/log/rag-api/health-monitor.log"
HEALTH_URL="http://localhost:8000/health"

timestamp=$(date '+%Y-%m-%d %H:%M:%S')

if response=$(curl -sf "$HEALTH_URL" 2>&1); then
    echo "[$timestamp] OK - API is healthy" >> "$LOG_FILE"
else
    echo "[$timestamp] FAIL - API is down or unhealthy" >> "$LOG_FILE"

    # Optional: Send alert (configure email or webhook)
    # curl -X POST https://your-webhook-url \
    #   -H "Content-Type: application/json" \
    #   -d "{\"text\": \"RAG API is down!\"}"

    # Optional: Restart container
    # docker restart rag-api
fi
EOF

chmod +x /opt/rag-api/monitor-health.sh

# Create logrotate config
cat > /etc/logrotate.d/rag-api <<EOF
/var/log/rag-api/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
    sharedscripts
    postrotate
        docker kill -s HUP rag-api 2>/dev/null || true
    endscript
}
EOF

echo ""
echo "=== Monitoring Setup Complete ==="
echo ""
echo "Installed services:"
echo "- Node Exporter: http://localhost:9100/metrics (system metrics)"
echo "- cAdvisor: http://localhost:8080 (Docker metrics)"
echo "- Health Monitor: /opt/rag-api/monitor-health.sh"
echo ""
echo "Next steps:"
echo "1. Add health monitor to crontab:"
echo "   crontab -e"
echo "   */5 * * * * /opt/rag-api/monitor-health.sh"
echo ""
echo "2. (Optional) Install Uptime Kuma for dashboard:"
echo "   docker run -d --restart=unless-stopped -p 3001:3001 -v uptime-kuma:/app/data --name uptime-kuma louislam/uptime-kuma:1"
echo "   Access at: http://your-server-ip:3001"
echo ""
echo "3. (Optional) Set up Prometheus + Grafana for advanced monitoring"
