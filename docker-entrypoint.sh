#!/usr/bin/env bash
set -e

# =============================================================================
# PortAct – All-in-One Container Entrypoint
# Initialises PostgreSQL, runs migrations, then starts all services.
# =============================================================================

# Add PostgreSQL binaries to PATH (Debian installs them under /usr/lib/postgresql/15/bin)
export PATH="/usr/lib/postgresql/15/bin:$PATH"

PGDATA="${PGDATA:-/var/lib/postgresql/data}"
PG_USER="${POSTGRES_USER:-portact_user}"
PG_PASS="${POSTGRES_PASSWORD:-portact_password}"
PG_DB="${POSTGRES_DB:-portact_db}"
DATABASE_URL="postgresql://${PG_USER}:${PG_PASS}@localhost:5432/${PG_DB}"

VERSION=$(cat /app/VERSION 2>/dev/null || echo "unknown")

echo "──────────────────────────────────────────────"
echo "  PortAct v${VERSION} – Starting All-in-One Container"
echo "──────────────────────────────────────────────"

# ── 1. Initialise PostgreSQL data directory if empty ─────────────────────────

# Ensure postgres user owns the data directory (Docker volumes start as root)
mkdir -p "$PGDATA"
chown -R postgres:postgres "$PGDATA"
chown -R postgres:postgres /run/postgresql
mkdir -p /var/log/supervisor
chmod 777 /var/log/supervisor

if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "[entrypoint] Initialising PostgreSQL data directory..."
    su postgres -c "initdb -D $PGDATA --auth=trust --encoding=UTF8 --locale=C"

    # Allow password authentication from localhost
    echo "host all all 127.0.0.1/32 md5" >> "$PGDATA/pg_hba.conf"
    echo "host all all ::1/128 md5" >> "$PGDATA/pg_hba.conf"
    echo "local all all trust" > /tmp/pg_hba_temp.conf
    cat "$PGDATA/pg_hba.conf" >> /tmp/pg_hba_temp.conf
    mv /tmp/pg_hba_temp.conf "$PGDATA/pg_hba.conf"
    chown postgres:postgres "$PGDATA/pg_hba.conf"

    # Listen on localhost only (internal to the container)
    sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" "$PGDATA/postgresql.conf"

    echo "[entrypoint] PostgreSQL data directory initialised."
fi

# ── 2. Start PostgreSQL temporarily ──────────────────────────────────────────

echo "[entrypoint] Starting PostgreSQL..."
su postgres -c "pg_ctl -D $PGDATA -l /var/log/supervisor/postgresql.log start -w -t 30"

# ── 3. Create database user and database ─────────────────────────────────────

echo "[entrypoint] Ensuring database user and database exist..."
su postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'\"" | grep -q 1 \
    || su postgres -c "psql -c \"CREATE USER ${PG_USER} WITH PASSWORD '${PG_PASS}';\""

su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='${PG_DB}'\"" | grep -q 1 \
    || su postgres -c "psql -c \"CREATE DATABASE ${PG_DB} OWNER ${PG_USER};\""

su postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE ${PG_DB} TO ${PG_USER};\"" 2>/dev/null || true
su postgres -c "psql -d ${PG_DB} -c \"GRANT ALL ON SCHEMA public TO ${PG_USER};\"" 2>/dev/null || true

# ── 4. Generate backend .env ─────────────────────────────────────────────────

SECRET_KEY="${SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')}"

cat > /app/backend/.env <<ENVEOF
APP_NAME=PortAct
DEBUG=False
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000
DATABASE_URL=${DATABASE_URL}
DB_ECHO=False
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
BACKEND_CORS_ORIGINS=["http://localhost:8080","http://localhost:3000","http://localhost:8000"]
MAX_UPLOAD_SIZE=10485760
UPLOAD_DIR=./uploads
ALLOWED_EXTENSIONS=.pdf,.csv,.xlsx,.xls,.doc,.docx
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
FRONTEND_URL=http://localhost:8080
REDIS_URL=redis://localhost:6379/0
ENVEOF

echo "[entrypoint] Backend .env generated."

# ── 5. Run Alembic migrations ────────────────────────────────────────────────

echo "[entrypoint] Running database migrations..."
cd /app/backend
alembic upgrade head
echo "[entrypoint] Migrations complete."

# ── 6. Stop temporary PostgreSQL ─────────────────────────────────────────────

echo "[entrypoint] Stopping temporary PostgreSQL..."
su postgres -c "pg_ctl -D $PGDATA stop -m fast -w"

# ── 7. Start all services via supervisord ────────────────────────────────────

echo "[entrypoint] Starting all services..."
echo "──────────────────────────────────────────────"
echo "  PortAct is available at http://localhost:8080"
echo "──────────────────────────────────────────────"

exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/portact.conf
