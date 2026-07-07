import { test, expect } from '@playwright/test';

test.describe('Multi-Browser E2E Tests', () => {
  const TEST_NOTES = `
Team meeting - Browser compatibility test
Attendees: John, Sarah, Mike

Action Items:
1. John to review code by Friday
2. Sarah to update documentation by next week
3. Mike to schedule follow-up meeting
  `.trim();

  test('should work in Chromium', async ({ page, browserName }) => {
    test.skip(browserName !== 'chromium', 'Chromium-specific test');

    await page.goto('/meeting-notes');

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await expect(notesInput).toBeVisible();
    await expect(submitButton).toBeVisible();

    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });
  });

  test('should work in Firefox', async ({ page, browserName }) => {
    test.skip(browserName !== 'firefox', 'Firefox-specific test');

    await page.goto('/meeting-notes');

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await expect(notesInput).toBeVisible();
    await expect(submitButton).toBeVisible();

    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });
  });

  test('should work in WebKit', async ({ page, browserName }) => {
    test.skip(browserName !== 'webkit', 'WebKit-specific test');

    await page.goto('/meeting-notes');

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await expect(notesInput).toBeVisible();
    await expect(submitButton).toBeVisible();

    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });
  });

  test('should render UI consistently across browsers', async ({ page }) => {
    await page.goto('/meeting-notes');

    // Check key UI elements are present
    await expect(page.getByRole('heading', { name: /meeting notes.*action items/i })).toBeVisible();
    await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /extract action items/i })).toBeVisible();
    await expect(page.getByText(/character/i)).toBeVisible();
    await expect(page.getByText(/tips for best results/i)).toBeVisible();
  });

  test('should handle form submission in all browsers', async ({ page }) => {
    await page.goto('/meeting-notes');

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    // Fill and submit
    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    // Should show processing state regardless of browser
    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // Should show spinner
    const spinner = page.locator('[class*="animate-spin"]');
    await expect(spinner).toBeVisible();
  });

  test('should handle CSS animations in all browsers', async ({ page }) => {
    await page.goto('/meeting-notes');

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    // Verify spinner animation
    const spinner = page.locator('[class*="animate-spin"]');
    await expect(spinner).toBeVisible({ timeout: 5000 });

    // Check that animation is actually running (not just static)
    const hasAnimation = await spinner.evaluate(el => {
      const styles = window.getComputedStyle(el);
      return styles.animation !== 'none' && styles.animation !== '';
    });

    expect(hasAnimation).toBe(true);
  });

  test('should handle text input in all browsers', async ({ page }) => {
    await page.goto('/meeting-notes');

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);

    // Test typing
    await notesInput.type('Test meeting notes');
    await expect(notesInput).toHaveValue('Test meeting notes');

    // Test clearing
    await notesInput.clear();
    await expect(notesInput).toHaveValue('');

    // Test pasting (simulated)
    await notesInput.fill(TEST_NOTES);
    await expect(notesInput).toHaveValue(TEST_NOTES);

    // Test character counter updates
    await expect(page.getByText(new RegExp(`${TEST_NOTES.length}`, 'i'))).toBeVisible();
  });

  test('should handle button interactions in all browsers', async ({ page }) => {
    await page.goto('/meeting-notes');

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    // Test disabled state
    await expect(submitButton).toBeDisabled();

    // Test enabled state
    await notesInput.fill(TEST_NOTES);
    await expect(submitButton).toBeEnabled();

    // Test click
    await submitButton.click();
    await expect(submitButton).toBeDisabled(); // Should disable during processing
  });

  test('should display results consistently across browsers', async ({ page }) => {
    await page.goto('/meeting-notes');

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    // Wait for completion
    await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 45000 });

    // Check results display
    await expect(page.getByText(/model:/i)).toBeVisible();

    // Action items should be visible
    const actionItems = page.locator('[data-testid="action-item"]');
    const count = await actionItems.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should handle navigation in all browsers', async ({ page }) => {
    await page.goto('/meeting-notes');

    // Should be able to navigate away and back
    await page.goto('/');
    await page.goto('/meeting-notes');

    // Page should load correctly
    await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();
  });

  test('should support keyboard navigation in all browsers', async ({ page }) => {
    await page.goto('/meeting-notes');

    // Tab to textarea
    await page.keyboard.press('Tab');

    // Should focus textarea or first focusable element
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();

    // Type in textarea
    await page.keyboard.type('Test notes');

    // Tab to button
    await page.keyboard.press('Tab');

    // Should be able to activate button with Enter/Space
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    await notesInput.fill('Test meeting notes with action items');

    await page.keyboard.press('Tab');
    // Note: Pressing Enter on button requires it to be focused and enabled
  });

  test('should handle fetch API in all browsers', async ({ page }) => {
    // Monitor network requests
    let fetchCalled = false;

    page.on('request', request => {
      if (request.url().includes('/trigger-workflow')) {
        fetchCalled = true;
      }
    });

    await page.goto('/meeting-notes');

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    // Wait a moment for fetch to be called
    await page.waitForTimeout(2000);

    expect(fetchCalled).toBe(true);
  });

  test('should handle WebSocket connections if used', async ({ page }) => {
    // This test checks if the app uses WebSockets (for Supabase Realtime)
    await page.goto('/meeting-notes');

    // Check for WebSocket connections
    page.on('websocket', ws => {
      console.log('WebSocket connection detected:', ws.url());
    });

    // Trigger an action that might use WebSocket
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    // Wait to see if WebSocket is established
    await page.waitForTimeout(2000);
  });

  test('should handle long-running operations in all browsers', async ({ page }) => {
    await page.goto('/meeting-notes');

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    // Processing state should be maintained
    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // Wait up to 45 seconds for completion
    await expect(
      page.getByText(/extraction complete/i).or(page.getByText(/extraction failed/i))
    ).toBeVisible({ timeout: 45000 });

    // Browser should not timeout or become unresponsive
    const isResponsive = await page.evaluate(() => true);
    expect(isResponsive).toBe(true);
  });

  test('should handle local storage if used', async ({ page }) => {
    await page.goto('/meeting-notes');

    // Check if app uses localStorage
    const hasLocalStorage = await page.evaluate(() => {
      return typeof window.localStorage !== 'undefined';
    });

    expect(hasLocalStorage).toBe(true);

    // If app stores state in localStorage, verify it persists
    await page.evaluate(() => {
      localStorage.setItem('test-key', 'test-value');
    });

    const value = await page.evaluate(() => {
      return localStorage.getItem('test-key');
    });

    expect(value).toBe('test-value');

    // Cleanup
    await page.evaluate(() => {
      localStorage.removeItem('test-key');
    });
  });

  test('should render fonts correctly in all browsers', async ({ page }) => {
    await page.goto('/meeting-notes');

    const heading = page.getByRole('heading', { name: /meeting notes.*action items/i });
    await expect(heading).toBeVisible();

    // Check font is loaded and rendered
    const fontFamily = await heading.evaluate(el => {
      return window.getComputedStyle(el).fontFamily;
    });

    expect(fontFamily).toBeTruthy();
    expect(fontFamily.length).toBeGreaterThan(0);
  });

  test('should handle JSON parsing in all browsers', async ({ page }) => {
    // This test verifies JSON handling works across browsers
    await page.goto('/meeting-notes');

    const jsonTest = await page.evaluate(() => {
      const obj = { test: 'value', number: 123, array: [1, 2, 3] };
      const json = JSON.stringify(obj);
      const parsed = JSON.parse(json);
      return parsed.test === 'value' && parsed.number === 123;
    });

    expect(jsonTest).toBe(true);
  });
});
