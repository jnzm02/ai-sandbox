#!/bin/bash
set -e

# Update RAG API from GitHub
# Run this on the server to pull latest code and redeploy
#
# Usage:
#   ./update-from-git.sh           # Pull and deploy (default)
#   ./update-from-git.sh --build   # Pull and rebuild image
#   ./update-from-git.sh --check   # Check for updates only

REPO_URL="https://github.com/jnzm02/ai-sandbox.git"
APP_DIR="/opt/rag-api"
BRANCH="main"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "  RAG API Update from Git"
echo "========================================="
echo ""

# Parse arguments
CHECK_ONLY=false
BUILD_IMAGE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --build)
            BUILD_IMAGE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--check] [--build]"
            exit 1
            ;;
    esac
done

# Change to app directory
cd "$APP_DIR" || {
    echo -e "${RED}❌ Error: App directory not found at $APP_DIR${NC}"
    exit 1
}

# Check if git repository exists
if [ ! -d .git ]; then
    echo "Initializing Git repository..."
    git init
    git remote add origin "$REPO_URL"
fi

# Fetch latest changes
echo "[1/5] Fetching latest changes from GitHub..."
git fetch origin "$BRANCH"

# Check if updates are available
LOCAL_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "none")
REMOTE_COMMIT=$(git rev-parse origin/$BRANCH)

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo -e "${GREEN}✅ Already up to date${NC}"
    echo "Current commit: $LOCAL_COMMIT"
    exit 0
fi

echo -e "${YELLOW}Updates available:${NC}"
echo "  Local:  $LOCAL_COMMIT"
echo "  Remote: $REMOTE_COMMIT"
echo ""

# Show changes
echo "Changes:"
git log --oneline HEAD..origin/$BRANCH 2>/dev/null || echo "  (First pull)"
echo ""

if [ "$CHECK_ONLY" = true ]; then
    echo "Check-only mode. Exiting."
    exit 0
fi

# Confirm update
read -p "Pull updates and redeploy? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Update cancelled"
    exit 0
fi

# Create backup before update
echo ""
echo "[2/5] Creating pre-update backup..."
./backup-full.sh || {
    echo -e "${YELLOW}⚠️  Backup failed, but continuing...${NC}"
}

# Pull changes
echo ""
echo "[3/5] Pulling latest code..."
git reset --hard origin/$BRANCH

# Update deployment scripts permissions
echo ""
echo "[4/5] Updating script permissions..."
chmod +x deploy/*.sh

# Redeploy application
echo ""
echo "[5/5] Redeploying application..."

if [ "$BUILD_IMAGE" = true ]; then
    echo "Building Docker image from updated code..."
    ./deploy/deploy.sh --build
else
    echo "Pulling latest Docker image..."
    ./deploy/deploy.sh --pull
fi

# Verify deployment
echo ""
echo "Verifying deployment..."
sleep 5

if curl -sf http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Update successful!${NC}"
    echo ""
    echo "Current version: $(git rev-parse --short HEAD)"
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Check logs: docker logs rag-api"
    exit 1
fi

echo ""
echo "========================================="
echo "  Update Complete"
echo "========================================="
echo ""
echo "Changes applied:"
git log --oneline -5
echo ""
