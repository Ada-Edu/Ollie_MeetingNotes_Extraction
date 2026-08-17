import { Page, expect } from '@playwright/test';

/**
 * Test data and helper functions for E2E tests
 */

// Sample Meeting Notes Test Data
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
  `.trim(),

  edgeCases: `
Special Characters & Formatting Test

Attendees: John O'Brien, Sarah-Jane Smith, Mike (Chen), Dr. Lisa Wang

Action Items:
1. John O'Brien to review the Q&A document by 7/20/2026
2. Sarah-Jane will update "Project Alpha" & "Project Beta" files by July 25
3. Dr. Lisa Wang needs to schedule 1:1 meetings @ 2:00 PM on 07/22/2026
4. Mike (Chen) to fix issues #123, #456, and #789 by end-of-day Friday
  `.trim()
};

// Expected Results for Test Data
export const EXPECTED_RESULTS = {
  complete: {
    actionItemCount: 3,
    hasOwners: true,
    hasDueDates: true,
    hasConfidenceScores: true,
    owners: ['John', 'Mike', 'Sarah'],
    dueDates: ['July 15', 'next week', 'ASAP']
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
  },
  noDueDates: {
    actionItemCount: 2,
    hasOwners: true,
    hasDueDates: false
  },
  noActionItems: {
    actionItemCount: 0,
    shouldShowWarning: true
  },
  urgentItems: {
    actionItemCount: 3,
    hasUrgentItems: true,
    urgentKeywords: ['IMMEDIATELY', 'within the next hour', 'end of day TODAY']
  },
  longText: {
    actionItemCount: 10,
    owners: ['John', 'Mike', 'Sarah', 'Alice', 'Bob', 'Everyone'],
    hasDueDates: true
  }
};

// Wait Functions
export async function waitForElement(page: Page, selector: string, timeout = 30000) {
  await page.waitForSelector(selector, { timeout, state: 'visible' });
}

export async function waitForText(page: Page, text: string | RegExp, timeout = 30000) {
  await page.waitForSelector(`text=${text}`, { timeout });
}

export async function waitForNavigation(page: Page, timeout = 5000) {
  await page.waitForLoadState('networkidle', { timeout });
}

export async function waitForApiResponse(page: Page, urlPattern: string | RegExp, timeout = 10000) {
  return await page.waitForResponse(
    (response) => {
      const url = response.url();
      if (typeof urlPattern === 'string') {
        return url.includes(urlPattern);
      }
      return urlPattern.test(url);
    },
    { timeout }
  );
}

export async function waitForTextContent(page: Page, selector: string, expectedText: string, timeout = 5000) {
  await page.waitForFunction(
    ({ selector, expectedText }) => {
      const element = document.querySelector(selector);
      return element?.textContent?.includes(expectedText);
    },
    { selector, expectedText },
    { timeout }
  );
}

export async function waitForCondition(condition: () => boolean | Promise<boolean>, timeout = 5000, interval = 100) {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    if (await condition()) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, interval));
  }
  throw new Error(`Condition not met within ${timeout}ms`);
}

// Form Helpers
export async function fillForm(page: Page, formData: Record<string, string>) {
  for (const [selector, value] of Object.entries(formData)) {
    await page.fill(selector, value);
  }
}

export async function fillAndSubmitForm(page: Page, notesText: string) {
  const notesInput = page.getByPlaceholder(/paste your meeting notes/i);
  const submitButton = page.getByRole('button', { name: /extract action items/i });

  await notesInput.fill(notesText);
  await submitButton.click();
}

export async function submitForm(page: Page, submitButtonSelector: string) {
  await page.click(submitButtonSelector);
}

export async function clearForm(page: Page, selectors: string[]) {
  for (const selector of selectors) {
    await page.fill(selector, '');
  }
}

export async function selectDropdownOption(page: Page, selector: string, value: string) {
  await page.selectOption(selector, value);
}

export async function uploadFile(page: Page, fileInputSelector: string, filePath: string) {
  await page.setInputFiles(fileInputSelector, filePath);
}

// Workflow-specific wait functions
export async function waitForProcessing(page: Page, timeout = 5000) {
  await page.getByText(/processing/i).waitFor({ state: 'visible', timeout });
}

export async function waitForCompletion(page: Page, timeout = 45000) {
  await page.getByText(/extraction complete/i).waitFor({ state: 'visible', timeout });
}

export async function waitForFailure(page: Page, timeout = 10000) {
  await page.getByText(/extraction failed|error/i).waitFor({ state: 'visible', timeout });
}

// Action Item Verification
export async function verifyActionItemCount(page: Page, expectedCount: number) {
  const actionItems = await page.locator('[data-testid="action-item"]').count();
  expect(actionItems).toBe(expectedCount);
}

export async function verifyActionItemExists(page: Page, text: string) {
  const actionItem = page.locator('[data-testid="action-item"]', { hasText: text });
  await expect(actionItem).toBeVisible();
}

export async function verifyActionItemOwner(page: Page, itemIndex: number, expectedOwner: string) {
  const ownerElement = page.locator('[data-testid="action-item"]').nth(itemIndex).locator('[data-testid="owner"]');
  await expect(ownerElement).toHaveText(expectedOwner);
}

export async function verifyActionItemDueDate(page: Page, itemIndex: number, expectedDate: string) {
  const dueDateElement = page.locator('[data-testid="action-item"]').nth(itemIndex).locator('[data-testid="due-date"]');
  await expect(dueDateElement).toContainText(expectedDate);
}

export async function verifyActionItemStatus(page: Page, itemIndex: number, expectedStatus: string) {
  const statusElement = page.locator('[data-testid="action-item"]').nth(itemIndex).locator('[data-testid="status"]');
  await expect(statusElement).toHaveText(expectedStatus);
}

export async function getActionItemsCount(page: Page): Promise<number> {
  const items = page.locator('[data-testid="action-item"]');
  return await items.count();
}

export async function getAllActionItems(page: Page) {
  const actionItems = await page.locator('[data-testid="action-item"]').all();
  return Promise.all(
    actionItems.map(async (item) => ({
      text: await item.textContent(),
      owner: await item.locator('[data-testid="owner"]').textContent().catch(() => null),
      dueDate: await item.locator('[data-testid="due-date"]').textContent().catch(() => null),
      status: await item.locator('[data-testid="status"]').textContent().catch(() => null),
    }))
  );
}

export async function verifyActionItemStructure(page: Page, index = 0) {
  const items = page.locator('[data-testid="action-item"]');
  const item = items.nth(index);

  await item.waitFor({ state: 'visible' });

  const hasDescription = await item.getByText(/.{10,}/).count() > 0;
  const hasOwner = await item.getByText(/owner|unassigned/i).count() > 0;
  const hasDueDate = await item.getByText(/due date|no due date/i).count() > 0;
  const hasConfidence = await item.getByText(/confidence|\d+%/i).count() > 0;

  return {
    hasDescription,
    hasOwner,
    hasDueDate,
    hasConfidence
  };
}

// API Mocking
export async function mockApiSuccess(page: Page, endpoint: string, responseData: any) {
  await page.route(endpoint, (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(responseData),
    });
  });
}

export async function mockApiError(page: Page, endpoint: string, statusCode = 500, errorMessage = 'Internal Server Error') {
  await page.route(endpoint, (route) => {
    route.fulfill({
      status: statusCode,
      contentType: 'application/json',
      body: JSON.stringify({ error: errorMessage }),
    });
  });
}

export async function mockApiDelay(page: Page, endpoint: string, delayMs: number, responseData?: any) {
  await page.route(endpoint, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(responseData || { success: true }),
    });
  });
}

export async function mockApiWithValidation(page: Page, endpoint: string, validator: (request: any) => boolean, responseData: any) {
  await page.route(endpoint, async (route) => {
    const request = route.request();
    const postData = request.postDataJSON();

    if (validator(postData)) {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(responseData),
      });
    } else {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Invalid request' }),
      });
    }
  });
}

export async function mockWorkflowTrigger(
  page: Page,
  response: { success: boolean; workflow_id?: string; error?: string }
) {
  await page.route('http://localhost:8000/trigger-workflow', (route) => {
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

export async function clearMocks(page: Page) {
  await page.unroute('**/*');
}

export async function clearApiMocks(page: Page) {
  await page.unroute('**/*');
}

// Screenshot Capture
export async function captureScreenshot(page: Page, name: string, fullPage = false) {
  await page.screenshot({
    path: `./e2e/screenshots/${name}-${Date.now()}.png`,
    fullPage,
  });
}

export async function captureElementScreenshot(page: Page, selector: string, name: string) {
  const element = page.locator(selector);
  await element.screenshot({
    path: `./e2e/screenshots/${name}-${Date.now()}.png`,
  });
}

export async function captureScreenshotOnFailure(page: Page, testName: string) {
  await captureScreenshot(page, `failure-${testName}`, true);
}

export async function takeDebugScreenshot(page: Page, name: string) {
  await page.screenshot({ path: `e2e/screenshots/${name}.png`, fullPage: true });
}

// Console Logging
export function setupConsoleLogging(page: Page) {
  const logs: Array<{ type: string; message: string }> = [];

  page.on('console', (msg) => {
    logs.push({
      type: msg.type(),
      message: msg.text(),
    });
  });

  return {
    getLogs: () => logs,
    getErrors: () => logs.filter((log) => log.type === 'error'),
    getWarnings: () => logs.filter((log) => log.type === 'warning'),
    clear: () => logs.splice(0, logs.length),
  };
}

export function setupConsoleLogger(page: Page) {
  page.on('console', (msg) => {
    console.log(`[Browser Console] ${msg.type()}: ${msg.text()}`);
  });
}

export async function waitForConsoleMessage(page: Page, expectedMessage: string | RegExp, timeout = 5000) {
  return new Promise<void>((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`Console message not found within ${timeout}ms`));
    }, timeout);

    page.on('console', (msg) => {
      const text = msg.text();
      const matches = typeof expectedMessage === 'string'
        ? text.includes(expectedMessage)
        : expectedMessage.test(text);

      if (matches) {
        clearTimeout(timeoutId);
        resolve();
      }
    });
  });
}

// Network Error Handling
export async function simulateNetworkOffline(page: Page) {
  await page.context().setOffline(true);
}

export async function simulateNetworkOnline(page: Page) {
  await page.context().setOffline(false);
}

export async function simulateSlowNetwork(page: Page) {
  await page.route('**/*', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    route.continue();
  });
}

export async function interceptAndFailRequest(page: Page, urlPattern: string | RegExp, errorCode = 'failed') {
  await page.route(urlPattern, (route) => {
    route.abort(errorCode);
  });
}

export async function monitorNetworkRequests(page: Page) {
  const requests: Array<{ url: string; method: string; status?: number }> = [];

  page.on('request', (request) => {
    requests.push({
      url: request.url(),
      method: request.method(),
    });
  });

  page.on('response', (response) => {
    const request = requests.find((req) => req.url === response.url());
    if (request) {
      request.status = response.status();
    }
  });

  return {
    getRequests: () => requests,
    getFailedRequests: () => requests.filter((req) => req.status && req.status >= 400),
    clear: () => requests.splice(0, requests.length),
  };
}

export function setupNetworkErrorHandler(page: Page) {
  page.on('requestfailed', (request) => {
    console.error(`[Network Error] ${request.url()}: ${request.failure()?.errorText}`);
  });
}

// Utility Functions
export async function retry<T>(
  fn: () => Promise<T>,
  maxAttempts = 3,
  delayMs = 1000
): Promise<T> {
  let lastError: Error;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      if (attempt < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    }
  }

  throw lastError!;
}

export function generateRandomString(length = 10) {
  return Math.random().toString(36).substring(2, 2 + length);
}

export function generateTestEmail() {
  return `test-${generateRandomString()}@example.com`;
}

export async function scrollToElement(page: Page, selector: string) {
  await page.locator(selector).scrollIntoViewIfNeeded();
}

export async function hoverElement(page: Page, selector: string) {
  await page.hover(selector);
}

export async function clickWithRetry(page: Page, selector: string, maxAttempts = 3) {
  await retry(async () => {
    await page.click(selector);
  }, maxAttempts);
}
