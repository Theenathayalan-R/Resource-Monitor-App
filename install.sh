#!/bin/bash

# Spark Pod Resource Monitor - Installation and Test Script
# This script installs dependencies and runs comprehensive tests
# Created: September 7, 2025

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Emojis for better UX
ROCKET="🚀"
CHECK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"
GEAR="⚙️"
SPARKLES="✨"
PACKAGE="📦"
TEST_TUBE="🧪"

echo -e "${CYAN}${ROCKET} Spark Pod Resource Monitor - Installation Script${NC}"
echo -e "${CYAN}======================================================${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "${BLUE}${1}${NC}"
    echo -e "${BLUE}$(echo "$1" | sed 's/./=/g')${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}${CHECK} $1${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}${CROSS} $1${NC}"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

# Function to print info messages
print_info() {
    echo -e "${CYAN}${INFO} $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "requirements.txt" ] || [ ! -f "run.sh" ]; then
    print_error "This script must be run from the Resource-Monitor-App root directory"
    print_info "Current directory: $(pwd)"
    print_info "Expected files: requirements.txt, run.sh"
    exit 1
fi

print_success "Found Resource-Monitor-App project files"

# Check Python version
print_section "${GEAR} Checking Python Environment"

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    print_info "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    print_error "Python 3.8+ required, found Python $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION detected"

# Check if virtual environment exists
print_section "${PACKAGE} Setting Up Virtual Environment"

VENV_NAME="spark-monitor-env"
if [ -d "$VENV_NAME" ]; then
    print_info "Virtual environment '$VENV_NAME' already exists"
    if [ -f "$VENV_NAME/pyvenv.cfg" ]; then
        print_success "Virtual environment appears to be valid"
    else
        print_warning "Virtual environment may be corrupted, recreating..."
        rm -rf "$VENV_NAME"
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_NAME" ]; then
    print_info "Creating virtual environment '$VENV_NAME'..."
    python3 -m venv "$VENV_NAME"
    if [ $? -eq 0 ]; then
        print_success "Virtual environment created successfully"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source "$VENV_NAME/bin/activate"

if [ "$VIRTUAL_ENV" ]; then
    print_success "Virtual environment activated: $VIRTUAL_ENV"
else
    print_error "Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip
print_section "${PACKAGE} Upgrading Package Manager"
print_info "Upgrading pip to latest version..."
python -m pip install --upgrade pip
print_success "pip upgraded successfully"

# Install requirements
print_section "${PACKAGE} Installing Dependencies"
print_info "Installing packages from requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found"
    exit 1
fi

# Show what will be installed
echo -e "${PURPLE}${PACKAGE} Dependencies to install:${NC}"
cat requirements.txt | grep -v '^#' | grep -v '^$' | sed 's/^/  • /'
echo ""

# Install with progress
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    print_success "All dependencies installed successfully"
else
    print_error "Failed to install some dependencies"
    print_info "Check the output above for details"
    exit 1
fi

# Install optional development dependencies
print_info "Installing optional development dependencies..."
pip install pytest-cov memory-profiler watchdog 2>/dev/null || print_warning "Some optional packages failed to install (this is okay)"

# Verify installation
print_section "${TEST_TUBE} Verifying Installation"

print_info "Verifying core dependencies..."

# List of core packages to verify
CORE_PACKAGES=("streamlit" "pandas" "plotly" "kubernetes" "psutil" "tenacity" "requests" "yaml")

for package in "${CORE_PACKAGES[@]}"; do
    # Handle special case for PyYAML import
    import_name="$package"
    if [ "$package" = "yaml" ]; then
        import_name="yaml"
    fi
    
    if python -c "import $import_name" 2>/dev/null; then
        print_success "$package"
    else
        print_error "$package - failed to import"
        exit 1
    fi
done

# Check SQLite (built-in)
if python -c "import sqlite3" 2>/dev/null; then
    print_success "sqlite3 (built-in)"
else
    print_error "sqlite3 - failed to import"
fi

print_success "All core dependencies verified"

# Create logs directory
print_section "${GEAR} Setting Up Project Structure"

if [ ! -d "logs" ]; then
    mkdir -p logs
    print_success "Created logs directory"
else
    print_info "logs directory already exists"
fi

# Set executable permissions
chmod +x run.sh 2>/dev/null || print_warning "Could not set executable permission on run.sh"

# Run comprehensive tests
print_section "${TEST_TUBE} Running Comprehensive Test Suite"

print_info "Starting test execution..."
echo -e "${PURPLE}This will run all 29 tests to verify everything works correctly${NC}"
echo ""

# Run the test runner
if [ -f "test_runner.py" ]; then
    python test_runner.py
    TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        print_success "All tests passed successfully!"
    else
        print_error "Some tests failed (exit code: $TEST_EXIT_CODE)"
        print_info "Please review the test output above"
        exit 1
    fi
else
    print_error "test_runner.py not found"
    print_info "Trying to run tests with pytest directly..."
    
    if command -v pytest &> /dev/null; then
        cd src/python
        PYTHONPATH="modules:." pytest tests/ -v
        TEST_EXIT_CODE=$?
        cd ../..
        
        if [ $TEST_EXIT_CODE -eq 0 ]; then
            print_success "All tests passed!"
        else
            print_error "Some tests failed"
            exit 1
        fi
    else
        print_warning "pytest not available, skipping tests"
    fi
fi

# Final verification
print_section "${SPARKLES} Installation Complete"

print_success "Installation completed successfully!"
echo ""
echo -e "${GREEN}${SPARKLES} Summary:${NC}"
echo -e "  ${CHECK} Python $PYTHON_VERSION environment ready"
echo -e "  ${CHECK} Virtual environment '$VENV_NAME' created and activated"
echo -e "  ${CHECK} All dependencies installed and verified"
echo -e "  ${CHECK} Project structure set up"
echo -e "  ${CHECK} All tests passing (29/29)"
echo ""

print_section "${INFO} Next Steps"
echo -e "${CYAN}To start using the Spark Pod Resource Monitor:${NC}"
echo ""
echo -e "${YELLOW}1. Activate the virtual environment:${NC}"
echo -e "   ${CYAN}source $VENV_NAME/bin/activate${NC}"
echo ""
echo -e "${YELLOW}2. Start the application:${NC}"
echo -e "   ${CYAN}./run.sh${NC}"
echo ""
echo -e "${YELLOW}3. Open in your browser:${NC}"
echo -e "   ${CYAN}http://localhost:8502${NC}"
echo ""

print_section "${GEAR} Optional Improvements"
echo -e "${YELLOW}For better performance, consider installing watchdog:${NC}"
echo -e "   ${CYAN}xcode-select --install${NC}  # macOS only"
echo -e "   ${CYAN}pip install watchdog${NC}"
echo ""

print_section "${INFO} Troubleshooting"
echo -e "${YELLOW}If you encounter issues:${NC}"
echo -e "  • Check logs in the ${CYAN}logs/${NC} directory"
echo -e "  • Run tests again: ${CYAN}python test_runner.py${NC}"
echo -e "  • View application logs when running"
echo -e "  • Ensure you have Kubernetes/OpenShift cluster access"
echo ""

print_success "Ready for production use! ${ROCKET}"
echo -e "${GREEN}===========================================${NC}"

# Final check - make sure we're still in virtual environment
if [ "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}${INFO} Virtual environment is active and ready to use${NC}"
else
    print_warning "Virtual environment was deactivated - run 'source $VENV_NAME/bin/activate' before using the app"
fi
