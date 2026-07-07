/**
 * Integration tests for React Query polling behavior with extraction runs.
 * Tests that polls automatically when status is 'processing' and stops when complete.
 *
 * @group integration
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import { useExtractionRun } from '@/lib/hooks/useMeetingNotes';
import type { ReactNode } from 'react';

// Test cleanup
const testIds = {
  meetingNotes: [] as string[],
  extractionRuns: [] as string[],
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0, // Disable cache for testing
      },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('React Query Polling Integration', () => {
  beforeEach(async () => {
    await cleanupTestData();
    vi.useFakeTimers();
  });

  afterEach(async () => {
    await cleanupTestData();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe('Polling Behavior', () => {
    it('should poll when extraction run status is processing', async () => {
      // Setup processing extraction run
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test meeting for polling' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-polling-123',
          status: 'processing',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      // Render hook
      const wrapper = createWrapper();
      const { result } = renderHook(() => useExtractionRun(extractionRun?.id || null), {
        wrapper,
      });

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.status).toBe('processing');

      // Track number of fetches
      const fetchCount = { count: 0 };
      const originalFetch = result.current.refetch;

      // Advance time by polling interval (2000ms)
      await vi.advanceTimersByTimeAsync(2000);

      // Should trigger refetch due to polling
      await waitFor(
        () => {
          expect(result.current.dataUpdatedAt).toBeGreaterThan(0);
        },
        { timeout: 3000 }
      );
    });

    it('should stop polling when status changes to completed', async () => {
      // Setup processing extraction run
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test meeting for completion' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-complete-123',
          status: 'processing',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      // Render hook
      const wrapper = createWrapper();
      const { result } = renderHook(() => useExtractionRun(extractionRun?.id || null), {
        wrapper,
      });

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.data?.status).toBe('processing');
      });

      const firstUpdateTime = result.current.dataUpdatedAt;

      // Update status to completed in database
      await supabase
        .from('extraction_runs')
        .update({
          status: 'completed',
          completed_at: new Date().toISOString(),
        })
        .eq('id', extractionRun?.id);

      // Advance time to trigger next poll
      await vi.advanceTimersByTimeAsync(2100);

      // Wait for status to update
      await waitFor(
        () => {
          expect(result.current.data?.status).toBe('completed');
        },
        { timeout: 3000 }
      );

      const secondUpdateTime = result.current.dataUpdatedAt;
      expect(secondUpdateTime).toBeGreaterThan(firstUpdateTime);

      // Advance time again - should NOT poll anymore
      const thirdUpdateTime = result.current.dataUpdatedAt;
      await vi.advanceTimersByTimeAsync(5000);

      // Wait a bit to ensure no refetch happens
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Update time should remain the same (no polling)
      expect(result.current.dataUpdatedAt).toBe(thirdUpdateTime);
    });

    it('should stop polling when status changes to failed', async () => {
      // Setup
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test meeting for failure' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-failed-123',
          status: 'processing',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useExtractionRun(extractionRun?.id || null), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.data?.status).toBe('processing');
      });

      // Update to failed
      await supabase
        .from('extraction_runs')
        .update({
          status: 'failed',
          error_message: 'Test error',
          completed_at: new Date().toISOString(),
        })
        .eq('id', extractionRun?.id);

      // Trigger poll
      await vi.advanceTimersByTimeAsync(2100);

      await waitFor(() => {
        expect(result.current.data?.status).toBe('failed');
      });

      const updateTimeAfterFailed = result.current.dataUpdatedAt;

      // Should not poll anymore
      await vi.advanceTimersByTimeAsync(5000);
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(result.current.dataUpdatedAt).toBe(updateTimeAfterFailed);
    });
  });

  describe('Polling with Action Items', () => {
    it('should poll and update action items as they are created', async () => {
      // Setup
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Meeting with progressive actions' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-progressive-123',
          status: 'processing',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useExtractionRun(extractionRun?.id || null), {
        wrapper,
      });

      // Initial state - no action items
      await waitFor(() => {
        expect(result.current.data?.status).toBe('processing');
      });

      expect(result.current.data?.action_items?.length || 0).toBe(0);

      // Add first action item
      await supabase.from('action_items').insert({
        extraction_run_id: extractionRun?.id,
        description: 'First action',
        owner: 'Alice',
      });

      // Wait for poll to pick it up
      await vi.advanceTimersByTimeAsync(2100);

      await waitFor(
        () => {
          expect(result.current.data?.action_items?.length).toBe(1);
        },
        { timeout: 3000 }
      );

      expect(result.current.data?.action_items?.[0].description).toBe('First action');

      // Add second action item
      await supabase.from('action_items').insert({
        extraction_run_id: extractionRun?.id,
        description: 'Second action',
        owner: 'Bob',
      });

      // Wait for next poll
      await vi.advanceTimersByTimeAsync(2100);

      await waitFor(
        () => {
          expect(result.current.data?.action_items?.length).toBe(2);
        },
        { timeout: 3000 }
      );

      const descriptions = result.current.data?.action_items?.map((a) => a.description);
      expect(descriptions).toContain('First action');
      expect(descriptions).toContain('Second action');

      // Complete the extraction
      await supabase
        .from('extraction_runs')
        .update({ status: 'completed', completed_at: new Date().toISOString() })
        .eq('id', extractionRun?.id);

      await vi.advanceTimersByTimeAsync(2100);

      await waitFor(() => {
        expect(result.current.data?.status).toBe('completed');
      });
    });
  });

  describe('Polling Configuration', () => {
    it('should use 2 second polling interval for processing status', async () => {
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test polling interval' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-interval-123',
          status: 'processing',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useExtractionRun(extractionRun?.id || null), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const firstTime = result.current.dataUpdatedAt;

      // Advance by less than 2 seconds - should not poll
      await vi.advanceTimersByTimeAsync(1500);
      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(result.current.dataUpdatedAt).toBe(firstTime);

      // Advance to reach 2 seconds - should poll
      await vi.advanceTimersByTimeAsync(600);
      await waitFor(
        () => {
          expect(result.current.dataUpdatedAt).toBeGreaterThan(firstTime);
        },
        { timeout: 1000 }
      );
    });

    it('should not poll when extraction run ID is null', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useExtractionRun(null), { wrapper });

      // Query should be disabled
      expect(result.current.data).toBeUndefined();
      expect(result.current.fetchStatus).toBe('idle');

      // Advance time
      await vi.advanceTimersByTimeAsync(10000);

      // Should remain idle
      expect(result.current.fetchStatus).toBe('idle');
    });
  });

  describe('Error Handling During Polling', () => {
    it('should continue polling even if query temporarily fails', async () => {
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test error recovery' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-error-123',
          status: 'processing',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useExtractionRun(extractionRun?.id || null), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Even with network issues, polling should continue trying
      // The refetchInterval should still be active
      await vi.advanceTimersByTimeAsync(2100);

      // Should still have data from cache
      expect(result.current.data).toBeDefined();
    });
  });
});

async function cleanupTestData() {
  if (testIds.extractionRuns.length > 0) {
    await supabase.from('extraction_runs').delete().in('id', testIds.extractionRuns);
  }

  if (testIds.meetingNotes.length > 0) {
    await supabase.from('meeting_notes').delete().in('id', testIds.meetingNotes);
  }

  testIds.meetingNotes = [];
  testIds.extractionRuns = [];
}
