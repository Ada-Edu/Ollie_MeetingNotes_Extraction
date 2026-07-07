# End-to-End Test Suite

Comprehensive E2E tests for the Meeting Notes Action Item Extraction application.

## Overview

This test suite covers the complete user journey from frontend submission through AI processing to database persistence and result display.

## Test Coverage

### Frontend E2E Tests (Playwright)

Located in `/frontend/e2e/`:

#### 1. Complete Extraction Flow (`complete-extraction-flow.spec.ts`)
- Full submission to results workflow
- Minimal action items handling
- Results persistence across page refresh
- Confidence score display
- Unassigned owners (anti-hallucination)
- No due dates (anti-hallucination)
- Model provider information display

**Run**: `npm run test:e2e`

#### 2. Error Handling (`error-handling.spec.ts`)
- Empty input validation
- Too short input validation
- Maximum character limit enforcement
- API server unavailable
- Workflow trigger failure
- Model API failure handling
- Database persistence errors
- Network interruption recovery
- User-friendly error messages
- Retry after error

**Run**: `npm run test:e2e -- error-handling`

#### 3. Status Polling (`status-polling.spec.ts`)
- Extraction run creation with processing status
- Polling every 2 seconds
- Stop polling on completion
- Stop polling on failure
- Real-time status updates
- Results display on completion
- Network delay handling
- UI state maintenance during polling
- Immediate UI updates on status change
- Rapid successive submissions
- Resume polling after visibility change

**Run**: `npm run test:e2e -- status-polling`

#### 4. Multi-Browser Compatibility (`multi-browser.spec.ts`)
- Chromium support
- Firefox support
- WebKit support
- Consistent UI rendering
- Form submission across browsers
- CSS animations
- Text input handling
- Button interactions
- Results display consistency
- Navigation
- Keyboard navigation
- Fetch API compatibility
- WebSocket connections
- Long-running operations
- LocalStorage support
- Font rendering
- JSON parsing

**Run**: `npm run test:e2e -- --project=chromium,firefox,webkit`

#### 5. Accessibility (`accessibility.spec.ts`)
- Document structure
- Form labels
- Keyboard navigation
- Focus indicators
- ARIA attributes
- Screen reader announcements
- Button state descriptions
- Color contrast
- Form validation errors
- Semantic HTML
- Icon/image context
- Focus management
- High contrast mode
- Reduced motion preference
- Loading state feedback
- Clear error messages
- Proper button labels

**Run**: `npm run test:e2e -- accessibility`

#### 6. Responsive Design (`responsive-design.spec.ts`)
- Mobile viewport (iPhone 12)
- Tablet viewport (iPad Pro)
- Desktop viewport (1920x1080)
- Touch-friendly buttons
- Vertical stacking on mobile
- Mobile keyboard handling
- Mobile scrolling
- Results without overflow
- Text size readability
- Tablet space utilization
- Touch and mouse support
- Max-width constraints
- Content centering
- Viewport transitions
- Portrait orientation
- Landscape orientation
- Common breakpoints (320px - 1920px)
- Touch interactions
- Font scaling
- Flexible layouts
- Image scaling
- Spacing and padding

**Run**: `npm run test:e2e -- responsive-design`

### Backend Integration Tests (Pytest)

Located in `/temporal/tests/test_e2e_workflow.py`:

#### 1. Complete Extraction Flow
- Full workflow execution
- Minimal notes processing
- Unassigned owners handling
- No due dates handling

#### 2. Error Handling
- Too short notes validation
- Failure recording in database

#### 3. API Server Integration
- Workflow trigger via API
- Health check endpoint
- Invalid workflow rejection
- Missing arguments rejection

#### 4. Database Persistence
- Extraction run creation
- Action items linking
- Cascade deletion

**Run**: `cd temporal && pytest tests/test_e2e_workflow.py -v`

## Prerequisites

### Frontend Tests
```bash
cd frontend
npm install
npm install -D @playwright/test
npx playwright install
```

### Backend Tests
```bash
cd temporal
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx
```

### Required Services
- Supabase (local): `supabase start`
- Temporal Server: `docker compose up temporal temporal-db`
- Temporal Worker: `cd temporal && python start_all.py`
- Frontend Dev Server: `cd frontend && npm run dev`

## Running Tests

### Run All Frontend E2E Tests
```bash
cd frontend
npm run test:e2e
```

### Run Specific Test File
```bash
cd frontend
npm run test:e2e -- complete-extraction-flow
```

### Run in UI Mode (Interactive)
```bash
cd frontend
npm run test:e2e:ui
```

### Run in Specific Browser
```bash
cd frontend
npm run test:e2e -- --project=chromium
npm run test:e2e -- --project=firefox
npm run test:e2e -- --project=webkit
```

### Run All Backend Tests
```bash
cd temporal
pytest tests/test_e2e_workflow.py -v
```

### Run Specific Test Class
```bash
cd temporal
pytest tests/test_e2e_workflow.py::TestCompleteExtractionFlow -v
```

### Run with Coverage
```bash
cd temporal
pytest tests/test_e2e_workflow.py --cov=src --cov-report=html
```

## Test Configuration

### Playwright Configuration
File: `/frontend/playwright.config.ts`

Key settings:
- Base URL: `http://localhost:3000`
- Timeout: 30 seconds
- Retries: 2 (on CI)
- Projects: Chromium, Firefox, WebKit
- Web Server: Auto-starts dev server

### Pytest Configuration
File: `/temporal/pytest.ini`

Key settings:
- Async support: pytest-asyncio
- Test discovery: `test_*.py`
- Markers: asyncio, integration

## Environment Variables

### Frontend Tests
```bash
VITE_SUPABASE_URL=http://localhost:54321
VITE_SUPABASE_ANON_KEY=<anon-key>
```

### Backend Tests
```bash
TEMPORAL_ADDRESS=localhost:7233
SUPABASE_URL=http://localhost:54321
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
API_URL=http://localhost:8000

# AI Model Configuration
MODEL_PROVIDER=bedrock
AWS_REGION=af-south-1
AWS_BEARER_TOKEN_BEDROCK=<bearer-token>
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-6
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  frontend-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: Install Playwright
        run: npx playwright install --with-deps
      - name: Start services
        run: |
          docker compose up -d
          cd temporal && python start_all.py &
      - name: Run E2E tests
        run: cd frontend && npm run test:e2e
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: frontend/playwright-report/

  backend-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: cd temporal && pip install -r requirements.txt && pip install pytest pytest-asyncio
      - name: Start services
        run: docker compose up -d
      - name: Run integration tests
        run: cd temporal && pytest tests/test_e2e_workflow.py -v
```

## Test Data

### Sample Meeting Notes
Located in test files and can be customized per test.

Example:
```
Team Standup - July 7, 2026
Attendees: Sarah (PM), John (Dev), Mike (Architect)

Yesterday:
- Completed user authentication
- Fixed database pooling

Today:
- Working on API documentation
- Starting payment integration

Action Items:
1. John to follow up with Sarah on Q4 budget by July 15
2. Mike to review the architectural design doc by next week
3. Sarah to schedule a meeting with design team ASAP
```

## Debugging

### Frontend Tests

**View Test Report**:
```bash
cd frontend
npm run test:e2e:report
```

**Run in Debug Mode**:
```bash
cd frontend
npx playwright test --debug
```

**Record Test**:
```bash
cd frontend
npx playwright codegen http://localhost:3000/meeting-notes
```

### Backend Tests

**Verbose Output**:
```bash
cd temporal
pytest tests/test_e2e_workflow.py -v -s
```

**Debug with Print Statements**:
```bash
cd temporal
pytest tests/test_e2e_workflow.py -v -s --log-cli-level=DEBUG
```

**Run Single Test**:
```bash
cd temporal
pytest tests/test_e2e_workflow.py::TestCompleteExtractionFlow::test_complete_workflow_execution -v
```

## Troubleshooting

### Frontend Tests Failing

**Issue**: Tests timeout waiting for elements
**Solution**: 
- Ensure backend services are running
- Check `http://localhost:3000` is accessible
- Increase timeout in test if needed

**Issue**: "Page not found" errors
**Solution**:
- Verify frontend dev server is running
- Check route is defined in `/frontend/src/routes/`

### Backend Tests Failing

**Issue**: "Connection refused" to Temporal
**Solution**:
- Start Temporal: `docker compose up temporal temporal-db`
- Check Temporal UI: `http://localhost:8080`

**Issue**: "Connection refused" to Supabase
**Solution**:
- Start Supabase: `supabase start`
- Check Supabase Studio: `http://localhost:54323`

**Issue**: Model API errors
**Solution**:
- Verify AWS credentials in `.env`
- Test connection: `python test_bedrock_final.py`
- Check model ID is correct

## Performance Benchmarks

Expected test durations:

### Frontend E2E Tests
- Complete extraction flow: 45-60 seconds
- Error handling: 10-30 seconds
- Status polling: 45-60 seconds
- Multi-browser: 5-10 seconds per browser
- Accessibility: 10-20 seconds
- Responsive design: 20-40 seconds

**Total**: ~5-10 minutes (parallel execution)

### Backend Integration Tests
- Complete workflow: 30-60 seconds per test
- Error handling: 10-20 seconds per test
- API integration: 5-10 seconds per test
- Database persistence: 30-60 seconds per test

**Total**: ~3-5 minutes

## Continuous Improvement

### Adding New Tests
1. Identify user flow or edge case
2. Create test file in appropriate directory
3. Follow naming convention: `*.spec.ts` or `test_*.py`
4. Add descriptive test names
5. Include cleanup/teardown
6. Update this README

### Test Maintenance
- Review test failures regularly
- Update selectors if UI changes
- Adjust timeouts as needed
- Keep test data realistic
- Document known issues

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Temporal Testing Guide](https://docs.temporal.io/develop/python/testing)
- [Supabase Local Development](https://supabase.com/docs/guides/cli/local-development)

## Support

For test-related issues:
1. Check test output for error messages
2. Review troubleshooting section
3. Check service logs
4. Verify environment variables
5. Create issue with full error output

---

**Last Updated**: July 7, 2026
**Test Suite Version**: 1.0.0
**Coverage**: Frontend E2E, Backend Integration, Multi-Browser, Accessibility, Responsive
