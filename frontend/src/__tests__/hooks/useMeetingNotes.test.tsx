import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCreateMeetingNote, useExtractionRun, useExtractionRuns } from '@/lib/hooks/useMeetingNotes';
import { supabase } from '@/lib/supabase';
import { ReactNode } from 'react';

// Mock supabase client
vi.mock('@/lib/supabase', () => ({
  supabase: {
    from: vi.fn()
  }
}));

// Mock fetch for workflow API
global.fetch = vi.fn();

describe('useMeetingNotes Hooks', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => JSX.Element;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });
    wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  describe('useCreateMeetingNote', () => {
    it('should create meeting note and trigger workflow successfully', async () => {
      const mockNote = {
        id: 'note-123',
        notes_text: 'Test meeting notes',
        created_at: '2026-07-07T10:00:00Z'
      };
      const mockRun = {
        id: 'run-123',
        meeting_notes_id: 'note-123',
        workflow_id: 'extract-note-123',
        status: 'processing'
      };

      // Mock supabase chain for meeting_notes
      const selectMock = vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: mockNote, error: null })
      });
      const insertNotesMock = vi.fn().mockReturnValue({
        select: selectMock
      });

      // Mock supabase chain for extraction_runs
      const selectRunMock = vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: mockRun, error: null })
      });
      const insertRunsMock = vi.fn().mockReturnValue({
        select: selectRunMock
      });

      (supabase.from as any).mockImplementation((table: string) => {
        if (table === 'meeting_notes') {
          return { insert: insertNotesMock };
        }
        if (table === 'extraction_runs') {
          return { insert: insertRunsMock };
        }
      });

      // Mock fetch for workflow trigger
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, workflow_id: 'extract-note-123' })
      });

      const { result } = renderHook(() => useCreateMeetingNote(), { wrapper });

      result.current.mutate('Test meeting notes');

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(insertNotesMock).toHaveBeenCalledWith({ notes_text: 'Test meeting notes' });
      expect(insertRunsMock).toHaveBeenCalledWith({
        meeting_notes_id: 'note-123',
        workflow_id: 'extract-note-123',
        status: 'processing'
      });
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/trigger-workflow',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
      );
    });

    it('should handle database error when creating meeting note', async () => {
      const insertMock = vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({ data: null, error: new Error('Database error') })
        })
      });

      (supabase.from as any).mockReturnValue({ insert: insertMock });

      const { result } = renderHook(() => useCreateMeetingNote(), { wrapper });

      result.current.mutate('Test meeting notes');

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeTruthy();
    });

    it('should handle workflow trigger failure and update extraction run', async () => {
      const mockNote = { id: 'note-123', notes_text: 'Test', created_at: '2026-07-07T10:00:00Z' };
      const mockRun = { id: 'run-123', meeting_notes_id: 'note-123', workflow_id: 'extract-note-123', status: 'processing' };

      const updateMock = vi.fn().mockReturnValue({
        eq: vi.fn().mockResolvedValue({ data: null, error: null })
      });
      const selectMock = vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: mockNote, error: null })
      });
      const selectRunMock = vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: mockRun, error: null })
      });

      (supabase.from as any).mockImplementation((table: string) => {
        if (table === 'meeting_notes') {
          return { insert: vi.fn().mockReturnValue({ select: selectMock }) };
        }
        if (table === 'extraction_runs') {
          return {
            insert: vi.fn().mockReturnValue({ select: selectRunMock }),
            update: updateMock
          };
        }
      });

      (global.fetch as any).mockResolvedValue({
        ok: false,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Workflow service unavailable' })
      });

      const { result } = renderHook(() => useCreateMeetingNote(), { wrapper });

      result.current.mutate('Test meeting notes');

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(updateMock).toHaveBeenCalled();
    });

    it('should invalidate queries on success', async () => {
      const mockNote = { id: 'note-123', notes_text: 'Test', created_at: '2026-07-07T10:00:00Z' };
      const mockRun = { id: 'run-123', meeting_notes_id: 'note-123', workflow_id: 'extract-note-123', status: 'processing' };

      const selectMock = vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: mockNote, error: null })
      });
      const selectRunMock = vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: mockRun, error: null })
      });

      (supabase.from as any).mockImplementation((table: string) => {
        if (table === 'meeting_notes') {
          return { insert: vi.fn().mockReturnValue({ select: selectMock }) };
        }
        if (table === 'extraction_runs') {
          return { insert: vi.fn().mockReturnValue({ select: selectRunMock }) };
        }
      });

      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ success: true })
      });

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateMeetingNote(), { wrapper });

      result.current.mutate('Test meeting notes');

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['extraction-runs'] });
    });
  });

  describe('useExtractionRun', () => {
    it('should fetch extraction run with action items', async () => {
      const mockData = {
        id: 'run-123',
        status: 'completed',
        model_provider: 'azure',
        model_name: 'gpt-4',
        action_items: [
          { id: '1', description: 'Task 1', owner: 'John', due_date: '2026-07-15', confidence: 0.95, created_at: '2026-07-07T10:00:00Z' }
        ]
      };

      const selectMock = vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({ data: mockData, error: null })
        })
      });

      (supabase.from as any).mockReturnValue({ select: selectMock });

      const { result } = renderHook(() => useExtractionRun('run-123'), { wrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockData);
      expect(selectMock).toHaveBeenCalledWith(expect.stringContaining('action_items'));
    });

    it('should not fetch when extractionRunId is null', () => {
      const selectMock = vi.fn();
      (supabase.from as any).mockReturnValue({ select: selectMock });

      const { result } = renderHook(() => useExtractionRun(null), { wrapper });

      expect(result.current.data).toBeUndefined();
      expect(result.current.fetchStatus).toBe('idle');
      expect(selectMock).not.toHaveBeenCalled();
    });

    it('should poll when status is processing', async () => {
      const mockData = {
        id: 'run-123',
        status: 'processing'
      };

      const selectMock = vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({ data: mockData, error: null })
        })
      });

      (supabase.from as any).mockReturnValue({ select: selectMock });

      const { result } = renderHook(() => useExtractionRun('run-123'), { wrapper });

      await waitFor(() => {
        expect(result.current.data?.status).toBe('processing');
      });

      // Polling should be enabled for processing status
      expect(result.current.data?.status).toBe('processing');
    });

    it('should handle fetch error', async () => {
      const selectMock = vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({ data: null, error: new Error('Fetch error') })
        })
      });

      (supabase.from as any).mockReturnValue({ select: selectMock });

      const { result } = renderHook(() => useExtractionRun('run-123'), { wrapper });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });

  describe('useExtractionRuns', () => {
    it('should fetch list of extraction runs', async () => {
      const mockData = [
        {
          id: 'run-1',
          status: 'completed',
          created_at: '2026-07-07T10:00:00Z',
          meeting_notes: { notes_text: 'Notes 1' }
        },
        {
          id: 'run-2',
          status: 'processing',
          created_at: '2026-07-07T09:00:00Z',
          meeting_notes: { notes_text: 'Notes 2' }
        }
      ];

      const limitMock = vi.fn().mockResolvedValue({ data: mockData, error: null });
      const orderMock = vi.fn().mockReturnValue({ limit: limitMock });
      const selectMock = vi.fn().mockReturnValue({ order: orderMock });

      (supabase.from as any).mockReturnValue({ select: selectMock });

      const { result } = renderHook(() => useExtractionRuns(), { wrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockData);
      expect(orderMock).toHaveBeenCalledWith('created_at', { ascending: false });
      expect(limitMock).toHaveBeenCalledWith(10);
    });

    it('should handle empty results', async () => {
      const limitMock = vi.fn().mockResolvedValue({ data: [], error: null });
      const orderMock = vi.fn().mockReturnValue({ limit: limitMock });
      const selectMock = vi.fn().mockReturnValue({ order: orderMock });

      (supabase.from as any).mockReturnValue({ select: selectMock });

      const { result } = renderHook(() => useExtractionRuns(), { wrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual([]);
    });

    it('should handle fetch error', async () => {
      const limitMock = vi.fn().mockResolvedValue({ data: null, error: new Error('Fetch error') });
      const orderMock = vi.fn().mockReturnValue({ limit: limitMock });
      const selectMock = vi.fn().mockReturnValue({ order: orderMock });

      (supabase.from as any).mockReturnValue({ select: selectMock });

      const { result } = renderHook(() => useExtractionRuns(), { wrapper });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });
});
