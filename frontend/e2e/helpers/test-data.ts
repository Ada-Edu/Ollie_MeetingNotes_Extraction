/**
 * Test data and helper functions for E2E tests
 */

export const TEST_MEETING_NOTES = {
  complete: `
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
  `.trim(),

  minimal: `
Quick sync
- John will call the client
- Review needed
  `.trim(),

  unassignedOwners: `
Meeting notes:
- Review the design document by next week
- Update the API documentation
- Schedule a team sync
  `.trim(),

  noDueDates: `
Action items:
1. John to follow up with the team soon
2. Sarah to review the code when she has time
  `.trim(),

  tooShort: 'Short',

  longText: `
Quarterly Planning Meeting - Q3 2026
Date: July 7, 2026
Duration: 2 hours
Location: Conference Room A / Zoom

Attendees:
- Sarah Johnson (Product Manager)
- John Smith (Lead Developer)
- Mike Chen (Solutions Architect)
- Alice Brown (UX Designer)
- Bob Wilson (QA Lead)

Agenda:
1. Review Q2 Accomplishments
2. Q3 Goals and Priorities
3. Resource Allocation
4. Risk Assessment
5. Action Items

Discussion Summary:

Q2 Review:
The team successfully delivered the user authentication system, which is now live and serving 10,000+ users. Performance has been excellent with 99.9% uptime. The database pooling issue that caused slowdowns in June has been resolved. Customer feedback has been overwhelmingly positive.

Q3 Goals:
- Complete API documentation rewrite
- Implement payment integration with Stripe
- Launch mobile app beta
- Improve system monitoring and alerting
- Expand team by hiring 2 developers

Resource Allocation:
Budget approved for additional cloud infrastructure. Need to finalize vendor contracts by end of July. Training budget allocated for team certifications.

Risk Assessment:
Main risks identified:
1. Timeline pressure for mobile app launch
2. Dependency on third-party payment provider
3. Potential scaling challenges during growth phase

Mitigation strategies discussed for each risk factor.

Action Items:
1. John to follow up with Sarah on Q4 budget planning by July 15, 2026
2. Mike to review the comprehensive architectural design document for the mobile app by July 20, 2026
3. Sarah to schedule a follow-up meeting with the design team ASAP to finalize UI mockups
4. Alice to complete user research interviews by end of month
5. Bob to set up automated testing infrastructure by August 1, 2026
6. John to investigate migration path for legacy API clients
7. Sarah to present Q3 roadmap to executive team next Friday
8. Mike to evaluate serverless architecture options for microservices
9. Everyone to complete security training by July 31, 2026
10. John to mentor new hires during their first month

Next Meeting: August 7, 2026
  `.trim(),

  noActionItems: `
Team sync - July 7, 2026

We discussed the project status.
Everyone is aligned on the timeline.
No specific action items this week.
Everything is on track.
  `.trim(),

  multipleOwners: `
Project kickoff meeting

Action items:
1. Sarah and John to review requirements together by Friday
2. Mike, Alice, and Bob to set up development environment
3. The entire team to attend training session next Monday
  `.trim(),

  urgentItems: `
Emergency meeting - Production incident

URGENT action items:
1. John to fix the critical bug IMMEDIATELY
2. Sarah to notify all customers within the next hour
3. Mike to investigate root cause by end of day TODAY
  `.trim(),

  vagueDates: `
Team discussion

Action items:
1. John to review the code sometime next week
2. Sarah to update docs in the near future
3. Mike to schedule a meeting soon
4. Alice to provide feedback eventually
  `.trim()
};

export const EXPECTED_RESULTS = {
  complete: {
    actionItemCount: 3,
    hasOwners: true,
    hasDueDates: true,
    hasConfidenceScores: true
  },
  minimal: {
    actionItemCount: 1,
    hasOwners: true,
    hasDueDates: false,
    hasConfidenceScores: true
  },
  unassignedOwners: {
    actionItemCount: 3,
    hasUnassigned: true,
    hasDueDates: false,
    hasConfidenceScores: true
  }
};

/**
 * Wait for element with custom timeout
 */
export async function waitForElement(
  page: any,
  selector: string,
  timeout: number = 30000
) {
  return await page.waitForSelector(selector, { timeout });
}

/**
 * Wait for text content with custom timeout
 */
export async function waitForText(
  page: any,
  text: string | RegExp,
  timeout: number = 30000
) {
  return await page.waitForSelector(`text=${text}`, { timeout });
}

/**
 * Fill form and submit
 */
export async function fillAndSubmitForm(
  page: any,
  notesText: string
) {
  const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
  const submitButton = page.getByRole('button', { name: /extract action items/i });

  await notesInput.fill(notesText);
  await submitButton.click();
}

/**
 * Wait for processing to start
 */
export async function waitForProcessing(page: any, timeout: number = 5000) {
  await page.getByText(/processing/i).waitFor({ state: 'visible', timeout });
}

/**
 * Wait for completion
 */
export async function waitForCompletion(page: any, timeout: number = 45000) {
  await page.getByText(/extraction complete/i).waitFor({ state: 'visible', timeout });
}

/**
 * Wait for failure
 */
export async function waitForFailure(page: any, timeout: number = 10000) {
  await page.getByText(/extraction failed|error/i).waitFor({ state: 'visible', timeout });
}

/**
 * Get action items count
 */
export async function getActionItemsCount(page: any): Promise<number> {
  const items = page.locator('[data-testid="action-item"]');
  return await items.count();
}

/**
 * Verify action item structure
 */
export async function verifyActionItemStructure(page: any, index: number = 0) {
  const items = page.locator('[data-testid="action-item"]');
  const item = items.nth(index);

  await item.waitFor({ state: 'visible' });

  // Check for description
  const hasDescription = await item.getByText(/.{10,}/).count() > 0;

  // Check for owner or "Unassigned"
  const hasOwner = await item.getByText(/owner|unassigned/i).count() > 0;

  // Check for due date or "No due date"
  const hasDueDate = await item.getByText(/due date|no due date/i).count() > 0;

  // Check for confidence
  const hasConfidence = await item.getByText(/confidence|\d+%/i).count() > 0;

  return {
    hasDescription,
    hasOwner,
    hasDueDate,
    hasConfidence
  };
}

/**
 * Mock API response
 */
export async function mockWorkflowTrigger(
  page: any,
  response: { success: boolean; workflow_id?: string; error?: string }
) {
  await page.route('http://localhost:8000/trigger-workflow', route => {
    if (response.success) {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          workflow_id: response.workflow_id || 'test-workflow-id',
          message: 'Workflow triggered successfully'
        })
      });
    } else {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: response.error || 'Internal server error'
        })
      });
    }
  });
}

/**
 * Clear all mocks
 */
export async function clearMocks(page: any) {
  await page.unroute('**/*');
}

/**
 * Take screenshot for debugging
 */
export async function takeDebugScreenshot(
  page: any,
  name: string
) {
  await page.screenshot({ path: `e2e/screenshots/${name}.png`, fullPage: true });
}

/**
 * Log page console messages
 */
export function setupConsoleLogger(page: any) {
  page.on('console', (msg: any) => {
    console.log(`[Browser Console] ${msg.type()}: ${msg.text()}`);
  });
}

/**
 * Check for network errors
 */
export function setupNetworkErrorHandler(page: any) {
  page.on('requestfailed', (request: any) => {
    console.error(`[Network Error] ${request.url()}: ${request.failure()?.errorText}`);
  });
}
