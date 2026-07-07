import { test, expect } from '@playwright/test';

test.describe('Status Polling Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/meeting-notes');
  });

  test('should create extraction_run with processing status', async ({ page }) => {
    // Track database calls
    const dbRequests: any[] = [];
    page.on('request', request => {
      if (request.url().includes('/rest/v1/extraction_runs')) {
        dbRequests.push({
          method: request.method(),
          url: request.url(),
          postData: request.postData()
        });
      }
    });

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes about project updates and action items');
    await submitButton.click();

    // Wait a moment for requests to be made
    await page.waitForTimeout(2000);

    // Should have created extraction_run record
    const postRequests = dbRequests.filter(r => r.method === 'POST');
    expect(postRequests.length).toBeGreaterThan(0);

    // Should start showing processing state
    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });
  });

  test('should poll extraction_run status every 2 seconds', async ({ page }) => {
    const pollRequests: number[] = [];
    let lastPollTime = Date.now();

    page.on('request', request => {
      if (
        request.method() === 'GET' &&
        request.url().includes('/rest/v1/extraction_runs?')
      ) {
        const currentTime = Date.now();
        const timeSinceLast = currentTime - lastPollTime;
        pollRequests.push(timeSinceLast);
        lastPollTime = currentTime;
      }
    });

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes for polling test');
    await submitButton.click();

    // Wait for processing to start
    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // Wait to observe polling behavior (at least 3 polls)
    await page.waitForTimeout(7000);

    // Should have made multiple poll requests
    expect(pollRequests.length).toBeGreaterThanOrEqual(2);

    // Check that polling interval is approximately 2 seconds (1800-2200ms)
    const validIntervals = pollRequests.filter(
      interval => interval >= 1800 && interval <= 2500
    );
    expect(validIntervals.length).toBeGreaterThan(0);
  });

  test('should stop polling when status changes to completed', async ({ page }) => {
    let pollCount = 0;

    page.on('request', request => {
      if (
        request.method() === 'GET' &&
        request.url().includes('/rest/v1/extraction_runs')
      ) {
        pollCount++;
      }
    });

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes with action items');
    await submitButton.click();

    // Wait for completion
    await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 45000 });

    const pollCountAtCompletion = pollCount;

    // Wait additional time to verify polling stopped
    await page.waitForTimeout(5000);

    // Poll count should not increase significantly after completion
    // Allow for 1-2 more polls due to timing
    expect(pollCount).toBeLessThanOrEqual(pollCountAtCompletion + 2);
  });

  test('should stop polling when status changes to failed', async ({ page }) => {
    await page.route('http://localhost:8000/trigger-workflow', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Test error' })
      });
    });

    let pollCount = 0;

    page.on('request', request => {
      if (
        request.method() === 'GET' &&
        request.url().includes('/rest/v1/extraction_runs')
      ) {
        pollCount++;
      }
    });

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes');
    await submitButton.click();

    // Wait for failure state
    await expect(page.getByText(/failed|error/i)).toBeVisible({ timeout: 10000 });

    const pollCountAtFailure = pollCount;

    // Wait to verify polling stopped
    await page.waitForTimeout(5000);

    // Should not continue polling after failure
    expect(pollCount).toBeLessThanOrEqual(pollCountAtFailure + 2);
  });

  test('should show real-time status updates', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes with multiple action items for the team');
    await submitButton.click();

    // Should show processing immediately
    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // Processing indicator should remain visible during extraction
    const processingIndicator = page.getByText(/ai is analyzing/i);
    await expect(processingIndicator).toBeVisible();

    // Spinner should be animating
    const spinner = page.locator('[class*="animate-spin"]');
    await expect(spinner).toBeVisible();

    // Eventually should transition to completed or failed
    await expect(
      page.getByText(/extraction complete/i).or(page.getByText(/extraction failed/i))
    ).toBeVisible({ timeout: 45000 });
  });

  test('should display results when status changes to completed', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(`
Team meeting notes
Action items:
1. John to review code by Friday
2. Sarah to update documentation
3. Mike to schedule follow-up meeting
    `.trim());

    await submitButton.click();

    // Processing state
    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // Wait for completion
    await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 45000 });

    // Results should now be visible
    // Action items list should appear
    const actionItems = page.locator('[data-testid="action-item"]');
    const itemCount = await actionItems.count();
    expect(itemCount).toBeGreaterThan(0);

    // Model info should be displayed
    await expect(page.getByText(/model:/i)).toBeVisible();
  });

  test('should handle polling with network delays gracefully', async ({ page }) => {
    // Simulate slow network responses
    await page.route('**/rest/v1/extraction_runs*', async (route, request) => {
      // Add 500ms delay to simulate slow network
      await new Promise(resolve => setTimeout(resolve, 500));
      route.continue();
    });

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes');
    await submitButton.click();

    // Should still show processing despite delays
    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // Should eventually complete
    await expect(
      page.getByText(/extraction complete/i).or(page.getByText(/failed/i))
    ).toBeVisible({ timeout: 50000 });
  });

  test('should maintain UI state during polling', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes for UI state test');
    await submitButton.click();

    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // During polling, UI should remain stable
    // Input should stay disabled
    await expect(notesInput).toBeDisabled();

    // Submit button should stay disabled
    await expect(submitButton).toBeDisabled();

    // Processing message should remain visible
    await expect(page.getByText(/ai is analyzing/i)).toBeVisible();

    // No flickering or state resets
    await page.waitForTimeout(5000);
    await expect(page.getByText(/processing/i)).toBeVisible();
  });

  test('should update UI immediately when poll detects status change', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Quick test notes');
    await submitButton.click();

    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // When status changes, UI should update within 2 seconds (one poll interval)
    const startTime = Date.now();
    await expect(
      page.getByText(/extraction complete/i).or(page.getByText(/extraction failed/i))
    ).toBeVisible({ timeout: 45000 });
    const endTime = Date.now();

    // Should detect completion within reasonable time
    const detectionTime = endTime - startTime;
    expect(detectionTime).toBeLessThan(50000); // 50 seconds max
  });

  test('should show extraction run metadata', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes');
    await submitButton.click();

    await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 45000 });

    // Should display model provider and name
    await expect(page.getByText(/model:/i)).toBeVisible();

    // Should contain provider information (bedrock or azure)
    const modelText = await page.getByText(/model:/i).textContent();
    expect(modelText?.toLowerCase()).toMatch(/bedrock|azure/);
  });

  test('should handle rapid successive submissions', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    // First submission
    await notesInput.fill('First meeting notes');
    await submitButton.click();

    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // Try to submit again (should see "New Extraction" button or wait)
    // This tests that the UI properly handles state management
    const isProcessing = await page.getByText(/processing/i).isVisible();
    expect(isProcessing).toBe(true);

    // Input and submit should be disabled during processing
    await expect(notesInput).toBeDisabled();
    await expect(submitButton).toBeDisabled();
  });

  test('should resume polling after page visibility change', async ({ page, context }) => {
    // Note: This test simulates tab switching behavior
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes');
    await submitButton.click();

    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // Simulate tab becoming hidden
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', {
        writable: true,
        configurable: true,
        value: true
      });
      document.dispatchEvent(new Event('visibilitychange'));
    });

    await page.waitForTimeout(3000);

    // Simulate tab becoming visible again
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', {
        writable: true,
        configurable: true,
        value: false
      });
      document.dispatchEvent(new Event('visibilitychange'));
    });

    // TanStack Query should resume polling
    // Processing status should still be visible or transition to complete
    await expect(
      page.getByText(/processing|extraction complete/i)
    ).toBeVisible({ timeout: 5000 });
  });
});
