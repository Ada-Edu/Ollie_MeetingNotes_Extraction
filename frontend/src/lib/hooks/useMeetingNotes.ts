import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { supabase } from '../supabase';

export interface ActionItem {
  id: string;
  description: string;
  owner: string | null;
  due_date: string | null;
  confidence: number | null;
  created_at: string;
}

export interface ExtractionRun {
  id: string;
  status: 'processing' | 'completed' | 'failed';
  error_message: string | null;
  model_provider: string | null;
  model_name: string | null;
  completed_at: string | null;
  action_items?: ActionItem[];
}

/**
 * Create meeting note and get extraction run ID
 */
export function useCreateMeetingNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (notes: string) => {
      // Step 1: Create meeting note record
      const { data: meetingNote, error: noteError } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: notes })
        .select()
        .single();

      if (noteError) throw noteError;

      // Step 2: Create extraction run with 'processing' status
      // Use the same workflow_id format that will be passed to Temporal
      const workflowId = `extract-${meetingNote.id}`;
      const { data: extractionRun, error: runError } = await supabase
        .from('extraction_runs')
        .insert({
          meeting_notes_id: meetingNote.id,
          workflow_id: workflowId,
          status: 'processing'
        })
        .select()
        .single();

      if (runError) throw runError;

      // Step 3: Trigger Temporal workflow via API server
      try {
        const response = await fetch('http://localhost:8000/trigger-workflow', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            workflow_name: 'ExtractMeetingActionItemsWorkflow',
            workflow_id: workflowId,
            args: {
              meeting_notes_id: meetingNote.id,
              notes_text: notes
            },
            task_queue: 'main'
          })
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
          console.error('Failed to trigger workflow:', errorData);

          // Update extraction run to failed status
          await supabase
            .from('extraction_runs')
            .update({
              status: 'failed',
              error_message: `Workflow trigger failed: ${errorData.detail || response.statusText}`
            })
            .eq('id', extractionRun.id);

          throw new Error(`Failed to trigger extraction workflow: ${errorData.detail || response.statusText}`);
        }

        const result = await response.json();
        console.log('Workflow triggered successfully:', result);
      } catch (triggerError) {
        console.error('Error triggering workflow:', triggerError);

        // Update extraction run to failed
        await supabase
          .from('extraction_runs')
          .update({
            status: 'failed',
            error_message: `Workflow trigger error: ${triggerError instanceof Error ? triggerError.message : String(triggerError)}`
          })
          .eq('id', extractionRun.id);

        throw triggerError;
      }

      return {
        meeting_notes_id: meetingNote.id,
        extraction_run_id: extractionRun.id
      };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['extraction-runs'] });
    }
  });
}

/**
 * Get extraction run with action items
 */
export function useExtractionRun(extractionRunId: string | null) {
  return useQuery({
    queryKey: ['extraction-run', extractionRunId],
    queryFn: async () => {
      if (!extractionRunId) return null;

      const { data, error } = await supabase
        .from('extraction_runs')
        .select(`
          *,
          action_items (
            id,
            description,
            owner,
            due_date,
            confidence,
            created_at
          )
        `)
        .eq('id', extractionRunId)
        .single();

      if (error) throw error;
      return data as ExtractionRun;
    },
    enabled: !!extractionRunId,
    // Poll every 2 seconds if still processing
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === 'processing' ? 2000 : false;
    }
  });
}

/**
 * Get all extraction runs for a user
 */
export function useExtractionRuns() {
  return useQuery({
    queryKey: ['extraction-runs'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('extraction_runs')
        .select(`
          *,
          meeting_notes (
            notes_text
          )
        `)
        .order('created_at', { ascending: false })
        .limit(10);

      if (error) throw error;
      return data;
    }
  });
}
