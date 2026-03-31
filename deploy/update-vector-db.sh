#!/bin/bash
set -e

# Update Vector Database on Production Server
# Use this when you need to re-index documentation or add new content
#
# Workflow:
# 1. Run locally: python src/ingest.py (to create updated vector DB)
# 2. Run this script to upload and update production

REMOTE_USER="root"
REMOTE_HOST=""
REMOTE_PATH="/opt/rag-api/data/chroma_db"
LOCAL_PATH="./data/chroma_db"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            REMOTE_HOST="$2"
            shift 2
            ;;
        --user)
            REMOTE_USER="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --host SERVER_IP [--user USER]"
            echo "Example: $0 --host 192.168.1.100 --user deploy"
            exit 1
            ;;
    esac
done

# Validate inputs
if [ -z "$REMOTE_HOST" ]; then
    echo "Error: Remote host not specified"
    echo "Usage: $0 --host SERVER_IP [--user USER]"
    exit 1
fi

if [ ! -d "$LOCAL_PATH" ]; then
    echo "Error: Local vector database not found at $LOCAL_PATH"
    echo "Please run 'python src/ingest.py' first to create the database"
    exit 1
fi

echo "=== Vector Database Update ==="
echo "Local DB: $LOCAL_PATH"
echo "Remote: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"
echo ""

# Confirm action
read -p "This will replace the production vector database. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 0
fi

# Step 1: Create backup on remote server
echo "[1/5] Creating backup on remote server..."
ssh "$REMOTE_USER@$REMOTE_HOST" "cd /opt/rag-api && ./backup.sh" || {
    echo "Warning: Backup failed, but continuing..."
}

# Step 2: Stop the API container
echo "[2/5] Stopping API container..."
ssh "$REMOTE_USER@$REMOTE_HOST" "docker stop rag-api" || {
    echo "Warning: Container may not be running"
}

# Step 3: Upload new vector database
echo "[3/5] Uploading new vector database..."
rsync -avz --progress --delete \
    "$LOCAL_PATH/" \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"

# Verify upload
REMOTE_SIZE=$(ssh "$REMOTE_USER@$REMOTE_HOST" "du -sh $REMOTE_PATH | cut -f1")
LOCAL_SIZE=$(du -sh "$LOCAL_PATH" | cut -f1)
echo "Local size: $LOCAL_SIZE"
echo "Remote size: $REMOTE_SIZE"

# Step 4: Restart the API container
echo "[4/5] Restarting API container..."
ssh "$REMOTE_USER@$REMOTE_HOST" "cd /opt/rag-api && ./deploy.sh"

# Step 5: Verify deployment
echo "[5/5] Verifying deployment..."
sleep 5

ssh "$REMOTE_USER@$REMOTE_HOST" "curl -sf http://localhost:8000/health" > /dev/null && {
    echo "✅ Health check passed"
} || {
    echo "❌ Health check failed"
    echo "Check logs: ssh $REMOTE_USER@$REMOTE_HOST 'docker logs rag-api'"
    exit 1
}

echo ""
echo "=== Update Complete ==="
echo ""
echo "Vector database updated successfully on $REMOTE_HOST"
echo ""
echo "Next steps:"
echo "1. Test a query to verify new content is indexed"
echo "2. Monitor logs: ssh $REMOTE_USER@$REMOTE_HOST 'docker logs -f rag-api'"
echo "3. Check metrics/monitoring for any issues"