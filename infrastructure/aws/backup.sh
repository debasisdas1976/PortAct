#!/usr/bin/env bash
# =============================================================
# PortAct – Automated PostgreSQL Backup to S3
#
# Retention policy:
#   - Daily backups: kept for 7 days
#   - Weekly backups (Sunday): kept for 30 days
#
# Usage:
#   ./backup.sh                    # Uses defaults
#   S3_BACKUP_BUCKET=my-bk ./backup.sh   # Override bucket
#
# Cron (set up by setup.sh):
#   0 2 * * * /opt/portact/infrastructure/aws/backup.sh
# =============================================================
set -euo pipefail

# Configuration
S3_BACKUP_BUCKET="${S3_BACKUP_BUCKET:-portact-backups}"
AWS_REGION="${AWS_REGION:-ap-south-1}"
CONTAINER_NAME="portact-postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)  # 1=Monday, 7=Sunday
BACKUP_DIR="/tmp/portact-backups"

# Load env vars for DB credentials
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    export $(grep -E '^POSTGRES_(USER|PASSWORD|DB)=' "$SCRIPT_DIR/.env" | xargs)
fi

POSTGRES_USER="${POSTGRES_USER:-portact_user}"
POSTGRES_DB="${POSTGRES_DB:-portact_db}"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting PortAct database backup..."

# ---------------------------------------------------------------------------
# 1. Dump the database
# ---------------------------------------------------------------------------
DUMP_FILE="$BACKUP_DIR/portact_${TIMESTAMP}.sql.gz"

docker exec "$CONTAINER_NAME" pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --no-owner \
    --no-acl \
    | gzip > "$DUMP_FILE"

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "  Dump created: $DUMP_FILE ($DUMP_SIZE)"

# ---------------------------------------------------------------------------
# 2. Upload to S3
# ---------------------------------------------------------------------------
S3_KEY="daily/portact_${TIMESTAMP}.sql.gz"
aws s3 cp "$DUMP_FILE" "s3://${S3_BACKUP_BUCKET}/${S3_KEY}" \
    --region "$AWS_REGION" \
    --storage-class STANDARD_IA

echo "  Uploaded to s3://${S3_BACKUP_BUCKET}/${S3_KEY}"

# Weekly backup (Sunday)
if [[ "$DAY_OF_WEEK" == "7" ]]; then
    WEEKLY_KEY="weekly/portact_${TIMESTAMP}.sql.gz"
    aws s3 cp "$DUMP_FILE" "s3://${S3_BACKUP_BUCKET}/${WEEKLY_KEY}" \
        --region "$AWS_REGION" \
        --storage-class STANDARD_IA
    echo "  Weekly backup: s3://${S3_BACKUP_BUCKET}/${WEEKLY_KEY}"
fi

# ---------------------------------------------------------------------------
# 3. Clean up old backups
# ---------------------------------------------------------------------------
# Remove local dump
rm -f "$DUMP_FILE"

# Remove daily backups older than 7 days from S3
CUTOFF_DAILY=$(date -d "7 days ago" +%Y%m%d 2>/dev/null || date -v-7d +%Y%m%d)
echo "  Cleaning daily backups older than $CUTOFF_DAILY..."
aws s3 ls "s3://${S3_BACKUP_BUCKET}/daily/" --region "$AWS_REGION" 2>/dev/null | while read -r line; do
    FILE=$(echo "$line" | awk '{print $4}')
    FILE_DATE=$(echo "$FILE" | grep -oP '\d{8}' | head -1)
    if [[ -n "$FILE_DATE" && "$FILE_DATE" < "$CUTOFF_DAILY" ]]; then
        aws s3 rm "s3://${S3_BACKUP_BUCKET}/daily/${FILE}" --region "$AWS_REGION"
        echo "    Deleted: daily/$FILE"
    fi
done

# Remove weekly backups older than 30 days from S3
CUTOFF_WEEKLY=$(date -d "30 days ago" +%Y%m%d 2>/dev/null || date -v-30d +%Y%m%d)
echo "  Cleaning weekly backups older than $CUTOFF_WEEKLY..."
aws s3 ls "s3://${S3_BACKUP_BUCKET}/weekly/" --region "$AWS_REGION" 2>/dev/null | while read -r line; do
    FILE=$(echo "$line" | awk '{print $4}')
    FILE_DATE=$(echo "$FILE" | grep -oP '\d{8}' | head -1)
    if [[ -n "$FILE_DATE" && "$FILE_DATE" < "$CUTOFF_WEEKLY" ]]; then
        aws s3 rm "s3://${S3_BACKUP_BUCKET}/weekly/${FILE}" --region "$AWS_REGION"
        echo "    Deleted: weekly/$FILE"
    fi
done

echo "[$(date)] Backup complete."
