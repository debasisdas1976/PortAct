#!/usr/bin/env bash
#
# PortAct — Restart Script
# Cleanly stops everything, runs pending migrations, and starts fresh.
#
# Usage:  ./scripts/restart_app.sh
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Locate venv (prefer backend/venv, fallback to project-root .venv)
VENV_DIR="$BACKEND_DIR/venv"
[[ ! -d "$VENV_DIR" ]] && VENV_DIR="$PROJECT_DIR/.venv"
[[ ! -d "$VENV_DIR" ]] && { echo "ERROR: Python venv not found. Run install.sh first."; exit 1; }

# ── Colors ───────────────────────────────────────────────────────────────────
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'
print_success() { echo -e "  ${GREEN}✓${NC} $1"; }
print_warning() { echo -e "  ${YELLOW}!${NC} $1"; }
print_error()   { echo -e "  ${RED}✗${NC} $1"; }
print_info()    { echo -e "  ${CYAN}→${NC} $1"; }

echo ""
echo -e "${BOLD}======================================"
echo    "  PortAct — Restart"
echo -e "======================================${NC}"
echo ""

# ── Helper: kill everything on a port, wait until it's free ─────────────────
kill_port() {
    local port="$1"
    local pids
    pids="$(lsof -ti :"$port" 2>/dev/null || true)"
    [[ -z "$pids" ]] && return 0

    # Graceful SIGTERM first
    echo "$pids" | xargs kill 2>/dev/null || true
    local waited=0
    while lsof -ti :"$port" &>/dev/null && [[ $waited -lt 6 ]]; do
        sleep 1; ((waited++))
    done

    # Force-kill any stragglers
    pids="$(lsof -ti :"$port" 2>/dev/null || true)"
    [[ -n "$pids" ]] && echo "$pids" | xargs kill -9 2>/dev/null || true

    # Final confirmation
    waited=0
    while lsof -ti :"$port" &>/dev/null && [[ $waited -lt 4 ]]; do
        sleep 1; ((waited++))
    done
    if lsof -ti :"$port" &>/dev/null; then
        print_error "Port $port is still in use! Cannot continue safely."
        return 1
    fi
    return 0
}

# ── Helper: poll a URL until it responds ─────────────────────────────────────
wait_for_url() {
    local url="$1" max="$2" waited=0
    while ! curl -sf "$url" &>/dev/null; do
        sleep 1; ((waited++))
        [[ $waited -ge $max ]] && return 1
    done
    return 0
}

# ── Helper: wait for a port to open ──────────────────────────────────────────
wait_for_port_open() {
    local port="$1" max="$2" waited=0
    while ! lsof -ti :"$port" &>/dev/null; do
        sleep 1; ((waited++))
        [[ $waited -ge $max ]] && return 1
    done
    return 0
}

# ── Step 1: Stop all existing processes ──────────────────────────────────────
echo "Step 1: Stopping existing processes..."

pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "react-scripts start"  2>/dev/null || true
pkill -f "node.*portact"        2>/dev/null || true

# Kill by port — catches --reload child processes and anything pkill missed
kill_port 8000 && print_success "Port 8000 is free" || exit 1
kill_port 3000 && print_success "Port 3000 is free" || exit 1

# ── Step 2: Ensure PostgreSQL is running ─────────────────────────────────────
echo ""
echo "Step 2: Checking PostgreSQL..."

if ! pg_isready -q 2>/dev/null; then
    print_warning "PostgreSQL not ready — attempting to start..."
    OS_TYPE="$(uname -s)"
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        started=false
        for ver in 17 16 15; do
            if brew list "postgresql@$ver" &>/dev/null 2>&1; then
                brew services start "postgresql@$ver" 2>/dev/null || true
                started=true; break
            fi
        done
        if [[ "$started" == false ]] && brew list postgresql &>/dev/null 2>&1; then
            brew services start postgresql 2>/dev/null || true
        fi
    else
        sudo systemctl start postgresql 2>/dev/null || true
    fi

    pg_waited=0
    while ! pg_isready -q 2>/dev/null && [[ $pg_waited -lt 15 ]]; do
        sleep 1; ((pg_waited++))
    done
    pg_isready -q 2>/dev/null || { print_error "PostgreSQL did not start. Please start it manually."; exit 1; }
fi
print_success "PostgreSQL is ready"

# ── Step 3: Run pending migrations ───────────────────────────────────────────
echo ""
echo "Step 3: Running database migrations..."

cd "$BACKEND_DIR"
source "$VENV_DIR/bin/activate" || { print_error "Cannot activate venv at $VENV_DIR"; exit 1; }

MIGRATION_OUT="$(alembic upgrade head 2>&1)"
MIGRATION_STATUS=$?
APPLIED="$(echo "$MIGRATION_OUT" | grep -c "Running upgrade" || true)"

if [[ $MIGRATION_STATUS -ne 0 ]]; then
    print_error "Migration failed:"
    echo "$MIGRATION_OUT"
    exit 1
elif [[ "$APPLIED" -gt 0 ]]; then
    print_success "$APPLIED migration(s) applied"
else
    print_success "Database already at latest migration"
fi

# ── Step 4: Start backend ─────────────────────────────────────────────────────
echo ""
echo "Step 4: Starting backend..."

cd "$BACKEND_DIR"
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 \
    > "$PROJECT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
print_info "Backend PID: $BACKEND_PID"

# Poll /health — waits for the full lifespan startup to complete (up to 45s)
print_info "Waiting for backend to be ready..."
if wait_for_url "http://localhost:8000/health" 45; then
    print_success "Backend is healthy"
else
    print_error "Backend did not respond within 45s — check backend.log:"
    echo ""
    tail -30 "$PROJECT_DIR/backend.log" 2>/dev/null | cat
    exit 1
fi

# ── Step 5: Start frontend ────────────────────────────────────────────────────
echo ""
echo "Step 5: Starting frontend..."

cd "$FRONTEND_DIR"
BROWSER=none nohup npm start > "$PROJECT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
print_info "Frontend PID: $FRONTEND_PID"

# Webpack compilation takes 20-60 seconds; wait up to 90s
print_info "Waiting for frontend to compile (up to 90s)..."
if wait_for_port_open 3000 90; then
    print_success "Frontend is ready"
else
    print_warning "Frontend is taking longer than expected — check frontend.log"
fi

deactivate 2>/dev/null || true
cd "$PROJECT_DIR"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}======================================"
echo    "  PortAct is running!"
echo -e "======================================${NC}"
echo ""
echo -e "  Frontend:  ${CYAN}http://localhost:3000${NC}"
echo -e "  API:       ${CYAN}http://localhost:8000${NC}"
echo -e "  API Docs:  ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo    "  Logs:  tail -f backend.log  |  tail -f frontend.log"
echo ""
