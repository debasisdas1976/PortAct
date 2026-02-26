#!/usr/bin/env bash
#
# PortAct — Migration Script
# Safely upgrades an existing PortAct installation to the latest version.
#
# What this script does:
#   1. Detects your installation type (Docker or native)
#   2. Creates a database backup
#   3. Pulls the latest code
#   4. Updates dependencies
#   5. Runs database migrations
#   6. Applies post-migration data fixes
#   7. Verifies everything works
#   8. Restarts the application
#
# Usage:
#   ./scripts/migrate.sh                # Full migration
#   ./scripts/migrate.sh --backup-only  # Just create a backup, don't migrate
#   ./scripts/migrate.sh --no-restart   # Migrate but don't restart servers
#   ./scripts/migrate.sh --help         # Show usage
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKUP_DIR="$PROJECT_DIR/backups"
VENV_DIR="$BACKEND_DIR/venv"

# Fallback venv location
if [[ ! -d "$VENV_DIR" ]]; then
    VENV_DIR="$PROJECT_DIR/.venv"
fi

# ── Defaults ────────────────────────────────────────────────────────────────

DB_NAME="${POSTGRES_DB:-portact_db}"
DB_USER="${POSTGRES_USER:-portact_user}"
DB_PASS="${POSTGRES_PASSWORD:-portact_password}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

BACKUP_ONLY=false
NO_RESTART=false

TOTAL_STEPS=8
STEP=0

# ── Colors ──────────────────────────────────────────────────────────────────

BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

print_header() {
    local width=60
    echo ""
    echo -e "${MAGENTA}$(printf '═%.0s' $(seq 1 $width))${NC}"
    echo -e "${MAGENTA}  ${BOLD}$1${NC}"
    echo -e "${MAGENTA}$(printf '═%.0s' $(seq 1 $width))${NC}"
    echo ""
}

print_step() {
    ((STEP++))
    echo ""
    echo -e "${BLUE}${BOLD}[$STEP/$TOTAL_STEPS]${NC} ${BOLD}$1${NC}"
    echo -e "${BLUE}$(printf '─%.0s' $(seq 1 50))${NC}"
}

print_success() { echo -e "  ${GREEN}✓${NC} $1"; }
print_warning() { echo -e "  ${YELLOW}!${NC} $1"; }
print_error()   { echo -e "  ${RED}✗${NC} $1"; }
print_info()    { echo -e "  ${CYAN}→${NC} $1"; }
fail()          { print_error "$1"; echo ""; exit 1; }

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Safely migrates an existing PortAct installation to the latest version."
    echo ""
    echo "Options:"
    echo "  --backup-only    Create a database backup and exit"
    echo "  --no-restart     Run migration but don't restart servers"
    echo "  --help, -h       Show this help message"
    echo ""
    echo "For the full migration guide, see: MIGRATION.md"
}

# ── Argument Parsing ────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backup-only) BACKUP_ONLY=true; shift ;;
        --no-restart)  NO_RESTART=true; shift ;;
        --help|-h)     show_usage; exit 0 ;;
        *)             print_warning "Unknown option: $1"; shift ;;
    esac
done

# ── Pre-flight ──────────────────────────────────────────────────────────────

print_header "PortAct — Migration Tool"

[[ -d "$BACKEND_DIR" ]] && [[ -d "$FRONTEND_DIR" ]] \
    || fail "This script must be run from the PortAct project root."

OLD_VERSION=$(cat "$PROJECT_DIR/VERSION" 2>/dev/null || echo "unknown")
print_info "Current version: ${BOLD}$OLD_VERSION${NC}"

# Read DB connection from backend .env if it exists
if [[ -f "$BACKEND_DIR/.env" ]]; then
    # Extract DATABASE_URL from .env
    DB_URL=$(grep -E "^DATABASE_URL=" "$BACKEND_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2-)
    if [[ -n "$DB_URL" ]]; then
        # Parse postgresql://user:pass@host:port/dbname
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

        print_info "Database: ${DB_NAME} @ ${DB_HOST}:${DB_PORT}"
    fi
fi

# ── Step 1: Stop running servers ────────────────────────────────────────────

print_step "Stopping running servers"

pkill -f "uvicorn app.main:app" 2>/dev/null && print_success "Backend stopped" \
    || print_warning "Backend was not running"
pkill -f "react-scripts start" 2>/dev/null && print_success "Frontend stopped" \
    || print_warning "Frontend was not running"
pkill -f "node.*frontend" 2>/dev/null || true
sleep 2

# ── Step 2: Create database backup ─────────────────────────────────────────

print_step "Creating database backup"

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/portact_pre_migrate_${TIMESTAMP}.sql.gz"

if command -v pg_dump &>/dev/null; then
    if PGPASSWORD="$DB_PASS" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        --no-owner --no-acl \
        "$DB_NAME" 2>/dev/null | gzip > "$BACKUP_FILE"; then

        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        print_success "Backup created: $BACKUP_FILE ($BACKUP_SIZE)"
    else
        rm -f "$BACKUP_FILE"
        print_warning "Could not create backup (pg_dump failed)"
        print_warning "Continuing without backup — make sure you have one!"
    fi
else
    print_warning "pg_dump not found — skipping backup"
    print_warning "Make sure you have a recent backup before proceeding!"
fi

if [[ "$BACKUP_ONLY" == true ]]; then
    echo ""
    print_success "Backup complete. Exiting (--backup-only mode)."
    echo ""
    exit 0
fi

# ── Step 3: Pull latest code ───────────────────────────────────────────────

print_step "Pulling latest code from GitHub"

cd "$PROJECT_DIR"
if git pull --ff-only 2>/dev/null; then
    print_success "Code updated"
elif git pull 2>/dev/null; then
    print_success "Code updated (merged)"
else
    fail "Git pull failed. Please resolve conflicts manually and re-run."
fi

NEW_VERSION=$(cat "$PROJECT_DIR/VERSION" 2>/dev/null || echo "unknown")
print_info "New version: ${BOLD}$NEW_VERSION${NC}"

# ── Step 4: Update backend dependencies ─────────────────────────────────────

print_step "Updating backend dependencies"

if [[ ! -d "$VENV_DIR" ]]; then
    fail "Python virtual environment not found at $VENV_DIR. Run install.sh first."
fi

cd "$BACKEND_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate" || fail "Could not activate Python venv"

pip install --upgrade pip -q 2>&1 | tail -1 || true
if pip install -r requirements.txt -q 2>&1; then
    print_success "Backend packages updated"
else
    print_warning "Some backend packages may not have updated cleanly"
fi

# ── Step 5: Run database migrations ─────────────────────────────────────────

print_step "Running database migrations"

cd "$BACKEND_DIR"

# Show current migration status
CURRENT_REV=$(alembic current 2>&1 | grep -oE '[a-f0-9]{12}' | head -1 || echo "none")
print_info "Current migration: $CURRENT_REV"

# Run migrations
MIGRATION_OUTPUT=$(alembic upgrade head 2>&1)
MIGRATION_EXIT=$?

if [[ $MIGRATION_EXIT -eq 0 ]]; then
    # Count how many migrations were applied
    APPLIED=$(echo "$MIGRATION_OUTPUT" | grep -c "Running upgrade" || echo "0")
    if [[ "$APPLIED" -gt 0 ]]; then
        print_success "$APPLIED migration(s) applied"
    else
        print_success "Database already up to date"
    fi
else
    echo "$MIGRATION_OUTPUT"
    echo ""
    fail "Migration failed! Your backup is at: $BACKUP_FILE"
fi

NEW_REV=$(alembic current 2>&1 | grep -oE '[a-f0-9]{12}' | head -1 || echo "unknown")
print_info "New migration: $NEW_REV"

# ── Step 6: Apply post-migration data fixes ─────────────────────────────────

print_step "Applying post-migration data fixes"

cd "$BACKEND_DIR"
if [[ -f "scripts/post_migrate_fix.py" ]]; then
    if python scripts/post_migrate_fix.py 2>&1; then
        print_success "Data fixes applied"
    else
        print_warning "Data fix script had issues (non-critical — the app should still work)"
    fi
else
    print_warning "post_migrate_fix.py not found — skipping data fixes"
fi

# ── Step 7: Update frontend dependencies ────────────────────────────────────

print_step "Updating frontend dependencies"

cd "$FRONTEND_DIR"
if npm install 2>&1 | tail -3; then
    print_success "Frontend packages updated"
else
    print_warning "Some frontend packages may not have updated cleanly"
fi

# ── Step 8: Restart and verify ──────────────────────────────────────────────

print_step "Restarting and verifying"

if [[ "$NO_RESTART" == true ]]; then
    print_info "Skipping restart (--no-restart was specified)"
else
    cd "$BACKEND_DIR"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    print_success "Backend started (PID: $BACKEND_PID)"

    # Wait for backend to be ready
    print_info "Waiting for backend to start..."
    RETRIES=0
    while [[ $RETRIES -lt 30 ]]; do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            break
        fi
        sleep 1
        ((RETRIES++))
    done

    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        HEALTH=$(curl -s http://localhost:8000/health)
        print_success "Backend is healthy: $HEALTH"
    else
        print_warning "Backend did not respond to health check within 30s"
        print_warning "Check backend.log for details"
    fi

    cd "$FRONTEND_DIR"
    BROWSER=none nohup npm start > "$PROJECT_DIR/frontend.log" 2>&1 &
    print_success "Frontend started (PID: $!)"
fi

deactivate 2>/dev/null || true

# ── Summary ─────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}$(printf '═%.0s' $(seq 1 60))${NC}"
echo -e "${GREEN}  ${BOLD}PortAct Migration Complete!${NC}"
echo -e "${GREEN}$(printf '═%.0s' $(seq 1 60))${NC}"
echo ""
echo -e "  ${BOLD}Version:${NC}  $OLD_VERSION → $NEW_VERSION"

if [[ -f "$BACKUP_FILE" ]]; then
    echo -e "  ${BOLD}Backup:${NC}   $BACKUP_FILE"
fi

echo ""

if [[ "$NO_RESTART" != true ]]; then
    echo -e "  ${BOLD}Open in your browser:${NC}"
    echo -e "    ${CYAN}http://localhost:3000${NC}"
    echo ""
    echo -e "  ${BOLD}API docs:${NC} ${CYAN}http://localhost:8000/docs${NC}"
fi

echo ""
echo -e "  ${BOLD}If something goes wrong, restore from backup:${NC}"

if [[ -f "$BACKUP_FILE" ]]; then
    echo -e "    gunzip -c $BACKUP_FILE | psql -h $DB_HOST -U $DB_USER $DB_NAME"
fi

echo ""
echo -e "${GREEN}$(printf '═%.0s' $(seq 1 60))${NC}"
echo ""
