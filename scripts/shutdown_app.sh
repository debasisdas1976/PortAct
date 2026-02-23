#!/bin/bash

# PortAct - Application Shutdown Script
# This script cleanly stops both backend and frontend servers

set -e

# Resolve project root (scripts live in <project>/scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "======================================"
echo "PortAct Application Shutdown"
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

# Step 1: Stop Backend Server
echo "Step 1: Stopping backend server..."
echo "-----------------------------------"

# Find and kill uvicorn processes
BACKEND_PIDS=$(pgrep -f "uvicorn app.main:app" || true)

if [ -z "$BACKEND_PIDS" ]; then
    print_warning "Backend server not running"
else
    for PID in $BACKEND_PIDS; do
        print_status "Stopping backend process (PID: $PID)..."
        kill $PID 2>/dev/null || true
    done
    
    # Wait for graceful shutdown
    sleep 2
    
    # Force kill if still running
    BACKEND_PIDS=$(pgrep -f "uvicorn app.main:app" || true)
    if [ ! -z "$BACKEND_PIDS" ]; then
        print_warning "Force stopping backend processes..."
        for PID in $BACKEND_PIDS; do
            kill -9 $PID 2>/dev/null || true
        done
    fi
    
    print_status "Backend server stopped"
fi

# Step 2: Stop Frontend Server
echo ""
echo "Step 2: Stopping frontend server..."
echo "-----------------------------------"

# Find and kill React/npm processes
FRONTEND_PIDS=$(pgrep -f "react-scripts start" || true)

if [ -z "$FRONTEND_PIDS" ]; then
    print_warning "Frontend server not running"
else
    for PID in $FRONTEND_PIDS; do
        print_status "Stopping frontend process (PID: $PID)..."
        kill $PID 2>/dev/null || true
    done
    
    # Wait for graceful shutdown
    sleep 2
    
    # Force kill if still running
    FRONTEND_PIDS=$(pgrep -f "react-scripts start" || true)
    if [ ! -z "$FRONTEND_PIDS" ]; then
        print_warning "Force stopping frontend processes..."
        for PID in $FRONTEND_PIDS; do
            kill -9 $PID 2>/dev/null || true
        done
    fi
    
    print_status "Frontend server stopped"
fi

# Also kill any node processes related to frontend
NODE_FRONTEND_PIDS=$(pgrep -f "node.*frontend" || true)
if [ ! -z "$NODE_FRONTEND_PIDS" ]; then
    print_status "Cleaning up additional frontend processes..."
    for PID in $NODE_FRONTEND_PIDS; do
        kill $PID 2>/dev/null || true
    done
fi

# Step 3: Stop PostgreSQL database
echo ""
echo "Step 3: Stopping PostgreSQL database..."
echo "-----------------------------------"

if pg_isready -q 2>/dev/null; then
    OS_TYPE="$(uname -s)"
    PG_STOPPED=false

    if [ "$OS_TYPE" = "Darwin" ]; then
        # macOS: stop via brew services (try 17, 16, 15 in order)
        for pg_ver in 17 16 15; do
            if brew list "postgresql@$pg_ver" &>/dev/null; then
                print_status "Stopping PostgreSQL @$pg_ver via Homebrew..."
                brew services stop "postgresql@$pg_ver" 2>/dev/null || true
                PG_STOPPED=true
                break
            fi
        done
        # Fallback: if installed as plain "postgresql" formula
        if [ "$PG_STOPPED" = false ] && brew list postgresql &>/dev/null; then
            print_status "Stopping PostgreSQL via Homebrew..."
            brew services stop postgresql 2>/dev/null || true
            PG_STOPPED=true
        fi
    else
        # Linux: stop via systemctl
        if command -v systemctl &>/dev/null; then
            print_status "Stopping PostgreSQL via systemctl..."
            sudo systemctl stop postgresql 2>/dev/null || true
            PG_STOPPED=true
        fi
    fi

    # Fallback: use pg_ctl directly if brew/systemctl didn't work
    if [ "$PG_STOPPED" = false ]; then
        PG_DATA_DIR=""
        # Try to detect data directory from running postgres process
        PG_DATA_DIR=$(ps aux | grep '[p]ostgres.*-D' | head -1 | sed -n 's/.*-D \([^ ]*\).*/\1/p' || true)
        if [ -n "$PG_DATA_DIR" ] && [ -d "$PG_DATA_DIR" ]; then
            print_status "Stopping PostgreSQL via pg_ctl (data dir: $PG_DATA_DIR)..."
            pg_ctl -D "$PG_DATA_DIR" stop -m fast 2>/dev/null || true
            PG_STOPPED=true
        fi
    fi

    # Verify shutdown
    sleep 2
    if pg_isready -q 2>/dev/null; then
        print_warning "PostgreSQL is still running — you may need to stop it manually"
    else
        print_status "PostgreSQL stopped gracefully"
    fi
else
    print_warning "PostgreSQL is not running"
fi

# Step 4: Verify shutdown
echo ""
echo "Step 4: Verifying shutdown..."
echo "-----------------------------------"

sleep 1

REMAINING_BACKEND=$(pgrep -f "uvicorn app.main:app" || true)
REMAINING_FRONTEND=$(pgrep -f "react-scripts start" || true)

if [ -z "$REMAINING_BACKEND" ] && [ -z "$REMAINING_FRONTEND" ]; then
    print_status "All application processes stopped successfully"
else
    if [ ! -z "$REMAINING_BACKEND" ]; then
        print_error "Some backend processes still running (PIDs: $REMAINING_BACKEND)"
    fi
    if [ ! -z "$REMAINING_FRONTEND" ]; then
        print_error "Some frontend processes still running (PIDs: $REMAINING_FRONTEND)"
    fi
    print_warning "You may need to manually kill remaining processes"
fi

# Step 5: Clean up log files (optional)
echo ""
echo "Step 5: Log file cleanup..."
echo "-----------------------------------"

if [ -f "backend.log" ] || [ -f "frontend.log" ]; then
    read -p "Do you want to archive log files? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        if [ -f "backend.log" ]; then
            mv backend.log "backend_${TIMESTAMP}.log"
            print_status "Backend log archived as backend_${TIMESTAMP}.log"
        fi
        if [ -f "frontend.log" ]; then
            mv frontend.log "frontend_${TIMESTAMP}.log"
            print_status "Frontend log archived as frontend_${TIMESTAMP}.log"
        fi
    else
        print_status "Log files kept as is"
    fi
else
    print_status "No log files to clean up"
fi

echo ""
echo "======================================"
echo "Application Shutdown Complete!"
echo "======================================"
echo ""
echo "To start the application again, run:"
echo "  ./scripts/run_app.sh     (fresh start with setup)"
echo "  ./scripts/restart_app.sh (quick restart)"
echo ""

# Made with Bob