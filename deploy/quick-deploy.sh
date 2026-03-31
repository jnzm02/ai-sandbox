#!/bin/bash
set -e

# Quick Deployment Script for Fresh VPS
# This is a single-command deployment for experienced users
# For detailed step-by-step guide, see DEPLOYMENT_VPS.md

echo "=== RAG API Quick Deploy ==="
echo ""
echo "This script will:"
echo "  1. Set up server (Docker, Nginx, SSL)"
echo "  2. Upload vector database"
echo "  3. Configure environment"
echo "  4. Deploy application"
echo ""

# Check if running on server or local
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" = "ubuntu" ] && [ -f /root/.profile ]; then
        echo "Running on Ubuntu server - assuming fresh VPS setup"
        ON_SERVER=true
    else
        ON_SERVER=false
    fi
else
    ON_SERVER=false
fi

if [ "$ON_SERVER" = true ]; then
    # ========================================================================
    # SERVER SIDE: Setup and deploy
    # ========================================================================
    echo ""
    echo "=== Server Setup Mode ==="
    echo ""

    # Check if already set up
    if command -v docker &> /dev/null && [ -d /opt/rag-api ]; then
        echo "Server already set up. Updating deployment..."
        cd /opt/rag-api
        ./deploy.sh --pull
        exit 0
    fi

    # Run server setup
    if [ ! -f ./server-setup.sh ]; then
        echo "Downloading server setup script..."
        curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/ai-sandbox/main/deploy/server-setup.sh -o server-setup.sh
        chmod +x server-setup.sh
    fi

    echo "Running server setup..."
    ./server-setup.sh

    echo ""
    echo "=== Server Setup Complete ==="
    echo ""
    echo "Next steps:"
    echo "1. Upload vector database: scp -r data/chroma_db root@SERVER:/opt/rag-api/data/"
    echo "2. Configure .env: nano /opt/rag-api/.env"
    echo "3. Deploy: cd /opt/rag-api && ./deploy.sh --pull"
    echo ""

else
    # ========================================================================
    # LOCAL SIDE: Push to server
    # ========================================================================
    echo ""
    echo "=== Deploy from Local Machine ==="
    echo ""

    # Get server details
    read -p "Enter server IP or hostname: " SERVER_HOST
    read -p "Enter SSH user [root]: " SSH_USER
    SSH_USER=${SSH_USER:-root}

    SERVER="$SSH_USER@$SERVER_HOST"

    # Verify local prerequisites
    echo ""
    echo "Checking local prerequisites..."

    if [ ! -f .env ]; then
        echo "❌ Error: .env file not found"
        echo "   Create it from .env.example and add your ANTHROPIC_API_KEY"
        exit 1
    fi

    if [ ! -d data/chroma_db ]; then
        echo "❌ Error: Vector database not found at data/chroma_db"
        echo "   Run 'python src/ingest.py' to create it"
        exit 1
    fi

    echo "✅ Local prerequisites met"

    # Test SSH connection
    echo ""
    echo "Testing SSH connection to $SERVER..."
    if ! ssh -o ConnectTimeout=5 "$SERVER" "echo 'SSH connection successful'" > /dev/null 2>&1; then
        echo "❌ Error: Cannot connect to $SERVER"
        echo "   Please check your SSH configuration"
        exit 1
    fi
    echo "✅ SSH connection successful"

    # Upload setup scripts
    echo ""
    echo "Uploading deployment scripts..."
    ssh "$SERVER" "mkdir -p /opt/rag-api/deploy"
    scp deploy/*.sh "$SERVER:/opt/rag-api/deploy/"
    ssh "$SERVER" "chmod +x /opt/rag-api/deploy/*.sh"

    # Run server setup if needed
    echo ""
    echo "Setting up server (this may take a few minutes)..."
    ssh "$SERVER" "cd /opt/rag-api/deploy && sudo ./server-setup.sh" || {
        echo "Note: Server setup may have already been run"
    }

    # Upload vector database
    echo ""
    echo "Uploading vector database (this may take a while)..."
    rsync -avz --progress data/chroma_db/ "$SERVER:/opt/rag-api/data/chroma_db/"

    # Upload and configure .env
    echo ""
    echo "Configuring environment..."
    scp .env "$SERVER:/opt/rag-api/.env"
    ssh "$SERVER" "chmod 600 /opt/rag-api/.env"

    # Upload docker-compose.yml (if using compose)
    if [ -f docker-compose.yml ]; then
        scp docker-compose.yml "$SERVER:/opt/rag-api/"
    fi

    # Deploy application
    echo ""
    echo "Deploying application..."

    # Ask about Docker Hub or build on server
    read -p "Pull from Docker Hub? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ssh "$SERVER" "cd /opt/rag-api && ./deploy/deploy.sh --pull"
    else
        echo "Building on server (this will take a while)..."
        # Upload source code
        rsync -avz --exclude='data/' --exclude='.*' \
            ./ "$SERVER:/opt/rag-api/"
        ssh "$SERVER" "cd /opt/rag-api && ./deploy/deploy.sh --build"
    fi

    # Configure domain (optional)
    echo ""
    read -p "Configure domain and SSL? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your domain (e.g., api.example.com): " DOMAIN

        # Upload and configure Nginx
        scp deploy/nginx.conf "$SERVER:/etc/nginx/sites-available/rag-api"
        ssh "$SERVER" "sed -i 's/your-domain.com/$DOMAIN/g' /etc/nginx/sites-available/rag-api"
        ssh "$SERVER" "ln -sf /etc/nginx/sites-available/rag-api /etc/nginx/sites-enabled/"
        ssh "$SERVER" "nginx -t && systemctl reload nginx"

        # Obtain SSL certificate
        echo ""
        echo "Obtaining SSL certificate (you'll need to answer some questions)..."
        ssh -t "$SERVER" "certbot --nginx -d $DOMAIN"
    fi

    # Test deployment
    echo ""
    echo "Testing deployment..."
    if ssh "$SERVER" "curl -sf http://localhost:8000/health" > /dev/null; then
        echo "✅ Deployment successful!"
    else
        echo "⚠️  Health check failed. Checking logs..."
        ssh "$SERVER" "docker logs rag-api --tail=20"
    fi

    echo ""
    echo "=== Deployment Complete ==="
    echo ""
    echo "Your RAG API is now running on $SERVER_HOST"
    echo ""
    echo "Access points:"
    echo "  - Local: http://$SERVER_HOST:8000/health"
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "  - Public: https://$DOMAIN/health"
        echo "  - API Docs: https://$DOMAIN/docs"
    else
        echo "  - Public: http://$SERVER_HOST:8000/docs"
    fi
    echo ""
    echo "Useful commands:"
    echo "  - View logs: ssh $SERVER 'docker logs -f rag-api'"
    echo "  - Restart: ssh $SERVER 'cd /opt/rag-api && ./deploy/deploy.sh'"
    echo "  - Update DB: ./deploy/update-vector-db.sh --host $SERVER_HOST"
    echo ""

fi