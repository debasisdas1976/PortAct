#!/usr/bin/env bash
#
# PortAct Pre-release Test Suite
# Run all backend and frontend tests with coverage.
# Exit code 0 = all passed, non-zero = failure.
#
# Usage:
#   bash scripts/run_tests.sh            # Run everything
#   bash scripts/run_tests.sh backend    # Backend only
#   bash scripts/run_tests.sh frontend   # Frontend only
#
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

BACKEND_PASS=0
FRONTEND_PASS=0
BACKEND_EXIT=0
FRONTEND_EXIT=0
RUN_BACKEND=true
RUN_FRONTEND=true

# Parse optional argument
if [ "${1:-}" = "backend" ]; then
    RUN_FRONTEND=false
elif [ "${1:-}" = "frontend" ]; then
    RUN_BACKEND=false
fi

echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  PortAct Pre-release Test Suite${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""

# ── Backend ──────────────────────────────────────────────────

if [ "$RUN_BACKEND" = true ]; then
    echo -e "${BOLD}[1/4] Backend Lint (flake8 — syntax errors only)${NC}"
    cd "$PROJECT_ROOT/backend"

    # Activate venv if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    if python -m flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics 2>/dev/null; then
        echo -e "  ${GREEN}PASS${NC} — No syntax errors"
    else
        echo -e "  ${RED}FAIL${NC} — Syntax errors detected"
        BACKEND_EXIT=1
    fi

    echo ""
    echo -e "${BOLD}[2/4] Backend Tests (pytest + coverage)${NC}"
    # DATABASE_URL must be a PG-compatible URL so database.py engine creation
    # doesn't fail (pool_size/max_overflow are PG-only). The actual test DB
    # is controlled by TEST_DATABASE_URL (defaults to SQLite in conftest.py).
    export DATABASE_URL="${DATABASE_URL:-postgresql://localhost/portact_test_dummy}"
    export TEST_DATABASE_URL="${TEST_DATABASE_URL:-sqlite:///}"
    export SECRET_KEY="${SECRET_KEY:-test-secret-key}"
    export ENVIRONMENT="${ENVIRONMENT:-test}"

    if python -m pytest tests/ -v \
        --cov=app \
        --cov-config=.coveragerc \
        --cov-report=term-missing \
        --cov-report=html:htmlcov \
        --tb=short \
        -q; then
        BACKEND_PASS=1
        echo -e "  ${GREEN}PASS${NC}"
    else
        echo -e "  ${RED}FAIL${NC}"
        BACKEND_EXIT=1
    fi
else
    echo -e "${YELLOW}  SKIP${NC} — Backend tests (--frontend only)"
    BACKEND_PASS=1
fi

echo ""

# ── Frontend ─────────────────────────────────────────────────

if [ "$RUN_FRONTEND" = true ]; then
    echo -e "${BOLD}[3/4] Frontend Lint${NC}"
    cd "$PROJECT_ROOT/frontend"
    echo -e "  ${YELLOW}SKIP${NC} — CRA handles lint during build"

    echo ""
    echo -e "${BOLD}[4/4] Frontend Tests (jest + coverage)${NC}"
    if CI=true npx react-scripts test --coverage --watchAll=false --verbose 2>&1; then
        FRONTEND_PASS=1
        echo -e "  ${GREEN}PASS${NC}"
    else
        echo -e "  ${RED}FAIL${NC}"
        FRONTEND_EXIT=1
    fi
else
    echo -e "${YELLOW}  SKIP${NC} — Frontend tests (--backend only)"
    FRONTEND_PASS=1
fi

echo ""

# ── Summary ──────────────────────────────────────────────────

echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  SUMMARY${NC}"
echo -e "${BOLD}============================================${NC}"

if [ "$RUN_BACKEND" = true ]; then
    if [ $BACKEND_PASS -eq 1 ]; then
        echo -e "  Backend tests:  ${GREEN}PASS${NC}"
    else
        echo -e "  Backend tests:  ${RED}FAIL${NC}"
    fi
fi

if [ "$RUN_FRONTEND" = true ]; then
    if [ $FRONTEND_PASS -eq 1 ]; then
        echo -e "  Frontend tests: ${GREEN}PASS${NC}"
    else
        echo -e "  Frontend tests: ${RED}FAIL${NC}"
    fi
fi

echo ""

if [ "$RUN_BACKEND" = true ]; then
    echo "  Backend coverage:  backend/htmlcov/index.html"
fi
if [ "$RUN_FRONTEND" = true ]; then
    echo "  Frontend coverage: frontend/coverage/lcov-report/index.html"
fi

echo ""

EXIT_CODE=$((BACKEND_EXIT + FRONTEND_EXIT))
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "  ${GREEN}${BOLD}ALL CHECKS PASSED — Ready for release${NC}"
else
    echo -e "  ${RED}${BOLD}CHECKS FAILED — Fix issues before release${NC}"
fi

exit $EXIT_CODE
