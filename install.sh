#!/bin/bash

#############################################
# 16-PadtecMon Installation Script
# This script will:
# 1. Clone the repository from GitHub
# 2. Check if Docker is installed
# 3. Install Docker if needed
# 4. Set up the application
# 5. Start all services
#############################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/keslleykledston/16-PadtecMon.git"
INSTALL_DIR="16-PadtecMon"

# Functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root. It's recommended to run this script as a regular user."
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            VER=$VERSION_ID
        else
            OS="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        OS="unknown"
    fi
    print_info "Detected OS: $OS"
}

# Check if Docker is installed
check_docker() {
    print_info "Checking for Docker installation..."
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker is already installed: $DOCKER_VERSION"
        return 0
    else
        print_warning "Docker is not installed."
        return 1
    fi
}

# Check if Docker Compose is installed
check_docker_compose() {
    print_info "Checking for Docker Compose..."
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
        print_success "Docker Compose is installed: $COMPOSE_VERSION"
        return 0
    elif docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version)
        print_success "Docker Compose (plugin) is installed: $COMPOSE_VERSION"
        return 0
    else
        print_warning "Docker Compose is not installed."
        return 1
    fi
}

# Install Docker on Ubuntu/Debian
install_docker_debian() {
    print_info "Installing Docker on Debian/Ubuntu..."
    
    sudo apt-get update
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$OS/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up the repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    print_success "Docker installed successfully!"
    print_warning "You may need to log out and back in for group changes to take effect."
}

# Install Docker on CentOS/RHEL/Fedora
install_docker_rhel() {
    print_info "Installing Docker on RHEL/CentOS/Fedora..."
    
    sudo yum install -y yum-utils
    sudo yum-config-manager --add-repo https://download.docker.com/linux/$OS/docker-ce.repo
    sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
    
    print_success "Docker installed successfully!"
    print_warning "You may need to log out and back in for group changes to take effect."
}

# Install Docker on macOS
install_docker_macos() {
    print_info "Installing Docker on macOS..."
    
    if command -v brew &> /dev/null; then
        brew install --cask docker
        print_success "Docker Desktop installed via Homebrew!"
        print_warning "Please start Docker Desktop from Applications folder."
    else
        print_error "Homebrew is not installed. Please install Docker Desktop manually from:"
        print_error "https://www.docker.com/products/docker-desktop"
        exit 1
    fi
}

# Install Docker based on OS
install_docker() {
    case $OS in
        ubuntu|debian)
            install_docker_debian
            ;;
        centos|rhel|fedora)
            install_docker_rhel
            ;;
        macos)
            install_docker_macos
            ;;
        *)
            print_error "Unsupported OS: $OS"
            print_error "Please install Docker manually from: https://docs.docker.com/get-docker/"
            exit 1
            ;;
    esac
}

# Clone repository
clone_repository() {
    print_info "Cloning repository from $REPO_URL..."
    
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory $INSTALL_DIR already exists."
        read -p "Remove and re-clone? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            print_info "Using existing directory."
            cd "$INSTALL_DIR"
            return 0
        fi
    fi
    
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    print_success "Repository cloned successfully!"
}

# Setup environment file
setup_environment() {
    print_info "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_success "Created .env file from .env.example"
        else
            print_warning "No .env.example found. Creating basic .env file..."
            cat > .env << EOF
# Database Configuration
DB_HOST=timescaledb
DB_PORT=5432
DB_NAME=padtec_mon
DB_USER=padtec_user
DB_PASSWORD=padtec_password

# RabbitMQ Configuration
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=padtec
RABBITMQ_PASSWORD=padtec_password

# Padtec API Configuration
PADTEC_API_URL=http://your-padtec-api-url:8181/nms-api/
PADTEC_API_TOKEN=your-api-token-here

# Application Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
COLLECTOR_INTERVAL=300
EOF
            print_success "Created basic .env file"
        fi
        
        print_warning "Please edit .env file with your Padtec API credentials:"
        print_warning "  - PADTEC_API_URL"
        print_warning "  - PADTEC_API_TOKEN"
        
        read -p "Press Enter to continue after editing .env file..."
    else
        print_success ".env file already exists"
    fi
}

# Build and start services
start_services() {
    print_info "Building and starting Docker containers..."
    
    # Build containers
    print_info "Building containers (this may take a few minutes)..."
    docker-compose build --no-cache
    
    # Start services
    print_info "Starting services..."
    docker-compose up -d
    
    print_success "All services started successfully!"
}

# Wait for services to be healthy
wait_for_services() {
    print_info "Waiting for services to be healthy..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose ps | grep -q "healthy"; then
            print_success "Services are healthy!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    print_warning "Services may still be starting. Check with: docker-compose ps"
}

# Display service URLs
display_info() {
    echo ""
    echo "=========================================="
    print_success "16-PadtecMon Installation Complete!"
    echo "=========================================="
    echo ""
    echo "Service URLs:"
    echo "  Frontend:  http://localhost:3000"
    echo "  Backend:   http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/docs"
    echo ""
    echo "Useful Commands:"
    echo "  View logs:        docker-compose logs -f"
    echo "  Stop services:    docker-compose down"
    echo "  Restart services: docker-compose restart"
    echo "  View status:      docker-compose ps"
    echo ""
    echo "Configuration:"
    echo "  Edit .env file to update Padtec API credentials"
    echo "  Restart services after changes: docker-compose restart"
    echo ""
    echo "=========================================="
}

# Main installation flow
main() {
    echo ""
    echo "=========================================="
    echo "  16-PadtecMon Installation Script"
    echo "=========================================="
    echo ""
    
    check_root
    detect_os
    
    # Check and install Docker
    if ! check_docker; then
        read -p "Install Docker now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_docker
        else
            print_error "Docker is required. Exiting."
            exit 1
        fi
    fi
    
    # Check Docker Compose
    if ! check_docker_compose; then
        print_error "Docker Compose is required but not found."
        print_error "Please install Docker Compose and try again."
        exit 1
    fi
    
    # Clone repository
    clone_repository
    
    # Setup environment
    setup_environment
    
    # Start services
    start_services
    
    # Wait for services
    wait_for_services
    
    # Display information
    display_info
}

# Run main function
main
