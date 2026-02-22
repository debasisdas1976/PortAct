#!/bin/bash

# PortAct - Complete Application Setup and Run Script
# This script sets up and runs both backend and frontend

set -e

echo "======================================"
echo "PortAct Application Setup & Run"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running on macOS or Linux
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
else
    print_error "Unsupported operating system"
    exit 1
fi

print_status "Detected OS: $OS"

# Step 1: Check Prerequisites
echo ""
echo "Step 1: Checking Prerequisites..."
echo "--------------------------------"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python found: $PYTHON_VERSION"
else
    print_error "Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_status "Node.js found: $NODE_VERSION"
else
    print_error "Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    print_status "npm found: v$NPM_VERSION"
else
    print_error "npm is not installed. Please install npm."
    exit 1
fi

# Check PostgreSQL
if command -v psql &> /dev/null; then
    PSQL_VERSION=$(psql --version)
    print_status "PostgreSQL found: $PSQL_VERSION"
else
    print_warning "PostgreSQL not found. Please ensure PostgreSQL is installed and running."
fi

# Step 2: Setup Backend
echo ""
echo "Step 2: Setting up Backend..."
echo "--------------------------------"

cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_status "Created .env file. Please update it with your configuration."
    else
        print_error ".env.example not found!"
    fi
fi

# Setup database
print_status "Setting up database..."
if [ -f "setup_database.sh" ]; then
    chmod +x setup_database.sh
    ./setup_database.sh
else
    print_warning "setup_database.sh not found. Please setup database manually."
fi

# Run migrations
print_status "Running database migrations..."
alembic upgrade head

cd ..

# Step 3: Setup Frontend
echo ""
echo "Step 3: Setting up Frontend..."
echo "--------------------------------"

cd frontend

# Install npm dependencies
if [ ! -d "node_modules" ]; then
    print_status "Installing npm dependencies..."
    npm install
else
    print_status "npm dependencies already installed."
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    print_status "Creating frontend .env file..."
    echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > .env
fi

cd ..

# Step 4: Start the application
echo ""
echo "Step 4: Starting Application..."
echo "--------------------------------"

print_status "Starting backend server..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

print_status "Starting frontend development server..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "======================================"
echo "Application Started Successfully!"
echo "======================================"
echo ""
echo "Backend API: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    print_status "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    print_status "Servers stopped."
    exit 0
}

# Trap Ctrl+C
trap cleanup INT

# Wait for processes
wait

# Made with Bob
