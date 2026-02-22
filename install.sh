#!/usr/bin/env bash
#
# PortAct – Single-Click Installation Script
# Installs all dependencies, sets up the database, and launches the application.
#
# Quick install (one-liner):
#   curl -fsSL https://raw.githubusercontent.com/debasisdas1976/PortAct/main/install.sh | bash
#
# Or clone first, then run:
#   git clone https://github.com/debasisdas1976/PortAct.git && cd PortAct && ./install.sh
#
# Usage:
#   ./install.sh              # Full install + launch
#   ./install.sh --no-start   # Install only, don't launch
#   ./install.sh --seed-demo  # Install + seed demo user + launch
#   ./install.sh --help       # Show usage
#

# ── Repository URL ───────────────────────────────────────────────────────────

REPO_URL="https://github.com/debasisdas1976/PortAct.git"
CLONE_DIR="PortAct"

# ── Auto-clone: if not inside the project, clone it first ────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || pwd)"

# Detect if we're running inside the PortAct project (has backend/ and frontend/)
if [[ ! -d "$SCRIPT_DIR/backend" ]] || [[ ! -d "$SCRIPT_DIR/frontend" ]]; then
    echo ""
    echo "PortAct project files not found. Downloading them now..."
    echo ""

    # Install git if not available
    if ! command -v git &>/dev/null; then
        echo "Setting up a few tools needed for the download..."
        echo ""
        if [[ "$OSTYPE" == darwin* ]]; then
            echo "A dialog box may appear on your screen — please click 'Install' to continue."
            echo ""
            xcode-select --install 2>/dev/null || true
            echo "Waiting for the installation to finish (this is a one-time setup)..."
            until command -v git &>/dev/null; do
                sleep 5
            done
            echo "Done!"
        else
            sudo apt-get update -qq 2>/dev/null
            sudo apt-get install -y git 2>/dev/null
        fi

        if ! command -v git &>/dev/null; then
            echo ""
            echo "We were unable to set up the download tools automatically."
            echo "Please install 'git' on your computer and run this script again."
            echo ""
            exit 1
        fi
    fi

    # Clone into current working directory
    TARGET_DIR="$(pwd)/$CLONE_DIR"
    if [[ -d "$TARGET_DIR" ]]; then
        echo "Found an existing copy at: $TARGET_DIR"
        echo "Checking for updates..."
        git -C "$TARGET_DIR" pull --ff-only 2>/dev/null || true
    else
        echo "Downloading PortAct..."
        if ! git clone "$REPO_URL" "$TARGET_DIR" 2>/dev/null; then
            echo ""
            echo "Download failed. Please check your internet connection and try again."
            echo ""
            exit 1
        fi
    fi

    echo ""
    echo "Download complete. Starting installation..."
    echo ""
    exec bash "$TARGET_DIR/install.sh" "$@"
fi

# ── Constants ────────────────────────────────────────────────────────────────

PROJECT_DIR="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"

DB_NAME="portact_db"
DB_USER="portact_user"
DB_PASSWORD="portact_password"
DB_HOST="localhost"
DB_PORT="5432"

BACKEND_PORT=8000
FRONTEND_PORT=3000

NO_START=false
SEED_DEMO=false

BACKEND_PID=""
FRONTEND_PID=""

OS=""
ARCH=""
PYTHON_CMD="python3"

# Track which step we're on for the error handler
CURRENT_STEP=""

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
    echo -e "${MAGENTA}$(printf '═%.0s' $(seq 1 $width))${NC}"
    echo -e "${MAGENTA}  ${BOLD}$text${NC}"
    echo -e "${MAGENTA}$(printf '═%.0s' $(seq 1 $width))${NC}"
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

fail() {
    echo ""
    print_error "$1"
    if [[ -n "${2:-}" ]]; then
        echo -e "    ${YELLOW}Suggestion:${NC} $2"
    fi
    echo ""
    exit 1
}

command_exists() {
    command -v "$1" &>/dev/null
}

# Compare semantic versions: returns 0 (true) if $1 >= $2
version_ge() {
    local ver1="$1"
    local ver2="$2"
    if [[ "$(printf '%s\n' "$ver2" "$ver1" | sort -V | head -n1)" == "$ver2" ]]; then
        return 0
    else
        return 1
    fi
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "PortAct single-click installer. Clones the project (if needed),"
    echo "installs all dependencies, configures the database, and launches"
    echo "the application."
    echo ""
    echo "Quick install (one-liner):"
    echo "  curl -fsSL https://raw.githubusercontent.com/debasisdas1976/PortAct/main/install.sh | bash"
    echo ""
    echo "Options:"
    echo "  --no-start     Install everything but don't launch the app"
    echo "  --seed-demo    Seed a demo user account (demouser@portact.com / portact1)"
    echo "  --help, -h     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                        # Full install + launch"
    echo "  $0 --no-start             # Install only"
    echo "  $0 --seed-demo            # Install + demo data + launch"
    echo "  $0 --no-start --seed-demo # Install + demo data, no launch"
}

# ── Global Error Handler ────────────────────────────────────────────────────
# Catches any unexpected command failure and shows a friendly message.

on_error() {
    echo ""
    echo -e "  ${RED}✗${NC} Something went wrong during: ${BOLD}${CURRENT_STEP:-installation}${NC}"
    echo ""
    echo -e "    This usually happens due to a network issue or a missing permission."
    echo ""
    echo -e "    What you can try:"
    echo -e "      1. Check your internet connection"
    echo -e "      2. Make sure you have permission to install software on this computer"
    echo -e "      3. Run the installer again — it will pick up where it left off"
    echo ""
    echo -e "    If the problem persists, please visit:"
    echo -e "      ${CYAN}https://github.com/debasisdas1976/PortAct/issues${NC}"
    echo ""
    exit 1
}
trap on_error ERR

# ── Argument Parsing ─────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-start)  NO_START=true; shift ;;
        --seed-demo) SEED_DEMO=true; shift ;;
        --help|-h)   show_usage; exit 0 ;;
        *)           print_warning "Unknown option: $1"; shift ;;
    esac
done

# ── Cleanup Trap ─────────────────────────────────────────────────────────────

cleanup() {
    echo ""
    print_info "Shutting down the application..."
    if [[ -n "$BACKEND_PID" ]]; then
        kill "$BACKEND_PID" 2>/dev/null || true
        print_info "Backend server stopped"
    fi
    if [[ -n "$FRONTEND_PID" ]]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
        print_info "Frontend server stopped"
    fi
    echo ""
    print_success "Application stopped. You can restart anytime by running ./install.sh"
    exit 0
}
trap cleanup INT TERM

# ── Step 1: OS Detection ────────────────────────────────────────────────────

detect_os() {
    CURRENT_STEP="detecting your operating system"

    case "$OSTYPE" in
        darwin*)  OS="macos" ;;
        linux*)   OS="linux" ;;
        *)
            fail "This installer currently supports macOS and Linux (Ubuntu/Debian)." \
                 "If you are on Windows, please use WSL (Windows Subsystem for Linux) and try again."
            ;;
    esac

    ARCH=$(uname -m)

    if [[ "$OS" == "linux" ]] && ! command_exists apt-get; then
        fail "This installer works with Ubuntu and Debian-based Linux systems." \
             "If you are on a different Linux distribution (Fedora, Arch, etc.), please see the manual installation guide in the project README."
    fi

    print_success "Operating system: $OS ($ARCH)"
}

# ── Step 2: System Dependency Installation ───────────────────────────────────

install_homebrew() {
    CURRENT_STEP="installing Homebrew (package manager for macOS)"

    if command_exists brew; then
        print_success "Homebrew is already installed"
        return 0
    fi
    print_info "Installing Homebrew (a package manager that helps install other tools)..."
    if ! /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; then
        fail "Could not install Homebrew." \
             "Please check your internet connection and try again."
    fi

    # Add Homebrew to PATH for this session (Apple Silicon vs Intel)
    if [[ "$ARCH" == "arm64" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    print_success "Homebrew installed"
}

install_python_macos() {
    CURRENT_STEP="installing Python"

    if command_exists python3; then
        local py_ver
        py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if version_ge "$py_ver" "3.11"; then
            PYTHON_CMD="python3"
            print_success "Python $py_ver is already installed"
            return 0
        fi
    fi
    print_info "Installing Python (the programming language for the backend)..."
    if ! brew install python@3.11; then
        fail "Could not install Python." \
             "Try running 'brew update' and then run this installer again."
    fi
    brew link python@3.11 --overwrite 2>/dev/null || true
    PYTHON_CMD="python3"
    print_success "Python 3.11 installed"
}

install_python_linux() {
    CURRENT_STEP="installing Python"

    if command_exists python3; then
        local py_ver
        py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if version_ge "$py_ver" "3.11"; then
            PYTHON_CMD="python3"
            print_success "Python $py_ver is already installed"
            return 0
        fi
    fi

    print_info "Installing Python (the programming language for the backend)..."
    sudo apt-get install -y software-properties-common 2>/dev/null || true
    sudo add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
    sudo apt-get update -qq 2>/dev/null || true
    if ! sudo apt-get install -y python3.11 python3.11-venv python3.11-dev 2>/dev/null; then
        if ! sudo apt-get install -y python3 python3-venv python3-dev python3-pip; then
            fail "Could not install Python." \
                 "Try running 'sudo apt-get update' and then run this installer again."
        fi
    fi

    if command_exists python3.11; then
        PYTHON_CMD="python3.11"
    else
        PYTHON_CMD="python3"
    fi
    print_success "Python installed"
}

install_node_macos() {
    CURRENT_STEP="installing Node.js"

    if command_exists node; then
        local node_major
        node_major=$(node --version | sed 's/v//' | cut -d. -f1)
        if [[ "$node_major" -ge 18 ]]; then
            print_success "Node.js $(node --version) is already installed"
            return 0
        fi
    fi
    print_info "Installing Node.js (the runtime for the frontend)..."
    if ! brew install node@18; then
        fail "Could not install Node.js." \
             "Try running 'brew update' and then run this installer again."
    fi
    brew link node@18 --overwrite 2>/dev/null || true
    print_success "Node.js installed"
}

install_node_linux() {
    CURRENT_STEP="installing Node.js"

    if command_exists node; then
        local node_major
        node_major=$(node --version | sed 's/v//' | cut -d. -f1)
        if [[ "$node_major" -ge 18 ]]; then
            print_success "Node.js $(node --version) is already installed"
            return 0
        fi
    fi
    print_info "Installing Node.js (the runtime for the frontend)..."
    if ! curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -; then
        fail "Could not set up the Node.js package source." \
             "Please check your internet connection and try again."
    fi
    if ! sudo apt-get install -y nodejs; then
        fail "Could not install Node.js." \
             "Try running 'sudo apt-get update' and then run this installer again."
    fi
    print_success "Node.js installed"
}

install_postgresql_macos() {
    CURRENT_STEP="installing PostgreSQL (database)"

    if brew list postgresql@15 &>/dev/null || brew list postgresql@16 &>/dev/null || brew list postgresql@17 &>/dev/null; then
        print_success "PostgreSQL is already installed"
    elif command_exists psql; then
        print_success "PostgreSQL is already installed"
    else
        print_info "Installing PostgreSQL (the database for storing your data)..."
        if ! brew install postgresql@15; then
            fail "Could not install PostgreSQL." \
                 "Try running 'brew update' and then run this installer again."
        fi
        print_success "PostgreSQL installed"
    fi

    # Add PostgreSQL binaries to PATH if needed
    for pg_ver in 17 16 15; do
        local pg_prefix
        pg_prefix="$(brew --prefix postgresql@$pg_ver 2>/dev/null || true)"
        if [[ -n "$pg_prefix" ]] && [[ -d "$pg_prefix/bin" ]] && [[ ":$PATH:" != *":$pg_prefix/bin:"* ]]; then
            export PATH="$pg_prefix/bin:$PATH"
            break
        fi
    done

    # Start PostgreSQL if not running
    if ! pg_isready -q 2>/dev/null; then
        print_info "Starting the database server..."
        for pg_ver in 17 16 15; do
            if brew list "postgresql@$pg_ver" &>/dev/null; then
                brew services start "postgresql@$pg_ver" 2>/dev/null || true
                break
            fi
        done

        local retries=0
        while ! pg_isready -q 2>/dev/null && [[ $retries -lt 15 ]]; do
            sleep 1
            ((retries++))
        done
        if ! pg_isready -q 2>/dev/null; then
            fail "The database server did not start in time." \
                 "Try restarting your computer and running this installer again."
        fi
    fi
    print_success "Database server is running"
}

install_postgresql_linux() {
    CURRENT_STEP="installing PostgreSQL (database)"

    if command_exists psql; then
        print_success "PostgreSQL is already installed"
    else
        print_info "Installing PostgreSQL (the database for storing your data)..."
        if ! sudo apt-get install -y postgresql postgresql-contrib libpq-dev; then
            fail "Could not install PostgreSQL." \
                 "Try running 'sudo apt-get update' and then run this installer again."
        fi
        print_success "PostgreSQL installed"
    fi

    # Start if not running
    if ! pg_isready -q 2>/dev/null; then
        print_info "Starting the database server..."
        sudo systemctl start postgresql 2>/dev/null || true
        sudo systemctl enable postgresql 2>/dev/null || true
        sleep 2
        if ! pg_isready -q 2>/dev/null; then
            fail "The database server did not start." \
                 "Try restarting your computer and running this installer again."
        fi
    fi
    print_success "Database server is running"
}

install_system_libs() {
    CURRENT_STEP="installing supporting libraries"

    if [[ "$OS" == "macos" ]]; then
        if ! brew list libmagic &>/dev/null 2>&1; then
            print_info "Installing a few supporting libraries..."
            brew install libmagic 2>/dev/null || true
        fi
        print_success "Supporting libraries ready"
    else
        print_info "Installing a few supporting libraries..."
        sudo apt-get install -y build-essential libpq-dev libmagic1 curl -qq 2>/dev/null || true
        print_success "Supporting libraries ready"
    fi
}

# ── Step 3: Database Setup ───────────────────────────────────────────────────

run_psql_as_superuser() {
    local sql="$1"
    local db="${2:-postgres}"

    if [[ "$OS" == "macos" ]]; then
        psql -d "$db" -tAc "$sql" 2>/dev/null
    else
        sudo -u postgres psql -d "$db" -tAc "$sql" 2>/dev/null
    fi
}

configure_pg_hba_linux() {
    if [[ "$OS" != "linux" ]]; then return 0; fi

    CURRENT_STEP="configuring database access"

    local pg_hba
    pg_hba=$(sudo -u postgres psql -tAc "SHOW hba_file" 2>/dev/null | tr -d ' ')

    if [[ -z "$pg_hba" ]] || [[ ! -f "$pg_hba" ]]; then
        print_warning "Could not automatically configure database access (will try default settings)"
        return 0
    fi

    if sudo grep -q "$DB_USER" "$pg_hba" 2>/dev/null; then
        print_success "Database access already configured"
        return 0
    fi

    print_info "Configuring database access permissions..."

    sudo sed -i "/^local\s\+all\s\+all\s\+peer/i local   $DB_NAME    $DB_USER                                md5" "$pg_hba" 2>/dev/null || true
    echo "host    $DB_NAME    $DB_USER    127.0.0.1/32    md5" | sudo tee -a "$pg_hba" >/dev/null
    echo "host    $DB_NAME    $DB_USER    ::1/128         md5" | sudo tee -a "$pg_hba" >/dev/null

    sudo systemctl reload postgresql 2>/dev/null || true
    print_success "Database access configured"
}

setup_database() {
    CURRENT_STEP="setting up the database"

    # Create user if not exists
    local user_exists
    user_exists=$(run_psql_as_superuser "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" || echo "0")

    if [[ "$user_exists" != "1" ]]; then
        print_info "Creating database user..."
        if ! run_psql_as_superuser "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"; then
            fail "Could not create the database user." \
                 "Make sure the database server is running and try again."
        fi
        print_success "Database user created"
    else
        print_success "Database user already exists"
    fi

    # Create database if not exists
    local db_exists
    db_exists=$(run_psql_as_superuser "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" || echo "0")

    if [[ "$db_exists" != "1" ]]; then
        print_info "Creating the application database..."
        if ! run_psql_as_superuser "CREATE DATABASE $DB_NAME OWNER $DB_USER;"; then
            fail "Could not create the application database." \
                 "Make sure the database server is running and try again."
        fi
        print_success "Application database created"
    else
        print_success "Application database already exists"
    fi

    # Grant privileges
    print_info "Setting up database permissions..."
    run_psql_as_superuser "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" || true
    run_psql_as_superuser "GRANT ALL ON SCHEMA public TO $DB_USER;" "$DB_NAME" || true
    run_psql_as_superuser "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;" "$DB_NAME" || true
    run_psql_as_superuser "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;" "$DB_NAME" || true
    run_psql_as_superuser "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;" "$DB_NAME" || true
    run_psql_as_superuser "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;" "$DB_NAME" || true
    print_success "Database permissions configured"

    # Verify connectivity
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1" &>/dev/null; then
        print_success "Database connection verified"
    else
        print_warning "Could not verify database connection directly (the application may still work fine)"
    fi
}

# ── Step 4: Backend Setup ───────────────────────────────────────────────────

setup_backend() {
    cd "$BACKEND_DIR"

    # Create virtual environment
    CURRENT_STEP="creating the Python environment"
    if [[ ! -d "$VENV_DIR" ]]; then
        print_info "Setting up the Python environment..."
        if ! "$PYTHON_CMD" -m venv "$VENV_DIR"; then
            fail "Could not set up the Python environment." \
                 "Make sure Python is installed correctly. You can try: $PYTHON_CMD --version"
        fi
        print_success "Python environment created"
    else
        print_success "Python environment already exists"
    fi

    # Activate venv
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    # Upgrade pip
    print_info "Preparing the package installer..."
    pip install --upgrade pip -q 2>&1 | tail -1 || true

    # Install requirements
    CURRENT_STEP="installing backend packages"
    print_info "Installing backend packages (this may take a few minutes)..."
    if ! pip install -r requirements.txt; then
        fail "Some backend packages could not be installed." \
             "Check your internet connection and try running the installer again."
    fi
    print_success "Backend packages installed"

    # Create .env file
    CURRENT_STEP="creating backend configuration"
    if [[ ! -f "$BACKEND_DIR/.env" ]]; then
        if [[ ! -f "$BACKEND_DIR/.env.example" ]]; then
            fail "Configuration template file is missing (.env.example)." \
                 "The project files may be incomplete. Try deleting the PortAct folder and running the installer again."
        fi

        print_info "Creating backend configuration..."
        cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"

        # Generate secure SECRET_KEY
        local secret_key
        secret_key=$("$PYTHON_CMD" -c "import secrets; print(secrets.token_urlsafe(32))")

        # Platform-aware sed in-place
        if [[ "$OS" == "macos" ]]; then
            sed -i '' "s|your-secret-key-change-this-in-production|$secret_key|g" "$BACKEND_DIR/.env"
            sed -i '' "s|ENVIRONMENT=production|ENVIRONMENT=development|g" "$BACKEND_DIR/.env"
            sed -i '' "s|DEBUG=False|DEBUG=True|g" "$BACKEND_DIR/.env"
        else
            sed -i "s|your-secret-key-change-this-in-production|$secret_key|g" "$BACKEND_DIR/.env"
            sed -i "s|ENVIRONMENT=production|ENVIRONMENT=development|g" "$BACKEND_DIR/.env"
            sed -i "s|DEBUG=False|DEBUG=True|g" "$BACKEND_DIR/.env"
        fi

        print_success "Backend configuration created"
    else
        print_success "Backend configuration already exists"
    fi

    # Run Alembic migrations
    CURRENT_STEP="setting up database tables"
    print_info "Setting up the database tables..."
    if ! alembic upgrade head; then
        fail "Could not set up the database tables." \
             "Make sure the database server is running and the configuration in backend/.env is correct."
    fi
    print_success "Database tables are ready"

    # Seed expense categories (idempotent)
    if [[ -f "$BACKEND_DIR/seed_categories.py" ]]; then
        print_info "Loading default categories..."
        python "$BACKEND_DIR/seed_categories.py" 2>/dev/null || true
    fi

    # Seed demo user if requested
    if [[ "$SEED_DEMO" == true ]] && [[ -f "$BACKEND_DIR/seed_demo_user.py" ]]; then
        CURRENT_STEP="creating demo user account"
        print_info "Creating demo user account..."
        if ! python "$BACKEND_DIR/seed_demo_user.py"; then
            print_warning "Could not create the demo user (the app will still work — you can register a new account)"
        else
            print_success "Demo user created (email: demouser@portact.com, password: portact1)"
        fi
    fi

    deactivate
    cd "$PROJECT_DIR"
}

# ── Step 5: Frontend Setup ──────────────────────────────────────────────────

setup_frontend() {
    cd "$FRONTEND_DIR"

    # Create .env
    CURRENT_STEP="creating frontend configuration"
    if [[ ! -f "$FRONTEND_DIR/.env" ]]; then
        print_info "Creating frontend configuration..."
        echo "REACT_APP_API_URL=http://localhost:$BACKEND_PORT/api/v1" > "$FRONTEND_DIR/.env"
        print_success "Frontend configuration created"
    else
        print_success "Frontend configuration already exists"
    fi

    # Install npm dependencies
    CURRENT_STEP="installing frontend packages"
    if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
        print_info "Installing frontend packages (this may take a few minutes)..."
        if ! npm install; then
            fail "Some frontend packages could not be installed." \
                 "Check your internet connection and try running the installer again."
        fi
        print_success "Frontend packages installed"
    else
        print_success "Frontend packages already installed"
    fi

    cd "$PROJECT_DIR"
}

# ── Step 6: Directory Creation ──────────────────────────────────────────────

create_directories() {
    CURRENT_STEP="creating application folders"
    mkdir -p "$BACKEND_DIR/uploads"
    mkdir -p "$BACKEND_DIR/logs"
    mkdir -p "$PROJECT_DIR/statements"
    print_success "Application folders ready"
}

# ── Step 7: Verification ────────────────────────────────────────────────────

verify_installation() {
    CURRENT_STEP="verifying the installation"
    local all_ok=true

    # Python venv
    if [[ -f "$VENV_DIR/bin/python" ]]; then
        print_success "Python environment: Ready"
    else
        print_error "Python environment: Not found"
        all_ok=false
    fi

    # Key Python packages
    if "$VENV_DIR/bin/python" -c "import fastapi, sqlalchemy, pydantic" 2>/dev/null; then
        print_success "Backend packages: Ready"
    else
        print_error "Backend packages: Not fully installed"
        all_ok=false
    fi

    # Frontend packages
    if [[ -d "$FRONTEND_DIR/node_modules/react" ]]; then
        print_success "Frontend packages: Ready"
    else
        print_error "Frontend packages: Not fully installed"
        all_ok=false
    fi

    # .env files
    if [[ -f "$BACKEND_DIR/.env" ]]; then
        print_success "Backend configuration: Ready"
    else
        print_error "Backend configuration: Missing"
        all_ok=false
    fi

    if [[ -f "$FRONTEND_DIR/.env" ]]; then
        print_success "Frontend configuration: Ready"
    else
        print_error "Frontend configuration: Missing"
        all_ok=false
    fi

    # Database connectivity
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1" &>/dev/null; then
        print_success "Database connection: Ready"
    else
        print_warning "Database connection: Could not verify (the app may still work fine)"
    fi

    # Alembic migration status
    cd "$BACKEND_DIR"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    if alembic current 2>/dev/null | grep -q "head"; then
        print_success "Database tables: Up to date"
    else
        print_warning "Database tables: Could not verify status"
    fi
    deactivate
    cd "$PROJECT_DIR"

    if [[ "$all_ok" == false ]]; then
        echo ""
        print_warning "Some components may not be fully set up."
        print_warning "Try running this installer again — it will fix anything that's missing."
    fi
}

# ── Step 8: Application Launch ──────────────────────────────────────────────

start_application() {
    CURRENT_STEP="launching the application"

    if [[ "$NO_START" == true ]]; then
        print_info "Skipping application launch (--no-start was specified)"
        return 0
    fi

    # Start backend
    print_info "Starting the backend server..."
    cd "$BACKEND_DIR"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    nohup uvicorn app.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" > "$PROJECT_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    print_success "Backend server started"

    # Wait for backend health check
    print_info "Waiting for the backend to be ready..."
    local retries=0
    while [[ $retries -lt 30 ]]; do
        if curl -sf "http://localhost:$BACKEND_PORT/docs" >/dev/null 2>&1; then
            print_success "Backend is ready"
            break
        fi
        sleep 1
        ((retries++))
    done
    if [[ $retries -eq 30 ]]; then
        print_warning "The backend is taking longer than usual to start"
        print_warning "It may still be loading — give it a moment and then open the app"
    fi

    # Start frontend (suppress auto-open browser)
    print_info "Starting the frontend server..."
    cd "$FRONTEND_DIR"
    BROWSER=none nohup npm start > "$PROJECT_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    print_success "Frontend server started"

    # Give frontend a moment to compile
    sleep 3
    cd "$PROJECT_DIR"
}

# ── Summary Banner ──────────────────────────────────────────────────────────

print_summary() {
    local width=60
    echo ""
    echo -e "${GREEN}$(printf '═%.0s' $(seq 1 $width))${NC}"
    echo -e "${GREEN}  ${BOLD}PortAct — Installation Complete!${NC}"
    echo -e "${GREEN}$(printf '═%.0s' $(seq 1 $width))${NC}"
    echo ""
    echo -e "  ${BOLD}Open the app in your browser:${NC}"
    echo -e "    ${CYAN}http://localhost:$FRONTEND_PORT${NC}"
    echo ""
    echo -e "  ${BOLD}Other links:${NC}"
    echo -e "    API Documentation:  ${CYAN}http://localhost:$BACKEND_PORT/docs${NC}"
    echo ""

    if [[ "$SEED_DEMO" == true ]]; then
        echo -e "  ${BOLD}Demo Account (ready to use):${NC}"
        echo -e "    Email:     ${CYAN}demouser@portact.com${NC}"
        echo -e "    Password:  portact1"
        echo ""
    fi

    echo -e "  ${BOLD}Database credentials:${NC}"
    echo -e "    Host:      $DB_HOST:$DB_PORT"
    echo -e "    Database:  $DB_NAME"
    echo -e "    User:      $DB_USER"
    echo -e "    Password:  $DB_PASSWORD"
    echo ""

    if [[ "$NO_START" == true ]]; then
        echo -e "  ${BOLD}To start the application later:${NC}"
        echo -e "    Just run: ${CYAN}./install.sh${NC}"
    else
        echo -e "  ${BOLD}To stop the application:${NC}"
        echo -e "    Press ${BOLD}Ctrl+C${NC} in this terminal"
        echo ""
        echo -e "  ${BOLD}To restart later:${NC}"
        echo -e "    Just run: ${CYAN}./install.sh${NC}"
    fi

    echo ""
    echo -e "${GREEN}$(printf '═%.0s' $(seq 1 $width))${NC}"

    if [[ "$NO_START" == false ]]; then
        echo ""
        echo -e "  The app is running. Press ${BOLD}Ctrl+C${NC} to stop."
        echo ""
        wait
    fi
}

# ── Main ────────────────────────────────────────────────────────────────────

main() {
    print_header "PortAct Installer"

    local total_steps=8
    local step=1

    # Root check for macOS
    if [[ "$EUID" -eq 0 ]] && [[ "$OSTYPE" == darwin* ]]; then
        fail "Please run this installer as a regular user, not as an administrator (root)." \
             "Just run: ./install.sh  (without 'sudo' in front)"
    fi

    # Step 1: OS Detection
    print_step $step $total_steps "Detecting your system"
    detect_os
    ((step++))

    # Step 2: System Dependencies
    print_step $step $total_steps "Installing required software"
    if [[ "$OS" == "macos" ]]; then
        install_homebrew
        install_python_macos
        install_node_macos
        install_postgresql_macos
    else
        print_info "Updating system package list..."
        sudo apt-get update -qq 2>/dev/null || true
        install_python_linux
        install_node_linux
        install_postgresql_linux
    fi
    install_system_libs
    ((step++))

    # Step 3: Database Setup
    print_step $step $total_steps "Setting up the database"
    if [[ "$OS" == "linux" ]]; then
        configure_pg_hba_linux
    fi
    setup_database
    ((step++))

    # Step 4: Backend Setup
    print_step $step $total_steps "Setting up the backend"
    setup_backend
    ((step++))

    # Step 5: Frontend Setup
    print_step $step $total_steps "Setting up the frontend"
    setup_frontend
    ((step++))

    # Step 6: Directories
    print_step $step $total_steps "Preparing application folders"
    create_directories
    ((step++))

    # Step 7: Verification
    print_step $step $total_steps "Verifying everything is ready"
    verify_installation
    ((step++))

    # Step 8: Launch
    print_step $step $total_steps "Launching the application"
    start_application

    # Done!
    print_summary
}

main "$@"
