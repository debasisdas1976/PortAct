#!/bin/bash

# =============================================================================
# PortAct – One-Command Docker Launcher
# For complete beginners: installs Docker if needed, pulls the image, and runs.
#
# Usage:  curl -sSL <raw-url> | bash
#    or:  ./scripts/run_docker.sh
# =============================================================================

set -e

# ── Configuration ────────────────────────────────────────────────────────────

IMAGE="debasisdas1976/portact:latest"
CONTAINER_NAME="portact"
VOLUME_NAME="portact-data"
HOST_PORT=8080
APP_URL="http://localhost:${HOST_PORT}"

# ── Colors & helpers ─────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}[i]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
fail()    { echo -e "${RED}[✗]${NC} $1"; exit 1; }

command_exists() { command -v "$1" &>/dev/null; }

# ── Banner ───────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}======================================"
echo "  PortAct – Docker Launcher"
echo -e "======================================${NC}"
echo ""

# ── Step 1: Check / Install Docker ──────────────────────────────────────────

echo -e "${BOLD}Step 1: Checking for Docker...${NC}"
echo "-----------------------------------"

if command_exists docker && docker info &>/dev/null; then
    DOCKER_VERSION=$(docker --version | sed 's/Docker version //' | cut -d',' -f1)
    success "Docker is installed and running (v${DOCKER_VERSION})"
elif command_exists docker; then
    # Docker is installed but the daemon isn't running
    warn "Docker is installed but not running."

    OS_TYPE="$(uname -s)"
    if [ "$OS_TYPE" = "Darwin" ]; then
        info "Starting Docker Desktop... (this may take a minute)"
        open -a Docker 2>/dev/null || true

        echo -n "  Waiting for Docker to start "
        for i in $(seq 1 60); do
            if docker info &>/dev/null; then
                echo ""
                success "Docker Desktop is running"
                break
            fi
            echo -n "."
            sleep 2
        done

        if ! docker info &>/dev/null; then
            echo ""
            fail "Docker did not start in time. Please open Docker Desktop manually and run this script again."
        fi
    else
        info "Trying to start the Docker daemon..."
        sudo systemctl start docker 2>/dev/null || true
        sleep 3
        if docker info &>/dev/null; then
            success "Docker daemon started"
        else
            fail "Could not start Docker. Please start it manually and run this script again."
        fi
    fi
else
    # Docker is not installed at all
    warn "Docker is not installed."
    echo ""

    OS_TYPE="$(uname -s)"
    if [ "$OS_TYPE" = "Darwin" ]; then
        # ── macOS ──
        if command_exists brew; then
            info "Installing Docker Desktop via Homebrew..."
            brew install --cask docker
            success "Docker Desktop installed"

            info "Starting Docker Desktop... (first launch takes a minute or two)"
            open -a Docker

            echo -n "  Waiting for Docker to initialise "
            for i in $(seq 1 90); do
                if docker info &>/dev/null; then
                    echo ""
                    success "Docker Desktop is ready"
                    break
                fi
                echo -n "."
                sleep 2
            done

            if ! docker info &>/dev/null; then
                echo ""
                echo ""
                warn "Docker Desktop is still starting up."
                echo "  Please wait for it to finish, then run this script again."
                exit 1
            fi
        else
            echo "  Please install Docker Desktop from:"
            echo ""
            echo "    https://www.docker.com/products/docker-desktop/"
            echo ""
            echo "  After installing, open Docker Desktop and run this script again."
            exit 1
        fi
    else
        # ── Linux ──
        info "Installing Docker via the official convenience script..."
        echo "  (This will ask for your sudo password.)"
        echo ""

        if command_exists curl; then
            curl -fsSL https://get.docker.com | sudo sh
        elif command_exists wget; then
            wget -qO- https://get.docker.com | sudo sh
        else
            fail "Neither curl nor wget found. Please install Docker manually: https://docs.docker.com/engine/install/"
        fi

        # Add current user to the docker group so they don't need sudo
        if ! groups "$USER" | grep -q '\bdocker\b'; then
            info "Adding your user to the 'docker' group..."
            sudo usermod -aG docker "$USER"
            warn "You may need to log out and back in for group changes to take effect."
            warn "For now, this script will use sudo for Docker commands."
            DOCKER_CMD="sudo docker"
        fi

        sudo systemctl start docker 2>/dev/null || true
        sudo systemctl enable docker 2>/dev/null || true
        sleep 2

        if ${DOCKER_CMD:-docker} info &>/dev/null; then
            success "Docker installed and running"
        else
            fail "Docker installed but could not start. Try rebooting and running this script again."
        fi
    fi
fi

DOCKER="${DOCKER_CMD:-docker}"

# ── Step 2: Pull the latest image ───────────────────────────────────────────

echo ""
echo -e "${BOLD}Step 2: Pulling PortAct image...${NC}"
echo "-----------------------------------"

info "Downloading ${IMAGE} (this may take a few minutes on first run)..."
if $DOCKER pull "$IMAGE"; then
    success "Image pulled successfully"
else
    fail "Failed to pull the image. Check your internet connection and try again."
fi

# ── Step 3: Stop any existing container ──────────────────────────────────────

echo ""
echo -e "${BOLD}Step 3: Preparing to launch...${NC}"
echo "-----------------------------------"

if $DOCKER ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    if $DOCKER ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        info "Stopping existing PortAct container..."
        $DOCKER stop "$CONTAINER_NAME" >/dev/null
    fi
    info "Removing old container..."
    $DOCKER rm "$CONTAINER_NAME" >/dev/null
    success "Old container removed"
else
    success "No existing container to clean up"
fi

# ── Step 4: Run the container ────────────────────────────────────────────────

echo ""
echo -e "${BOLD}Step 4: Starting PortAct...${NC}"
echo "-----------------------------------"

info "Launching container..."
$DOCKER run -d \
    --name "$CONTAINER_NAME" \
    -p "${HOST_PORT}:8080" \
    -v "${VOLUME_NAME}:/var/lib/postgresql/data" \
    --restart unless-stopped \
    "$IMAGE" >/dev/null

success "Container started"

# Wait for the app to become healthy
info "Waiting for PortAct to initialise (database setup + migrations)..."
echo -n "  "

HEALTHY=false
for i in $(seq 1 90); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${APP_URL}/health" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        HEALTHY=true
        echo ""
        break
    fi
    echo -n "."
    sleep 2
done

if [ "$HEALTHY" = true ]; then
    success "PortAct is up and healthy!"
else
    echo ""
    warn "PortAct is still starting. Check logs with:  docker logs ${CONTAINER_NAME}"
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}======================================"
echo "  PortAct is ready!"
echo -e "======================================${NC}"
echo ""
echo "  Open in your browser:"
echo ""
echo -e "    ${GREEN}${APP_URL}${NC}"
echo ""
echo "  Useful commands:"
echo "    docker logs ${CONTAINER_NAME}        View logs"
echo "    docker stop ${CONTAINER_NAME}        Stop the app"
echo "    docker start ${CONTAINER_NAME}       Start again"
echo "    docker rm -f ${CONTAINER_NAME}       Remove the container"
echo ""
echo "  Your data is stored in the Docker volume '${VOLUME_NAME}'."
echo "  It persists across container restarts and upgrades."
echo ""

# Try to open the browser automatically
if [ "$(uname -s)" = "Darwin" ]; then
    open "$APP_URL" 2>/dev/null || true
elif command_exists xdg-open; then
    xdg-open "$APP_URL" 2>/dev/null || true
fi
