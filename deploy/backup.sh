#!/bin/bash
set -e

# Backup script for RAG API vector database
# Run this via cron: 0 2 * * * /opt/rag-api/backup.sh

BACKUP_DIR="/opt/rag-api/backups"
DATA_DIR="/opt/rag-api/data/chroma_db"
BACKUP_NAME="chroma_db_$(date +%Y%m%d_%H%M%S).tar.gz"
RETENTION_DAYS=7

echo "=== RAG API Backup ==="
echo "Starting backup at $(date)"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create compressed backup
echo "Creating backup: $BACKUP_NAME"
tar -czf "$BACKUP_DIR/$BACKUP_NAME" -C "$(dirname $DATA_DIR)" "$(basename $DATA_DIR)"

# Check backup size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)
echo "Backup created: $BACKUP_SIZE"

# Remove old backups
echo "Removing backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "chroma_db_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# List current backups
echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"

echo ""
echo "Backup completed at $(date)"

# Optional: Upload to S3/Object Storage
# Uncomment and configure if you want off-site backups
# echo "Uploading to S3..."
# aws s3 cp "$BACKUP_DIR/$BACKUP_NAME" s3://your-bucket/rag-api-backups/
# or
# rclone copy "$BACKUP_DIR/$BACKUP_NAME" remote:rag-api-backups/