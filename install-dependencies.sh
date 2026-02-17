#!/bin/bash

# Quick dependency installation script for PortAct
# This resolves all import errors by installing dependencies locally

set -e

echo "========================================="
echo "  PortAct Dependency Installer"
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

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

# Check Node
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi
print_success "Node.js found: $(node --version)"

# Install Backend Dependencies
echo ""
print_info "Installing backend dependencies..."
cd backend

if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

print_info "Activating virtual environment..."
source venv/bin/activate

print_info "Installing Python packages..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

print_success "Backend dependencies installed"

# Verify backend installation
print_info "Verifying backend installation..."
python -c "
import fastapi
import sqlalchemy
import pydantic
from jose import jwt
from passlib.context import CryptContext
print('✓ All core packages imported successfully')
" && print_success "Backend verification passed"

cd ..

# Install Frontend Dependencies
echo ""
print_info "Installing frontend dependencies..."
cd frontend

if [ ! -d "node_modules" ]; then
    print_info "Installing npm packages..."
    npm install
    print_success "Frontend dependencies installed"
else
    print_info "node_modules already exists, skipping..."
fi

# Verify frontend installation
print_info "Verifying frontend installation..."
if [ -d "node_modules/react" ]; then
    print_success "Frontend verification passed"
else
    print_error "Frontend verification failed"
fi

cd ..

# Summary
echo ""
echo "========================================="
echo "  Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your IDE to use the Python interpreter:"
echo "   ${PWD}/backend/venv/bin/python"
echo ""
echo "2. Reload your IDE/editor to recognize the imports"
echo ""
echo "3. To run the application:"
echo "   Option A (Docker): ./setup.sh"
echo "   Option B (Local):"
echo "     Terminal 1: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "     Terminal 2: cd frontend && npm start"
echo ""
echo "4. Access the application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "========================================="

# Made with Bob
