/**
 * Integration tests for Supabase API integration with meeting notes tables.
 * Tests CRUD operations and React Query integration without mocking Supabase client.
 *
 * @group integration
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import { useCreateMeetingNote, useExtractionRun, useExtractionRuns } from '@/lib/hooks/useMeetingNotes';
import type { ReactNode } from 'react';

// Test IDs for cleanup
const testIds = {
  meetingNotes: [] as string[],
  extractionRuns: [] as string[],
};

// Helper to create wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('Supabase API Integration - Meeting Notes Tables', () => {
  beforeEach(async () => {
    // Clean up any existing test data
    await cleanupTestData();
  });

  afterEach(async () => {
    // Clean up after each test
    await cleanupTestData();
  });

  describe('Meeting Notes CRUD Operations', () => {
    it('should create a meeting note and insert into database', async () => {
      const { data: meetingNote, error } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test meeting notes for integration test' })
        .select()
        .single();

      expect(error).toBeNull();
      expect(meetingNote).toBeDefined();
      expect(meetingNote?.id).toBeDefined();
      expect(meetingNote?.notes_text).toBe('Test meeting notes for integration test');
      expect(meetingNote?.created_at).toBeDefined();

      if (meetingNote?.id) {
        testIds.meetingNotes.push(meetingNote.id);
      }
    });

    it('should read meeting notes from database', async () => {
      // Create test data
      const { data: created } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Read test meeting notes' })
        .select()
        .single();

      if (created?.id) {
        testIds.meetingNotes.push(created.id);
      }

      // Read back
      const { data: retrieved, error } = await supabase
        .from('meeting_notes')
        .select('*')
        .eq('id', created?.id)
        .single();

      expect(error).toBeNull();
      expect(retrieved).toBeDefined();
      expect(retrieved?.notes_text).toBe('Read test meeting notes');
      expect(retrieved?.id).toBe(created?.id);
    });

    it('should update meeting notes in database', async () => {
      // Create
      const { data: created } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Original notes' })
        .select()
        .single();

      if (created?.id) {
        testIds.meetingNotes.push(created.id);
      }

      // Update
      const { data: updated, error } = await supabase
        .from('meeting_notes')
        .update({ notes_text: 'Updated notes' })
        .eq('id', created?.id)
        .select()
        .single();

      expect(error).toBeNull();
      expect(updated?.notes_text).toBe('Updated notes');
      expect(updated?.updated_at).not.toBe(created?.updated_at);
    });

    it('should validate notes_text length constraints', async () => {
      // Test empty string (should fail)
      const { error: emptyError } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: '' })
        .select()
        .single();

      expect(emptyError).toBeDefined();
      expect(emptyError?.message).toMatch(/check|constraint/i);

      // Test very long string (over 10000 chars - should fail)
      const longText = 'a'.repeat(10001);
      const { error: longError } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: longText })
        .select()
        .single();

      expect(longError).toBeDefined();
      expect(longError?.message).toMatch(/check|constraint/i);
    });
  });

  describe('Extraction Runs CRUD Operations', () => {
    it('should create extraction run with processing status', async () => {
      // Create meeting note first
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test notes for extraction' })
        .select()
        .single();

      if (meetingNote?.id) {
        testIds.meetingNotes.push(meetingNote.id);
      }

      // Create extraction run
      const { data: extractionRun, error } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-workflow-123',
          status: 'processing',
        })
        .select()
        .single();

      expect(error).toBeNull();
      expect(extractionRun).toBeDefined();
      expect(extractionRun?.status).toBe('processing');
      expect(extractionRun?.workflow_id).toBe('test-workflow-123');
      expect(extractionRun?.meeting_notes_id).toBe(meetingNote?.id);
      expect(extractionRun?.started_at).toBeDefined();

      if (extractionRun?.id) {
        testIds.extractionRuns.push(extractionRun.id);
      }
    });

    it('should update extraction run to completed status', async () => {
      // Setup
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test notes' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-workflow-complete',
          status: 'processing',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      // Update to completed
      const { data: updated, error } = await supabase
        .from('extraction_runs')
        .update({
          status: 'completed',
          model_provider: 'azure',
          model_name: 'gpt-4',
          completed_at: new Date().toISOString(),
        })
        .eq('id', extractionRun?.id)
        .select()
        .single();

      expect(error).toBeNull();
      expect(updated?.status).toBe('completed');
      expect(updated?.model_provider).toBe('azure');
      expect(updated?.model_name).toBe('gpt-4');
      expect(updated?.completed_at).toBeDefined();
    });

    it('should validate status enum constraint', async () => {
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test notes' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      // Try to insert with invalid status
      const { error } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-workflow',
          status: 'invalid_status' as any,
        });

      expect(error).toBeDefined();
      expect(error?.message).toMatch(/check|constraint/i);
    });
  });

  describe('Action Items CRUD Operations', () => {
    it('should create action items linked to extraction run', async () => {
      // Setup extraction run
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Meeting with action items' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-workflow-actions',
          status: 'completed',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      // Create action items
      const { data: actionItem, error } = await supabase
        .from('action_items')
        .insert({
          extraction_run_id: extractionRun?.id,
          description: 'Follow up with client',
          owner: 'John Doe',
          due_date: '2026-07-15',
          confidence: 0.95,
        })
        .select()
        .single();

      expect(error).toBeNull();
      expect(actionItem).toBeDefined();
      expect(actionItem?.description).toBe('Follow up with client');
      expect(actionItem?.owner).toBe('John Doe');
      expect(actionItem?.due_date).toBe('2026-07-15');
      expect(actionItem?.confidence).toBe(0.95);
    });

    it('should handle action items without owner or due date', async () => {
      // Setup
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test notes' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-workflow',
          status: 'completed',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      // Create action item with nulls
      const { data: actionItem, error } = await supabase
        .from('action_items')
        .insert({
          extraction_run_id: extractionRun?.id,
          description: 'Review documentation',
          owner: null,
          due_date: null,
          confidence: null,
        })
        .select()
        .single();

      expect(error).toBeNull();
      expect(actionItem?.description).toBe('Review documentation');
      expect(actionItem?.owner).toBeNull();
      expect(actionItem?.due_date).toBeNull();
      expect(actionItem?.confidence).toBeNull();
    });

    it('should cascade delete action items when extraction run is deleted', async () => {
      // Setup
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test notes' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-cascade',
          status: 'completed',
        })
        .select()
        .single();

      const { data: actionItem } = await supabase
        .from('action_items')
        .insert({
          extraction_run_id: extractionRun?.id,
          description: 'Test action',
        })
        .select()
        .single();

      const actionItemId = actionItem?.id;

      // Delete extraction run
      await supabase
        .from('extraction_runs')
        .delete()
        .eq('id', extractionRun?.id);

      // Check action item was deleted
      const { data: deletedItem } = await supabase
        .from('action_items')
        .select()
        .eq('id', actionItemId)
        .single();

      expect(deletedItem).toBeNull();
    });
  });

  describe('React Query Integration with Supabase', () => {
    it('should fetch extraction run with action items using useExtractionRun', async () => {
      // Setup test data
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Test meeting' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-query-123',
          status: 'completed',
          model_provider: 'azure',
          model_name: 'gpt-4',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      await supabase.from('action_items').insert({
        extraction_run_id: extractionRun?.id,
        description: 'Test action from query',
        owner: 'Test Owner',
      });

      // Test hook
      const wrapper = createWrapper();
      const { result } = renderHook(() => useExtractionRun(extractionRun?.id || null), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toBeDefined();
      expect(result.current.data?.id).toBe(extractionRun?.id);
      expect(result.current.data?.status).toBe('completed');
      expect(result.current.data?.action_items).toBeDefined();
      expect(result.current.data?.action_items?.length).toBeGreaterThan(0);
      expect(result.current.data?.action_items?.[0].description).toBe('Test action from query');
    });

    it('should list extraction runs using useExtractionRuns', async () => {
      // Create multiple test runs
      const { data: note1 } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Meeting 1' })
        .select()
        .single();

      const { data: note2 } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Meeting 2' })
        .select()
        .single();

      if (note1?.id) testIds.meetingNotes.push(note1.id);
      if (note2?.id) testIds.meetingNotes.push(note2.id);

      const { data: run1 } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: note1?.id,
          workflow_id: 'test-list-1',
          status: 'completed',
        })
        .select()
        .single();

      const { data: run2 } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: note2?.id,
          workflow_id: 'test-list-2',
          status: 'processing',
        })
        .select()
        .single();

      if (run1?.id) testIds.extractionRuns.push(run1.id);
      if (run2?.id) testIds.extractionRuns.push(run2.id);

      // Test hook
      const wrapper = createWrapper();
      const { result } = renderHook(() => useExtractionRuns(), { wrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toBeDefined();
      expect(result.current.data?.length).toBeGreaterThanOrEqual(2);

      const runIds = result.current.data?.map((r) => r.id);
      expect(runIds).toContain(run1?.id);
      expect(runIds).toContain(run2?.id);
    });
  });

  describe('Relational Queries', () => {
    it('should query extraction run with nested action items', async () => {
      // Setup
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Meeting with multiple actions' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-nested',
          status: 'completed',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      // Create multiple action items
      await supabase.from('action_items').insert([
        {
          extraction_run_id: extractionRun?.id,
          description: 'Action 1',
          owner: 'Alice',
        },
        {
          extraction_run_id: extractionRun?.id,
          description: 'Action 2',
          owner: 'Bob',
        },
      ]);

      // Query with nested relation
      const { data, error } = await supabase
        .from('extraction_runs')
        .select(`
          *,
          action_items (
            id,
            description,
            owner,
            due_date,
            confidence
          )
        `)
        .eq('id', extractionRun?.id)
        .single();

      expect(error).toBeNull();
      expect(data?.action_items).toBeDefined();
      expect(data?.action_items?.length).toBe(2);
      expect(data?.action_items?.some((a: any) => a.description === 'Action 1')).toBe(true);
      expect(data?.action_items?.some((a: any) => a.owner === 'Bob')).toBe(true);
    });

    it('should query extraction runs with nested meeting notes', async () => {
      const { data: meetingNote } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: 'Original meeting text' })
        .select()
        .single();

      if (meetingNote?.id) testIds.meetingNotes.push(meetingNote.id);

      const { data: extractionRun } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote?.id,
          workflow_id: 'test-parent',
          status: 'completed',
        })
        .select()
        .single();

      if (extractionRun?.id) testIds.extractionRuns.push(extractionRun.id);

      // Query with parent relation
      const { data, error } = await supabase
        .from('extraction_runs')
        .select(`
          *,
          meeting_notes (
            notes_text
          )
        `)
        .eq('id', extractionRun?.id)
        .single();

      expect(error).toBeNull();
      expect(data?.meeting_notes).toBeDefined();
      expect((data?.meeting_notes as any).notes_text).toBe('Original meeting text');
    });
  });
});

// Cleanup helper
async function cleanupTestData() {
  // Delete in correct order (child to parent due to foreign keys)
  // Action items will cascade delete with extraction_runs

  if (testIds.extractionRuns.length > 0) {
    await supabase
      .from('extraction_runs')
      .delete()
      .in('id', testIds.extractionRuns);
  }

  if (testIds.meetingNotes.length > 0) {
    await supabase
      .from('meeting_notes')
      .delete()
      .in('id', testIds.meetingNotes);
  }

  testIds.meetingNotes = [];
  testIds.extractionRuns = [];
}
