#!/bin/bash

# Database setup script for PortAct
# This script creates the PostgreSQL database and user

set -e

echo "========================================="
echo "  PortAct Database Setup"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Database configuration
DB_NAME="portact_db"
DB_USER="portact_user"
DB_PASSWORD="portact_password"

print_info "Creating PostgreSQL database and user..."

# Check if PostgreSQL is running
if ! pg_isready -q; then
    print_error "PostgreSQL is not running. Please start it first:"
    echo "  brew services start postgresql@14"
    exit 1
fi

print_success "PostgreSQL is running"

# Create user if it doesn't exist
print_info "Creating database user: $DB_USER"
psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 || \
    psql postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
print_success "User created/verified"

# Create database if it doesn't exist
print_info "Creating database: $DB_NAME"
psql postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || \
    psql postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
print_success "Database created/verified"

# Grant privileges
print_info "Granting privileges..."
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
psql $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;"
print_success "Privileges granted"

echo ""
echo "========================================="
echo "  Database Setup Complete!"
echo "========================================="
echo ""
echo "Database Details:"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo "  Connection: postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "Next steps:"
echo "  1. Run migrations: alembic upgrade head"
echo "  2. Start the app: uvicorn app.main:app --reload"
echo ""

# Made with Bob
