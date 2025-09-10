#!/bin/bash

# OSRS Discord Bot Startup Script
# This script handles the startup process for the bot with proper environment setup

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
PYTHON_MIN_VERSION="3.9"
VENV_DIR="$PROJECT_DIR/venv"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"

# Function to print colored output
print_status() {
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

# Function to check Python version
check_python_version() {
    print_status "Checking Python version..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    required_version=$PYTHON_MIN_VERSION
    
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        print_error "Python $python_version is installed, but Python $required_version or higher is required"
        exit 1
    fi
    
    print_success "Python $python_version is installed"
}

# Function to create virtual environment
setup_virtual_environment() {
    print_status "Setting up virtual environment..."
    
    if [ ! -d "$VENV_DIR" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip
    
    print_success "Virtual environment ready"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        print_error "Requirements file not found: $REQUIREMENTS_FILE"
        exit 1
    fi
    
    # Install requirements
    pip install -r "$REQUIREMENTS_FILE"
    
    print_success "Dependencies installed"
}

# Function to check environment configuration
check_environment_config() {
    print_status "Checking environment configuration..."
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE" ]; then
            print_warning "Environment file not found. Copying from example..."
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            print_warning "Please edit $ENV_FILE with your configuration before running the bot"
            
            # Check if we're in interactive mode
            if [ -t 0 ]; then
                echo
                read -p "Would you like to edit the environment file now? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    ${EDITOR:-nano} "$ENV_FILE"
                fi
            fi
        else
            print_error "Environment file not found and no example available"
            print_error "Please create $ENV_FILE with your configuration"
            exit 1
        fi
    else
        print_success "Environment file found"
    fi
    
    # Check for required environment variables
    source "$ENV_FILE"
    
    required_vars=("DISCORD_TOKEN" "GUILD_ID")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            print_error "  - $var"
        done
        print_error "Please set these variables in $ENV_FILE"
        exit 1
    fi
    
    print_success "Environment configuration is valid"
}

# Function to initialize database
initialize_database() {
    print_status "Checking database initialization..."
    
    # Check if database files exist
    db_files=("database/users.json" "database/competitions.json" "database/leaderboards.json")
    missing_files=()
    
    for file in "${db_files[@]}"; do
        if [ ! -f "$PROJECT_DIR/$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -ne 0 ]; then
        print_warning "Database files not found. Initializing database..."
        
        if [ -f "$PROJECT_DIR/scripts/init_database.py" ]; then
            python3 "$PROJECT_DIR/scripts/init_database.py"
        else
            print_error "Database initialization script not found"
            exit 1
        fi
    else
        print_success "Database files found"
    fi
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    directories=("logs" "database" "database/backups")
    
    for dir in "${directories[@]}"; do
        mkdir -p "$PROJECT_DIR/$dir"
    done
    
    print_success "Directories created"
}

# Function to run pre-flight checks
run_preflight_checks() {
    print_status "Running pre-flight checks..."
    
    # Check if bot script exists
    if [ ! -f "$PROJECT_DIR/main.py" ]; then
        print_error "Bot main script not found: $PROJECT_DIR/main.py"
        exit 1
    fi
    
    # Test import of main modules
    cd "$PROJECT_DIR"
    if ! python3 -c "import config.settings; import core.bot" 2>/dev/null; then
        print_error "Failed to import main modules. Check for syntax errors."
        exit 1
    fi
    
    print_success "Pre-flight checks passed"
}

# Function to start the bot
start_bot() {
    print_status "Starting OSRS Discord Bot..."
    
    cd "$PROJECT_DIR"
    
    # Set the Python path
    export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
    
    # Start the bot
    exec python3 main.py
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --skip-deps     Skip dependency installation"
    echo "  --skip-db       Skip database initialization"
    echo "  --dev           Development mode (more verbose output)"
    echo "  --help          Show this help message"
    echo
    echo "Environment Variables:"
    echo "  SKIP_DEPS=1     Skip dependency installation"
    echo "  SKIP_DB=1       Skip database initialization"
    echo "  DEV_MODE=1      Enable development mode"
}

# Main function
main() {
    # Parse command line arguments
    SKIP_DEPS=false
    SKIP_DB=false
    DEV_MODE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --skip-db)
                SKIP_DB=true
                shift
                ;;
            --dev)
                DEV_MODE=true
                export DEBUG=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Check environment variables
    if [ "$SKIP_DEPS" = "1" ]; then SKIP_DEPS=true; fi
    if [ "$SKIP_DB" = "1" ]; then SKIP_DB=true; fi
    if [ "$DEV_MODE" = "1" ]; then DEV_MODE=true; fi
    
    # Print banner
    echo
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    OSRS Discord Bot                          ║"
    echo "║                      Starting Up...                         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo
    
    # Change to project directory
    cd "$PROJECT_DIR"
    
    # Run setup steps
    check_python_version
    create_directories
    
    if [ "$SKIP_DEPS" = false ]; then
        setup_virtual_environment
        install_dependencies
    else
        print_warning "Skipping dependency installation"
        # Still need to activate venv if it exists
        if [ -d "$VENV_DIR" ]; then
            source "$VENV_DIR/bin/activate"
        fi
    fi
    
    check_environment_config
    
    if [ "$SKIP_DB" = false ]; then
        initialize_database
    else
        print_warning "Skipping database initialization"
    fi
    
    run_preflight_checks
    
    # Final message
    echo
    print_success "Setup complete! Starting bot..."
    echo
    
    # Start the bot
    start_bot
}

# Trap signals for graceful shutdown
trap 'print_warning "Received interrupt signal. Shutting down..."; exit 130' INT TERM

# Run main function with all arguments
main "$@"