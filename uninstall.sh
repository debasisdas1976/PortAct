#!/usr/bin/env bash
#
# PortAct – Uninstall Script
# Stops the application, removes the database, and deletes all project files.
#
# Usage:
#   ./uninstall.sh           # Interactive uninstall (asks for confirmation)
#   ./uninstall.sh --yes     # Skip confirmation prompts
#   ./uninstall.sh --help    # Show usage
#

set -euo pipefail

# ── Constants ────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || pwd)"
PROJECT_DIR="$SCRIPT_DIR"

DB_NAME="portact_db"
DB_USER="portact_user"

SKIP_CONFIRM=false
OS=""

# ── Colors ───────────────────────────────────────────────────────────────────

BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Utility Functions ────────────────────────────────────────────────────────

print_header() {
    local text="$1"
    local width=60
    echo ""
    echo -e "${RED}$(printf '═%.0s' $(seq 1 $width))${NC}"
    echo -e "${RED}  ${BOLD}$text${NC}"
    echo -e "${RED}$(printf '═%.0s' $(seq 1 $width))${NC}"
    echo ""
}

print_step() {
    local step_num="$1"
    local total="$2"
    local text="$3"
    echo ""
    echo -e "${BLUE}${BOLD}[$step_num/$total]${NC} ${BOLD}$text${NC}"
    echo -e "${BLUE}$(printf '─%.0s' $(seq 1 50))${NC}"
}

print_success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "  ${YELLOW}!${NC} $1"
}

print_error() {
    echo -e "  ${RED}✗${NC} $1"
}

print_info() {
    echo -e "  ${CYAN}→${NC} $1"
}

command_exists() {
    command -v "$1" &>/dev/null
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Completely removes PortAct from your computer:"
    echo "  - Stops the running application"
    echo "  - Removes the database and database user"
    echo "  - Deletes all application files and folders"
    echo ""
    echo "Options:"
    echo "  --yes, -y    Skip confirmation prompts (use with caution)"
    echo "  --help, -h   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0          # Interactive uninstall"
    echo "  $0 --yes    # Uninstall without asking"
}

# ── Argument Parsing ─────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes|-y)  SKIP_CONFIRM=true; shift ;;
        --help|-h) show_usage; exit 0 ;;
        *)         print_warning "Unknown option: $1"; shift ;;
    esac
done

# ── OS Detection ─────────────────────────────────────────────────────────────

detect_os() {
    case "$OSTYPE" in
        darwin*) OS="macos" ;;
        linux*)  OS="linux" ;;
        *)       OS="unknown" ;;
    esac
}

# ── PostgreSQL helper (same pattern as install.sh) ───────────────────────────

run_psql_as_superuser() {
    local sql="$1"
    local db="${2:-postgres}"

    if [[ "$OS" == "macos" ]]; then
        psql -d "$db" -tAc "$sql" 2>/dev/null
    elif [[ "$OS" == "linux" ]]; then
        sudo -u postgres psql -d "$db" -tAc "$sql" 2>/dev/null
    else
        return 1
    fi
}

# ── Step 1: Stop the Application ─────────────────────────────────────────────

stop_application() {
    # Stop backend (uvicorn) processes
    local backend_pids
    backend_pids=$(pgrep -f "uvicorn app.main:app" 2>/dev/null || true)

    if [[ -n "$backend_pids" ]]; then
        print_info "Stopping the backend server..."
        for pid in $backend_pids; do
            kill "$pid" 2>/dev/null || true
        done
        sleep 2
        # Force kill if still running
        backend_pids=$(pgrep -f "uvicorn app.main:app" 2>/dev/null || true)
        if [[ -n "$backend_pids" ]]; then
            for pid in $backend_pids; do
                kill -9 "$pid" 2>/dev/null || true
            done
        fi
        print_success "Backend server stopped"
    else
        print_success "Backend server is not running"
    fi

    # Stop frontend (react-scripts) processes
    local frontend_pids
    frontend_pids=$(pgrep -f "react-scripts start" 2>/dev/null || true)

    if [[ -n "$frontend_pids" ]]; then
        print_info "Stopping the frontend server..."
        for pid in $frontend_pids; do
            kill "$pid" 2>/dev/null || true
        done
        sleep 2
        # Force kill if still running
        frontend_pids=$(pgrep -f "react-scripts start" 2>/dev/null || true)
        if [[ -n "$frontend_pids" ]]; then
            for pid in $frontend_pids; do
                kill -9 "$pid" 2>/dev/null || true
            done
        fi
        print_success "Frontend server stopped"
    else
        print_success "Frontend server is not running"
    fi

    # Also clean up any node processes related to the frontend
    local node_pids
    node_pids=$(pgrep -f "node.*$PROJECT_DIR/frontend" 2>/dev/null || true)
    if [[ -n "$node_pids" ]]; then
        for pid in $node_pids; do
            kill "$pid" 2>/dev/null || true
        done
    fi
}

# ── Step 2: Remove the Database ──────────────────────────────────────────────

remove_database() {
    if ! command_exists psql; then
        print_warning "PostgreSQL is not installed — nothing to remove"
        return 0
    fi

    if ! pg_isready -q 2>/dev/null; then
        print_warning "The database server is not running — skipping database removal"
        print_info "If you want to remove the database, start PostgreSQL and run this script again"
        return 0
    fi

    # Drop the database
    local db_exists
    db_exists=$(run_psql_as_superuser "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "0")

    if [[ "$db_exists" == "1" ]]; then
        print_info "Removing the application database..."
        # Terminate active connections first
        run_psql_as_superuser "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" 2>/dev/null || true
        if run_psql_as_superuser "DROP DATABASE $DB_NAME;" 2>/dev/null; then
            print_success "Database '$DB_NAME' removed"
        else
            print_warning "Could not remove the database — you may need to remove it manually"
            print_info "Run: psql -c \"DROP DATABASE $DB_NAME;\""
        fi
    else
        print_success "Database '$DB_NAME' does not exist (already removed)"
    fi

    # Drop the database user
    local user_exists
    user_exists=$(run_psql_as_superuser "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null || echo "0")

    if [[ "$user_exists" == "1" ]]; then
        print_info "Removing the database user..."
        if run_psql_as_superuser "DROP USER $DB_USER;" 2>/dev/null; then
            print_success "Database user '$DB_USER' removed"
        else
            print_warning "Could not remove the database user — you may need to remove it manually"
            print_info "Run: psql -c \"DROP USER $DB_USER;\""
        fi
    else
        print_success "Database user '$DB_USER' does not exist (already removed)"
    fi

    # Clean up pg_hba.conf entry on Linux
    if [[ "$OS" == "linux" ]]; then
        local pg_hba
        pg_hba=$(sudo -u postgres psql -tAc "SHOW hba_file" 2>/dev/null | tr -d ' ' || true)
        if [[ -n "$pg_hba" ]] && [[ -f "$pg_hba" ]]; then
            if sudo grep -q "$DB_USER" "$pg_hba" 2>/dev/null; then
                print_info "Cleaning up database access configuration..."
                sudo sed -i "/$DB_USER/d" "$pg_hba" 2>/dev/null || true
                sudo systemctl reload postgresql 2>/dev/null || true
                print_success "Database access configuration cleaned up"
            fi
        fi
    fi
}

# ── Step 3: Delete Project Files ─────────────────────────────────────────────

delete_project_files() {
    # We need to move out of the project directory before deleting it
    local parent_dir
    parent_dir="$(dirname "$PROJECT_DIR")"

    print_info "Removing all application files and folders..."
    print_info "Location: $PROJECT_DIR"

    cd "$parent_dir"

    if rm -rf "$PROJECT_DIR"; then
        print_success "All application files removed"
    else
        print_error "Could not remove some files"
        print_info "You can manually delete the folder: $PROJECT_DIR"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
    print_header "PortAct Uninstaller"

    detect_os

    # Verify we're in the PortAct project
    if [[ ! -d "$PROJECT_DIR/backend" ]] || [[ ! -d "$PROJECT_DIR/frontend" ]]; then
        print_error "This does not appear to be the PortAct project folder."
        print_info "Please run this script from inside the PortAct directory."
        echo ""
        exit 1
    fi

    echo -e "  ${BOLD}This will completely remove PortAct from your computer:${NC}"
    echo ""
    echo -e "    ${RED}•${NC} Stop the running application"
    echo -e "    ${RED}•${NC} Delete the database (${BOLD}$DB_NAME${NC}) and all its data"
    echo -e "    ${RED}•${NC} Delete the database user (${BOLD}$DB_USER${NC})"
    echo -e "    ${RED}•${NC} Delete all project files at:"
    echo -e "      ${CYAN}$PROJECT_DIR${NC}"
    echo ""
    echo -e "  ${YELLOW}${BOLD}This action cannot be undone.${NC}"
    echo ""

    if [[ "$SKIP_CONFIRM" != true ]]; then
        read -p "  Are you sure you want to continue? (type 'yes' to confirm): " confirmation
        echo ""
        if [[ "$confirmation" != "yes" ]]; then
            print_info "Uninstall cancelled. No changes were made."
            echo ""
            exit 0
        fi
    fi

    local total_steps=3
    local step=1

    # Step 1: Stop the application
    print_step $step $total_steps "Stopping the application"
    stop_application
    ((step++))

    # Step 2: Remove the database
    print_step $step $total_steps "Removing the database"
    remove_database
    ((step++))

    # Step 3: Delete all project files
    print_step $step $total_steps "Deleting application files"
    delete_project_files

    # Done
    local width=60
    echo ""
    echo -e "${GREEN}$(printf '═%.0s' $(seq 1 $width))${NC}"
    echo -e "${GREEN}  ${BOLD}PortAct has been removed from your computer.${NC}"
    echo -e "${GREEN}$(printf '═%.0s' $(seq 1 $width))${NC}"
    echo ""
    echo -e "  To reinstall PortAct in the future, run:"
    echo -e "    ${CYAN}curl -fsSL https://raw.githubusercontent.com/debasisdas1976/PortAct/main/install.sh | bash${NC}"
    echo ""
    echo -e "  Thank you for using PortAct!"
    echo ""
}

main "$@"
