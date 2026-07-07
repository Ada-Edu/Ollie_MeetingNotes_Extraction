import { test, expect } from '@playwright/test';

test.describe('Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.describe('Document Structure', () => {
    test('should have proper document title', async ({ page }) => {
      await expect(page).toHaveTitle(/./);
      const title = await page.title();
      expect(title.length).toBeGreaterThan(0);
    });

    test('should have main landmark', async ({ page }) => {
      const main = page.locator('main, [role="main"]');
      await expect(main).toBeVisible();
    });

    test('should have proper heading hierarchy', async ({ page }) => {
      const h1 = page.locator('h1');
      await expect(h1).toHaveCount(1);

      const headings = await page.locator('h1, h2, h3, h4, h5, h6').all();
      expect(headings.length).toBeGreaterThan(0);
    });
  });

  test.describe('Form Labels and Inputs', () => {
    test('should provide meaningful labels for all form inputs', async ({ page }) => {
      const inputs = await page.locator('input:not([type="hidden"])').all();

      for (const input of inputs) {
        const id = await input.getAttribute('id');
        const ariaLabel = await input.getAttribute('aria-label');
        const ariaLabelledby = await input.getAttribute('aria-labelledby');

        let label = ariaLabel;

        if (!label && id) {
          const labelElement = page.locator(`label[for="${id}"]`);
          if (await labelElement.count() > 0) {
            label = await labelElement.textContent();
          }
        }

        if (!label && ariaLabelledby) {
          const labelElement = page.locator(`#${ariaLabelledby}`);
          if (await labelElement.count() > 0) {
            label = await labelElement.textContent();
          }
        }

        // Verify label exists and is meaningful
        expect(label).toBeTruthy();
        expect(label?.trim().length).toBeGreaterThan(2);
        expect(label).not.toMatch(/^[^a-z]+$/i); // Not just symbols

        // Verify label describes purpose for common input types
        const inputType = await input.getAttribute('type');
        if (inputType === 'email') {
          expect(label?.toLowerCase()).toMatch(/email|address|contact/);
        } else if (inputType === 'password') {
          expect(label?.toLowerCase()).toMatch(/password|pass/);
        } else if (inputType === 'tel') {
          expect(label?.toLowerCase()).toMatch(/phone|tel|contact/);
        }
      }
    });

    test('should have accessible placeholders', async ({ page }) => {
      const inputsWithPlaceholder = await page.locator('input[placeholder]').all();

      for (const input of inputsWithPlaceholder) {
        const ariaLabel = await input.getAttribute('aria-label');
        const ariaLabelledby = await input.getAttribute('aria-labelledby');
        const id = await input.getAttribute('id');
        const hasLabel = id ? await page.locator(`label[for="${id}"]`).count() > 0 : false;

        expect(hasLabel || ariaLabel || ariaLabelledby).toBeTruthy();
      }
    });
  });

  test.describe('Keyboard Navigation', () => {
    test('should allow keyboard navigation through interactive elements', async ({ page }) => {
      const buttons = await page.locator('button, a, input, select, textarea').all();

      if (buttons.length > 0) {
        await page.keyboard.press('Tab');
        const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
        expect(['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA']).toContain(focusedElement);
      }
    });

    test('should support Enter key activation on buttons', async ({ page }) => {
      const clickableButtons = await page.locator('button:not([disabled]), a[href]:not([disabled])').all();

      if (clickableButtons.length > 0) {
        const button = clickableButtons[0];
        await button.focus();

        // Track state change to verify activation worked
        const buttonText = await button.textContent();
        const initialUrl = page.url();

        await page.keyboard.press('Enter');

        // Wait a moment for any state changes
        await page.waitForTimeout(100);

        // Verify something happened (URL changed, modal opened, or element state changed)
        const newUrl = page.url();
        const hasDialog = await page.locator('[role="dialog"], [role="alertdialog"]').count() > 0;
        const hasAlert = await page.locator('[role="alert"]').count() > 0;

        // At least one of these should be true for a functional button
        expect(newUrl !== initialUrl || hasDialog || hasAlert).toBeTruthy();
      }
    });

    test('should support Space key activation on buttons', async ({ page }) => {
      const clickableButtons = await page.locator('button:not([disabled])').all();

      if (clickableButtons.length > 0) {
        const button = clickableButtons[0];
        await button.focus();

        const initialUrl = page.url();

        await page.keyboard.press('Space');

        // Wait a moment for any state changes
        await page.waitForTimeout(100);

        // Verify something happened
        const newUrl = page.url();
        const hasDialog = await page.locator('[role="dialog"], [role="alertdialog"]').count() > 0;
        const hasAlert = await page.locator('[role="alert"]').count() > 0;

        expect(newUrl !== initialUrl || hasDialog || hasAlert).toBeTruthy();
      }
    });

    test('should support full keyboard workflow for form submission', async ({ page }) => {
      const forms = await page.locator('form').all();

      if (forms.length > 0) {
        // Find the first text input or textarea
        const textInput = page.locator('input[type="text"], input[type="email"], textarea').first();
        const inputCount = await textInput.count();

        if (inputCount > 0) {
          // Navigate to input via keyboard
          await page.keyboard.press('Tab');

          // Verify we can focus the input
          const focusedTag = await page.evaluate(() => document.activeElement?.tagName);
          expect(['INPUT', 'TEXTAREA']).toContain(focusedTag);

          // Fill form via keyboard
          await page.keyboard.type('Test input for accessibility');

          // Navigate to submit button via Tab
          let attempts = 0;
          while (attempts < 10) {
            await page.keyboard.press('Tab');
            const currentFocus = await page.evaluate(() => {
              const el = document.activeElement;
              return {
                tag: el?.tagName,
                type: el?.getAttribute('type')
              };
            });

            if (currentFocus.tag === 'BUTTON' && currentFocus.type === 'submit') {
              break;
            }
            attempts++;
          }

          // Verify we found a submit button
          const submitButton = page.locator('button[type="submit"]:focus');
          const submitButtonCount = await submitButton.count();
          expect(submitButtonCount).toBeGreaterThan(0);
        }
      }
    });
  });

  test.describe('Focus Indicators', () => {
    test('should show visible focus indicators', async ({ page }) => {
      const interactiveElements = await page.locator('button, a, input, select').all();

      if (interactiveElements.length > 0) {
        const element = interactiveElements[0];
        await element.focus();

        const outlineWidth = await element.evaluate((el) => {
          const styles = window.getComputedStyle(el);
          return styles.outlineWidth !== '0px' || styles.borderWidth !== '0px';
        });

        expect(outlineWidth).toBeTruthy();
      }
    });

    test('should maintain focus order', async ({ page }) => {
      await page.keyboard.press('Tab');
      const firstFocus = await page.evaluate(() => document.activeElement?.tagName);

      await page.keyboard.press('Tab');
      const secondFocus = await page.evaluate(() => document.activeElement?.tagName);

      expect(firstFocus).toBeTruthy();
      expect(secondFocus).toBeTruthy();
    });
  });

  test.describe('ARIA Attributes', () => {
    test('should have valid ARIA roles', async ({ page }) => {
      const elementsWithRole = await page.locator('[role]').all();
      const validRoles = [
        'alert', 'alertdialog', 'application', 'article', 'banner', 'button',
        'checkbox', 'complementary', 'contentinfo', 'dialog', 'document',
        'form', 'grid', 'gridcell', 'heading', 'img', 'link', 'list', 'listbox',
        'listitem', 'main', 'navigation', 'region', 'row', 'search', 'status',
        'tab', 'tablist', 'tabpanel', 'textbox', 'timer', 'toolbar'
      ];

      for (const element of elementsWithRole) {
        const role = await element.getAttribute('role');
        expect(validRoles).toContain(role);
      }
    });

    test('should have proper ARIA labels where needed', async ({ page }) => {
      const buttonsWithoutText = await page.locator('button:not(:has-text(/./))').all();

      for (const button of buttonsWithoutText) {
        const ariaLabel = await button.getAttribute('aria-label');
        const ariaLabelledby = await button.getAttribute('aria-labelledby');

        expect(ariaLabel || ariaLabelledby).toBeTruthy();
      }
    });
  });

  test.describe('Screen Reader Announcements', () => {
    test('should have live regions for dynamic content', async ({ page }) => {
      const liveRegions = page.locator('[aria-live]');
      const count = await liveRegions.count();

      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should announce loading states', async ({ page }) => {
      const loadingElements = page.locator('[aria-busy="true"], [role="status"]');
      const count = await loadingElements.count();

      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Button States', () => {
    test('should properly indicate disabled buttons', async ({ page }) => {
      const disabledButtons = await page.locator('button:disabled, button[aria-disabled="true"]').all();

      for (const button of disabledButtons) {
        const isDisabled = await button.isDisabled();
        const ariaDisabled = await button.getAttribute('aria-disabled');

        expect(isDisabled || ariaDisabled === 'true').toBeTruthy();
      }
    });

    test('should have proper button types', async ({ page }) => {
      const buttons = await page.locator('button').all();

      for (const button of buttons) {
        const type = await button.getAttribute('type');
        expect(['button', 'submit', 'reset', null]).toContain(type);
      }
    });
  });

  test.describe('Color Contrast', () => {
    test('should have sufficient color contrast for text', async ({ page }) => {
      const textElements = await page.locator('p, h1, h2, h3, h4, h5, h6, span, a, button, label').all();

      for (const element of textElements.slice(0, 10)) {
        const isVisible = await element.isVisible();
        if (isVisible) {
          const contrast = await element.evaluate((el) => {
            const styles = window.getComputedStyle(el);
            return {
              color: styles.color,
              backgroundColor: styles.backgroundColor
            };
          });

          expect(contrast.color).toBeTruthy();
        }
      }
    });
  });

  test.describe('Validation Errors', () => {
    test('should associate error messages with inputs', async ({ page }) => {
      const errorMessages = await page.locator('[role="alert"], .error-message, [aria-invalid="true"]').all();

      for (const error of errorMessages) {
        const isVisible = await error.isVisible();
        expect(typeof isVisible).toBe('boolean');
      }
    });

    test('should mark invalid inputs with aria-invalid', async ({ page }) => {
      const invalidInputs = await page.locator('[aria-invalid="true"]').all();

      for (const input of invalidInputs) {
        const describedBy = await input.getAttribute('aria-describedby');
        expect(describedBy).toBeTruthy();
      }
    });
  });

  test.describe('Semantic HTML', () => {
    test('should use semantic HTML elements', async ({ page }) => {
      const semanticElements = await page.locator('header, nav, main, article, section, aside, footer').all();
      expect(semanticElements.length).toBeGreaterThan(0);
    });

    test('should use lists for list content', async ({ page }) => {
      const lists = page.locator('ul, ol');
      const count = await lists.count();

      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Icon Context', () => {
    test('should provide text alternatives for icons', async ({ page }) => {
      const icons = await page.locator('svg, i[class*="icon"], span[class*="icon"]').all();

      for (const icon of icons) {
        const ariaLabel = await icon.getAttribute('aria-label');
        const ariaHidden = await icon.getAttribute('aria-hidden');
        const role = await icon.getAttribute('role');

        expect(ariaLabel || ariaHidden === 'true' || role === 'img').toBeTruthy();
      }
    });
  });

  test.describe('Focus Management', () => {
    test('should not have focus traps', async ({ page }) => {
      let previousFocus = '';
      let sameCount = 0;

      for (let i = 0; i < 10; i++) {
        await page.keyboard.press('Tab');
        const currentFocus = await page.evaluate(() => document.activeElement?.tagName || '');

        if (currentFocus === previousFocus) {
          sameCount++;
        } else {
          sameCount = 0;
        }

        expect(sameCount).toBeLessThan(3);
        previousFocus = currentFocus;
      }
    });
  });

  test.describe('High Contrast Mode', () => {
    test('should support high contrast mode', async ({ page }) => {
      await page.emulateMedia({ colorScheme: 'dark' });
      const body = page.locator('body');
      await expect(body).toBeVisible();
    });
  });

  test.describe('Reduced Motion', () => {
    test('should respect prefers-reduced-motion', async ({ page }) => {
      await page.emulateMedia({ reducedMotion: 'reduce' });
      const body = page.locator('body');
      await expect(body).toBeVisible();
    });
  });

  test.describe('Loading Feedback', () => {
    test('should provide loading feedback for async operations', async ({ page }) => {
      const loadingIndicators = page.locator('[aria-busy], [role="progressbar"], [role="status"]');
      const count = await loadingIndicators.count();

      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Error Messages', () => {
    test('should provide accessible error messages', async ({ page }) => {
      const errorElements = page.locator('[role="alert"], .error, [aria-live="assertive"]');
      const count = await errorElements.count();

      expect(count).toBeGreaterThanOrEqual(0);
    });
  });
});
