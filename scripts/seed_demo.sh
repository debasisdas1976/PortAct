#!/bin/bash

# Seed the PortAct demo user with comprehensive portfolio data.
#
# Usage:
#   bash scripts/seed_demo.sh
#
# Creates demo user: demouser@portact.com / portact1

set -e

# Resolve project root (scripts live in <project>/scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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
    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""
}

print_header "PortAct Demo User Seeder"

# Check backend directory
if [ ! -d "$PROJECT_DIR/backend" ]; then
    print_error "backend/ directory not found at $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR/backend"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    print_success "Activated virtual environment (.venv)"
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    print_success "Activated virtual environment (venv)"
else
    print_error "No Python virtual environment found in backend/"
    print_info "Create one with:"
    echo "  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check that required packages are installed
python -c "import bcrypt, sqlalchemy" 2>/dev/null || {
    print_error "Required Python packages not installed."
    print_info "Run: pip install -r requirements.txt"
    exit 1
}

# Check .env exists
if [ ! -f ".env" ]; then
    print_error ".env file not found in backend/"
    print_info "Copy .env.example to .env and configure DATABASE_URL."
    exit 1
fi

# Run the seed script
print_info "Running seed_demo_user.py..."
echo ""

python seed_demo_user.py
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    print_success "Demo environment ready!"
    echo ""
    echo "  Login:    demouser@portact.com"
    echo "  Password: portact1"
    echo ""
else
    print_error "Seeding failed (exit code $EXIT_CODE)"
fi

exit $EXIT_CODE
