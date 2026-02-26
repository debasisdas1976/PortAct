#!/usr/bin/env bash
#
# PortAct – Update Script (for native installs)
# Pulls the latest code, updates dependencies, runs migrations, and restarts.
#
# Usage:  ./update.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || pwd)"
PROJECT_DIR="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"

# Fallback venv location
if [[ ! -d "$VENV_DIR" ]]; then
    VENV_DIR="$PROJECT_DIR/.venv"
fi

# ── Colors ───────────────────────────────────────────────────────────────────

BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step() {
    local step_num="$1" total="$2" text="$3"
    echo ""
    echo -e "${BLUE}${BOLD}[$step_num/$total]${NC} ${BOLD}$text${NC}"
    echo -e "${BLUE}$(printf '─%.0s' $(seq 1 50))${NC}"
}
print_success() { echo -e "  ${GREEN}✓${NC} $1"; }
print_warning() { echo -e "  ${YELLOW}!${NC} $1"; }
print_error()   { echo -e "  ${RED}✗${NC} $1"; }
print_info()    { echo -e "  ${CYAN}→${NC} $1"; }
fail()          { print_error "$1"; exit 1; }

# ── Pre-flight checks ────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}======================================"
echo "  PortAct – Updater"
echo -e "======================================${NC}"
echo ""

[[ -d "$BACKEND_DIR" ]] && [[ -d "$FRONTEND_DIR" ]] \
    || fail "This script must be run from the PortAct project root."

[[ -d "$VENV_DIR" ]] \
    || fail "Python virtual environment not found at $VENV_DIR. Run install.sh first."

OLD_VERSION=$(cat "$PROJECT_DIR/VERSION" 2>/dev/null || echo "unknown")
print_info "Current version: $OLD_VERSION"

TOTAL_STEPS=8
STEP=1

BACKUP_DIR="$PROJECT_DIR/backups"
DB_NAME="portact_db"
DB_USER="portact_user"
DB_PASS="portact_password"
DB_HOST="localhost"
DB_PORT="5432"

# Read DB connection from backend .env if it exists
if [[ -f "$BACKEND_DIR/.env" ]]; then
    DB_URL=$(grep -E "^DATABASE_URL=" "$BACKEND_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2-)
    if [[ -n "$DB_URL" ]]; then
        DB_USER_PARSED=$(echo "$DB_URL" | sed -n 's|postgresql://\([^:]*\):.*|\1|p')
        DB_PASS_PARSED=$(echo "$DB_URL" | sed -n 's|postgresql://[^:]*:\([^@]*\)@.*|\1|p')
        DB_HOST_PARSED=$(echo "$DB_URL" | sed -n 's|.*@\([^:]*\):.*|\1|p')
        DB_PORT_PARSED=$(echo "$DB_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
        DB_NAME_PARSED=$(echo "$DB_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')
        [[ -n "$DB_USER_PARSED" ]] && DB_USER="$DB_USER_PARSED"
        [[ -n "$DB_PASS_PARSED" ]] && DB_PASS="$DB_PASS_PARSED"
        [[ -n "$DB_HOST_PARSED" ]] && DB_HOST="$DB_HOST_PARSED"
        [[ -n "$DB_PORT_PARSED" ]] && DB_PORT="$DB_PORT_PARSED"
        [[ -n "$DB_NAME_PARSED" ]] && DB_NAME="$DB_NAME_PARSED"
    fi
fi

# ── Step 1: Stop running servers ─────────────────────────────────────────────

print_step $STEP $TOTAL_STEPS "Stopping running servers"
pkill -f "uvicorn app.main:app" 2>/dev/null && print_success "Backend stopped" || print_warning "Backend was not running"
pkill -f "react-scripts start" 2>/dev/null && print_success "Frontend stopped" || print_warning "Frontend was not running"
pkill -f "node.*frontend" 2>/dev/null || true
sleep 2
((STEP++))

# ── Step 2: Create database backup ──────────────────────────────────────────

print_step $STEP $TOTAL_STEPS "Creating database backup"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/portact_pre_update_${TIMESTAMP}.sql.gz"

if command -v pg_dump &>/dev/null; then
    if PGPASSWORD="$DB_PASS" pg_dump \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        --no-owner --no-acl "$DB_NAME" 2>/dev/null | gzip > "$BACKUP_FILE"; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        print_success "Backup created: $BACKUP_FILE ($BACKUP_SIZE)"
    else
        rm -f "$BACKUP_FILE"
        print_warning "Could not create backup (continuing anyway)"
    fi
else
    print_warning "pg_dump not found — skipping backup"
fi
((STEP++))

# ── Step 3: Pull latest code ─────────────────────────────────────────────────

print_step $STEP $TOTAL_STEPS "Pulling latest code"
cd "$PROJECT_DIR"
if git pull --ff-only 2>/dev/null; then
    print_success "Code updated"
else
    print_warning "Could not fast-forward. Trying merge..."
    if git pull; then
        print_success "Code updated (merged)"
    else
        fail "Git pull failed. Please resolve conflicts manually and re-run."
    fi
fi

NEW_VERSION=$(cat "$PROJECT_DIR/VERSION" 2>/dev/null || echo "unknown")
print_info "New version: $NEW_VERSION"
((STEP++))

# ── Step 4: Update backend dependencies ──────────────────────────────────────

print_step $STEP $TOTAL_STEPS "Updating backend dependencies"
cd "$BACKEND_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate" || fail "Could not activate Python venv at $VENV_DIR"
pip install --upgrade pip -q 2>&1 | tail -1 || true
if pip install -r requirements.txt -q; then
    print_success "Backend packages updated"
else
    print_warning "Some backend packages may not have updated cleanly"
fi
((STEP++))

# ── Step 5: Run database migrations ──────────────────────────────────────────

print_step $STEP $TOTAL_STEPS "Running database migrations"
cd "$BACKEND_DIR"
if alembic upgrade head 2>&1; then
    print_success "Database migrations applied"
else
    print_warning "Migration check completed (may already be at head)"
fi
((STEP++))

# ── Step 6: Apply post-migration data fixes ──────────────────────────────────

print_step $STEP $TOTAL_STEPS "Applying data fixes"
cd "$BACKEND_DIR"
if [[ -f "scripts/post_migrate_fix.py" ]]; then
    if python scripts/post_migrate_fix.py 2>&1; then
        print_success "Data fixes applied"
    else
        print_warning "Data fix script had issues (non-critical)"
    fi
else
    print_success "No data fixes needed"
fi
((STEP++))

# ── Step 7: Update frontend dependencies ─────────────────────────────────────

print_step $STEP $TOTAL_STEPS "Updating frontend dependencies"
cd "$FRONTEND_DIR"
if npm install 2>&1 | tail -5; then
    print_success "Frontend packages updated"
else
    print_warning "Some frontend packages may not have updated cleanly"
fi
((STEP++))

# ── Step 8: Restart application ──────────────────────────────────────────────

print_step $STEP $TOTAL_STEPS "Restarting application"

cd "$BACKEND_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/backend.log" 2>&1 &
print_success "Backend started (PID: $!)"

sleep 3

cd "$FRONTEND_DIR"
BROWSER=none nohup npm start > "$PROJECT_DIR/frontend.log" 2>&1 &
print_success "Frontend started (PID: $!)"

deactivate 2>/dev/null || true

# ── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}======================================"
echo -e "  PortAct updated: $OLD_VERSION → $NEW_VERSION"
echo -e "======================================${NC}"
echo ""
echo -e "  ${BOLD}Open in your browser:${NC}"
echo -e "    ${CYAN}http://localhost:3000${NC}"
echo ""
echo -e "  ${BOLD}API docs:${NC} ${CYAN}http://localhost:8000/docs${NC}"
echo ""
