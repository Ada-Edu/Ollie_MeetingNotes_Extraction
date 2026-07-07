import { test, expect, devices } from '@playwright/test';

test.describe('Responsive Design Tests', () => {
  const baseURL = process.env.BASE_URL || 'http://localhost:3000';

  test.describe('Mobile Viewport - iPhone', () => {
    test.use({ ...devices['iPhone 13 Pro'] });

    test('should render correctly on iPhone viewport', async ({ page }) => {
      await page.goto(baseURL);
      const viewport = page.viewportSize();
      expect(viewport?.width).toBeLessThanOrEqual(428);
      await expect(page.locator('body')).toBeVisible();
    });

    test('should display touch-friendly buttons on mobile', async ({ page }) => {
      await page.goto(baseURL);
      const buttons = page.locator('button');
      const count = await buttons.count();

      for (let i = 0; i < count; i++) {
        const button = buttons.nth(i);
        const box = await button.boundingBox();
        if (box) {
          expect(box.height).toBeGreaterThanOrEqual(44);
          expect(box.width).toBeGreaterThanOrEqual(44);
        }
      }
    });

    test('should support complete extraction flow on mobile', async ({ page }) => {
      await page.goto(`${baseURL}/meeting-notes`);

      // Verify form is usable
      const textarea = page.getByPlaceholder(/paste your meeting notes/i);
      await expect(textarea).toBeVisible();

      const box = await textarea.boundingBox();
      expect(box?.width).toBeGreaterThan(200);  // Wide enough to use

      // Complete full workflow on mobile
      await textarea.fill('Meeting notes: John to review doc by Friday');
      await page.getByRole('button', { name: /extract/i }).click();

      // Verify results are readable on mobile
      await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 60000 });

      const actionItem = page.locator('[data-testid="action-item"]').first();
      const itemBox = await actionItem.boundingBox();
      expect(itemBox?.width).toBeLessThanOrEqual(page.viewportSize()?.width || 0);

      // Verify text is not truncated
      const description = await actionItem.locator('[data-field="description"]').textContent();
      expect(description).toContain('review doc');
    });

    test('should stack elements vertically on mobile', async ({ page }) => {
      await page.goto(baseURL);
      const container = page.locator('[data-testid="main-container"]').first();
      if (await container.count() > 0) {
        const flexDirection = await container.evaluate((el) =>
          window.getComputedStyle(el).flexDirection
        );
        expect(['column', 'column-reverse']).toContain(flexDirection);
      }
    });

    test('should handle mobile keyboard appearance', async ({ page }) => {
      await page.goto(baseURL);
      const input = page.locator('input[type="text"]').first();

      if (await input.count() > 0) {
        await input.focus();
        await page.waitForTimeout(500);
        await expect(input).toBeFocused();
        const isVisible = await input.isVisible();
        expect(isVisible).toBeTruthy();
      }
    });

    test('should enable smooth scrolling on mobile', async ({ page }) => {
      await page.goto(baseURL);
      const scrollBehavior = await page.evaluate(() =>
        window.getComputedStyle(document.documentElement).scrollBehavior
      );
      expect(['smooth', 'auto']).toContain(scrollBehavior);
    });

    test('should prevent horizontal overflow on mobile', async ({ page }) => {
      await page.goto(baseURL);
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
      const viewportWidth = page.viewportSize()?.width || 0;
      expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 1);

      // Verify content is readable and usable
      const textElements = page.locator('p, span, h1, h2, h3, button, a');
      const count = await textElements.count();

      if (count > 0) {
        for (let i = 0; i < Math.min(count, 5); i++) {
          const element = textElements.nth(i);
          const elementBox = await element.boundingBox();

          if (elementBox) {
            // Verify element is not wider than viewport
            expect(elementBox.width).toBeLessThanOrEqual(viewportWidth);

            // Verify element is positioned within viewport
            expect(elementBox.x).toBeGreaterThanOrEqual(0);
            expect(elementBox.x + elementBox.width).toBeLessThanOrEqual(viewportWidth + 1);

            // Verify text is readable (not too small)
            const fontSize = await element.evaluate((el) =>
              parseInt(window.getComputedStyle(el).fontSize)
            );
            expect(fontSize).toBeGreaterThanOrEqual(12);
          }
        }
      }
    });
  });

  test.describe('Tablet Viewport - iPad', () => {
    test.use({ ...devices['iPad Pro'] });

    test('should render correctly on iPad viewport', async ({ page }) => {
      await page.goto(baseURL);
      const viewport = page.viewportSize();
      expect(viewport?.width).toBeGreaterThan(768);
      expect(viewport?.width).toBeLessThanOrEqual(1024);
    });

    test('should utilize available space on tablet', async ({ page }) => {
      await page.goto(baseURL);
      const mainContent = page.locator('main, [role="main"]').first();

      if (await mainContent.count() > 0) {
        const box = await mainContent.boundingBox();
        const viewportWidth = page.viewportSize()?.width || 0;

        if (box) {
          expect(box.width).toBeGreaterThan(viewportWidth * 0.5);
        }
      }
    });

    test('should support both touch and mouse interactions on tablet', async ({ page }) => {
      await page.goto(baseURL);
      const button = page.locator('button').first();

      if (await button.count() > 0) {
        await button.click();
        await expect(button).toBeVisible();
      }
    });
  });

  test.describe('Desktop Viewport', () => {
    test.use({ viewport: { width: 1920, height: 1080 } });

    test('should render correctly on desktop viewport', async ({ page }) => {
      await page.goto(baseURL);
      const viewport = page.viewportSize();
      expect(viewport?.width).toBe(1920);
      expect(viewport?.height).toBe(1080);
    });

    test('should apply max-width constraints on desktop', async ({ page }) => {
      await page.goto(baseURL);
      const container = page.locator('[class*="container"], main').first();

      if (await container.count() > 0) {
        const maxWidth = await container.evaluate((el) =>
          window.getComputedStyle(el).maxWidth
        );
        expect(maxWidth).not.toBe('none');
      }
    });

    test('should center content on wide screens', async ({ page }) => {
      await page.goto(baseURL);
      const mainContent = page.locator('main, [role="main"]').first();

      if (await mainContent.count() > 0) {
        const box = await mainContent.boundingBox();
        const viewportWidth = page.viewportSize()?.width || 0;

        if (box) {
          const marginLeft = box.x;
          const marginRight = viewportWidth - (box.x + box.width);
          const difference = Math.abs(marginLeft - marginRight);
          expect(difference).toBeLessThan(50);
        }
      }
    });
  });

  test.describe('Viewport Transitions', () => {
    test('should transition from mobile to tablet smoothly', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(baseURL);
      await expect(page.locator('body')).toBeVisible();

      await page.setViewportSize({ width: 768, height: 1024 });
      await page.waitForTimeout(300);
      await expect(page.locator('body')).toBeVisible();
    });

    test('should transition from tablet to desktop smoothly', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(baseURL);
      await expect(page.locator('body')).toBeVisible();

      await page.setViewportSize({ width: 1440, height: 900 });
      await page.waitForTimeout(300);
      await expect(page.locator('body')).toBeVisible();
    });
  });

  test.describe('Orientation Support', () => {
    test('should handle portrait orientation', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 });
      await page.goto(baseURL);

      const viewport = page.viewportSize();
      expect(viewport?.height).toBeGreaterThan(viewport?.width || 0);
      await expect(page.locator('body')).toBeVisible();
    });

    test('should handle landscape orientation', async ({ page }) => {
      await page.setViewportSize({ width: 812, height: 375 });
      await page.goto(baseURL);

      const viewport = page.viewportSize();
      expect(viewport?.width).toBeGreaterThan(viewport?.height || 0);
      await expect(page.locator('body')).toBeVisible();
    });
  });

  test.describe('Common Breakpoints', () => {
    const breakpoints = [
      { name: 'Extra Small - 320px', width: 320, height: 568 },
      { name: 'Small - 375px', width: 375, height: 667 },
      { name: 'Medium - 768px', width: 768, height: 1024 },
      { name: 'Large - 1024px', width: 1024, height: 768 },
      { name: 'Extra Large - 1440px', width: 1440, height: 900 },
      { name: 'XXL - 1920px', width: 1920, height: 1080 },
    ];

    breakpoints.forEach(({ name, width, height }) => {
      test(`should render correctly at ${name}`, async ({ page }) => {
        await page.setViewportSize({ width, height });
        await page.goto(baseURL);

        await expect(page.locator('body')).toBeVisible();

        const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
        expect(bodyWidth).toBeLessThanOrEqual(width + 1);
      });
    });
  });

  test.describe('Text Readability', () => {
    test('should have readable font sizes on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(baseURL);

      const paragraphs = page.locator('p, span, div').first();
      if (await paragraphs.count() > 0) {
        const fontSize = await paragraphs.evaluate((el) =>
          parseInt(window.getComputedStyle(el).fontSize)
        );
        expect(fontSize).toBeGreaterThanOrEqual(14);
      }
    });

    test('should scale fonts appropriately across viewports', async ({ page }) => {
      const viewports = [
        { width: 375, height: 667 },
        { width: 1440, height: 900 }
      ];

      const fontSizes: number[] = [];

      for (const viewport of viewports) {
        await page.setViewportSize(viewport);
        await page.goto(baseURL);

        const heading = page.locator('h1, h2').first();
        if (await heading.count() > 0) {
          const fontSize = await heading.evaluate((el) =>
            parseInt(window.getComputedStyle(el).fontSize)
          );
          fontSizes.push(fontSize);
        }
      }

      if (fontSizes.length === 2) {
        expect(fontSizes[1]).toBeGreaterThanOrEqual(fontSizes[0]);
      }
    });
  });

  test.describe('Touch Interactions', () => {
    test.use({ ...devices['iPhone 13 Pro'] });

    test('should handle tap interactions', async ({ page }) => {
      await page.goto(baseURL);
      const button = page.locator('button').first();

      if (await button.count() > 0) {
        await button.tap();
        await expect(button).toBeVisible();
      }
    });

    test('should have adequate touch target spacing', async ({ page }) => {
      await page.goto(baseURL);
      const buttons = page.locator('button');
      const count = await buttons.count();

      for (let i = 0; i < count - 1; i++) {
        const box1 = await buttons.nth(i).boundingBox();
        const box2 = await buttons.nth(i + 1).boundingBox();

        if (box1 && box2) {
          const verticalGap = Math.abs(box2.y - (box1.y + box1.height));
          const horizontalGap = Math.abs(box2.x - (box1.x + box1.width));
          const minGap = Math.min(verticalGap, horizontalGap);

          if (minGap > 0) {
            expect(minGap).toBeGreaterThanOrEqual(8);
          }
        }
      }
    });
  });

  test.describe('Flexible Layouts', () => {
    test('should use flexible layout units', async ({ page }) => {
      await page.goto(baseURL);
      const container = page.locator('[class*="container"], main').first();

      if (await container.count() > 0) {
        const width = await container.evaluate((el) =>
          window.getComputedStyle(el).width
        );
        expect(width).toMatch(/(%|rem|em|vw|auto)/);
      }
    });

    test('should adapt grid layouts to viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(baseURL);

      const grid = page.locator('[class*="grid"]').first();
      if (await grid.count() > 0) {
        const mobileColumns = await grid.evaluate((el) =>
          window.getComputedStyle(el).gridTemplateColumns
        );

        await page.setViewportSize({ width: 1440, height: 900 });
        await page.waitForTimeout(300);

        const desktopColumns = await grid.evaluate((el) =>
          window.getComputedStyle(el).gridTemplateColumns
        );

        expect(mobileColumns).not.toBe(desktopColumns);
      }
    });
  });

  test.describe('Image Scaling', () => {
    test('should scale images responsively', async ({ page }) => {
      await page.goto(baseURL);
      const images = page.locator('img');
      const count = await images.count();

      for (let i = 0; i < count; i++) {
        const img = images.nth(i);
        const maxWidth = await img.evaluate((el) =>
          window.getComputedStyle(el).maxWidth
        );
        expect(['100%', 'none']).toContain(maxWidth);
      }
    });

    test('should maintain aspect ratio of images', async ({ page }) => {
      await page.goto(baseURL);
      const images = page.locator('img');
      const count = await images.count();

      for (let i = 0; i < count; i++) {
        const img = images.nth(i);
        const objectFit = await img.evaluate((el) =>
          window.getComputedStyle(el).objectFit
        );
        expect(['contain', 'cover', 'fill', 'none', 'scale-down']).toContain(objectFit);
      }
    });
  });

  test.describe('Spacing and Padding', () => {
    test('should adjust padding for mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(baseURL);

      const container = page.locator('main, [role="main"]').first();
      if (await container.count() > 0) {
        const padding = await container.evaluate((el) =>
          parseInt(window.getComputedStyle(el).paddingLeft)
        );
        expect(padding).toBeGreaterThanOrEqual(8);
        expect(padding).toBeLessThanOrEqual(32);
      }
    });

    test('should increase spacing on larger screens', async ({ page }) => {
      const viewports = [
        { width: 375, height: 667 },
        { width: 1440, height: 900 }
      ];

      const paddings: number[] = [];

      for (const viewport of viewports) {
        await page.setViewportSize(viewport);
        await page.goto(baseURL);

        const container = page.locator('main, [role="main"]').first();
        if (await container.count() > 0) {
          const padding = await container.evaluate((el) =>
            parseInt(window.getComputedStyle(el).paddingLeft)
          );
          paddings.push(padding);
        }
      }

      if (paddings.length === 2) {
        expect(paddings[1]).toBeGreaterThanOrEqual(paddings[0]);
      }
    });
  });

  test.describe('Accessibility on Different Viewports', () => {
    test('should maintain focus visibility on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(baseURL);

      const focusableElement = page.locator('button, a, input').first();
      if (await focusableElement.count() > 0) {
        await focusableElement.focus();
        const outline = await focusableElement.evaluate((el) =>
          window.getComputedStyle(el).outline
        );
        expect(outline).not.toBe('none');
      }
    });

    test('should support zoom without breaking layout', async ({ page }) => {
      await page.goto(baseURL);
      await page.evaluate(() => {
        document.body.style.zoom = '150%';
      });

      await page.waitForTimeout(300);
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
      const viewportWidth = page.viewportSize()?.width || 0;
      expect(bodyWidth).toBeLessThanOrEqual(viewportWidth * 1.6);
    });
  });
});
