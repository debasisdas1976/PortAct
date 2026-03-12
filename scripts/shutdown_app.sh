#!/usr/bin/env bash
#
# PortAct — Shutdown Script
# Cleanly stops backend, frontend, and (optionally) PostgreSQL.
#
# Usage:
#   ./scripts/shutdown_app.sh           # stop backend + frontend
#   ./scripts/shutdown_app.sh --with-db # also stop PostgreSQL
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

WITH_DB=false
[[ "$1" == "--with-db" ]] && WITH_DB=true

# ── Colors ───────────────────────────────────────────────────────────────────
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
print_success() { echo -e "  ${GREEN}✓${NC} $1"; }
print_warning() { echo -e "  ${YELLOW}!${NC} $1"; }
print_error()   { echo -e "  ${RED}✗${NC} $1"; }

echo ""
echo -e "${BOLD}======================================"
echo    "  PortAct — Shutdown"
echo -e "======================================${NC}"
echo ""

# ── Helper: kill everything on a port, wait until free ───────────────────────
kill_port() {
    local port="$1" label="$2"
    local pids
    pids="$(lsof -ti :"$port" 2>/dev/null || true)"
    if [[ -z "$pids" ]]; then
        print_warning "$label not running on port $port"
        return 0
    fi

    # Graceful SIGTERM
    echo "$pids" | xargs kill 2>/dev/null || true
    local waited=0
    while lsof -ti :"$port" &>/dev/null && [[ $waited -lt 6 ]]; do
        sleep 1; ((waited++))
    done

    # Force-kill any stragglers
    pids="$(lsof -ti :"$port" 2>/dev/null || true)"
    [[ -n "$pids" ]] && echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1

    if lsof -ti :"$port" &>/dev/null; then
        print_error "$label (port $port) could not be stopped"
        return 1
    fi
    print_success "$label stopped (port $port cleared)"
    return 0
}

# ── Step 1: Stop backend ──────────────────────────────────────────────────────
echo "Step 1: Stopping backend..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
kill_port 8000 "Backend"

# ── Step 2: Stop frontend ─────────────────────────────────────────────────────
echo ""
echo "Step 2: Stopping frontend..."
pkill -f "react-scripts start" 2>/dev/null || true
pkill -f "node.*portact"       2>/dev/null || true
kill_port 3000 "Frontend"

# ── Step 3: Stop PostgreSQL (only if --with-db) ───────────────────────────────
if [[ "$WITH_DB" == true ]]; then
    echo ""
    echo "Step 3: Stopping PostgreSQL..."
    if ! pg_isready -q 2>/dev/null; then
        print_warning "PostgreSQL is not running"
    else
        OS_TYPE="$(uname -s)"
        stopped=false
        if [[ "$OS_TYPE" == "Darwin" ]]; then
            for ver in 17 16 15; do
                if brew list "postgresql@$ver" &>/dev/null 2>&1; then
                    brew services stop "postgresql@$ver" 2>/dev/null || true
                    stopped=true; break
                fi
            done
            if [[ "$stopped" == false ]] && brew list postgresql &>/dev/null 2>&1; then
                brew services stop postgresql 2>/dev/null || true
            fi
        else
            sudo systemctl stop postgresql 2>/dev/null || true
        fi

        sleep 2
        if pg_isready -q 2>/dev/null; then
            print_warning "PostgreSQL is still running (may need manual stop)"
        else
            print_success "PostgreSQL stopped"
        fi
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}======================================"
echo    "  PortAct is shut down"
echo -e "======================================${NC}"
echo ""
echo    "  To restart:  ./scripts/restart_app.sh"
echo ""
