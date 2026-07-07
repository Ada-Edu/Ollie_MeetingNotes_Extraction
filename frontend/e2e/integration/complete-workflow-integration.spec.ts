/**
 * Complete frontend-backend integration tests using Playwright E2E.
 * Tests the full workflow from frontend through API to Temporal and back.
 *
 * @group e2e-integration
 */

import { test, expect } from '@playwright/test';

test.describe('Complete Frontend-Backend Integration', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:5173');
  });

  test('should complete full workflow from frontend to backend and show results', async ({
    page,
  }) => {
    // Step 1: Enter meeting notes in frontend
    const meetingNotes = `
      Team Meeting - July 7, 2026

      Attendees: Alice, Bob, Carol

      Action Items:
      1. Alice to review Q3 budget proposal by July 15th
      2. Bob will update the project timeline and share with team
      3. Carol to schedule follow-up meeting with stakeholders by end of week
    `;

    await page.fill('textarea[name="notes"]', meetingNotes);

    // Step 2: Submit the form
    await page.click('button[type="submit"]');

    // Step 3: Verify loading state appears
    await expect(page.locator('text=/Processing|Extracting/i')).toBeVisible({
      timeout: 3000,
    });

    // Step 4: Wait for workflow to complete and results to appear
    // This tests the polling mechanism
    await expect(page.locator('text=/Action Items|Results/i')).toBeVisible({
      timeout: 30000, // Give Temporal workflow time to complete
    });

    // Step 5: Verify action items are displayed
    const actionItems = page.locator('[data-testid="action-item"]');
    await expect(actionItems).toHaveCount(3, { timeout: 5000 });

    // Step 6: Verify specific action item content
    await expect(page.locator('text=/Alice.*budget/i')).toBeVisible();
    await expect(page.locator('text=/Bob.*timeline/i')).toBeVisible();
    await expect(page.locator('text=/Carol.*meeting/i')).toBeVisible();

    // Step 7: Verify owners are extracted
    await expect(page.locator('text=/Alice/i')).toBeVisible();
    await expect(page.locator('text=/Bob/i')).toBeVisible();
    await expect(page.locator('text=/Carol/i')).toBeVisible();

    // Step 8: Verify due dates are shown
    await expect(page.locator('text=/July 15|2026-07-15/i')).toBeVisible();
    await expect(page.locator('text=/end of week/i')).toBeVisible();
  });

  test('should handle workflow failure gracefully', async ({ page }) => {
    // Submit invalid/empty meeting notes
    await page.fill('textarea[name="notes"]', 'Too short');

    await page.click('button[type="submit"]');

    // Should show error message
    await expect(
      page.locator('text=/Error|Failed|too short/i')
    ).toBeVisible({ timeout: 10000 });

    // Should not show action items
    await expect(page.locator('[data-testid="action-item"]')).not.toBeVisible();
  });

  test('should poll for status updates during processing', async ({ page }) => {
    const meetingNotes = 'Team meeting: Alice to review documentation by next week';

    await page.fill('textarea[name="notes"]', meetingNotes);
    await page.click('button[type="submit"]');

    // Verify initial processing state
    await expect(page.locator('text=/Processing/i')).toBeVisible();

    // Monitor for status changes (polling should happen every 2 seconds)
    let statusChanges = 0;
    const statusElement = page.locator('[data-testid="extraction-status"]');

    // Wait and check that status updates occur
    await page.waitForTimeout(2500); // Wait for at least one poll

    // Eventually should show completed
    await expect(page.locator('text=/Completed|Success/i')).toBeVisible({
      timeout: 30000,
    });
  });

  test('should display multiple action items with correct details', async ({
    page,
  }) => {
    const meetingNotes = `
      Project Kickoff Meeting

      1. John will create initial project plan by July 20th (HIGH PRIORITY)
      2. Sarah needs to set up development environment
      3. Mike to schedule weekly sync meetings starting next Monday
      4. Lisa will prepare stakeholder presentation by July 18th
      5. Team to review and approve architecture by July 25th
    `;

    await page.fill('textarea[name="notes"]', meetingNotes);
    await page.click('button[type="submit"]');

    // Wait for completion
    await expect(page.locator('[data-testid="action-item"]')).toHaveCount(5, {
      timeout: 30000,
    });

    // Verify each action item has required fields
    const items = await page.locator('[data-testid="action-item"]').all();

    for (const item of items) {
      // Each item should have description
      await expect(item.locator('[data-testid="action-description"]')).toBeVisible();

      // Owner might be present
      const owner = item.locator('[data-testid="action-owner"]');
      const ownerExists = await owner.count();
      if (ownerExists > 0) {
        await expect(owner).toBeVisible();
      }
    }
  });

  test('should show extraction run metadata (model provider, model name)', async ({
    page,
  }) => {
    const meetingNotes = 'Team meeting: Alice to complete task by Friday';

    await page.fill('textarea[name="notes"]', meetingNotes);
    await page.click('button[type="submit"]');

    // Wait for completion
    await expect(page.locator('text=/Completed/i')).toBeVisible({
      timeout: 30000,
    });

    // Check for model metadata
    const metadataSection = page.locator('[data-testid="extraction-metadata"]');
    if ((await metadataSection.count()) > 0) {
      await expect(metadataSection).toContainText(/azure|bedrock/i);
      await expect(metadataSection).toContainText(/gpt-4|claude/i);
    }
  });

  test('should handle action items without owners or due dates', async ({
    page,
  }) => {
    const meetingNotes = `
      Quick standup notes:
      - Update documentation
      - Review pull requests
      - Refactor authentication module
    `;

    await page.fill('textarea[name="notes"]', meetingNotes);
    await page.click('button[type="submit"]');

    await expect(page.locator('[data-testid="action-item"]')).toHaveCount(3, {
      timeout: 30000,
    });

    // Should show "Unassigned" or similar for items without owner
    await expect(page.locator('text=/Unassigned|No owner/i')).toBeVisible();

    // Should show "No due date" or similar
    await expect(page.locator('text=/No due date|No deadline/i')).toBeVisible();
  });

  test('should allow submitting another extraction after completion', async ({
    page,
  }) => {
    // First extraction
    await page.fill('textarea[name="notes"]', 'First meeting: Alice to review docs');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=/Completed/i')).toBeVisible({
      timeout: 30000,
    });

    // Second extraction
    await page.fill('textarea[name="notes"]', 'Second meeting: Bob to update code');
    await page.click('button[type="submit"]');

    // Should process second extraction
    await expect(page.locator('text=/Processing/i')).toBeVisible();
    await expect(page.locator('text=/Completed/i')).toBeVisible({
      timeout: 30000,
    });

    // Should show new action items
    await expect(page.locator('text=/Bob.*code/i')).toBeVisible();
  });

  test('should display confidence scores when available', async ({ page }) => {
    const meetingNotes = `
      Clear action items:
      1. John Smith to submit quarterly report by July 31st, 2026
      2. Review and approve budget proposal
    `;

    await page.fill('textarea[name="notes"]', meetingNotes);
    await page.click('button[type="submit"]');

    await expect(page.locator('[data-testid="action-item"]')).toHaveCount(2, {
      timeout: 30000,
    });

    // Check if confidence scores are displayed
    const confidenceElements = page.locator('[data-testid="action-confidence"]');
    const count = await confidenceElements.count();

    if (count > 0) {
      // Verify confidence is between 0 and 1 or displayed as percentage
      const confidenceText = await confidenceElements.first().textContent();
      expect(confidenceText).toMatch(/\d+%|0\.\d+/);
    }
  });
});

test.describe('Frontend-Backend Error Handling Integration', () => {
  test('should handle API connection errors', async ({ page }) => {
    // Intercept and fail the API call
    await page.route('**/trigger-workflow', (route) => {
      route.abort('connectionrefused');
    });

    await page.goto('http://localhost:5173');
    await page.fill('textarea[name="notes"]', 'Test meeting notes');
    await page.click('button[type="submit"]');

    // Should show connection error
    await expect(
      page.locator('text=/Connection|Network|Unable to connect/i')
    ).toBeVisible({ timeout: 5000 });
  });

  test('should handle workflow trigger failure', async ({ page }) => {
    // Intercept and return error
    await page.route('**/trigger-workflow', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Temporal service unavailable',
        }),
      });
    });

    await page.goto('http://localhost:5173');
    await page.fill('textarea[name="notes"]', 'Test meeting notes');
    await page.click('button[type="submit"]');

    // Should show error from API
    await expect(page.locator('text=/Temporal|unavailable/i')).toBeVisible({
      timeout: 5000,
    });
  });

  test('should handle extraction run not found', async ({ page }) => {
    await page.goto('http://localhost:5173');

    // Try to navigate to non-existent extraction run
    await page.goto('http://localhost:5173/extraction/non-existent-id');

    // Should show not found or error message
    await expect(
      page.locator('text=/Not found|Error|Invalid/i')
    ).toBeVisible();
  });
});

test.describe('Performance and Reliability Integration', () => {
  test('should handle slow API responses gracefully', async ({ page }) => {
    // Add delay to API responses
    await page.route('**/trigger-workflow', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      await route.continue();
    });

    await page.goto('http://localhost:5173');
    await page.fill('textarea[name="notes"]', 'Test meeting with slow API');
    await page.click('button[type="submit"]');

    // Should show loading state during delay
    await expect(page.locator('text=/Processing|Loading/i')).toBeVisible();

    // Should eventually complete
    await expect(page.locator('text=/Completed|Success/i')).toBeVisible({
      timeout: 40000,
    });
  });

  test('should stop polling after workflow completes', async ({ page }) => {
    const requestLog: string[] = [];

    // Track polling requests
    await page.route('**/extraction_runs**', (route) => {
      requestLog.push(new Date().toISOString());
      route.continue();
    });

    await page.goto('http://localhost:5173');
    await page.fill('textarea[name="notes"]', 'Test polling behavior');
    await page.click('button[type="submit"]');

    // Wait for completion
    await expect(page.locator('text=/Completed/i')).toBeVisible({
      timeout: 30000,
    });

    const requestsBeforeComplete = requestLog.length;

    // Wait additional time
    await page.waitForTimeout(8000);

    // Should not have made many more requests after completion
    expect(requestLog.length - requestsBeforeComplete).toBeLessThan(3);
  });

  test('should handle large meeting notes', async ({ page }) => {
    // Generate large meeting notes (but within 10000 char limit)
    const largeNotes = `
      Large Meeting Notes - Q3 Planning

      ${Array.from({ length: 50 }, (_, i) => `
      Action Item ${i + 1}: Team member ${i + 1} needs to complete task ${i + 1} by end of quarter.
      This includes review, testing, and documentation.
      `).join('\n')}
    `;

    await page.goto('http://localhost:5173');
    await page.fill('textarea[name="notes"]', largeNotes.substring(0, 9500));
    await page.click('button[type="submit"]');

    // Should process successfully
    await expect(page.locator('text=/Processing/i')).toBeVisible();
    await expect(page.locator('text=/Completed/i')).toBeVisible({
      timeout: 45000, // Longer timeout for large payload
    });

    // Should extract multiple action items
    const items = await page.locator('[data-testid="action-item"]').count();
    expect(items).toBeGreaterThan(10);
  });
});
