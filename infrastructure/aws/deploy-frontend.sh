#!/usr/bin/env bash
# =============================================================
# PortAct – Deploy Frontend to S3 + Invalidate CloudFront
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - Node.js 18+ installed
#   - S3 bucket created and configured for static hosting
#   - CloudFront distribution ID set below or via env var
#
# Usage:
#   ./deploy-frontend.sh
#   API_URL=https://api.example.com BUCKET=my-bucket ./deploy-frontend.sh
# =============================================================
set -euo pipefail

# Configuration (override via environment variables)
S3_BUCKET="${BUCKET:-portact-frontend}"
CLOUDFRONT_DIST_ID="${CLOUDFRONT_DIST_ID:-}"
API_URL="${API_URL:-https://your-domain.com}"
AWS_REGION="${AWS_REGION:-ap-south-1}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/../../frontend" && pwd)"

echo "============================================="
echo " PortAct – Frontend Deployment"
echo "============================================="
echo " S3 Bucket:      $S3_BUCKET"
echo " API URL:        $API_URL"
echo " CloudFront ID:  ${CLOUDFRONT_DIST_ID:-not set}"
echo ""

# ---------------------------------------------------------------------------
# 1. Build
# ---------------------------------------------------------------------------
echo "[1/3] Building frontend..."
cd "$FRONTEND_DIR"

# Set the API URL for the build
export REACT_APP_API_URL="${API_URL}/api/v1"
export REACT_APP_ENVIRONMENT=production
export REACT_APP_ENABLE_ANALYTICS=false
export REACT_APP_ENABLE_NOTIFICATIONS=true

npm ci --production=false
npm run build

echo "  Build complete. Output: $FRONTEND_DIR/build/"

# ---------------------------------------------------------------------------
# 2. Upload to S3
# ---------------------------------------------------------------------------
echo "[2/3] Syncing to S3..."

# Sync all files
aws s3 sync build/ "s3://${S3_BUCKET}/" \
    --region "$AWS_REGION" \
    --delete

# Set cache headers: long cache for hashed assets, no-cache for index.html
aws s3 cp "s3://${S3_BUCKET}/index.html" "s3://${S3_BUCKET}/index.html" \
    --region "$AWS_REGION" \
    --cache-control "no-cache, no-store, must-revalidate" \
    --content-type "text/html" \
    --metadata-directive REPLACE

aws s3 cp "s3://${S3_BUCKET}/static/" "s3://${S3_BUCKET}/static/" \
    --region "$AWS_REGION" \
    --recursive \
    --cache-control "public, max-age=31536000, immutable" \
    --metadata-directive REPLACE

echo "  Uploaded to s3://${S3_BUCKET}/"

# ---------------------------------------------------------------------------
# 3. Invalidate CloudFront cache
# ---------------------------------------------------------------------------
if [[ -n "$CLOUDFRONT_DIST_ID" ]]; then
    echo "[3/3] Invalidating CloudFront cache..."
    aws cloudfront create-invalidation \
        --distribution-id "$CLOUDFRONT_DIST_ID" \
        --paths "/*" \
        --region "$AWS_REGION"
    echo "  CloudFront invalidation initiated."
else
    echo "[3/3] Skipping CloudFront invalidation (no distribution ID set)."
    echo "  Set CLOUDFRONT_DIST_ID env var to enable."
fi

echo ""
echo "============================================="
echo " Frontend deployed successfully!"
echo "============================================="
