#!/bin/bash

# PortAct - Application Restart Script
# This script cleanly stops and restarts both backend and frontend

set -e

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

# Step 2: Run database migrations (if any pending)
echo ""
echo "Step 2: Running database migrations..."
echo "--------------------------------------"

cd backend
source ../.venv/bin/activate || source venv/bin/activate
alembic upgrade head
print_status "Database migrations completed"
cd ..

# Step 3: Start backend
echo ""
echo "Step 3: Starting backend server..."
echo "--------------------------------------"

cd backend
source ../.venv/bin/activate || source venv/bin/activate
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
print_status "Backend started (PID: $BACKEND_PID)"
cd ..

# Wait for backend to be ready
sleep 3

# Step 4: Start frontend
echo ""
echo "Step 4: Starting frontend server..."
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