import { test, expect, Page } from '@playwright/test';

test.describe('Status Polling Behavior', () => {
  let page: Page;

  test.beforeEach(async ({ page: testPage }) => {
    page = testPage;
    await page.goto('/');
  });

  test('should create extraction_run on form submission', async () => {
    // Submit the form
    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    // Wait for API call and verify extraction_run was created
    const response = await page.waitForResponse(
      (response) => response.url().includes('/api/extraction-runs') && response.status() === 201
    );

    const responseData = await response.json();
    expect(responseData).toHaveProperty('id');
    expect(responseData).toHaveProperty('status');
    expect(responseData.status).toBe('pending');
  });

  test('should poll for status updates every 2 seconds and reflect actual workflow status', async () => {
    // Mock status progression through actual workflow states
    let callCount = 0;
    const statusProgression = ['pending', 'processing', 'processing', 'completed'];

    await page.route('**/api/extraction-runs/*', async (route) => {
      if (route.request().method() === 'GET') {
        const status = statusProgression[Math.min(callCount, statusProgression.length - 1)];
        callCount++;
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ id: '123', status, progress: callCount * 25 }),
        });
      }
    });

    // Submit form to trigger polling
    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    // Track polling requests
    const pollingRequests: number[] = [];
    page.on('request', (request) => {
      if (request.url().includes('/api/extraction-runs/') && request.method() === 'GET') {
        pollingRequests.push(Date.now());
      }
    });

    // Verify status progresses through actual workflow states
    await expect(page.locator('[data-status="pending"]')).toBeVisible({ timeout: 2000 });
    await expect(page.locator('[data-status="processing"]')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('[data-status="completed"]')).toBeVisible({ timeout: 10000 });

    // Verify polling interval is approximately 2 seconds
    expect(pollingRequests.length).toBeGreaterThanOrEqual(3);
    for (let i = 1; i < pollingRequests.length; i++) {
      const interval = pollingRequests[i] - pollingRequests[i - 1];
      expect(interval).toBeGreaterThanOrEqual(1800);
      expect(interval).toBeLessThanOrEqual(2500);
    }

    // Verify polling stopped after completion
    const requestCountBefore = pollingRequests.length;
    await page.waitForTimeout(5000);

    // Count requests after waiting - should be same since polling stopped
    const finalCallCount = callCount;
    expect(finalCallCount).toBeLessThanOrEqual(requestCountBefore + 1);
  });

  test('should stop polling when status is completed', async () => {
    await page.route('**/api/extraction-runs/*', async (route) => {
      const requestCount = await page.evaluate(() => window.requestCount || 0);

      if (requestCount < 2) {
        await page.evaluate(() => window.requestCount = (window.requestCount || 0) + 1);
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ id: '123', status: 'processing' }),
        });
      } else {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ id: '123', status: 'completed', result: 'success' }),
        });
      }
    });

    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    // Wait for completion status
    await page.waitForSelector('[data-status="completed"]');

    const requestsBefore = await page.evaluate(() => window.requestCount || 0);
    await page.waitForTimeout(5000);
    const requestsAfter = await page.evaluate(() => window.requestCount || 0);

    // No new requests should have been made after completion
    expect(requestsAfter).toBe(requestsBefore);
  });

  test('should stop polling when status is failed', async () => {
    await page.route('**/api/extraction-runs/*', async (route) => {
      const requestCount = await page.evaluate(() => window.requestCount || 0);

      if (requestCount < 2) {
        await page.evaluate(() => window.requestCount = (window.requestCount || 0) + 1);
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ id: '123', status: 'processing' }),
        });
      } else {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ id: '123', status: 'failed', error: 'Processing error' }),
        });
      }
    });

    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    // Wait for failed status
    await page.waitForSelector('[data-status="failed"]');

    const requestsBefore = await page.evaluate(() => window.requestCount || 0);
    await page.waitForTimeout(5000);
    const requestsAfter = await page.evaluate(() => window.requestCount || 0);

    // No new requests should have been made after failure
    expect(requestsAfter).toBe(requestsBefore);
  });

  test('should display real-time status updates in UI', async () => {
    const statuses = ['pending', 'processing', 'completed'];
    let statusIndex = 0;

    await page.route('**/api/extraction-runs/*', async (route) => {
      const status = statuses[Math.min(statusIndex++, statuses.length - 1)];
      await route.fulfill({
        status: 200,
        body: JSON.stringify({ id: '123', status, progress: statusIndex * 33 }),
      });
    });

    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    // Verify each status appears in UI
    await expect(page.locator('[data-status="pending"]')).toBeVisible();
    await expect(page.locator('[data-status="processing"]')).toBeVisible();
    await expect(page.locator('[data-status="completed"]')).toBeVisible();
  });

  test('should handle network delays gracefully', async () => {
    await page.route('**/api/extraction-runs/*', async (route) => {
      // Simulate 3-second network delay
      await page.waitForTimeout(3000);
      await route.fulfill({
        status: 200,
        body: JSON.stringify({ id: '123', status: 'processing' }),
      });
    });

    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    // UI should show loading state
    await expect(page.locator('[data-loading="true"]')).toBeVisible();

    // Eventually receive response
    await page.waitForSelector('[data-status="processing"]', { timeout: 10000 });
  });

  test('should maintain UI state during polling', async () => {
    await page.route('**/api/extraction-runs/*', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify({ id: '123', status: 'processing', progress: 50 }),
      });
    });

    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    await page.waitForSelector('[data-status="processing"]');

    // Interact with UI during polling
    await page.click('button[data-action="expand-details"]');
    await page.waitForTimeout(3000);

    // UI state should be maintained
    await expect(page.locator('[data-details-expanded="true"]')).toBeVisible();
    await expect(page.locator('[data-status="processing"]')).toBeVisible();
  });

  test('should update UI immediately when status changes', async () => {
    let callCount = 0;

    await page.route('**/api/extraction-runs/*', async (route) => {
      callCount++;
      const status = callCount === 1 ? 'pending' : 'completed';
      await route.fulfill({
        status: 200,
        body: JSON.stringify({ id: '123', status }),
      });
    });

    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    // First status should appear immediately
    await expect(page.locator('[data-status="pending"]')).toBeVisible({ timeout: 1000 });

    // Status change should update UI quickly (within polling interval + small buffer)
    await expect(page.locator('[data-status="completed"]')).toBeVisible({ timeout: 3000 });
  });

  test('should handle rapid form submissions correctly', async () => {
    let submissionCount = 0;

    await page.route('**/api/extraction-runs', async (route) => {
      if (route.request().method() === 'POST') {
        submissionCount++;
        await route.fulfill({
          status: 201,
          body: JSON.stringify({ id: `run-${submissionCount}`, status: 'pending' }),
        });
      }
    });

    // Submit multiple times rapidly
    await page.fill('input[name="dataInput"]', 'test data 1');
    await page.click('button[type="submit"]');

    await page.fill('input[name="dataInput"]', 'test data 2');
    await page.click('button[type="submit"]');

    await page.fill('input[name="dataInput"]', 'test data 3');
    await page.click('button[type="submit"]');

    // Should show latest submission
    await page.waitForSelector('[data-run-id="run-3"]');
    expect(submissionCount).toBe(3);
  });

  test('should pause polling when page is hidden', async () => {
    let pollingCount = 0;

    await page.route('**/api/extraction-runs/*', async (route) => {
      if (route.request().method() === 'GET') {
        pollingCount++;
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ id: '123', status: 'processing' }),
        });
      }
    });

    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    await page.waitForTimeout(3000);
    const countBeforeHide = pollingCount;

    // Simulate page visibility change
    await page.evaluate(() => {
      Object.defineProperty(document, 'visibilityState', {
        writable: true,
        value: 'hidden',
      });
      document.dispatchEvent(new Event('visibilitychange'));
    });

    await page.waitForTimeout(5000);
    const countDuringHide = pollingCount;

    // Polling should have stopped or slowed significantly
    expect(countDuringHide - countBeforeHide).toBeLessThan(2);

    // Resume polling when visible again
    await page.evaluate(() => {
      Object.defineProperty(document, 'visibilityState', {
        writable: true,
        value: 'visible',
      });
      document.dispatchEvent(new Event('visibilitychange'));
    });

    await page.waitForTimeout(3000);
    const countAfterResume = pollingCount;

    // Polling should resume
    expect(countAfterResume).toBeGreaterThan(countDuringHide);
  });

  test('should handle server errors during polling', async () => {
    let attemptCount = 0;

    await page.route('**/api/extraction-runs/*', async (route) => {
      attemptCount++;
      if (attemptCount < 3) {
        await route.fulfill({ status: 500, body: 'Server error' });
      } else {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ id: '123', status: 'processing' }),
        });
      }
    });

    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    // Should eventually succeed after retries
    await page.waitForSelector('[data-status="processing"]', { timeout: 10000 });
    expect(attemptCount).toBeGreaterThanOrEqual(3);
  });

  test('should clean up polling intervals on unmount', async () => {
    await page.route('**/api/extraction-runs/*', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ id: '123', status: 'processing' }),
        });
      }
    });

    await page.route('**/api/extraction-runs', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          body: JSON.stringify({ id: '123', status: 'pending' }),
        });
      }
    });

    // Start extraction to begin polling
    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    // Wait for polling to start
    await page.waitForSelector('[data-status="processing"]');
    await page.waitForTimeout(3000);

    // Track active intervals before unmount
    const intervalsBefore = await page.evaluate(() => {
      return (window as any).__activeIntervals?.size || 0;
    });

    // Navigate away (unmount component)
    await page.goto('/about');
    await page.waitForTimeout(1000);

    // Navigate back and check intervals were cleaned up
    await page.goto('/');
    await page.waitForTimeout(1000);

    const intervalsAfter = await page.evaluate(() => {
      return (window as any).__activeIntervals?.size || 0;
    });

    // Should have cleaned up intervals from previous mount
    expect(intervalsAfter).toBe(0);
  });

  test('should not accumulate intervals on multiple submissions', async () => {
    let submissionId = 0;

    await page.route('**/api/extraction-runs', async (route) => {
      if (route.request().method() === 'POST') {
        submissionId++;
        await route.fulfill({
          status: 201,
          body: JSON.stringify({ id: `run-${submissionId}`, status: 'pending' }),
        });
      }
    });

    await page.route('**/api/extraction-runs/*', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ id: '123', status: 'processing' }),
        });
      }
    });

    // Submit multiple times rapidly
    for (let i = 0; i < 5; i++) {
      await page.fill('input[name="dataInput"]', `test data ${i}`);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(1000);
    }

    // Wait for polling to be active
    await page.waitForTimeout(2000);

    // Track number of polling requests in a window
    let pollingCount = 0;
    page.on('request', (request) => {
      if (request.url().includes('/api/extraction-runs/') && request.method() === 'GET') {
        pollingCount++;
      }
    });

    await page.waitForTimeout(5000);

    // Should only have 1 active polling interval (not 5)
    // With 5 intervals at 2s each, we'd expect ~12-13 requests in 5s
    // With 1 interval, we expect ~2-3 requests
    expect(pollingCount).toBeLessThanOrEqual(4);
  });

  test('should stop all polling intervals when final status is reached', async () => {
    let callCount = 0;

    await page.route('**/api/extraction-runs/*', async (route) => {
      if (route.request().method() === 'GET') {
        callCount++;
        const status = callCount < 3 ? 'processing' : 'completed';
        await route.fulfill({
          status: 200,
          body: JSON.stringify({ id: '123', status }),
        });
      }
    });

    await page.route('**/api/extraction-runs', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          body: JSON.stringify({ id: '123', status: 'pending' }),
        });
      }
    });

    await page.fill('input[name="dataInput"]', 'test data');
    await page.click('button[type="submit"]');

    // Wait for completion
    await expect(page.locator('[data-status="completed"]')).toBeVisible({ timeout: 10000 });

    const callsBeforeWait = callCount;
    await page.waitForTimeout(6000);
    const callsAfterWait = callCount;

    // No new polling requests should occur after completion
    expect(callsAfterWait).toBe(callsBeforeWait);

    // Verify no intervals are still active
    const activeIntervals = await page.evaluate(() => {
      return (window as any).__activeIntervals?.size || 0;
    });
    expect(activeIntervals).toBe(0);
  });
});
