#!/bin/bash
set -e

# Deployment script for RAG API
# Run this to deploy or update the application
# Usage: ./deploy.sh [--build] [--pull]

APP_DIR="/opt/rag-api"
DOCKER_IMAGE="ghcr.io/jnzm02/ai-sandbox:latest"
CONTAINER_NAME="rag-api"

# Parse arguments
BUILD_LOCAL=false
PULL_IMAGE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_LOCAL=true
            shift
            ;;
        --pull)
            PULL_IMAGE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--build] [--pull]"
            exit 1
            ;;
    esac
done

echo "=== RAG API Deployment ==="
echo ""

# Check if running from correct directory or as root
if [ ! -f "$APP_DIR/.env" ]; then
    echo "Error: $APP_DIR/.env not found"
    echo "Please create it from .env.production template"
    exit 1
fi

if [ ! -d "$APP_DIR/data/chroma_db" ]; then
    echo "Error: Vector database not found at $APP_DIR/data/chroma_db"
    echo "Please run ingest.py locally and copy the data directory"
    exit 1
fi

# Navigate to app directory
cd "$APP_DIR"

# Stop existing container if running
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "[1/5] Stopping existing container..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
else
    echo "[1/5] No existing container found"
fi

# Build or pull image
if [ "$BUILD_LOCAL" = true ]; then
    echo "[2/5] Building Docker image locally..."
    docker build -t $DOCKER_IMAGE .
elif [ "$PULL_IMAGE" = true ]; then
    echo "[2/5] Pulling Docker image from registry..."
    docker pull $DOCKER_IMAGE
else
    echo "[2/5] Using existing local image"
fi

# Run new container
echo "[3/5] Starting new container..."
docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    -p 127.0.0.1:8000:8000 \
    -v "$APP_DIR/data/chroma_db:/app/data/chroma_db:ro" \
    -v "/var/log/rag-api:/var/log/rag-api" \
    --env-file "$APP_DIR/.env" \
    --health-cmd="curl -f http://localhost:8000/health || exit 1" \
    --health-interval=30s \
    --health-timeout=10s \
    --health-retries=3 \
    --memory="2g" \
    --cpus="1.5" \
    $DOCKER_IMAGE

# Wait for health check
echo "[4/5] Waiting for container to be healthy..."
sleep 5
for i in {1..30}; do
    if [ "$(docker inspect --format='{{.State.Health.Status}}' $CONTAINER_NAME 2>/dev/null)" = "healthy" ]; then
        echo "Container is healthy!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

# Check status
echo "[5/5] Checking deployment status..."
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo ""
    echo "=== Deployment Successful ==="
    docker ps -f name=$CONTAINER_NAME
    echo ""
    echo "Logs: docker logs -f $CONTAINER_NAME"
    echo "Health: curl http://localhost:8000/health"
    echo ""

    # Test health endpoint
    sleep 2
    if curl -sf http://localhost:8000/health > /dev/null; then
        echo "Health check: PASSED"
    else
        echo "Health check: FAILED (container may still be starting)"
    fi
else
    echo ""
    echo "=== Deployment Failed ==="
    echo "Check logs: docker logs $CONTAINER_NAME"
    exit 1
fi

# Clean up old images
echo ""
echo "Cleaning up old Docker images..."
docker image prune -f

echo ""
echo "Deployment complete!"