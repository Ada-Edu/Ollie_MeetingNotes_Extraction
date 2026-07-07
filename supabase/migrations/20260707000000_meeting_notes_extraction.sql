-- Meeting Notes Action Item Extraction Schema
-- Created: 2026-07-07
-- Purpose: Support AI-powered extraction of action items from meeting notes via Temporal workflows

-- Meeting notes submissions
CREATE TABLE IF NOT EXISTS meeting_notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID, -- Optional: link to user if auth exists
  notes_text TEXT NOT NULL CHECK (char_length(notes_text) BETWEEN 1 AND 10000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_meeting_notes_updated_at
  BEFORE UPDATE ON meeting_notes
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

COMMENT ON TABLE meeting_notes IS 'Raw meeting notes submitted by users for action item extraction';
COMMENT ON COLUMN meeting_notes.notes_text IS 'Meeting notes text (1-10000 characters)';

-- Extraction runs (workflow executions)
CREATE TABLE IF NOT EXISTS extraction_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_notes_id UUID NOT NULL REFERENCES meeting_notes(id) ON DELETE CASCADE,
  workflow_id TEXT NOT NULL, -- Temporal workflow ID for tracking
  status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'failed')),
  model_provider TEXT CHECK (model_provider IN ('azure', 'bedrock')),
  model_name TEXT,
  error_message TEXT,
  raw_model_response JSONB, -- Full model response for debugging
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_extraction_runs_updated_at
  BEFORE UPDATE ON extraction_runs
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX idx_extraction_runs_meeting_notes_id ON extraction_runs(meeting_notes_id);
CREATE INDEX idx_extraction_runs_status ON extraction_runs(status);
CREATE INDEX idx_extraction_runs_workflow_id ON extraction_runs(workflow_id);
CREATE INDEX idx_extraction_runs_completed_at ON extraction_runs(completed_at) WHERE completed_at IS NOT NULL;

COMMENT ON TABLE extraction_runs IS 'Records of Temporal workflow executions for action item extraction';
COMMENT ON COLUMN extraction_runs.workflow_id IS 'Temporal workflow execution ID';
COMMENT ON COLUMN extraction_runs.status IS 'Workflow status: processing, completed, or failed';
COMMENT ON COLUMN extraction_runs.raw_model_response IS 'Full model API response for debugging';

-- Extracted action items
CREATE TABLE IF NOT EXISTS action_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  extraction_run_id UUID NOT NULL REFERENCES extraction_runs(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  owner TEXT, -- Can be NULL (will show as "Unassigned" in UI)
  due_date DATE, -- Can be NULL (will show as "No due date" in UI)
  confidence NUMERIC(3, 2) CHECK (confidence IS NULL OR (confidence BETWEEN 0 AND 1)),
  metadata JSONB DEFAULT '{}', -- Additional context from model
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_action_items_updated_at
  BEFORE UPDATE ON action_items
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX idx_action_items_extraction_run_id ON action_items(extraction_run_id);
CREATE INDEX idx_action_items_due_date ON action_items(due_date) WHERE due_date IS NOT NULL;
CREATE INDEX idx_action_items_owner ON action_items(owner) WHERE owner IS NOT NULL;

COMMENT ON TABLE action_items IS 'Action items extracted from meeting notes by AI model';
COMMENT ON COLUMN action_items.description IS 'Task description extracted from notes';
COMMENT ON COLUMN action_items.owner IS 'Person responsible (NULL = Unassigned)';
COMMENT ON COLUMN action_items.due_date IS 'Due date if mentioned (NULL = No due date)';
COMMENT ON COLUMN action_items.confidence IS 'Model confidence score (0.00-1.00)';
