#!/usr/bin/env bash
# =============================================================
# PortAct – EC2 Bootstrap Script
# Run on a fresh Amazon Linux 2023 (ARM/x86) instance.
#
# Usage:
#   chmod +x setup.sh
#   sudo ./setup.sh
# =============================================================
set -euo pipefail

REPO_URL="https://github.com/debasisdas1976/PortAct.git"
APP_DIR="/opt/portact"
DOMAIN=""  # Set via --domain flag or edit here

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain) DOMAIN="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "============================================="
echo " PortAct – AWS EC2 Setup"
echo "============================================="

# ---------------------------------------------------------------------------
# 1. System updates & dependencies
# ---------------------------------------------------------------------------
echo "[1/7] Installing system packages..."
dnf update -y
dnf install -y docker git

# ---------------------------------------------------------------------------
# 2. Start Docker
# ---------------------------------------------------------------------------
echo "[2/7] Starting Docker..."
systemctl enable docker
systemctl start docker

# Install Docker Compose plugin
DOCKER_COMPOSE_VERSION="v2.27.0"
ARCH=$(uname -m)
if [[ "$ARCH" == "aarch64" ]]; then
    COMPOSE_ARCH="aarch64"
else
    COMPOSE_ARCH="x86_64"
fi
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-${COMPOSE_ARCH}" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "Docker Compose version: $(docker compose version)"

# ---------------------------------------------------------------------------
# 3. Clone repository
# ---------------------------------------------------------------------------
echo "[3/7] Cloning PortAct..."
if [[ -d "$APP_DIR" ]]; then
    echo "  Directory exists — pulling latest..."
    cd "$APP_DIR" && git pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi

# ---------------------------------------------------------------------------
# 4. Create .env from template
# ---------------------------------------------------------------------------
ENV_FILE="$APP_DIR/infrastructure/aws/.env"
echo "[4/7] Setting up environment..."
if [[ ! -f "$ENV_FILE" ]]; then
    cp "$APP_DIR/infrastructure/aws/.env.production.template" "$ENV_FILE"
    # Generate a random secret key
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s|SECRET_KEY=CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32|SECRET_KEY=${SECRET_KEY}|" "$ENV_FILE"
    echo ""
    echo "  *** IMPORTANT: Edit $ENV_FILE with your actual values ***"
    echo "  At minimum, change: POSTGRES_PASSWORD, OPENAI_API_KEY, DOMAIN"
    echo ""
else
    echo "  .env already exists — skipping."
fi

# ---------------------------------------------------------------------------
# 5. SSL certificate (Let's Encrypt)
# ---------------------------------------------------------------------------
echo "[5/7] Setting up SSL..."
if [[ -n "$DOMAIN" ]]; then
    dnf install -y certbot
    mkdir -p /var/www/certbot

    # Get certificate (standalone mode — Nginx not running yet)
    certbot certonly --standalone \
        -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email "admin@${DOMAIN}" \
        --preferred-challenges http

    # Replace domain placeholder in nginx config
    sed -i "s/\${DOMAIN}/${DOMAIN}/g" "$APP_DIR/infrastructure/aws/nginx.prod.conf"

    # Set up auto-renewal cron
    echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker restart portact-nginx'" \
        | crontab -

    echo "  SSL certificate obtained for $DOMAIN"
else
    echo "  No --domain provided. Skipping SSL setup."
    echo "  Run later: sudo certbot certonly --standalone -d your-domain.com"
fi

# ---------------------------------------------------------------------------
# 6. Start the application
# ---------------------------------------------------------------------------
echo "[6/7] Starting PortAct..."
cd "$APP_DIR/infrastructure/aws"
docker compose -f docker-compose.prod.yml up -d --build

echo "Waiting for services to be healthy..."
sleep 15
docker compose -f docker-compose.prod.yml ps

# ---------------------------------------------------------------------------
# 7. Set up systemd service for auto-start on reboot
# ---------------------------------------------------------------------------
echo "[7/7] Creating systemd service..."
cat > /etc/systemd/system/portact.service << 'UNIT'
[Unit]
Description=PortAct Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/portact/infrastructure/aws
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable portact.service

# ---------------------------------------------------------------------------
# 8. Set up daily database backup
# ---------------------------------------------------------------------------
echo "Setting up daily backups..."
chmod +x "$APP_DIR/infrastructure/aws/backup.sh"
# Run backup daily at 2:00 AM UTC
(crontab -l 2>/dev/null; echo "0 2 * * * $APP_DIR/infrastructure/aws/backup.sh >> /var/log/portact-backup.log 2>&1") | crontab -

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "============================================="
echo " PortAct is running!"
echo "============================================="
echo ""
echo " Backend API:  http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000/health"
if [[ -n "$DOMAIN" ]]; then
    echo " HTTPS:        https://$DOMAIN"
fi
echo ""
echo " Next steps:"
echo "   1. Edit $ENV_FILE with production credentials"
echo "   2. Run: cd $APP_DIR/infrastructure/aws && docker compose -f docker-compose.prod.yml up -d"
echo "   3. Deploy frontend: ./deploy-frontend.sh"
echo ""
