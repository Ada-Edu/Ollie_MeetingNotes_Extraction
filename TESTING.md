# Testing Guide

This document provides comprehensive information about the testing infrastructure for the Meeting Notes Action Items Extraction project.

## Table of Contents

- [Overview](#overview)
- [Testing Stack](#testing-stack)
- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Writing Tests](#writing-tests)
- [CI/CD Integration](#cicd-integration)
- [Coverage Goals](#coverage-goals)
- [Troubleshooting](#troubleshooting)

## Overview

This project uses a comprehensive three-tier testing strategy:

1. **Unit Tests** - Test individual functions, components, and modules in isolation
2. **Integration Tests** - Test interactions between multiple components and services
3. **End-to-End (E2E) Tests** - Test complete user workflows through the UI

## Testing Stack

### Frontend

- **Test Framework**: Vitest
- **Component Testing**: React Testing Library
- **Mocking**: MSW (Mock Service Worker)
- **E2E Testing**: Playwright
- **Coverage**: Vitest coverage (v8)

### Backend

- **Test Framework**: pytest
- **Async Testing**: pytest-asyncio
- **Mocking**: pytest-mock
- **HTTP Mocking**: pytest-httpx
- **Temporal Testing**: temporalio.testing
- **Coverage**: pytest-cov

## Running Tests

### Frontend Tests

```bash
cd frontend

# Run all tests in watch mode
npm test

# Run unit tests with coverage
npm run test:unit

# Run tests in watch mode
npm run test:watch

# Open Vitest UI
npm run test:ui

# Run E2E tests
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui

# View E2E test report
npm run test:e2e:report
```

### Backend Tests

```bash
cd temporal

# Run all tests
pytest

# Run only unit tests (exclude integration tests)
pytest -m "not integration"

# Run only integration tests
pytest -m integration

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/activities/test_meeting_notes_activities.py

# Run specific test
pytest tests/activities/test_meeting_notes_activities.py::TestValidateMeetingNotesInput::test_valid_input

# Run with verbose output
pytest -v

# Run with output from print statements
pytest -s
```

### All Tests

From the project root:

```bash
# Run all frontend and backend unit tests
make test-all

# Run with coverage report
make test-coverage
```

## Test Structure

### Frontend Test Organization

```
frontend/
├── src/
│   ├── __tests__/
│   │   ├── setup.ts              # Test setup and MSW configuration
│   │   └── mocks/
│   │       ├── handlers.ts       # MSW request handlers
│   │       └── server.ts         # MSW server setup
│   ├── components/
│   │   └── __tests__/
│   │       └── ActionItemsList.test.tsx
│   └── lib/
│       └── hooks/
│           └── __tests__/
│               └── useMeetingNotes.test.ts
└── e2e/
    └── meeting-notes-extraction.spec.ts
```

### Backend Test Organization

```
temporal/
├── tests/
│   ├── conftest.py               # Shared fixtures
│   ├── activities/
│   │   └── test_meeting_notes_activities.py
│   ├── model_client/
│   │   └── test_factory.py
│   └── integration/
│       └── test_workflow_execution.py
└── pytest.ini                    # pytest configuration
```

## Writing Tests

### Frontend Unit Test Example

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MyComponent } from '../MyComponent';

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent title="Test" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});
```

### Frontend Hook Test Example

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMyHook } from '../useMyHook';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('useMyHook', () => {
  it('should fetch data', async () => {
    const { result } = renderHook(() => useMyHook(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});
```

### Backend Unit Test Example

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_my_activity():
    """Test my activity function."""
    # Arrange
    mock_client = Mock()
    mock_client.do_something = AsyncMock(return_value="result")

    # Act
    result = await my_activity(mock_client)

    # Assert
    assert result == "expected"
    mock_client.do_something.assert_called_once()
```

### E2E Test Example

```typescript
import { test, expect } from '@playwright/test';

test('user can submit meeting notes', async ({ page }) => {
  await page.goto('/meeting-notes');

  const notesInput = page.getByPlaceholder('Paste your meeting notes');
  await notesInput.fill('Test meeting notes');

  await page.getByRole('button', { name: 'Extract' }).click();

  await expect(page.getByText('Processing')).toBeVisible();
});
```

## CI/CD Integration

Tests run automatically on:
- Push to `main`, `develop`, or `feature/*` branches
- Pull requests to `main` or `develop`

### GitHub Actions Workflow

The CI pipeline runs:
1. **Frontend unit tests** - Vitest with coverage
2. **Backend unit tests** - pytest with coverage
3. **Linting** - ESLint
4. **Integration tests** - With Supabase local instance
5. **E2E tests** - Playwright with services running

### Viewing Test Results

- **Coverage reports**: Uploaded to Codecov (if configured)
- **E2E test reports**: Available as GitHub Actions artifacts
- **Playwright traces**: Available when tests fail

## Coverage Goals

### Current Targets

- **Frontend**: 75% overall, 80% for business logic
- **Backend**: 80% overall, 90% for critical paths
- **Critical paths**: 100% coverage required

### Critical Paths Requiring 100% Coverage

1. Meeting notes validation activity
2. Model extraction activity
3. Database persistence activity
4. Workflow error handling
5. Frontend submission flow
6. Action items display rendering

### Checking Coverage

```bash
# Frontend coverage
cd frontend
npm run test:unit
# Open frontend/coverage/index.html

# Backend coverage
cd temporal
pytest --cov=src --cov-report=html
# Open temporal/htmlcov/index.html
```

## Test Markers

Backend tests can be marked with pytest markers:

```python
@pytest.mark.unit
def test_my_unit():
    pass

@pytest.mark.integration
def test_my_integration():
    pass

@pytest.mark.e2e
def test_my_e2e():
    pass
```

Run specific markers:
```bash
pytest -m unit        # Run only unit tests
pytest -m integration # Run only integration tests
pytest -m "not integration" # Exclude integration tests
```

## Mocking External Services

### Frontend - MSW

MSW intercepts HTTP requests at the network level:

```typescript
// src/__tests__/mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/data', () => {
    return HttpResponse.json({ data: 'mocked' });
  })
];
```

### Backend - pytest-mock

Mock functions and async operations:

```python
@pytest.mark.asyncio
async def test_with_mock(mocker):
    mock_client = mocker.patch('module.client')
    mock_client.return_value.method = AsyncMock(return_value="result")
    # ... test code
```

## Troubleshooting

### Common Issues

**Frontend tests fail to import modules**
```bash
# Check vitest.config.ts has correct path aliases
# Ensure setup.ts is being loaded
```

**Backend async tests hang**
```bash
# Ensure pytest.ini has asyncio_mode = auto
# Check all async functions use AsyncMock, not Mock
```

**E2E tests timeout**
```bash
# Increase timeout in playwright.config.ts
# Check services are running: npm run dev, python start_api.py
# Verify Supabase is running: supabase status
```

**MSW not intercepting requests**
```bash
# Check handlers are properly exported
# Verify server.listen() is called in setup.ts
# Ensure baseURL matches request URLs
```

**pytest-cov missing coverage**
```bash
# Install with: pip install pytest-cov
# Check pytest.ini has correct --cov settings
# Ensure source files are in src/ directory
```

### Getting Help

1. Check test output for specific error messages
2. Run tests with verbose flag: `pytest -v` or `npm test -- --reporter=verbose`
3. Check CI logs on GitHub Actions
4. Review test setup files: `setup.ts`, `conftest.py`

## Best Practices

### General

- **Write tests first** for new features (TDD)
- **Keep tests fast** - Mock external dependencies
- **Test behavior, not implementation** - Focus on what, not how
- **One assertion per test** when possible
- **Use descriptive test names** - Should read like documentation

### Frontend

- **Use Testing Library queries** - getByRole, getByText, etc.
- **Avoid implementation details** - Don't test internal state
- **Test user interactions** - Click, type, navigate
- **Wait for async updates** - Use waitFor, findBy queries

### Backend

- **Use fixtures** for common setup
- **Mock external services** - Database, APIs, AI models
- **Test error paths** - Not just happy path
- **Use parametrize** for multiple test cases

### E2E

- **Test critical user journeys** - Not every edge case
- **Keep tests independent** - Each test should stand alone
- **Use page objects** for complex interactions
- **Handle timing issues** - Use waitFor, not sleep

## Contributing

When adding new features:

1. Write unit tests for new functions/components
2. Add integration tests for new workflows
3. Update E2E tests if user-facing changes
4. Ensure all tests pass locally before committing
5. Check coverage hasn't decreased

## Additional Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Playwright Documentation](https://playwright.dev/)
- [pytest Documentation](https://docs.pytest.org/)
- [MSW Documentation](https://mswjs.io/)
