#!/bin/bash

# PortAct Setup Script
# This script sets up the PortAct application for local development or production

set -e

echo "========================================="
echo "  PortAct Setup Script"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker is installed"
}

# Check if Docker Compose is installed
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    print_success "Docker Compose is installed"
}

# Generate secret key
generate_secret_key() {
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

# Setup backend environment
setup_backend_env() {
    print_info "Setting up backend environment..."
    
    if [ ! -f "backend/.env" ]; then
        cp backend/.env.example backend/.env
        
        # Generate and set secret key
        SECRET_KEY=$(generate_secret_key)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/your-secret-key-change-this-in-production/$SECRET_KEY/" backend/.env
        else
            sed -i "s/your-secret-key-change-this-in-production/$SECRET_KEY/" backend/.env
        fi
        
        print_success "Backend .env file created"
    else
        print_info "Backend .env file already exists"
    fi
}

# Setup frontend environment
setup_frontend_env() {
    print_info "Setting up frontend environment..."
    
    if [ ! -f "frontend/.env" ]; then
        echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > frontend/.env
        print_success "Frontend .env file created"
    else
        print_info "Frontend .env file already exists"
    fi
}

# Create necessary directories
create_directories() {
    print_info "Creating necessary directories..."
    
    mkdir -p backend/uploads
    mkdir -p backend/logs
    mkdir -p infrastructure/nginx
    
    print_success "Directories created"
}

# Build and start services
start_services() {
    print_info "Building and starting services..."
    
    cd infrastructure
    docker-compose up -d --build
    cd ..
    
    print_success "Services started"
}

# Wait for services to be ready
wait_for_services() {
    print_info "Waiting for services to be ready..."
    
    # Wait for PostgreSQL
    echo -n "Waiting for PostgreSQL"
    for i in {1..30}; do
        if docker exec portact-postgres pg_isready -U portact_user &> /dev/null; then
            echo ""
            print_success "PostgreSQL is ready"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    # Wait for backend
    echo -n "Waiting for backend API"
    for i in {1..30}; do
        if curl -s http://localhost:8000/health &> /dev/null; then
            echo ""
            print_success "Backend API is ready"
            break
        fi
        echo -n "."
        sleep 1
    done
}

# Display access information
display_info() {
    echo ""
    echo "========================================="
    echo "  Setup Complete!"
    echo "========================================="
    echo ""
    echo "Access the application:"
    echo "  Frontend:        http://localhost:3000"
    echo "  Backend API:     http://localhost:8000"
    echo "  API Docs:        http://localhost:8000/docs"
    echo "  MinIO Console:   http://localhost:9001"
    echo ""
    echo "Default MinIO credentials:"
    echo "  Username: minioadmin"
    echo "  Password: minioadmin"
    echo ""
    echo "To stop the application:"
    echo "  cd infrastructure && docker-compose down"
    echo ""
    echo "To view logs:"
    echo "  cd infrastructure && docker-compose logs -f"
    echo ""
    echo "For more information, see DEPLOYMENT.md"
    echo "========================================="
}

# Main setup flow
main() {
    echo "Starting setup process..."
    echo ""
    
    # Check prerequisites
    check_docker
    check_docker_compose
    
    # Setup environment
    setup_backend_env
    setup_frontend_env
    create_directories
    
    # Ask user if they want to start services
    read -p "Do you want to start the services now? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_services
        wait_for_services
        display_info
    else
        print_info "Setup complete. Run 'cd infrastructure && docker-compose up -d' to start services."
    fi
}

# Run main function
main

# Made with Bob
