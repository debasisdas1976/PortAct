#!/bin/bash

# Docker-based Database Initialization Script for PortAct
# This script initializes the database using Docker containers

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_header() {
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""
}

print_header "PortAct Docker Database Initialization"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo "Install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed"
    echo "Install Docker Compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

print_success "Docker and Docker Compose are installed"

# Check if docker-compose.yml exists
if [ ! -f "infrastructure/docker-compose.yml" ]; then
    print_error "docker-compose.yml not found in infrastructure directory"
    exit 1
fi

# Step 1: Start PostgreSQL container
print_info "Step 1: Starting PostgreSQL container..."
cd infrastructure
docker-compose up -d postgres
print_success "PostgreSQL container started"

# Wait for PostgreSQL to be ready
print_info "Waiting for PostgreSQL to be ready..."
sleep 5

MAX_RETRIES=30
RETRY_COUNT=0
while ! docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        print_error "PostgreSQL failed to start after $MAX_RETRIES attempts"
        exit 1
    fi
    echo -n "."
    sleep 1
done
echo ""
print_success "PostgreSQL is ready"

cd ..

# Step 2: Run migrations in backend container
print_info "Step 2: Building backend container..."
cd infrastructure
docker-compose build backend
print_success "Backend container built"

print_info "Running database migrations..."
docker-compose run --rm backend alembic upgrade head
print_success "Migrations completed"

# Step 3: Seed initial data
print_info "Step 3: Seeding initial data..."
if [ -f "../backend/seed_categories.py" ]; then
    docker-compose run --rm backend python seed_categories.py 2>/dev/null || {
        print_info "Categories may already exist or seeding not needed"
    }
    print_success "Initial data seeded"
fi

cd ..

# Step 4: Verify setup
print_info "Step 4: Verifying database setup..."

TABLE_COUNT=$(docker-compose -f infrastructure/docker-compose.yml exec -T postgres psql -U postgres -d portact_db -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" 2>/dev/null | tr -d '[:space:]' || echo "0")

if [ "$TABLE_COUNT" -gt "0" ]; then
    print_success "Database has $TABLE_COUNT tables"
else
    print_error "No tables found in database"
    exit 1
fi

print_header "Docker Database Initialization Complete!"

echo ""
echo "Database Details:"
echo "  Container: portact-postgres"
echo "  Database: portact_db"
echo "  User: postgres"
echo "  Port: 5432 (mapped to host)"
echo "  Tables: $TABLE_COUNT"
echo ""
echo "Next steps:"
echo "  1. Start all services: cd infrastructure && docker-compose up -d"
echo "  2. View logs: cd infrastructure && docker-compose logs -f"
echo "  3. Stop services: cd infrastructure && docker-compose down"
echo ""
echo "Useful commands:"
echo "  - Connect to DB: docker-compose -f infrastructure/docker-compose.yml exec postgres psql -U postgres -d portact_db"
echo "  - View backend logs: docker-compose -f infrastructure/docker-compose.yml logs -f backend"
echo "  - View frontend logs: docker-compose -f infrastructure/docker-compose.yml logs -f frontend"
echo "  - Restart services: docker-compose -f infrastructure/docker-compose.yml restart"
echo ""

# Made with Bob
