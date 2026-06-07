#!/bin/bash
#
# Post-receive hook for Botocharcoal deployment
# Install this at: /root/botocharcoal.ir.git/hooks/post-receive
#
# This hook automatically:
# 1. Checks out files from the bare repo to /var/www/botocharcoal.ir
# 2. Installs/updates Python dependencies
# 3. Runs Alembic migrations
# 4. Restarts systemd services
# 5. Provides comprehensive logging
#

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

REPO_PATH="/root/botocharcoal.ir.git"
WORK_DIR="/var/www/botocharcoal.ir"
VENV_PATH="${WORK_DIR}/venv"
PYTHON_BIN="${VENV_PATH}/bin/python3"
PIP_BIN="${VENV_PATH}/bin/pip"
ALEMBIC_BIN="${VENV_PATH}/bin/alembic"
LOG_DIR="${WORK_DIR}/logs"
LOG_FILE="${LOG_DIR}/deployment.log"

# Color codes for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Logging Functions
# ============================================================================

log_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

log_info() {
    echo -e "${BLUE}[$(log_timestamp)] [INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(log_timestamp)] [SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(log_timestamp)] [WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(log_timestamp)] [ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# ============================================================================
# Setup
# ============================================================================

# Ensure log directory exists
mkdir -p "$LOG_DIR"

log_info "=========================================="
log_info "Botocharcoal Post-Receive Hook Started"
log_info "=========================================="
log_info "Repo: $REPO_PATH"
log_info "Work Dir: $WORK_DIR"
log_info "Virtual Env: $VENV_PATH"

# ============================================================================
# Step 1: Checkout Repository
# ============================================================================

log_info "Step 1: Checking out files from repository..."

if [ ! -d "$WORK_DIR" ]; then
    log_info "Creating working directory: $WORK_DIR"
    mkdir -p "$WORK_DIR"
fi

# Use git worktree or archive to checkout files
cd "$REPO_PATH"

if ! git --work-tree="$WORK_DIR" checkout -f HEAD; then
    log_error "Failed to checkout files"
    exit 1
fi

log_success "Files checked out successfully"

# ============================================================================
# Step 2: Setup Virtual Environment
# ============================================================================

log_info "Step 2: Setting up Python virtual environment..."

cd "$WORK_DIR"

if [ ! -d "$VENV_PATH" ]; then
    log_info "Creating new virtual environment..."
    if ! python3.11 -m venv "$VENV_PATH"; then
        log_error "Failed to create virtual environment"
        exit 1
    fi
    log_success "Virtual environment created"
else
    log_info "Virtual environment already exists"
fi

# Activate virtual environment
source "${VENV_PATH}/bin/activate"

# ============================================================================
# Step 3: Install/Update Dependencies
# ============================================================================

log_info "Step 3: Installing/updating Python dependencies..."

# Upgrade pip, setuptools, wheel
log_info "Upgrading pip, setuptools, and wheel..."
if ! "$PIP_BIN" install --upgrade pip setuptools wheel >> "$LOG_FILE" 2>&1; then
    log_error "Failed to upgrade pip/setuptools/wheel"
    exit 1
fi

# Install requirements
if [ ! -f "$WORK_DIR/requirements.txt" ]; then
    log_error "requirements.txt not found in $WORK_DIR"
    exit 1
fi

log_info "Installing requirements from requirements.txt..."
if ! "$PIP_BIN" install -r "$WORK_DIR/requirements.txt" >> "$LOG_FILE" 2>&1; then
    log_error "Failed to install requirements"
    exit 1
fi

log_success "Dependencies installed successfully"

# ============================================================================
# Step 4: Validate Environment
# ============================================================================

log_info "Step 4: Validating environment..."

# Check if .env file exists
if [ ! -f "$WORK_DIR/.env" ]; then
    log_warning ".env file not found. Using .env.example as reference"
    if [ -f "$WORK_DIR/.env.example" ]; then
        log_info "Please configure .env manually at $WORK_DIR/.env"
    fi
else
    log_success ".env file exists"
fi

# Verify required environment variables
required_vars=("APP_ENV" "DATABASE_URL" "REDIS_URL" "SECRET_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" "$WORK_DIR/.env" 2>/dev/null; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    log_warning "Missing environment variables: ${missing_vars[*]}"
    log_warning "Please add these to $WORK_DIR/.env"
fi

# ============================================================================
# Step 5: Run Database Migrations
# ============================================================================

log_info "Step 5: Running Alembic migrations..."

cd "$WORK_DIR"

# Check if alembic.ini exists
if [ ! -f "$WORK_DIR/alembic.ini" ]; then
    log_error "alembic.ini not found"
    exit 1
fi

# Load environment variables
set -a
source "$WORK_DIR/.env" 2>/dev/null || true
set +a

# Run migrations
if ! "$ALEMBIC_BIN" upgrade head >> "$LOG_FILE" 2>&1; then
    log_error "Database migrations failed"
    log_error "Check logs at: $LOG_FILE"
    exit 1
fi

log_success "Database migrations completed successfully"

# ============================================================================
# Step 6: Verify Application Syntax
# ============================================================================

log_info "Step 6: Verifying Python syntax..."

# Find all Python files and compile them
python_files=$(find "$WORK_DIR/app" -name "*.py" -type f 2>/dev/null | wc -l)
log_info "Found $python_files Python files to check"

if ! find "$WORK_DIR/app" -name "*.py" -type f -exec "$PYTHON_BIN" -m py_compile {} \; >> "$LOG_FILE" 2>&1; then
    log_error "Python syntax check failed"
    exit 1
fi

log_success "Python syntax verified"

# ============================================================================
# Step 7: Restart Services
# ============================================================================

log_info "Step 7: Restarting systemd services..."

# List of services to restart
services=(
    "botocharcoal-web.service"
    "botocharcoal-worker.service"
    "botocharcoal-beat.service"
)

for service in "${services[@]}"; do
    log_info "Restarting $service..."
    
    if ! sudo systemctl restart "$service" >> "$LOG_FILE" 2>&1; then
        log_error "Failed to restart $service"
        log_warning "Attempting to check service status..."
        sudo systemctl status "$service" 2>&1 | tee -a "$LOG_FILE" || true
    else
        log_success "$service restarted"
    fi
done

# Wait a moment for services to stabilize
sleep 2

# Verify services are running
log_info "Verifying services are running..."
all_running=true

for service in "${services[@]}"; do
    if sudo systemctl is-active --quiet "$service"; then
        log_success "$service is running"
    else
        log_error "$service is NOT running"
        all_running=false
    fi
done

# ============================================================================
# Step 8: Run Health Checks
# ============================================================================

log_info "Step 8: Running health checks..."

# Simple health check - verify application can import
log_info "Verifying application imports..."
if ! "$PYTHON_BIN" -c "from app.main import app; print('Application imports successfully')" >> "$LOG_FILE" 2>&1; then
    log_error "Application import failed"
    exit 1
fi

log_success "Application imports successfully"

# ============================================================================
# Summary
# ============================================================================

log_info "=========================================="
if [ "$all_running" = true ]; then
    log_success "Deployment completed successfully!"
    log_success "All services are running"
else
    log_warning "Deployment completed with warnings"
    log_warning "Some services may not be running - check logs"
fi

log_info "=========================================="
log_info "Logs available at: $LOG_FILE"
log_info "Next steps:"
log_info "1. Verify services: sudo systemctl status botocharcoal-*.service"
log_info "2. Check logs: tail -f $LOG_FILE"
log_info "3. Monitor application: tail -f $LOG_DIR/error.log"
log_info "=========================================="

exit 0
