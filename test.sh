#!/bin/bash
# Spark Pod Resource Monitor - Test Script
# Runs unit tests, integration tests, or the full suite
# Created: September 7, 2025

set -euo pipefail

# Colors & Emojis (same style as install.sh)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

CHECK="✅"
CROSS="❌"
INFO="ℹ️"
TEST_TUBE="🧪"

echo -e "${CYAN}${TEST_TUBE} Spark Pod Resource Monitor - Test Runner${NC}"
echo -e "${CYAN}==============================================${NC}"

# Helpers
section() { echo -e "${BLUE}$1${NC}\n${BLUE}$(printf '%*s' "${#1}" '' | tr ' ' '=')${NC}"; }
ok() { echo -e "${GREEN}${CHECK} $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err() { echo -e "${RED}${CROSS} $1${NC}"; }
info() { echo -e "${CYAN}${INFO} $1${NC}"; }

# Determine paths
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$ROOT_DIR/src/python"
MODULES_DIR="$SRC_DIR/modules"

# Activate virtual environment if available
section "Environment"
if [[ -d "$ROOT_DIR/spark-monitor-env" && -f "$ROOT_DIR/spark-monitor-env/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT_DIR/spark-monitor-env/bin/activate" || warn "Could not activate virtual environment"
  ok "Virtual environment active: ${VIRTUAL_ENV:-system}"
else
  warn "Virtual environment not found, using system Python"
fi

PYTHON_BIN="${PYTHON:-${VIRTUAL_ENV:+$VIRTUAL_ENV/bin/python}}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Validate pytest is available
section "Dependency Check"
if "$PYTHON_BIN" -c "import pytest" >/dev/null 2>&1; then
  ok "pytest available"
else
  err "pytest is not installed. Install with: pip install pytest"
  exit 1
fi

# Build pytest command with optional coverage
PYTEST_BASE=("$PYTHON_BIN" -m pytest -v --tb=short --no-header --color=yes)
if "$PYTHON_BIN" -c "import pytest_cov" >/dev/null 2>&1; then
  PYTEST_BASE+=("--cov=modules" "--cov-report=term-missing")
fi

# Ensure PYTHONPATH
export PYTHONPATH="$MODULES_DIR:$SRC_DIR:${PYTHONPATH:-}"

# What to run
TARGET="${1:-all}"
case "$TARGET" in
  -h|--help|help)
    echo "Usage: ./test.sh [all|unit|integration]"
    echo "  all          Run complete test suite (default)"
    echo "  unit         Run unit tests only (database, utils, mock_data)"
    echo "  integration  Run integration tests only"
    exit 0
    ;;
  all)
    section "Running Complete Test Suite"
    if [[ -f "$ROOT_DIR/test_runner.py" ]]; then
      (cd "$ROOT_DIR" && "$PYTHON_BIN" test_runner.py)
    else
      (cd "$SRC_DIR" && "${PYTEST_BASE[@]}" tests/)
    fi
    ;;
  unit)
    section "Running Unit Tests"
    (cd "$SRC_DIR" && "${PYTEST_BASE[@]}" \
      tests/test_database.py \
      tests/test_utils.py \
      tests/test_mock_data.py)
    ;;
  integration)
    section "Running Integration Tests"
    (cd "$SRC_DIR" && "${PYTEST_BASE[@]}" tests/test_integration.py)
    ;;
  *)
    err "Unknown target: $TARGET"
    echo "Usage: ./test.sh [all|unit|integration]"
    exit 1
    ;;
esac

ok "Tests completed"
