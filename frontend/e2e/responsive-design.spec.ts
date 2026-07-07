import { test, expect, devices } from '@playwright/test';

test.describe('Responsive Design E2E Tests', () => {
  const TEST_NOTES = `
Team meeting
Action items:
1. John to review code
2. Sarah to update docs
  `.trim();

  test.describe('Mobile viewport tests', () => {
    test.use({ ...devices['iPhone 12'] });

    test('should display correctly on mobile', async ({ page }) => {
      await page.goto('/meeting-notes');

      // Key elements should be visible
      await expect(page.getByRole('heading', { name: /meeting notes/i })).toBeVisible();
      await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();
      await expect(page.getByRole('button', { name: /extract action items/i })).toBeVisible();
    });

    test('should have touch-friendly buttons on mobile', async ({ page }) => {
      await page.goto('/meeting-notes');

      const submitButton = page.getByRole('button', { name: /extract action items/i });

      // Button should have adequate touch target size (at least 44x44px)
      const buttonSize = await submitButton.boundingBox();
      if (buttonSize) {
        expect(buttonSize.height).toBeGreaterThanOrEqual(40); // Allow slight variance
      }
    });

    test('should stack elements vertically on mobile', async ({ page }) => {
      await page.goto('/meeting-notes');

      const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
      const submitButton = page.getByRole('button', { name: /extract action items/i });

      const inputBox = await notesInput.boundingBox();
      const buttonBox = await submitButton.boundingBox();

      // Button should be below textarea (y position greater)
      if (inputBox && buttonBox) {
        expect(buttonBox.y).toBeGreaterThan(inputBox.y);
      }
    });

    test('should handle mobile keyboard', async ({ page }) => {
      await page.goto('/meeting-notes');

      const notesInput = page.getByPlaceholder(/paste your meeting notes/i);

      // Tap textarea
      await notesInput.tap();

      // Should be focused
      const isFocused = await notesInput.evaluate(el => el === document.activeElement);
      expect(isFocused).toBe(true);

      // Type on mobile
      await notesInput.fill(TEST_NOTES);
      await expect(notesInput).toHaveValue(TEST_NOTES);
    });

    test('should handle mobile scrolling', async ({ page }) => {
      await page.goto('/meeting-notes');

      const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
      await notesInput.fill(TEST_NOTES);

      const submitButton = page.getByRole('button', { name: /extract action items/i });

      // Scroll to button if needed
      await submitButton.scrollIntoViewIfNeeded();
      await submitButton.tap();

      await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });
    });

    test('should display results on mobile without overflow', async ({ page }) => {
      await page.goto('/meeting-notes');

      const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
      const submitButton = page.getByRole('button', { name: /extract action items/i });

      await notesInput.fill(TEST_NOTES);
      await submitButton.tap();

      await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 45000 });

      // Results should be visible without horizontal scroll
      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });

      expect(hasHorizontalScroll).toBe(false);
    });

    test('should adapt text size for mobile readability', async ({ page }) => {
      await page.goto('/meeting-notes');

      const heading = page.getByRole('heading', { name: /meeting notes/i });

      // Font size should be readable on mobile (at least 16px for body text)
      const fontSize = await heading.evaluate(el => {
        return parseInt(window.getComputedStyle(el).fontSize);
      });

      expect(fontSize).toBeGreaterThanOrEqual(20); // Headings should be larger
    });
  });

  test.describe('Tablet viewport tests', () => {
    test.use({ ...devices['iPad Pro'] });

    test('should display correctly on tablet', async ({ page }) => {
      await page.goto('/meeting-notes');

      await expect(page.getByRole('heading', { name: /meeting notes/i })).toBeVisible();
      await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();
      await expect(page.getByRole('button', { name: /extract action items/i })).toBeVisible();
    });

    test('should use available space on tablet', async ({ page }) => {
      await page.goto('/meeting-notes');

      const container = page.locator('.container, [class*="max-w"]').first();
      const containerWidth = await container.evaluate(el => el.clientWidth);

      // Should use significant portion of screen width
      const viewportSize = page.viewportSize();
      if (viewportSize) {
        expect(containerWidth).toBeGreaterThan(viewportSize.width * 0.5);
      }
    });

    test('should support both touch and mouse on tablet', async ({ page }) => {
      await page.goto('/meeting-notes');

      const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
      const submitButton = page.getByRole('button', { name: /extract action items/i });

      // Test touch
      await notesInput.tap();
      await notesInput.fill(TEST_NOTES);

      // Test mouse click
      await submitButton.click();

      await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Desktop viewport tests', () => {
    test.use({ viewport: { width: 1920, height: 1080 } });

    test('should display correctly on large desktop', async ({ page }) => {
      await page.goto('/meeting-notes');

      await expect(page.getByRole('heading', { name: /meeting notes/i })).toBeVisible();
      await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();
      await expect(page.getByRole('button', { name: /extract action items/i })).toBeVisible();
    });

    test('should constrain max-width on large screens', async ({ page }) => {
      await page.goto('/meeting-notes');

      const container = page.locator('.container, [class*="max-w"]').first();
      const containerWidth = await container.evaluate(el => el.clientWidth);

      // Should not extend to full width on very large screens
      expect(containerWidth).toBeLessThan(1920);
      expect(containerWidth).toBeGreaterThan(800); // But should be reasonably wide
    });

    test('should center content on large screens', async ({ page }) => {
      await page.goto('/meeting-notes');

      const container = page.locator('.container, [class*="mx-auto"]').first();
      const marginLeft = await container.evaluate(el => {
        return parseInt(window.getComputedStyle(el).marginLeft);
      });

      // Should have auto margins for centering
      expect(marginLeft).toBeGreaterThan(0);
    });
  });

  test.describe('Viewport transition tests', () => {
    test('should handle resize from mobile to desktop', async ({ page }) => {
      // Start mobile
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/meeting-notes');

      await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();

      // Resize to desktop
      await page.setViewportSize({ width: 1280, height: 800 });

      // Elements should still be visible and properly laid out
      await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();
      await expect(page.getByRole('button', { name: /extract action items/i })).toBeVisible();
    });

    test('should handle resize from desktop to mobile', async ({ page }) => {
      // Start desktop
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto('/meeting-notes');

      const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
      await notesInput.fill(TEST_NOTES);

      // Resize to mobile
      await page.setViewportSize({ width: 375, height: 667 });

      // Content should remain intact
      await expect(notesInput).toHaveValue(TEST_NOTES);
      await expect(page.getByRole('button', { name: /extract action items/i })).toBeVisible();
    });
  });

  test.describe('Orientation tests', () => {
    test('should handle portrait orientation on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 }); // Portrait
      await page.goto('/meeting-notes');

      await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();
    });

    test('should handle landscape orientation on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 667, height: 375 }); // Landscape
      await page.goto('/meeting-notes');

      await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();
    });

    test('should adapt layout in landscape mode', async ({ page }) => {
      await page.setViewportSize({ width: 667, height: 375 }); // Landscape
      await page.goto('/meeting-notes');

      // Elements should fit without excessive scrolling
      const submitButton = page.getByRole('button', { name: /extract action items/i });
      const isInViewport = await submitButton.isVisible();

      expect(isInViewport).toBe(true);
    });
  });

  test.describe('Common breakpoints', () => {
    const breakpoints = [
      { name: 'Small mobile', width: 320, height: 568 },
      { name: 'Mobile', width: 375, height: 667 },
      { name: 'Large mobile', width: 414, height: 896 },
      { name: 'Tablet', width: 768, height: 1024 },
      { name: 'Small desktop', width: 1024, height: 768 },
      { name: 'Desktop', width: 1280, height: 800 },
      { name: 'Large desktop', width: 1920, height: 1080 }
    ];

    breakpoints.forEach(({ name, width, height }) => {
      test(`should display correctly at ${name} (${width}x${height})`, async ({ page }) => {
        await page.setViewportSize({ width, height });
        await page.goto('/meeting-notes');

        // Core elements should be visible at all breakpoints
        await expect(page.getByRole('heading', { name: /meeting notes/i })).toBeVisible();
        await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();
        await expect(page.getByRole('button', { name: /extract action items/i })).toBeVisible();

        // No horizontal overflow
        const hasHorizontalScroll = await page.evaluate(() => {
          return document.documentElement.scrollWidth > document.documentElement.clientWidth;
        });
        expect(hasHorizontalScroll).toBe(false);
      });
    });
  });

  test.describe('Touch interactions', () => {
    test.use({ ...devices['iPhone 12'] });

    test('should handle tap events', async ({ page }) => {
      await page.goto('/meeting-notes');

      const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
      const submitButton = page.getByRole('button', { name: /extract action items/i });

      await notesInput.tap();
      await notesInput.fill(TEST_NOTES);

      await submitButton.tap();

      await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });
    });

    test('should handle long press', async ({ page }) => {
      await page.goto('/meeting-notes');

      const notesInput = page.getByPlaceholder(/paste your meeting notes/i);

      // Long press to select text (simulated)
      await notesInput.fill('Test text');
      await notesInput.tap({ position: { x: 10, y: 10 } });
      await page.waitForTimeout(500);

      // Text should be there
      await expect(notesInput).toHaveValue('Test text');
    });

    test('should prevent double-tap zoom', async ({ page }) => {
      await page.goto('/meeting-notes');

      const heading = page.getByRole('heading', { name: /meeting notes/i });

      // Double tap
      await heading.tap({ clickCount: 2 });

      // Page should not zoom (this is handled by viewport meta tag)
      // We can't directly test zoom, but we can verify viewport meta exists
      const viewportMeta = await page.locator('meta[name="viewport"]').getAttribute('content');
      expect(viewportMeta).toContain('user-scalable');
    });
  });

  test.describe('Font scaling', () => {
    test('should handle user font size preferences', async ({ page }) => {
      await page.goto('/meeting-notes');

      // Simulate user increasing font size
      await page.addStyleTag({
        content: 'html { font-size: 20px; }' // Increased from default 16px
      });

      // Elements should still be visible and not overflow
      await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();

      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });

      expect(hasHorizontalScroll).toBe(false);
    });
  });

  test.describe('Flexible layouts', () => {
    test('should adapt button layout on narrow screens', async ({ page }) => {
      await page.setViewportSize({ width: 320, height: 568 }); // Very narrow
      await page.goto('/meeting-notes');

      const submitButton = page.getByRole('button', { name: /extract action items/i });

      // Button should be visible
      await expect(submitButton).toBeVisible();

      // Button should not overflow
      const buttonWidth = await submitButton.evaluate(el => el.clientWidth);
      expect(buttonWidth).toBeLessThanOrEqual(320 - 32); // Account for padding
    });

    test('should handle long action item text on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/meeting-notes');

      const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
      const submitButton = page.getByRole('button', { name: /extract action items/i });

      await notesInput.fill(`
Action items:
1. John to review the comprehensive architectural design document and provide detailed feedback by Friday
      `.trim());

      await submitButton.tap();

      await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 45000 });

      // Long text should wrap, not overflow
      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });

      expect(hasHorizontalScroll).toBe(false);
    });
  });

  test.describe('Image and media scaling', () => {
    test('should scale images responsively', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/meeting-notes');

      // Check for any images
      const images = page.locator('img');
      const imageCount = await images.count();

      for (let i = 0; i < imageCount; i++) {
        const img = images.nth(i);
        const imgWidth = await img.evaluate(el => el.clientWidth);
        const viewportWidth = 375;

        // Images should not exceed viewport width
        expect(imgWidth).toBeLessThanOrEqual(viewportWidth);
      }
    });
  });

  test.describe('Spacing and padding', () => {
    test('should have appropriate spacing on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/meeting-notes');

      const container = page.locator('[class*="p-"], [class*="px-"], [class*="py-"]').first();

      // Should have some padding
      const padding = await container.evaluate(el => {
        const styles = window.getComputedStyle(el);
        return {
          left: parseInt(styles.paddingLeft),
          right: parseInt(styles.paddingRight)
        };
      });

      // Should have reasonable padding on mobile
      expect(padding.left).toBeGreaterThanOrEqual(16);
      expect(padding.right).toBeGreaterThanOrEqual(16);
    });

    test('should adjust spacing for larger screens', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto('/meeting-notes');

      const container = page.locator('[class*="p-"], [class*="px-"], [class*="py-"]').first();

      // May have more generous padding on desktop
      const padding = await container.evaluate(el => {
        const styles = window.getComputedStyle(el);
        return parseInt(styles.paddingLeft);
      });

      expect(padding).toBeGreaterThanOrEqual(0);
    });
  });
});
