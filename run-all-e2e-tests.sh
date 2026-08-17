#!/bin/bash

# Complete E2E Test Suite Runner
# Validates all required services and runs comprehensive test suite

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test report locations
BACKEND_REPORT="./backend/test-reports"
FRONTEND_REPORT="./frontend/playwright-report"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  E2E Test Suite Execution${NC}"
echo -e "${BLUE}  Started: $(date)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check service health
check_service() {
    local service_name=$1
    local health_url=$2
    local max_retries=5
    local retry_count=0

    echo -e "${YELLOW}Checking ${service_name}...${NC}"

    while [ $retry_count -lt $max_retries ]; do
        if curl -sf "$health_url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ ${service_name} is running${NC}"
            return 0
        fi
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            echo -e "${YELLOW}  Retry $retry_count/$max_retries...${NC}"
            sleep 2
        fi
    done

    echo -e "${RED}✗ ${service_name} is not responding${NC}"
    return 1
}

# Function to run command with status reporting
run_test_suite() {
    local suite_name=$1
    local command=$2

    echo ""
    echo -e "${BLUE}----------------------------------------${NC}"
    echo -e "${BLUE}Running: ${suite_name}${NC}"
    echo -e "${BLUE}----------------------------------------${NC}"

    if eval "$command"; then
        echo -e "${GREEN}✓ ${suite_name} PASSED${NC}"
        return 0
    else
        echo -e "${RED}✗ ${suite_name} FAILED${NC}"
        return 1
    fi
}

# Track overall test status
TESTS_PASSED=0
TESTS_FAILED=0
SERVICES_OK=true

# Service Health Checks
echo -e "${BLUE}Step 1: Service Health Checks${NC}"
echo "================================"

if ! check_service "Supabase" "http://localhost:54321/rest/v1/"; then
    SERVICES_OK=false
fi

if ! check_service "Temporal" "http://localhost:7233"; then
    SERVICES_OK=false
fi

if ! check_service "API Server" "http://localhost:8000/health"; then
    SERVICES_OK=false
fi

if ! check_service "Frontend" "http://localhost:3000"; then
    SERVICES_OK=false
fi

if [ "$SERVICES_OK" = false ]; then
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ERROR: Not all services are running${NC}"
    echo -e "${RED}  Please start all required services${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi

echo -e "${GREEN}All services are running!${NC}"
echo ""

# Backend Integration Tests
echo -e "${BLUE}Step 2: Backend Integration Tests${NC}"
echo "=================================="

if run_test_suite "Backend Integration Tests (pytest)" "cd backend && pytest tests/integration/ -v --tb=short --html=$BACKEND_REPORT/report_${TIMESTAMP}.html --self-contained-html"; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Frontend Playwright Tests
echo ""
echo -e "${BLUE}Step 3: Frontend E2E Tests (Playwright)${NC}"
echo "========================================"

# Complete Flow Tests
if run_test_suite "Complete Flow Tests" "cd frontend && npx playwright test tests/e2e/complete-flow.spec.ts"; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Error Handling Tests
if run_test_suite "Error Handling Tests" "cd frontend && npx playwright test tests/e2e/error-handling.spec.ts"; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Status Polling Tests
if run_test_suite "Status Polling Tests" "cd frontend && npx playwright test tests/e2e/status-polling.spec.ts"; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Multi-Browser Tests
if run_test_suite "Multi-Browser Tests" "cd frontend && npx playwright test --project=chromium --project=firefox --project=webkit"; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Accessibility Tests
if run_test_suite "Accessibility Tests" "cd frontend && npx playwright test tests/e2e/accessibility.spec.ts"; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Responsive Design Tests
if run_test_suite "Responsive Design Tests" "cd frontend && npx playwright test tests/e2e/responsive.spec.ts"; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Test Execution Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Completed: $(date)"
echo ""
echo -e "Test Suites Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Test Suites Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

# Report Locations
echo -e "${BLUE}Test Report Locations:${NC}"
echo "----------------------"
echo -e "Backend Reports:  ${YELLOW}${BACKEND_REPORT}/${NC}"
echo -e "Frontend Reports: ${YELLOW}${FRONTEND_REPORT}/${NC}"
echo ""

# View reports commands
echo -e "${BLUE}View Reports:${NC}"
echo "-------------"
echo -e "Backend:  ${YELLOW}open ${BACKEND_REPORT}/report_${TIMESTAMP}.html${NC}"
echo -e "Frontend: ${YELLOW}npx playwright show-report${NC}"
echo ""

# Exit with appropriate status
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  SOME TESTS FAILED${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
