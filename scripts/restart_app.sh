#!/bin/bash

# PortAct - Application Restart Script
# This script cleanly stops and restarts both backend and frontend

set -e

# Resolve project root (scripts live in <project>/scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "======================================"
echo "PortAct Application Restart"
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

# Step 1: Stop running processes
echo "Step 1: Stopping running processes..."
echo "--------------------------------------"

# Stop backend (uvicorn)
print_status "Stopping backend server..."
pkill -f "uvicorn app.main:app" || print_warning "Backend not running or already stopped"

# Stop frontend (npm/react)
print_status "Stopping frontend server..."
pkill -f "react-scripts start" || print_warning "Frontend not running or already stopped"
pkill -f "node.*frontend" || true

# Wait a moment for processes to stop
sleep 2

# Step 2: Ensure PostgreSQL is running
echo ""
echo "Step 2: Checking PostgreSQL..."
echo "--------------------------------------"

if pg_isready -q 2>/dev/null; then
    print_status "PostgreSQL is already running"
else
    print_warning "PostgreSQL is not running. Starting it..."

    OS_TYPE="$(uname -s)"
    PG_STARTED=false

    if [ "$OS_TYPE" = "Darwin" ]; then
        # macOS: start via brew services (try 17, 16, 15 in order)
        for pg_ver in 17 16 15; do
            if brew list "postgresql@$pg_ver" &>/dev/null; then
                print_status "Starting PostgreSQL @$pg_ver via Homebrew..."
                brew services start "postgresql@$pg_ver" 2>/dev/null || true
                PG_STARTED=true
                break
            fi
        done
        # Fallback: plain "postgresql" formula
        if [ "$PG_STARTED" = false ] && brew list postgresql &>/dev/null; then
            print_status "Starting PostgreSQL via Homebrew..."
            brew services start postgresql 2>/dev/null || true
            PG_STARTED=true
        fi
    else
        # Linux: start via systemctl
        if command -v systemctl &>/dev/null; then
            print_status "Starting PostgreSQL via systemctl..."
            sudo systemctl start postgresql 2>/dev/null || true
            PG_STARTED=true
        fi
    fi

    # Fallback: pg_ctl with auto-detected data dir
    if [ "$PG_STARTED" = false ]; then
        PG_DATA_DIR=""
        for d in /usr/local/var/postgres /opt/homebrew/var/postgres /var/lib/postgresql/*/main; do
            if [ -d "$d" ]; then
                PG_DATA_DIR="$d"
                break
            fi
        done
        if [ -n "$PG_DATA_DIR" ]; then
            print_status "Starting PostgreSQL via pg_ctl (data dir: $PG_DATA_DIR)..."
            pg_ctl -D "$PG_DATA_DIR" -l /tmp/pg_restart.log start 2>/dev/null || true
            PG_STARTED=true
        fi
    fi

    # Wait for PostgreSQL to be ready
    sleep 3
    if pg_isready -q 2>/dev/null; then
        print_status "PostgreSQL started successfully"
    else
        print_error "Could not start PostgreSQL. Please start it manually and run this script again."
        exit 1
    fi
fi

# Step 3: Run database migrations (if any pending)
echo ""
echo "Step 3: Running database migrations..."
echo "--------------------------------------"

cd backend
source ../.venv/bin/activate || source venv/bin/activate
if alembic upgrade head 2>&1 | grep -q "overlaps"; then
    print_warning "Migration conflict detected, database is already up to date"
elif alembic upgrade head; then
    print_status "Database migrations completed"
else
    print_warning "Migration check completed (may already be at head)"
fi
cd ..

# Step 4: Start backend
echo ""
echo "Step 4: Starting backend server..."
echo "--------------------------------------"

cd backend
source ../.venv/bin/activate || source venv/bin/activate
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
print_status "Backend started (PID: $BACKEND_PID)"
cd ..

# Wait for backend to be ready
sleep 3

# Step 5: Start frontend
echo ""
echo "Step 5: Starting frontend server..."
echo "--------------------------------------"

cd frontend
nohup npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
print_status "Frontend started (PID: $FRONTEND_PID)"
cd ..

# Wait for frontend to be ready
sleep 3

echo ""
echo "======================================"
echo "Application Restarted Successfully!"
echo "======================================"
echo ""
echo "Backend API: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Frontend: http://localhost:3000"
echo ""
echo "Backend PID: $BACKEND_PID (logs: backend.log)"
echo "Frontend PID: $FRONTEND_PID (logs: frontend.log)"
echo ""
echo "To view logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo "To stop servers:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo "  or run: pkill -f 'uvicorn app.main:app' && pkill -f 'react-scripts start'"
echo ""

# Made with Bob