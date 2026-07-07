import { http, HttpResponse } from 'msw';

const SUPABASE_URL = 'http://localhost:54321';
const API_URL = 'http://localhost:8000';

export const handlers = [
  // Supabase meeting_notes endpoints
  http.post(`${SUPABASE_URL}/rest/v1/meeting_notes`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: 'test-note-id-123',
      notes_text: body.notes_text,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
  }),

  http.get(`${SUPABASE_URL}/rest/v1/meeting_notes`, () => {
    return HttpResponse.json([
      {
        id: 'test-note-id-1',
        notes_text: 'Test meeting notes 1',
        created_at: '2026-07-07T10:00:00Z',
        updated_at: '2026-07-07T10:00:00Z'
      },
      {
        id: 'test-note-id-2',
        notes_text: 'Test meeting notes 2',
        created_at: '2026-07-06T10:00:00Z',
        updated_at: '2026-07-06T10:00:00Z'
      }
    ]);
  }),

  // Supabase extraction_runs endpoints
  http.post(`${SUPABASE_URL}/rest/v1/extraction_runs`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: 'test-run-id-123',
      meeting_notes_id: body.meeting_notes_id,
      status: 'processing',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
  }),

  http.get(`${SUPABASE_URL}/rest/v1/extraction_runs`, ({ request }) => {
    const url = new URL(request.url);
    const meetingNotesId = url.searchParams.get('meeting_notes_id');

    return HttpResponse.json([
      {
        id: 'test-run-id-1',
        meeting_notes_id: meetingNotesId || 'test-note-id-1',
        status: 'completed',
        created_at: '2026-07-07T10:01:00Z',
        updated_at: '2026-07-07T10:02:00Z'
      }
    ]);
  }),

  // Supabase action_items endpoints
  http.get(`${SUPABASE_URL}/rest/v1/action_items`, ({ request }) => {
    const url = new URL(request.url);
    const extractionRunId = url.searchParams.get('extraction_run_id');

    return HttpResponse.json([
      {
        id: 'test-action-1',
        extraction_run_id: extractionRunId || 'test-run-id-1',
        description: 'Follow up with Sarah about project timeline',
        owner: 'John',
        due_date: '2026-07-15',
        confidence: 0.95,
        status: 'pending',
        created_at: '2026-07-07T10:02:00Z',
        updated_at: '2026-07-07T10:02:00Z'
      },
      {
        id: 'test-action-2',
        extraction_run_id: extractionRunId || 'test-run-id-1',
        description: 'Review design document',
        owner: 'Mike',
        due_date: '2026-07-10',
        confidence: 0.87,
        status: 'pending',
        created_at: '2026-07-07T10:02:00Z',
        updated_at: '2026-07-07T10:02:00Z'
      }
    ]);
  }),

  // Supabase entities endpoints
  http.get(`${SUPABASE_URL}/rest/v1/entities`, () => {
    return HttpResponse.json([
      {
        id: 'entity-1',
        name: 'John Doe',
        type: 'person',
        created_at: '2026-07-07T10:00:00Z'
      },
      {
        id: 'entity-2',
        name: 'Project Alpha',
        type: 'project',
        created_at: '2026-07-07T10:00:00Z'
      }
    ]);
  }),

  // API workflow trigger endpoint
  http.post(`${API_URL}/trigger-workflow`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      success: true,
      workflow_id: `workflow-${Date.now()}`,
      meeting_notes_id: body.meeting_notes_id
    });
  }),

  // API health check
  http.get(`${API_URL}/health`, () => {
    return HttpResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString()
    });
  })
];
