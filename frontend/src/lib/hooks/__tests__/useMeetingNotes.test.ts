import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCreateMeetingNote, useExtractionRun, useExtractionRuns } from '../useMeetingNotes';
import { supabase } from '../../supabase';
import type { ReactNode } from 'react';
import { createElement } from 'react';

// Mock supabase
vi.mock('../../supabase', () => ({
  supabase: {
    from: vi.fn()
  }
}));

// Mock fetch
global.fetch = vi.fn() as any;

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
};

describe('useMeetingNotes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn() as any;
  });

  describe('useCreateMeetingNote', () => {
    it('should successfully create meeting note and trigger workflow', async () => {
      const mockMeetingNote = {
        id: 'test-note-id',
        notes_text: 'Test notes',
        created_at: '2026-07-07T10:00:00Z'
      };

      const mockExtractionRun = {
        id: 'test-run-id',
        meeting_notes_id: 'test-note-id',
        status: 'processing',
        workflow_id: 'workflow-123'
      };

      // Mock supabase insert calls
      const mockSelect = vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: mockMeetingNote, error: null })
      });

      const mockInsert = vi.fn().mockReturnValue({
        select: mockSelect
      });

      vi.mocked(supabase.from).mockImplementation((table: string) => {
        if (table === 'meeting_notes') {
          return { insert: mockInsert } as any;
        }
        if (table === 'extraction_runs') {
          return {
            insert: vi.fn().mockReturnValue({
              select: vi.fn().mockReturnValue({
                single: vi.fn().mockResolvedValue({ data: mockExtractionRun, error: null })
              })
            })
          } as any;
        }
        return {} as any;
      });

      // Mock fetch for workflow trigger
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, workflow_id: 'workflow-123' })
      } as Response);

      const { result } = renderHook(() => useCreateMeetingNote(), {
        wrapper: createWrapper()
      });

      result.current.mutate('Test meeting notes');

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual({
        meeting_notes_id: 'test-note-id',
        extraction_run_id: 'test-run-id'
      });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/trigger-workflow',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
      );
    });

    it('should handle meeting note creation error', async () => {
      const mockError = { message: 'Database error' };

      const mockInsert = vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({ data: null, error: mockError })
        })
      });

      vi.mocked(supabase.from).mockReturnValue({ insert: mockInsert } as any);

      const { result } = renderHook(() => useCreateMeetingNote(), {
        wrapper: createWrapper()
      });

      result.current.mutate('Test notes');

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toEqual(mockError);
    });

    it('should handle workflow trigger failure', async () => {
      const mockMeetingNote = {
        id: 'test-note-id',
        notes_text: 'Test notes',
        created_at: '2026-07-07T10:00:00Z'
      };

      const mockExtractionRun = {
        id: 'test-run-id',
        meeting_notes_id: 'test-note-id',
        status: 'processing'
      };

      // Mock successful DB inserts
      vi.mocked(supabase.from).mockImplementation((table: string) => {
        if (table === 'meeting_notes') {
          return {
            insert: vi.fn().mockReturnValue({
              select: vi.fn().mockReturnValue({
                single: vi.fn().mockResolvedValue({ data: mockMeetingNote, error: null })
              })
            })
          } as any;
        }
        if (table === 'extraction_runs') {
          return {
            insert: vi.fn().mockReturnValue({
              select: vi.fn().mockReturnValue({
                single: vi.fn().mockResolvedValue({ data: mockExtractionRun, error: null })
              })
            }),
            update: vi.fn().mockReturnValue({
              eq: vi.fn().mockResolvedValue({ data: null, error: null })
            })
          } as any;
        }
        return {} as any;
      });

      // Mock failed workflow trigger
      (global.fetch as any).mockResolvedValue({
        ok: false,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Workflow service unavailable' })
      } as Response);

      const { result } = renderHook(() => useCreateMeetingNote(), {
        wrapper: createWrapper()
      });

      result.current.mutate('Test notes');

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  describe('useExtractionRun', () => {
    it('should fetch extraction run with action items', async () => {
      const mockData = {
        id: 'test-run-id',
        status: 'completed',
        action_items: [
          {
            id: 'action-1',
            description: 'Test action',
            owner: 'John',
            due_date: '2026-07-15',
            confidence: 0.95,
            created_at: '2026-07-07T10:00:00Z'
          }
        ]
      };

      const mockEq = vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: mockData, error: null })
      });

      const mockSelect = vi.fn().mockReturnValue({
        eq: mockEq
      });

      vi.mocked(supabase.from).mockReturnValue({ select: mockSelect } as any);

      const { result } = renderHook(() => useExtractionRun('test-run-id'), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockData);
      expect(mockSelect).toHaveBeenCalledWith(expect.stringContaining('action_items'));
    });

    it('should return null when extractionRunId is null', () => {
      const { result } = renderHook(() => useExtractionRun(null), {
        wrapper: createWrapper()
      });

      expect(result.current.data).toBeUndefined();
      expect(result.current.fetchStatus).toBe('idle');
    });

    it('should poll when status is processing', async () => {
      const mockData = {
        id: 'test-run-id',
        status: 'processing',
        action_items: []
      };

      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            single: vi.fn().mockResolvedValue({ data: mockData, error: null })
          })
        })
      } as any);

      const { result } = renderHook(() => useExtractionRun('test-run-id'), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.status).toBe('processing');
    });
  });

  describe('useExtractionRuns', () => {
    it('should fetch all extraction runs', async () => {
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
          created_at: '2026-07-06T10:00:00Z',
          meeting_notes: { notes_text: 'Notes 2' }
        }
      ];

      const mockLimit = vi.fn().mockResolvedValue({ data: mockData, error: null });
      const mockOrder = vi.fn().mockReturnValue({ limit: mockLimit });
      const mockSelect = vi.fn().mockReturnValue({ order: mockOrder });

      vi.mocked(supabase.from).mockReturnValue({ select: mockSelect } as any);

      const { result } = renderHook(() => useExtractionRuns(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockData);
      expect(mockOrder).toHaveBeenCalledWith('created_at', { ascending: false });
      expect(mockLimit).toHaveBeenCalledWith(10);
    });

    it('should handle fetch error', async () => {
      const mockError = { message: 'Network error' };

      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn().mockReturnValue({
          order: vi.fn().mockReturnValue({
            limit: vi.fn().mockResolvedValue({ data: null, error: mockError })
          })
        })
      } as any);

      const { result } = renderHook(() => useExtractionRuns(), {
        wrapper: createWrapper()
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toEqual(mockError);
    });
  });
});
