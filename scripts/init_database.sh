#!/bin/bash

# Complete Database Initialization Script for PortAct
# This script sets up the database, runs migrations, and seeds initial data

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

# Check if .env file exists
if [ ! -f "backend/.env" ]; then
    print_error ".env file not found in backend directory"
    print_info "Creating .env from .env.example..."
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        print_success ".env file created"
        print_info "Please edit backend/.env with your configuration"
        exit 0
    else
        print_error ".env.example not found"
        exit 1
    fi
fi

# Load environment variables
source backend/.env 2>/dev/null || true

# Database configuration from .env or defaults
DB_NAME="${POSTGRES_DB:-portact_db}"
DB_USER="${POSTGRES_USER:-portact_user}"
DB_PASSWORD="${POSTGRES_PASSWORD:-portact_password}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

print_header "PortAct Database Initialization"

# Step 1: Check PostgreSQL
print_info "Step 1: Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    print_error "PostgreSQL is not installed"
    echo "Install PostgreSQL:"
    echo "  macOS: brew install postgresql@15"
    echo "  Ubuntu: sudo apt install postgresql postgresql-contrib"
    exit 1
fi

if ! pg_isready -h $DB_HOST -p $DB_PORT -q 2>/dev/null; then
    print_error "PostgreSQL is not running on $DB_HOST:$DB_PORT"
    echo "Start PostgreSQL:"
    echo "  macOS: brew services start postgresql@15"
    echo "  Ubuntu: sudo systemctl start postgresql"
    echo "  Docker: docker-compose up -d postgres"
    exit 1
fi
print_success "PostgreSQL is running"

# Step 2: Create database and user
print_info "Step 2: Setting up database..."

# Check if user exists
USER_EXISTS=$(psql -h $DB_HOST -p $DB_PORT -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null || echo "0")

if [ "$USER_EXISTS" != "1" ]; then
    print_info "Creating database user: $DB_USER"
    psql -h $DB_HOST -p $DB_PORT -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || {
        print_error "Failed to create user. You may need to run with sudo or as postgres user"
        exit 1
    }
    print_success "User created"
else
    print_success "User already exists"
fi

# Check if database exists
DB_EXISTS=$(psql -h $DB_HOST -p $DB_PORT -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "0")

if [ "$DB_EXISTS" != "1" ]; then
    print_info "Creating database: $DB_NAME"
    psql -h $DB_HOST -p $DB_PORT -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || {
        print_error "Failed to create database"
        exit 1
    }
    print_success "Database created"
else
    print_success "Database already exists"
fi

# Grant privileges
print_info "Granting privileges..."
psql -h $DB_HOST -p $DB_PORT -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null
psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;" 2>/dev/null
psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;" 2>/dev/null
psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;" 2>/dev/null
print_success "Privileges granted"

# Step 3: Check Python environment
print_info "Step 3: Checking Python environment..."
cd backend

if [ ! -d ".venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv .venv
    print_success "Virtual environment created"
fi

source .venv/bin/activate

print_info "Installing/updating dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
print_success "Dependencies installed"

# Step 4: Run database migrations
print_info "Step 4: Running database migrations..."

if [ ! -f "alembic.ini" ]; then
    print_error "alembic.ini not found"
    exit 1
fi

# Check current migration status
print_info "Checking migration status..."
alembic current 2>/dev/null || {
    print_info "No migrations applied yet"
}

# Run migrations
print_info "Applying migrations..."
alembic upgrade head
print_success "Migrations applied"

# Step 5: Seed initial data
print_info "Step 5: Seeding initial data..."

if [ -f "seed_categories.py" ]; then
    print_info "Seeding expense categories..."
    python seed_categories.py 2>/dev/null || {
        print_info "Categories may already exist or seeding not needed"
    }
    print_success "Initial data seeded"
else
    print_info "No seed script found, skipping..."
fi

# Step 6: Verify setup
print_info "Step 6: Verifying database setup..."

# Check if tables exist
TABLE_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" 2>/dev/null || echo "0")

if [ "$TABLE_COUNT" -gt "0" ]; then
    print_success "Database has $TABLE_COUNT tables"
else
    print_error "No tables found in database"
    exit 1
fi

cd ..

print_header "Database Initialization Complete!"

echo ""
echo "Database Details:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Tables: $TABLE_COUNT"
echo ""
echo "Connection String:"
echo "  postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""
echo "Next steps:"
echo "  1. Start backend: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  2. Start frontend: cd frontend && npm start"
echo "  3. Or use: ./scripts/run_app.sh"
echo ""
echo "Useful commands:"
echo "  - View migrations: cd backend && alembic history"
echo "  - Create migration: cd backend && alembic revision --autogenerate -m 'description'"
echo "  - Rollback migration: cd backend && alembic downgrade -1"
echo "  - Connect to DB: psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
echo ""

# Made with Bob
