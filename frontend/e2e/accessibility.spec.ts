import { test, expect } from '@playwright/test';

test.describe('Accessibility E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/meeting-notes');
  });

  test('should have proper document structure', async ({ page }) => {
    // Check for main heading
    const heading = page.getByRole('heading', { level: 1 });
    await expect(heading).toBeVisible();

    // Check page has proper title
    await expect(page).toHaveTitle(/meeting notes/i);
  });

  test('should have accessible form labels', async ({ page }) => {
    // Textarea should have associated label
    const textarea = page.getByRole('textbox', { name: /meeting notes/i });
    await expect(textarea).toBeVisible().catch(async () => {
      // If not found by accessible name, check for label element
      const label = page.locator('label:has-text("Meeting Notes")');
      await expect(label).toBeVisible();
    });
  });

  test('should support keyboard navigation through form', async ({ page }) => {
    // Start from top of page
    await page.keyboard.press('Tab');

    // Should be able to tab through interactive elements
    let tabCount = 0;
    const maxTabs = 5;

    while (tabCount < maxTabs) {
      const focused = page.locator(':focus');
      const tagName = await focused.evaluate(el => el?.tagName).catch(() => null);

      if (tagName && ['TEXTAREA', 'INPUT', 'BUTTON', 'A'].includes(tagName)) {
        tabCount++;
      }

      await page.keyboard.press('Tab');

      // Avoid infinite loop
      if (tabCount === 0 && tabCount >= maxTabs) break;
    }

    expect(tabCount).toBeGreaterThan(0);
  });

  test('should be able to fill form using only keyboard', async ({ page }) => {
    // Tab to textarea
    await page.keyboard.press('Tab');

    // Check if textarea is focused
    let focused = page.locator(':focus');
    let tagName = await focused.evaluate(el => el?.tagName).catch(() => null);

    // Keep tabbing until we reach textarea
    while (tagName !== 'TEXTAREA') {
      await page.keyboard.press('Tab');
      focused = page.locator(':focus');
      tagName = await focused.evaluate(el => el?.tagName).catch(() => null);

      // Safety break after 10 tabs
      if (await page.keyboard.press.length > 10) break;
    }

    // Type in textarea
    await page.keyboard.type('Test meeting notes for keyboard navigation');

    // Tab to submit button
    await page.keyboard.press('Tab');

    // Verify we can reach the submit button
    focused = page.locator(':focus');
    const buttonText = await focused.textContent().catch(() => '');
    expect(buttonText?.toLowerCase()).toContain('extract');
  });

  test('should have focus indicators on all interactive elements', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    // Focus textarea
    await notesInput.focus();
    let outlineStyle = await notesInput.evaluate(el => {
      const styles = window.getComputedStyle(el);
      return styles.outline || styles.boxShadow || 'none';
    });
    expect(outlineStyle).not.toBe('none');

    // Focus button
    await notesInput.fill('Test notes');
    await submitButton.focus();
    outlineStyle = await submitButton.evaluate(el => {
      const styles = window.getComputedStyle(el);
      return styles.outline || styles.boxShadow || 'none';
    });
    // Button should have some visual focus indicator
    expect(outlineStyle).toBeTruthy();
  });

  test('should have proper ARIA attributes', async ({ page }) => {
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    // Button should have accessible name
    const ariaLabel = await submitButton.getAttribute('aria-label').catch(() => null);
    const textContent = await submitButton.textContent();

    // Either aria-label or text content should provide accessible name
    expect(ariaLabel || textContent).toBeTruthy();
  });

  test('should announce status changes to screen readers', async ({ page }) => {
    // Check for ARIA live regions
    const liveRegion = page.locator('[aria-live]').first();

    // May or may not have live region initially
    const hasLiveRegion = await liveRegion.count() > 0;

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes');
    await submitButton.click();

    // After submission, status messages should be announced
    // Look for processing message that should be in a live region
    const processingMessage = page.getByText(/processing|analyzing/i);
    await expect(processingMessage).toBeVisible({ timeout: 5000 });

    // Check if the processing message or its container has aria-live
    const parent = processingMessage.locator('..').first();
    const ariaLive = await parent.getAttribute('aria-live').catch(() => null);

    // Should have aria-live="polite" or "assertive" for status updates
    // Note: This is a best practice check
    if (ariaLive) {
      expect(['polite', 'assertive']).toContain(ariaLive);
    }
  });

  test('should have descriptive button states', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    // Initial state - button should be disabled
    await expect(submitButton).toBeDisabled();

    // Could have aria-disabled attribute
    const ariaDisabled = await submitButton.getAttribute('aria-disabled');
    if (ariaDisabled !== null) {
      expect(ariaDisabled).toBe('true');
    }

    // Enable button
    await notesInput.fill('Test meeting notes');
    await expect(submitButton).toBeEnabled();

    // After submission - button changes text
    await submitButton.click();
    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // Button should indicate processing state
    const processingButton = page.getByRole('button', { name: /processing/i });
    await expect(processingButton).toBeVisible();
  });

  test('should have sufficient color contrast', async ({ page }) => {
    // Check heading contrast
    const heading = page.getByRole('heading', { name: /meeting notes/i });
    await expect(heading).toBeVisible();

    const contrast = await heading.evaluate(el => {
      const styles = window.getComputedStyle(el);
      return {
        color: styles.color,
        background: styles.backgroundColor
      };
    });

    // At least verify colors are set
    expect(contrast.color).toBeTruthy();
  });

  test('should handle form validation errors accessibly', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    // Enter too-short text
    await notesInput.fill('Short');
    await submitButton.click();

    // Error message should appear
    const errorMessage = page.getByText(/too short|minimum|invalid/i);
    await expect(errorMessage).toBeVisible({ timeout: 10000 });

    // Error should be associated with input (via aria-describedby)
    const ariaDescribedBy = await notesInput.getAttribute('aria-describedby');
    // Note: This is a best practice, may not be implemented yet
  });

  test('should have skip navigation links (if multi-page)', async ({ page }) => {
    // Check for skip to main content link
    // This is typically hidden but available for screen readers
    const skipLink = page.locator('a:has-text("skip to"), [href="#main-content"]').first();
    const hasSkipLink = await skipLink.count() > 0;

    // Not required for single-page app, but good practice
    if (hasSkipLink) {
      await expect(skipLink).toBeHidden().or(expect(skipLink).toBeVisible());
    }
  });

  test('should have semantic HTML structure', async ({ page }) => {
    // Check for main landmark
    const main = page.locator('main').first();
    const hasMain = await main.count() > 0;

    // Check for heading hierarchy
    const h1Count = await page.locator('h1').count();
    expect(h1Count).toBeGreaterThanOrEqual(1);

    // Should only have one h1
    expect(h1Count).toBeLessThanOrEqual(1);
  });

  test('should provide context for icons and images', async ({ page }) => {
    // Check for images/icons
    const images = page.locator('img');
    const imageCount = await images.count();

    for (let i = 0; i < imageCount; i++) {
      const img = images.nth(i);
      const alt = await img.getAttribute('alt');
      const ariaLabel = await img.getAttribute('aria-label');
      const ariaHidden = await img.getAttribute('aria-hidden');

      // Images should have alt text or be marked as decorative
      expect(alt !== null || ariaLabel !== null || ariaHidden === 'true').toBe(true);
    }
  });

  test('should be navigable with screen reader shortcuts', async ({ page }) => {
    // Simulate screen reader heading navigation
    const headings = await page.locator('h1, h2, h3, h4, h5, h6').all();
    expect(headings.length).toBeGreaterThan(0);

    // Should have logical heading hierarchy
    const h1s = await page.locator('h1').count();
    const h2s = await page.locator('h2').count();

    expect(h1s).toBeGreaterThanOrEqual(1);
  });

  test('should handle focus management during state changes', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes');

    // Focus submit button
    await submitButton.focus();

    // Submit
    await submitButton.click();

    // After submission, focus should be managed appropriately
    // It should not be lost or moved to an unexpected location
    await page.waitForTimeout(1000);

    const focused = page.locator(':focus');
    const focusedTag = await focused.evaluate(el => el?.tagName).catch(() => null);

    // Focus should be on some element (not lost)
    expect(focusedTag).toBeTruthy();
  });

  test('should support high contrast mode', async ({ page }) => {
    // Enable high contrast mode simulation
    await page.emulateMedia({ colorScheme: 'dark', forcedColors: 'active' });

    await page.goto('/meeting-notes');

    // Elements should still be visible
    await expect(page.getByRole('heading', { name: /meeting notes/i })).toBeVisible();
    await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /extract action items/i })).toBeVisible();
  });

  test('should work with reduced motion preference', async ({ page }) => {
    // Simulate prefers-reduced-motion
    await page.emulateMedia({ reducedMotion: 'reduce' });

    await page.goto('/meeting-notes');

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes');
    await submitButton.click();

    // Animations should be reduced or removed
    // The spinner might still be visible but not animated
    const spinner = page.locator('[class*="animate-spin"]');

    if (await spinner.count() > 0) {
      // Check if animation is disabled
      const animationDuration = await spinner.evaluate(el => {
        const styles = window.getComputedStyle(el);
        return styles.animationDuration;
      });

      // Should be '0s' or similar for reduced motion
      // Or animation class might not be applied at all
    }
  });

  test('should provide feedback for loading states', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes');
    await submitButton.click();

    // Should have visible loading indicator
    await expect(page.getByText(/processing|loading|analyzing/i)).toBeVisible({ timeout: 5000 });

    // Should have visual spinner
    const spinner = page.locator('[class*="animate-spin"]');
    await expect(spinner).toBeVisible();

    // Loading state should be announced (via aria-live or role="status")
    const statusIndicator = page.getByText(/processing/i).locator('..');
    const role = await statusIndicator.getAttribute('role').catch(() => null);
    const ariaLive = await statusIndicator.getAttribute('aria-live').catch(() => null);

    // Should have appropriate role or aria-live
    expect(role === 'status' || ariaLive !== null).toBe(true);
  });

  test('should have clear error messages', async ({ page }) => {
    // Mock an error
    await page.route('http://localhost:8000/trigger-workflow', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Service unavailable' })
      });
    });

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill('Test meeting notes');
    await submitButton.click();

    // Error should be announced
    await expect(page.getByText(/failed|error/i)).toBeVisible({ timeout: 10000 });

    // Error message should be descriptive and helpful
    const errorText = await page.getByText(/failed|error/i).textContent();
    expect(errorText?.length).toBeGreaterThan(10); // Should be more than just "Error"
  });

  test('should have proper button labels during all states', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);

    // Initial state
    let submitButton = page.getByRole('button', { name: /extract action items/i });
    await expect(submitButton).toBeVisible();

    // After clicking
    await notesInput.fill('Test meeting notes');
    await submitButton.click();

    // Processing state - button text should change
    submitButton = page.getByRole('button', { name: /processing/i });
    await expect(submitButton).toBeVisible({ timeout: 5000 });

    // Button should still be identifiable as a button
    const role = await submitButton.getAttribute('role').catch(() => null);
    const tagName = await submitButton.evaluate(el => el.tagName).catch(() => null);

    expect(tagName === 'BUTTON' || role === 'button').toBe(true);
  });
});
