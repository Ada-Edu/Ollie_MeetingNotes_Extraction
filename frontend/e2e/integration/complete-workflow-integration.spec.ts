import { test, expect } from '@playwright/test';
import { Page } from '@playwright/test';
import { createClient } from '@supabase/supabase-js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
const SUPABASE_URL = process.env.VITE_SUPABASE_URL || 'http://localhost:54321';
const SUPABASE_ANON_KEY = process.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0';

// Initialize Supabase client for database verification
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

test.describe('Complete Workflow Integration Tests - Real Backend', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto(FRONTEND_URL);
  });

  test.afterEach(async () => {
    await page.close();
  });

  test('Real workflow integration - frontend to backend to database', async () => {
    // Navigate to extraction page
    await page.goto(`${FRONTEND_URL}/extraction`);

    // Fill in meeting notes with real data
    const meetingNotes = `
      Team meeting on January 15, 2026.
      Action: John needs to complete the project proposal by January 20, 2026.
      Action: Sarah will review the design documents by January 18, 2026.
    `;

    // NO MOCKING - Submit to real backend
    await page.fill('textarea[name="meetingNotes"]', meetingNotes);
    await page.click('button[type="submit"]');

    // Wait for REAL workflow to complete (actual AI processing)
    await expect(page.locator('text=Processing')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Extraction Complete')).toBeVisible({ timeout: 60000 });

    // Verify UI shows extracted action items
    await expect(page.locator('text=John')).toBeVisible();
    await expect(page.locator('text=Sarah')).toBeVisible();

    // CRITICAL: Verify in ACTUAL database that workflow completed
    const { data: extractionRuns, error } = await supabase
      .from('extraction_runs')
      .select('*, action_items(*)')
      .eq('status', 'completed')
      .order('created_at', { ascending: false })
      .limit(1);

    expect(error).toBeNull();
    expect(extractionRuns).toBeTruthy();
    expect(extractionRuns!.length).toBeGreaterThan(0);

    const latestRun = extractionRuns![0];
    expect(latestRun.status).toBe('completed');
    expect(latestRun.action_items).toBeTruthy();
    expect(latestRun.action_items.length).toBeGreaterThan(0);

    // Verify action items actually saved to database
    const actionItems = latestRun.action_items;
    expect(actionItems.some((item: any) => item.description.toLowerCase().includes('proposal'))).toBeTruthy();
    expect(actionItems.some((item: any) => item.owner && item.owner.toLowerCase().includes('john'))).toBeTruthy();
  });

  test('Database persistence - verify extraction run saved correctly', async () => {
    await page.goto(`${FRONTEND_URL}/extraction`);

    const meetingNotes = `
      Sprint planning meeting - July 7, 2026.
      Action: Mike to implement authentication by July 15.
      Action: Lisa to write API documentation by July 20.
      Action: Tom to set up CI/CD pipeline by July 10.
    `;

    // Submit without mocking
    await page.fill('textarea[name="meetingNotes"]', meetingNotes);
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Extraction Complete')).toBeVisible({ timeout: 60000 });

    // Query database to verify meeting notes were saved
    const { data: meetingNotesRecords, error: notesError } = await supabase
      .from('meeting_notes')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(1);

    expect(notesError).toBeNull();
    expect(meetingNotesRecords).toBeTruthy();
    expect(meetingNotesRecords!.length).toBe(1);
    expect(meetingNotesRecords![0].notes_text).toContain('Sprint planning meeting');

    // Query database to verify extraction run completed
    const { data: extractionRuns, error: runsError } = await supabase
      .from('extraction_runs')
      .select('*, action_items(*)')
      .eq('meeting_notes_id', meetingNotesRecords![0].id);

    expect(runsError).toBeNull();
    expect(extractionRuns).toBeTruthy();
    expect(extractionRuns!.length).toBeGreaterThan(0);
    expect(extractionRuns![0].status).toBe('completed');
    expect(extractionRuns![0].workflow_id).toBeTruthy();

    // Verify action items persisted
    expect(extractionRuns![0].action_items.length).toBeGreaterThan(0);
  });

  test('Multiple sequential workflow runs - no interference', async () => {
    await page.goto(`${FRONTEND_URL}/extraction`);

    // First extraction
    await page.fill('textarea[name="meetingNotes"]', 'First meeting: Action: Alice to review code by Friday');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Extraction Complete')).toBeVisible({ timeout: 60000 });

    const { data: firstRun } = await supabase
      .from('extraction_runs')
      .select('id, status')
      .eq('status', 'completed')
      .order('created_at', { ascending: false })
      .limit(1)
      .single();

    expect(firstRun).toBeTruthy();
    expect(firstRun!.status).toBe('completed');

    // Second extraction - verify independent execution
    await page.reload();
    await page.fill('textarea[name="meetingNotes"]', 'Second meeting: Action: Bob to deploy app by Monday');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Extraction Complete')).toBeVisible({ timeout: 60000 });

    const { data: bothRuns } = await supabase
      .from('extraction_runs')
      .select('id, status')
      .eq('status', 'completed')
      .order('created_at', { ascending: false })
      .limit(2);

    expect(bothRuns).toBeTruthy();
    expect(bothRuns!.length).toBe(2);
    expect(bothRuns![0].id).not.toBe(bothRuns![1].id);
  });

  test('Workflow with no action items - database reflects empty result', async () => {
    await page.goto(`${FRONTEND_URL}/extraction`);

    const noActionNotes = `
      Team sync - July 7, 2026.
      Discussed project status.
      Everything is on track.
      No specific actions needed.
    `;

    await page.fill('textarea[name="meetingNotes"]', noActionNotes);
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Extraction Complete')).toBeVisible({ timeout: 60000 });

    // Verify extraction run completed but has no action items
    const { data: extractionRuns } = await supabase
      .from('extraction_runs')
      .select('*, action_items(*)')
      .eq('status', 'completed')
      .order('created_at', { ascending: false })
      .limit(1);

    expect(extractionRuns).toBeTruthy();
    expect(extractionRuns![0].status).toBe('completed');
    expect(extractionRuns![0].action_items.length).toBe(0);
  });

  test('Action items with missing fields - database allows nulls', async () => {
    await page.goto(`${FRONTEND_URL}/extraction`);

    const partialActionNotes = `
      Quick meeting notes.
      - Review the design document (no owner mentioned)
      - John will follow up (no due date given)
    `;

    await page.fill('textarea[name="meetingNotes"]', partialActionNotes);
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Extraction Complete')).toBeVisible({ timeout: 60000 });

    const { data: extractionRuns } = await supabase
      .from('extraction_runs')
      .select('*, action_items(*)')
      .eq('status', 'completed')
      .order('created_at', { ascending: false })
      .limit(1);

    expect(extractionRuns).toBeTruthy();
    const actionItems = extractionRuns![0].action_items;
    expect(actionItems.length).toBeGreaterThan(0);

    // Verify some items may have null owner or null due_date
    const hasNullOwner = actionItems.some((item: any) => item.owner === null);
    const hasNullDueDate = actionItems.some((item: any) => item.due_date === null);

    expect(hasNullOwner || hasNullDueDate).toBeTruthy();
  });
});
