# =============================================================================
# PortAct – All-in-One Docker Image
# Bundles PostgreSQL 15, FastAPI backend, and React frontend in one container.
#
# Build:  docker build -t portact .
# Run:    docker run -d -p 8080:8080 -v portact-data:/var/lib/postgresql/data portact
# Open:   http://localhost:8080
# =============================================================================

# ── Stage 1: Build the React frontend ────────────────────────────────────────

FROM node:18-alpine AS frontend-build
WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci || npm install

COPY frontend/ ./
ENV REACT_APP_API_URL=/api/v1 \
    CI=false
RUN npm run build


# ── Stage 2: Final all-in-one image ──────────────────────────────────────────

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # PostgreSQL
    PGDATA=/var/lib/postgresql/data \
    POSTGRES_USER=portact_user \
    POSTGRES_PASSWORD=portact_password \
    POSTGRES_DB=portact_db

# Install PostgreSQL 15, nginx, supervisord, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        gnupg2 lsb-release curl ca-certificates \
    && echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/pgdg.gpg \
    && apt-get update && apt-get install -y --no-install-recommends \
        postgresql-15 \
        nginx \
        supervisor \
        gcc \
        libpq-dev \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy backend source code
COPY backend/ ./

# Create required directories
RUN mkdir -p /app/backend/uploads /app/backend/logs /var/log/supervisor

# Copy built frontend
COPY --from=frontend-build /app/build /app/frontend/build

# Copy container configuration files
COPY supervisord.conf /etc/supervisor/conf.d/portact.conf
COPY nginx-aio.conf /etc/nginx/sites-available/default
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Remove the default nginx config that conflicts
RUN rm -f /etc/nginx/sites-enabled/default \
    && ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Ensure postgres user owns the data directory parent
RUN mkdir -p /var/lib/postgresql && chown -R postgres:postgres /var/lib/postgresql \
    && mkdir -p /run/postgresql && chown -R postgres:postgres /run/postgresql

EXPOSE 8080

VOLUME ["/var/lib/postgresql/data"]

ENTRYPOINT ["/docker-entrypoint.sh"]
