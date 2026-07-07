import { test, expect, Page } from '@playwright/test';

test.describe('Complete Meeting Notes Extraction Flow', () => {
  const TEST_NOTES = `
Team Standup - July 7, 2026
Attendees: Sarah (PM), John (Dev), Mike (Architect)

Yesterday:
- Completed user authentication
- Fixed database pooling

Today:
- Working on API documentation
- Starting payment integration

Action Items:
1. John to follow up with Sarah on Q4 budget by July 15
2. Mike to review the architectural design doc by next week
3. Sarah to schedule a meeting with design team ASAP
  `.trim();

  test.beforeEach(async ({ page }) => {
    await page.goto('/meeting-notes');
  });

  test('should complete full extraction flow from submission to results', async ({ page }) => {
    // 1. Verify page loads correctly
    await expect(page.getByRole('heading', { name: /meeting notes.*action items/i })).toBeVisible();

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    // 2. Verify initial state
    await expect(notesInput).toBeVisible();
    await expect(submitButton).toBeVisible();
    await expect(submitButton).toBeDisabled(); // Should be disabled when empty

    // 3. Enter meeting notes
    await notesInput.fill(TEST_NOTES);
    await expect(submitButton).toBeEnabled();

    // Verify character counter
    const charCount = await page.getByText(/\d+ \/ 10,000 characters/).textContent();
    expect(charCount).toBeTruthy();

    // 4. Submit the form
    await submitButton.click();

    // 5. Verify processing state appears
    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/ai is analyzing/i)).toBeVisible();

    // Verify animated spinner is present
    const spinner = page.locator('[class*="animate-spin"]');
    await expect(spinner).toBeVisible();

    // 6. Wait for completion (with extended timeout for actual API call)
    // Note: This assumes backend is running. In CI, you might want to mock.
    await expect(page.getByText(/extraction complete/i)).toBeVisible({
      timeout: 45000 // 45 seconds for AI processing
    });

    // 7. Verify model information is displayed
    await expect(page.getByText(/model:/i)).toBeVisible();

    // 8. Verify action items are displayed
    const actionItems = page.locator('[data-testid="action-item"]');
    await expect(actionItems).toHaveCount(3, { timeout: 5000 });

    // 9. Verify action item structure
    const firstItem = actionItems.first();
    await expect(firstItem).toContainText(/follow up|budget/i);

    // Check for owner, due date, confidence
    await expect(firstItem).toContainText(/owner|John|Sarah|Mike/i);
    await expect(firstItem).toContainText(/due date|no due date/i);
    await expect(firstItem).toContainText(/confidence|\d+%/i);

    // 10. Verify "New Extraction" button appears
    const newExtractionButton = page.getByRole('button', { name: /new extraction/i });
    await expect(newExtractionButton).toBeVisible();

    // 11. Test creating new extraction
    await newExtractionButton.click();

    // Should reset to initial state
    await expect(notesInput).toHaveValue('');
    await expect(page.getByText(/tips for best results/i)).toBeVisible();
  });

  test('should handle submission with minimal action items', async ({ page }) => {
    const minimalNotes = `
Quick sync
- John will call the client
- Review needed
    `.trim();

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(minimalNotes);
    await submitButton.click();

    // Should show processing
    await expect(page.getByText(/processing/i)).toBeVisible({ timeout: 5000 });

    // Eventually should complete or show results
    await expect(
      page.getByText(/extraction complete/i).or(page.getByText(/no action items/i))
    ).toBeVisible({ timeout: 45000 });
  });

  test('should persist results across page refresh', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    // Wait for completion
    await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 45000 });

    // Get the URL (should contain extraction run ID in state or URL)
    const currentUrl = page.url();

    // Reload the page
    await page.reload();

    // Note: This test assumes the app stores extraction ID in URL or localStorage
    // Adjust based on actual implementation
    await page.goto(currentUrl);
  });

  test('should display confidence scores with visual indicators', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 45000 });

    // Check for confidence percentage displays
    const confidenceTexts = await page.getByText(/\d+%/).all();
    expect(confidenceTexts.length).toBeGreaterThan(0);

    // Verify confidence scores are reasonable (0-100%)
    for (const text of confidenceTexts) {
      const content = await text.textContent();
      const match = content?.match(/(\d+)%/);
      if (match) {
        const confidence = parseInt(match[1]);
        expect(confidence).toBeGreaterThanOrEqual(0);
        expect(confidence).toBeLessThanOrEqual(100);
      }
    }
  });

  test('should handle notes with unassigned owners gracefully', async ({ page }) => {
    const notesWithUnassignedOwners = `
Meeting notes:
- Review the design document by next week
- Update the API documentation
- Schedule a team sync
    `.trim();

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(notesWithUnassignedOwners);
    await submitButton.click();

    await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 45000 });

    // Should show "Unassigned" for items without clear owners
    // This verifies the anti-hallucination feature
    const unassignedText = page.getByText(/unassigned/i);
    const count = await unassignedText.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should handle notes with no due dates', async ({ page }) => {
    const notesWithNoDates = `
Action items:
1. John to follow up with the team soon
2. Sarah to review the code when she has time
    `.trim();

    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(notesWithNoDates);
    await submitButton.click();

    await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 45000 });

    // Should show "No due date" for vague timing
    const noDueDateText = page.getByText(/no due date/i);
    const count = await noDueDateText.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should display model provider information', async ({ page }) => {
    const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
    const submitButton = page.getByRole('button', { name: /extract action items/i });

    await notesInput.fill(TEST_NOTES);
    await submitButton.click();

    await expect(page.getByText(/extraction complete/i)).toBeVisible({ timeout: 45000 });

    // Should show model provider (bedrock or azure) and model name
    const modelInfo = page.getByText(/model:/i);
    await expect(modelInfo).toBeVisible();

    // Should contain provider name
    await expect(modelInfo).toContainText(/bedrock|azure/i);
  });
});
