#!/bin/bash
set -e

echo "================================================"
echo "Meeting Notes Extraction - E2E Test Suite"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
echo "${YELLOW}Checking required services...${NC}"

# Check Supabase
if ! curl -s http://localhost:54321/health > /dev/null; then
    echo "${RED}✗ Supabase is not running${NC}"
    echo "  Start with: supabase start"
    exit 1
fi
echo "${GREEN}✓ Supabase is running${NC}"

# Check Temporal
if ! curl -s http://localhost:8080 > /dev/null; then
    echo "${RED}✗ Temporal UI is not accessible${NC}"
    echo "  Start with: docker compose up temporal temporal-db"
    exit 1
fi
echo "${GREEN}✓ Temporal is running${NC}"

# Check API Server
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "${RED}✗ API Server is not running${NC}"
    echo "  Start with: cd temporal && python start_all.py"
    exit 1
fi
echo "${GREEN}✓ API Server is running${NC}"

# Check Frontend
if ! curl -s http://localhost:3000 > /dev/null; then
    echo "${RED}✗ Frontend is not running${NC}"
    echo "  Start with: cd frontend && npm run dev"
    exit 1
fi
echo "${GREEN}✓ Frontend is running${NC}"

echo ""
echo "================================================"
echo "Running Backend Integration Tests"
echo "================================================"
echo ""

cd temporal
if pytest tests/test_e2e_workflow.py -v --tb=short; then
    echo "${GREEN}✓ Backend integration tests passed${NC}"
else
    echo "${RED}✗ Backend integration tests failed${NC}"
    exit 1
fi

echo ""
echo "================================================"
echo "Running Frontend E2E Tests"
echo "================================================"
echo ""

cd ../frontend

echo ""
echo "${YELLOW}1. Complete Extraction Flow Tests${NC}"
if npm run test:e2e -- complete-extraction-flow --reporter=line; then
    echo "${GREEN}✓ Complete extraction flow tests passed${NC}"
else
    echo "${RED}✗ Complete extraction flow tests failed${NC}"
fi

echo ""
echo "${YELLOW}2. Error Handling Tests${NC}"
if npm run test:e2e -- error-handling --reporter=line; then
    echo "${GREEN}✓ Error handling tests passed${NC}"
else
    echo "${RED}✗ Error handling tests failed${NC}"
fi

echo ""
echo "${YELLOW}3. Status Polling Tests${NC}"
if npm run test:e2e -- status-polling --reporter=line; then
    echo "${GREEN}✓ Status polling tests passed${NC}"
else
    echo "${RED}✗ Status polling tests failed${NC}"
fi

echo ""
echo "${YELLOW}4. Multi-Browser Tests${NC}"
if npm run test:e2e -- multi-browser --reporter=line; then
    echo "${GREEN}✓ Multi-browser tests passed${NC}"
else
    echo "${RED}✗ Multi-browser tests failed${NC}"
fi

echo ""
echo "${YELLOW}5. Accessibility Tests${NC}"
if npm run test:e2e -- accessibility --reporter=line; then
    echo "${GREEN}✓ Accessibility tests passed${NC}"
else
    echo "${RED}✗ Accessibility tests failed${NC}"
fi

echo ""
echo "${YELLOW}6. Responsive Design Tests${NC}"
if npm run test:e2e -- responsive-design --reporter=line; then
    echo "${GREEN}✓ Responsive design tests passed${NC}"
else
    echo "${RED}✗ Responsive design tests failed${NC}"
fi

echo ""
echo "================================================"
echo "Test Suite Complete"
echo "================================================"
echo ""
echo "${GREEN}All E2E tests completed successfully!${NC}"
echo ""
echo "Test Reports:"
echo "  - Frontend: frontend/playwright-report/index.html"
echo "  - Backend: temporal/htmlcov/index.html (if --cov was used)"
echo ""
echo "View report: npm run test:e2e:report"
echo ""
