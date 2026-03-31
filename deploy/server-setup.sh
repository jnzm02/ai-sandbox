#!/bin/bash
set -e

# VPS Server Setup Script for RAG API
# Run this once on a fresh Ubuntu 22.04/24.04 VPS
# Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/ai-sandbox/main/deploy/server-setup.sh | bash

echo "=== RAG API Server Setup ==="
echo "This script will install Docker, Nginx, and configure the server"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "[1/8] Updating system packages..."
apt-get update
apt-get upgrade -y

# Install dependencies
echo "[2/8] Installing dependencies..."
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    ufw \
    git \
    htop \
    vim

# Install Docker
echo "[3/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Set up Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start Docker
    systemctl enable docker
    systemctl start docker

    echo "Docker installed successfully"
else
    echo "Docker already installed"
fi

# Install Docker Compose (standalone)
echo "[4/8] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_VERSION="v2.24.5"
    curl -SL "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    echo "Docker Compose installed successfully"
else
    echo "Docker Compose already installed"
fi

# Install Nginx
echo "[5/8] Installing Nginx..."
apt-get install -y nginx

# Configure Firewall
echo "[6/8] Configuring firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 'Nginx Full'
ufw allow 80/tcp
ufw allow 443/tcp
echo "Firewall configured"

# Create application directory
echo "[7/8] Creating application directory..."
mkdir -p /opt/rag-api
mkdir -p /opt/rag-api/data
mkdir -p /var/log/rag-api
chown -R $SUDO_USER:$SUDO_USER /opt/rag-api
chown -R www-data:www-data /var/log/rag-api

# Install Certbot for SSL
echo "[8/8] Installing Certbot for SSL certificates..."
apt-get install -y certbot python3-certbot-nginx

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Copy your vector database to /opt/rag-api/data/chroma_db/"
echo "2. Create /opt/rag-api/.env with your ANTHROPIC_API_KEY"
echo "3. Configure Nginx with your domain"
echo "4. Run deploy.sh to start the application"
echo ""
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker-compose --version)"
echo "Nginx version: $(nginx -v 2>&1)"