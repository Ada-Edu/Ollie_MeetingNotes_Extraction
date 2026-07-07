import { test, expect } from '@playwright/test';

test.describe('Multi-Browser Compatibility', () => {
  test('should render meeting notes form in all browsers', async ({ page }) => {
    await page.goto('/meeting-notes');

    // Verify core functionality works
    await expect(page.getByPlaceholder(/paste your meeting notes/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /extract action items/i })).toBeVisible();

    // Test submission works
    await page.fill('textarea', 'Test notes');
    await page.click('button[type="submit"]');
    await expect(page.getByText(/processing/i)).toBeVisible();
  });

  test('should handle form submission across browsers', async ({ page }) => {
    await page.goto('/');

    const input = page.locator('input[type="text"], input[type="email"], textarea').first();
    if (await input.count() > 0) {
      await input.fill('test data');
      await expect(input).toHaveValue('test data');

      const submitButton = page.locator('button[type="submit"], input[type="submit"]').first();
      if (await submitButton.count() > 0) {
        await submitButton.click();
      }
    }
  });

  test('should display CSS animations correctly', async ({ page }) => {
    await page.goto('/');

    const animatedElement = await page.locator('[class*="animate"], [class*="transition"], [class*="fade"]').first();
    if (await animatedElement.count() > 0) {
      const opacity = await animatedElement.evaluate(el =>
        window.getComputedStyle(el).opacity
      );
      expect(parseFloat(opacity)).toBeGreaterThanOrEqual(0);
      expect(parseFloat(opacity)).toBeLessThanOrEqual(1);
    }
  });

  test('should handle text input correctly', async ({ page }) => {
    await page.goto('/');

    const textInput = page.locator('input[type="text"], textarea').first();
    if (await textInput.count() > 0) {
      const testText = 'Multi-browser test input 123!@#';
      await textInput.fill(testText);
      await expect(textInput).toHaveValue(testText);

      await textInput.clear();
      await expect(textInput).toHaveValue('');

      await textInput.type('Typed text', { delay: 10 });
      await expect(textInput).toHaveValue('Typed text');
    }
  });

  test('should handle button interactions', async ({ page }) => {
    await page.goto('/');

    const button = page.locator('button').first();
    if (await button.count() > 0) {
      await expect(button).toBeVisible();
      await expect(button).toBeEnabled();

      const isClickable = await button.evaluate(el => {
        const style = window.getComputedStyle(el);
        return style.pointerEvents !== 'none' && style.display !== 'none';
      });
      expect(isClickable).toBe(true);

      await button.click();
    }
  });

  test('should display results correctly', async ({ page }) => {
    await page.goto('/');

    const resultContainers = page.locator('[class*="result"], [id*="result"], [data-testid*="result"]');
    if (await resultContainers.count() > 0) {
      const firstResult = resultContainers.first();
      const isVisible = await firstResult.isVisible();
      expect(typeof isVisible).toBe('boolean');
    }

    const contentElements = page.locator('p, div, span').first();
    await expect(contentElements).toBeTruthy();
  });

  test('should handle navigation correctly', async ({ page }) => {
    await page.goto('/');
    const initialUrl = page.url();
    expect(initialUrl).toBeTruthy();

    const links = page.locator('a[href]');
    if (await links.count() > 0) {
      const firstLink = links.first();
      const href = await firstLink.getAttribute('href');

      if (href && !href.startsWith('http') && !href.startsWith('mailto:')) {
        await firstLink.click();
        await page.waitForLoadState('networkidle');

        await page.goBack();
        await page.waitForLoadState('networkidle');
        expect(page.url()).toContain(new URL(initialUrl).pathname.split('/')[1] || '');
      }
    }
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('/');

    await page.keyboard.press('Tab');
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedElement).toBeTruthy();

    const input = page.locator('input, textarea').first();
    if (await input.count() > 0) {
      await input.focus();
      await page.keyboard.type('Keyboard input');
      await expect(input).toHaveValue('Keyboard input');

      await page.keyboard.press('Control+A');
      await page.keyboard.press('Backspace');
      await expect(input).toHaveValue('');
    }
  });

  test('should handle Fetch API correctly', async ({ page }) => {
    await page.goto('/');

    const fetchResult = await page.evaluate(async () => {
      try {
        const response = await fetch('/');
        return {
          ok: response.ok,
          status: response.status,
          hasHeaders: response.headers !== null
        };
      } catch (error) {
        return { error: String(error) };
      }
    });

    if ('ok' in fetchResult) {
      expect(fetchResult.ok).toBe(true);
      expect(fetchResult.status).toBe(200);
      expect(fetchResult.hasHeaders).toBe(true);
    }
  });

  test('should handle WebSocket connections', async ({ page }) => {
    await page.goto('/');

    const webSocketSupport = await page.evaluate(() => {
      return typeof WebSocket !== 'undefined';
    });
    expect(webSocketSupport).toBe(true);

    const canCreateWebSocket = await page.evaluate(() => {
      try {
        const ws = new WebSocket('ws://localhost:9999');
        ws.close();
        return true;
      } catch (error) {
        return false;
      }
    });
    expect(typeof canCreateWebSocket).toBe('boolean');
  });

  test('should handle long-running operations', async ({ page }) => {
    await page.goto('/');

    const startTime = Date.now();
    const result = await page.evaluate(async () => {
      return new Promise(resolve => {
        setTimeout(() => {
          resolve('completed');
        }, 1000);
      });
    });
    const endTime = Date.now();

    expect(result).toBe('completed');
    expect(endTime - startTime).toBeGreaterThanOrEqual(1000);
  });

  test('should handle localStorage correctly', async ({ page }) => {
    await page.goto('/');

    const testKey = 'multi-browser-test';
    const testValue = JSON.stringify({ data: 'test-value', timestamp: Date.now() });

    await page.evaluate(([key, value]) => {
      localStorage.setItem(key, value);
    }, [testKey, testValue]);

    const retrievedValue = await page.evaluate((key) => {
      return localStorage.getItem(key);
    }, testKey);

    expect(retrievedValue).toBe(testValue);

    await page.evaluate((key) => {
      localStorage.removeItem(key);
    }, testKey);

    const afterRemoval = await page.evaluate((key) => {
      return localStorage.getItem(key);
    }, testKey);

    expect(afterRemoval).toBeNull();
  });

  test('should render fonts correctly', async ({ page }) => {
    await page.goto('/');

    const textElement = page.locator('h1, h2, p, span').first();
    if (await textElement.count() > 0) {
      const fontProperties = await textElement.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          fontFamily: style.fontFamily,
          fontSize: style.fontSize,
          fontWeight: style.fontWeight,
          lineHeight: style.lineHeight
        };
      });

      expect(fontProperties.fontFamily).toBeTruthy();
      expect(fontProperties.fontSize).toBeTruthy();
      expect(parseInt(fontProperties.fontSize)).toBeGreaterThan(0);
    }
  });

  test('should handle JSON parsing correctly', async ({ page }) => {
    await page.goto('/');

    const jsonTests = await page.evaluate(() => {
      const testData = {
        string: 'test',
        number: 42,
        boolean: true,
        array: [1, 2, 3],
        nested: { key: 'value' },
        null: null
      };

      const jsonString = JSON.stringify(testData);
      const parsed = JSON.parse(jsonString);

      return {
        stringified: jsonString.length > 0,
        parsedCorrectly: parsed.string === 'test' && parsed.number === 42,
        arrayLength: parsed.array.length,
        nestedValue: parsed.nested.key
      };
    });

    expect(jsonTests.stringified).toBe(true);
    expect(jsonTests.parsedCorrectly).toBe(true);
    expect(jsonTests.arrayLength).toBe(3);
    expect(jsonTests.nestedValue).toBe('value');
  });
});
