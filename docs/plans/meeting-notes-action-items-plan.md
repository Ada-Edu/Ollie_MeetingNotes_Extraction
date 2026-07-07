# Implementation Plan: Meeting Notes → Action Items Extraction

**Date**: 2026-07-07  
**Spec Reference**: `docs/specs/meeting-notes-action-items.md`  
**Status**: Draft

---

## AI Draft Plan

### Overview
Implement an end-to-end feature for extracting action items from meeting notes using AI models (Azure OpenAI or AWS Bedrock) orchestrated through Temporal workflows, persisted in Supabase, and displayed in a React frontend.

### Implementation Steps

#### 1. Database Layer
**Files to create/modify**:
- `supabase/migrations/20260707000000_meeting_notes_extraction.sql`

**Tasks**:
- Create `meeting_notes` table (id, user_id, notes_text, created_at, updated_at)
- Create `extraction_runs` table (id, meeting_notes_id, workflow_id, status, model_provider, model_name, error_message, raw_model_response, started_at, completed_at, created_at, updated_at)
- Create `action_items` table (id, extraction_run_id, description, owner, due_date, confidence, metadata, created_at, updated_at)
- Add indexes for performance
- Add update triggers for timestamps

#### 2. Model Provider Abstraction
**Files to create**:
- `temporal/src/model_client/__init__.py`
- `temporal/src/model_client/base.py` - Abstract base class
- `temporal/src/model_client/azure_client.py` - Azure OpenAI client
- `temporal/src/model_client/bedrock_client.py` - AWS Bedrock client
- `temporal/src/model_client/factory.py` - Provider factory

**Tasks**:
- Define `BaseModelClient` interface with `extract_action_items()` method
- Implement Azure OpenAI client using `openai` library
- Implement Bedrock client using `boto3`
- Create factory function to instantiate correct provider based on env var
- Add configuration loading from environment variables
- Include proper error handling and logging

#### 3. Temporal Workflow
**Files to create/modify**:
- `temporal/src/workflows/meeting_notes_extraction.py` - Main workflow
- `temporal/src/activities/meeting_notes.py` - Activities
- `temporal/src/worker.py` - Register new workflow

**Workflow Activities**:
1. `validate_meeting_notes_input(notes: str) -> None`
   - Check notes length (1-10000 chars)
   - Validate not empty
   - Raise exception if invalid

2. `call_model_for_action_item_extraction(notes: str) -> dict`
   - Load model client from factory
   - Construct prompt for action item extraction
   - Call model API
   - Return raw response
   - Retry 3 times on failure with exponential backoff

3. `validate_and_normalize_action_items(raw_response: dict) -> list`
   - Validate JSON structure
   - Extract action items array
   - Normalize: set owner to "Unassigned" if missing
   - Normalize: set due_date to None if missing
   - Validate each item has description
   - Return normalized list

4. `persist_extraction_run_and_tasks(meeting_notes_id: str, action_items: list, raw_response: dict, model_info: dict) -> str`
   - Create extraction_run record (status='completed')
   - Create action_item records for each extracted item
   - Return extraction_run_id

5. `handle_extraction_error(meeting_notes_id: str, error: Exception, model_info: dict) -> str`
   - Create extraction_run record (status='failed')
   - Store error message
   - Return extraction_run_id

**Workflow Logic**:
```python
@workflow.defn
class ExtractMeetingActionItemsWorkflow:
    @workflow.run
    async def run(self, meeting_notes_id: str, notes: str) -> dict:
        try:
            # Step 1: Validate input
            await workflow.execute_activity(
                validate_meeting_notes_input,
                args=[notes],
                start_to_close_timeout=timedelta(seconds=5)
            )
            
            # Step 2: Call model
            raw_response = await workflow.execute_activity(
                call_model_for_action_item_extraction,
                args=[notes],
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0,
                    maximum_attempts=3
                ),
                start_to_close_timeout=timedelta(seconds=30)
            )
            
            # Step 3: Validate and normalize
            action_items = await workflow.execute_activity(
                validate_and_normalize_action_items,
                args=[raw_response],
                start_to_close_timeout=timedelta(seconds=5)
            )
            
            # Step 4: Persist
            extraction_run_id = await workflow.execute_activity(
                persist_extraction_run_and_tasks,
                args=[meeting_notes_id, action_items, raw_response, model_info],
                start_to_close_timeout=timedelta(seconds=10)
            )
            
            return {
                "status": "completed",
                "extraction_run_id": extraction_run_id,
                "action_items_count": len(action_items)
            }
            
        except Exception as e:
            # Step 5: Handle error
            extraction_run_id = await workflow.execute_activity(
                handle_extraction_error,
                args=[meeting_notes_id, str(e), model_info],
                start_to_close_timeout=timedelta(seconds=10)
            )
            
            return {
                "status": "failed",
                "extraction_run_id": extraction_run_id,
                "error": str(e)
            }
```

#### 4. Frontend Component
**Files to create**:
- `frontend/src/pages/MeetingNotesExtraction.tsx` - Main page
- `frontend/src/components/MeetingNotesInput.tsx` - Textarea component
- `frontend/src/components/ActionItemsList.tsx` - Results display
- `frontend/src/lib/hooks/useMeetingNotes.ts` - Custom hooks for API calls

**Components**:
- **MeetingNotesInput**: Textarea + submit button
- **ActionItemsList**: Display cards for each action item
- **ExtractionStatus**: Show processing/completed/failed status

**API Integration**:
- POST to start extraction (returns extraction_run_id)
- GET to fetch results (poll or manual refresh)
- Display loading state during processing
- Display error state on failure

#### 5. API/Backend Layer
**Approach**: Use existing Supabase client patterns

**Functions needed**:
- `createMeetingNoteAndStartExtraction(notes: string)` → Returns extraction_run_id
- `getExtractionStatus(extraction_run_id: string)` → Returns status + action_items
- Workflow triggered via Temporal Python client from activity or separate API

**Note**: May need simple API endpoint or serverless function to trigger Temporal workflow

#### 6. Configuration
**Files to modify**:
- `.env.example` - Add model configuration template
- `temporal/pyproject.toml` - Add dependencies (openai, boto3)
- `temporal/requirements.txt` - Update with new dependencies

**Environment Variables**:
```env
# Model Provider Configuration
MODEL_PROVIDER=azure  # or 'bedrock'

# Azure OpenAI (if MODEL_PROVIDER=azure)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# AWS Bedrock (if MODEL_PROVIDER=bedrock)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here
BEDROCK_MODEL_ID=anthropic.claude-v2
```

#### 7. Testing
**Files to create**:
- `temporal/tests/test_model_client.py` - Unit tests for model clients
- `temporal/tests/test_meeting_notes_activities.py` - Activity tests
- `temporal/tests/test_meeting_notes_workflow.py` - Workflow tests
- `frontend/src/__tests__/MeetingNotesExtraction.test.tsx` - Frontend tests

**Test Cases**:
- Valid notes extraction
- Empty notes validation error
- Notes too long validation error
- Model returns invalid JSON
- Model returns empty action items array
- Action item without owner (should show "Unassigned")
- Action item without due date (should show "No due date")
- Model API failure with retry
- Workflow timeout

### Timeline Estimate
- **Database + Config**: 2 hours
- **Model Client**: 4 hours
- **Temporal Workflow**: 6 hours
- **Frontend**: 4 hours
- **Testing**: 4 hours
- **Total**: ~20 hours (2.5 days)

---

## Critique of Draft Plan

### Strengths
✅ Clear breakdown of components (database, model, workflow, frontend)  
✅ Detailed workflow logic with retry policies  
✅ Explicit error handling strategy  
✅ Comprehensive test coverage  
✅ Environment configuration well-defined  

### Weaknesses
❌ **API layer is vague** - Doesn't specify how frontend triggers Temporal workflow  
❌ **Missing prompt engineering details** - How do we structure the model prompt?  
❌ **No schema for model response** - What JSON structure do we expect?  
❌ **Workflow triggering unclear** - Direct Temporal client call or via API?  
❌ **No discussion of frontend routing** - Where does this page live in the app?  
❌ **Missing validation details** - What's the exact JSON schema for action items?  
❌ **No mention of existing patterns** - Should review existing workflow and activity patterns  
❌ **Timeline seems optimistic** - Doesn't account for integration issues  

### Critical Gaps
1. **Prompt Template**: Need to define exact prompt for model
2. **JSON Schema**: Need explicit schema for model response validation
3. **API Layer**: Need to decide: Supabase Edge Function, separate API, or direct Temporal client?
4. **Frontend Integration**: Need to check existing routing patterns
5. **Error Messages**: Need user-friendly error message mapping

---

## Tightened Implementation Plan

### Phase 1: Foundation (Database + Config)

#### 1.1 Database Migration
**File**: `supabase/migrations/20260707000000_meeting_notes_extraction.sql`

```sql
-- Meeting notes table
CREATE TABLE meeting_notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  notes_text TEXT NOT NULL CHECK (char_length(notes_text) BETWEEN 1 AND 10000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_meeting_notes_updated_at
  BEFORE UPDATE ON meeting_notes
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Extraction runs table
CREATE TABLE extraction_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_notes_id UUID NOT NULL REFERENCES meeting_notes(id) ON DELETE CASCADE,
  workflow_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'failed')),
  model_provider TEXT CHECK (model_provider IN ('azure', 'bedrock')),
  model_name TEXT,
  error_message TEXT,
  raw_model_response JSONB,
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

-- Action items table
CREATE TABLE action_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  extraction_run_id UUID NOT NULL REFERENCES extraction_runs(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  owner TEXT,
  due_date DATE,
  confidence NUMERIC(3, 2) CHECK (confidence BETWEEN 0 AND 1),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_action_items_updated_at
  BEFORE UPDATE ON action_items
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX idx_action_items_extraction_run_id ON action_items(extraction_run_id);
CREATE INDEX idx_action_items_due_date ON action_items(due_date) WHERE due_date IS NOT NULL;
```

**Verification**: Run `supabase db reset` to apply migration

#### 1.2 Environment Configuration
**Files**: 
- `.env.example` (add new section)
- `temporal/pyproject.toml` (add dependencies)
- `temporal/requirements.txt` (regenerate)

**New env vars**:
```env
# AI Model Configuration
MODEL_PROVIDER=azure  # Options: azure, bedrock

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# AWS Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
BEDROCK_MODEL_ID=anthropic.claude-v2
```

**Dependencies to add**:
```toml
dependencies = [
  # ... existing
  "openai==1.10.0",
  "boto3==1.34.0",
]
```

### Phase 2: Model Provider Abstraction

#### 2.1 Base Model Client Interface
**File**: `temporal/src/model_client/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class ActionItem:
    description: str
    owner: str | None = None
    due_date: str | None = None  # ISO date format
    confidence: float | None = None

class BaseModelClient(ABC):
    @abstractmethod
    async def extract_action_items(self, notes: str) -> List[ActionItem]:
        """Extract action items from meeting notes.
        
        Returns:
            List of ActionItem objects
            
        Raises:
            ModelAPIError: If API call fails
            InvalidResponseError: If response doesn't match expected schema
        """
        pass
```

#### 2.2 Prompt Template
**File**: `temporal/src/model_client/prompts.py`

```python
SYSTEM_PROMPT = """You are an AI assistant that extracts action items from meeting notes.

Your task:
1. Identify all actionable tasks from the meeting notes
2. Extract: task description, owner (person responsible), due date
3. Do NOT hallucinate or guess information
4. If owner is unclear, omit the "owner" field
5. If due date is unclear, omit the "due_date" field
6. Return results as JSON array

JSON Schema:
{
  "action_items": [
    {
      "description": "string (required)",
      "owner": "string (optional)",
      "due_date": "YYYY-MM-DD (optional)",
      "confidence": number 0-1 (optional)
    }
  ]
}"""

def build_extraction_prompt(notes: str) -> str:
    return f"""{SYSTEM_PROMPT}

Meeting Notes:
\"\"\"
{notes}
\"\"\"

Extract action items and return only valid JSON:"""
```

#### 2.3 Azure Client Implementation
**File**: `temporal/src/model_client/azure_client.py`

```python
import os
import json
from openai import AzureOpenAI
from .base import BaseModelClient, ActionItem
from .prompts import build_extraction_prompt

class AzureModelClient(BaseModelClient):
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
    async def extract_action_items(self, notes: str) -> List[ActionItem]:
        prompt = build_extraction_prompt(notes)
        
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        return [ActionItem(**item) for item in data.get("action_items", [])]
```

#### 2.4 Factory Function
**File**: `temporal/src/model_client/factory.py`

```python
import os
from .base import BaseModelClient
from .azure_client import AzureModelClient
from .bedrock_client import BedrockModelClient

def get_model_client() -> BaseModelClient:
    provider = os.getenv("MODEL_PROVIDER", "").lower()
    
    if provider == "azure":
        return AzureModelClient()
    elif provider == "bedrock":
        return BedrockModelClient()
    else:
        raise ValueError(
            f"Invalid MODEL_PROVIDER: {provider}. "
            "Must be 'azure' or 'bedrock'. "
            "Set MODEL_PROVIDER environment variable."
        )
```

### Phase 3: Temporal Workflow & Activities

#### 3.1 Activities
**File**: `temporal/src/activities/meeting_notes.py`

```python
from temporalio import activity
from ..supabase_client import get_supabase_client
from ..model_client.factory import get_model_client
import logging

logger = logging.getLogger(__name__)

@activity.defn
async def validate_meeting_notes_input(notes: str) -> None:
    if not notes or not notes.strip():
        raise ValueError("Meeting notes cannot be empty")
    if len(notes) > 10000:
        raise ValueError("Meeting notes exceed 10,000 character limit")
    if len(notes) < 10:
        raise ValueError("Meeting notes too short (minimum 10 characters)")

@activity.defn
async def call_model_for_action_item_extraction(notes: str) -> dict:
    logger.info("Calling model for extraction")
    client = get_model_client()
    action_items = await client.extract_action_items(notes)
    
    return {
        "action_items": [
            {
                "description": item.description,
                "owner": item.owner,
                "due_date": item.due_date,
                "confidence": item.confidence
            }
            for item in action_items
        ],
        "model_provider": os.getenv("MODEL_PROVIDER"),
        "model_name": client.get_model_name()
    }

@activity.defn
async def persist_extraction_results(
    meeting_notes_id: str,
    workflow_id: str,
    action_items: list,
    model_info: dict
) -> str:
    client = get_supabase_client()
    
    # Create extraction run
    extraction_run = await client.create_extraction_run(
        meeting_notes_id=meeting_notes_id,
        workflow_id=workflow_id,
        status="completed",
        model_provider=model_info["model_provider"],
        model_name=model_info["model_name"]
    )
    
    # Create action items
    for item in action_items:
        await client.create_action_item(
            extraction_run_id=extraction_run["id"],
            **item
        )
    
    return extraction_run["id"]

@activity.defn
async def record_extraction_failure(
    meeting_notes_id: str,
    workflow_id: str,
    error_message: str,
    model_info: dict
) -> str:
    client = get_supabase_client()
    
    extraction_run = await client.create_extraction_run(
        meeting_notes_id=meeting_notes_id,
        workflow_id=workflow_id,
        status="failed",
        error_message=error_message,
        model_provider=model_info.get("model_provider"),
        model_name=model_info.get("model_name")
    )
    
    return extraction_run["id"]
```

#### 3.2 Workflow
**File**: `temporal/src/workflows/meeting_notes_extraction.py`

```python
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from ..activities.meeting_notes import (
        validate_meeting_notes_input,
        call_model_for_action_item_extraction,
        persist_extraction_results,
        record_extraction_failure
    )

@workflow.defn
class ExtractMeetingActionItemsWorkflow:
    @workflow.run
    async def run(self, meeting_notes_id: str, notes: str) -> dict:
        workflow_id = workflow.info().workflow_id
        model_info = {}
        
        try:
            # Validate input
            await workflow.execute_activity(
                validate_meeting_notes_input,
                args=[notes],
                start_to_close_timeout=timedelta(seconds=5)
            )
            
            # Call model with retries
            result = await workflow.execute_activity(
                call_model_for_action_item_extraction,
                args=[notes],
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0,
                    maximum_attempts=3
                ),
                start_to_close_timeout=timedelta(seconds=30)
            )
            
            action_items = result["action_items"]
            model_info = {
                "model_provider": result["model_provider"],
                "model_name": result["model_name"]
            }
            
            # Persist results
            extraction_run_id = await workflow.execute_activity(
                persist_extraction_results,
                args=[meeting_notes_id, workflow_id, action_items, model_info],
                start_to_close_timeout=timedelta(seconds=10)
            )
            
            return {
                "status": "completed",
                "extraction_run_id": extraction_run_id,
                "action_items_count": len(action_items)
            }
            
        except Exception as e:
            workflow.logger.error(f"Extraction failed: {str(e)}")
            
            extraction_run_id = await workflow.execute_activity(
                record_extraction_failure,
                args=[meeting_notes_id, workflow_id, str(e), model_info],
                start_to_close_timeout=timedelta(seconds=10)
            )
            
            return {
                "status": "failed",
                "extraction_run_id": extraction_run_id,
                "error": str(e)
            }
```

### Phase 4: Frontend Implementation

#### 4.1 React Hooks
**File**: `frontend/src/lib/hooks/useMeetingNotes.ts`

```typescript
import { useMutation, useQuery } from '@tanstack/react-query';
import { supabase } from '../supabase';

export function useCreateMeetingNote() {
  return useMutation({
    mutationFn: async (notes: string) => {
      // Create meeting note
      const { data: meetingNote, error } = await supabase
        .from('meeting_notes')
        .insert({ notes_text: notes })
        .select()
        .single();
      
      if (error) throw error;
      
      // TODO: Trigger Temporal workflow
      // For now, return mock extraction_run
      return {
        meeting_notes_id: meetingNote.id,
        extraction_run_id: 'pending'
      };
    }
  });
}

export function useExtractionRun(extraction_run_id: string) {
  return useQuery({
    queryKey: ['extraction_run', extraction_run_id],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('extraction_runs')
        .select(`
          *,
          action_items (*)
        `)
        .eq('id', extraction_run_id)
        .single();
      
      if (error) throw error;
      return data;
    },
    enabled: !!extraction_run_id,
    refetchInterval: (data) => 
      data?.status === 'processing' ? 2000 : false
  });
}
```

#### 4.2 Main Component
**File**: `frontend/src/pages/MeetingNotesExtraction.tsx`

```typescript
import { useState } from 'react';
import { useCreateMeetingNote, useExtractionRun } from '@/lib/hooks/useMeetingNotes';

export function MeetingNotesExtraction() {
  const [notes, setNotes] = useState('');
  const [extractionRunId, setExtractionRunId] = useState<string | null>(null);
  
  const createNote = useCreateMeetingNote();
  const { data: extractionRun, isLoading } = useExtractionRun(extractionRunId || '');
  
  const handleSubmit = async () => {
    const result = await createNote.mutateAsync(notes);
    setExtractionRunId(result.extraction_run_id);
  };
  
  return (
    <div className="container mx-auto p-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-4">Meeting Notes → Action Items</h1>
      
      <div className="mb-6">
        <label className="block text-sm font-medium mb-2">
          Paste your meeting notes:
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Enter meeting notes here..."
          className="w-full h-48 p-4 border rounded-lg"
          maxLength={10000}
        />
        <p className="text-sm text-gray-500 mt-1">
          {notes.length} / 10,000 characters
        </p>
      </div>
      
      <button
        onClick={handleSubmit}
        disabled={!notes.trim() || createNote.isPending || isLoading}
        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
      >
        {createNote.isPending ? 'Starting...' : 'Extract Action Items'}
      </button>
      
      {extractionRun && (
        <div className="mt-8">
          <h2 className="text-2xl font-semibold mb-4">
            Extraction Results
          </h2>
          
          <ExtractionStatus status={extractionRun.status} />
          
          {extractionRun.status === 'completed' && (
            <ActionItemsList items={extractionRun.action_items} />
          )}
          
          {extractionRun.status === 'failed' && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800">
                Extraction failed: {extractionRun.error_message}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

### Phase 5: Integration & Testing

#### Test Strategy
1. **Unit Tests**: Model client, validation logic
2. **Integration Tests**: Workflow execution with mocked model
3. **E2E Test**: Full flow from frontend to database

**Files**:
- `temporal/tests/test_model_client.py`
- `temporal/tests/test_meeting_notes_workflow.py`
- `frontend/src/__tests__/MeetingNotesExtraction.test.tsx`

### Assumptions
1. Existing `update_updated_at()` trigger function exists in database
2. Supabase client has async methods for CRUD operations
3. Temporal worker is already running and will pick up new workflow
4. Frontend can call Supabase directly (no intermediate API needed for MVP)
5. Model APIs are already configured with valid credentials

### Risks
1. **Model API rate limits** - Mitigation: Implement retry with backoff
2. **Workflow triggering** - Need to clarify how frontend triggers Temporal (may need serverless function)
3. **Model prompt quality** - May need iteration to improve extraction accuracy
4. **Frontend routing** - Need to integrate with existing TanStack Router setup

### Files Expected to Change/Create

**New Files** (17 files):
- `docs/specs/meeting-notes-action-items.md` ✅
- `docs/plans/meeting-notes-action-items-plan.md` ✅ (this file)
- `docs/adrs/0001-temporal-meeting-notes-action-items-and-model-hosting.md` (next)
- `supabase/migrations/20260707000000_meeting_notes_extraction.sql`
- `temporal/src/model_client/__init__.py`
- `temporal/src/model_client/base.py`
- `temporal/src/model_client/prompts.py`
- `temporal/src/model_client/azure_client.py`
- `temporal/src/model_client/bedrock_client.py`
- `temporal/src/model_client/factory.py`
- `temporal/src/activities/meeting_notes.py`
- `temporal/src/workflows/meeting_notes_extraction.py`
- `frontend/src/pages/MeetingNotesExtraction.tsx`
- `frontend/src/lib/hooks/useMeetingNotes.ts`
- `temporal/tests/test_model_client.py`
- `temporal/tests/test_meeting_notes_workflow.py`
- `frontend/src/__tests__/MeetingNotesExtraction.test.tsx`

**Modified Files** (4 files):
- `.env.example` - Add model configuration
- `temporal/pyproject.toml` - Add dependencies
- `temporal/requirements.txt` - Regenerate
- `temporal/src/worker.py` - Register new workflow

**Total**: 21 files

### Revised Timeline
- **Phase 1** (Database + Config): 2 hours
- **Phase 2** (Model Client): 6 hours (includes Bedrock + testing)
- **Phase 3** (Temporal): 8 hours (includes Supabase client updates)
- **Phase 4** (Frontend): 6 hours (includes routing integration)
- **Phase 5** (Testing + Integration): 6 hours
- **Contingency**: 4 hours
- **Total**: ~32 hours (4 days)

### Next Steps
1. ✅ Create spec
2. ✅ Create plan (this document)
3. → Create ADR
4. → Implement Phase 1 (Database)
5. → Implement Phase 2 (Model Client)
6. → Implement Phase 3 (Temporal)
7. → Implement Phase 4 (Frontend)
8. → Implement Phase 5 (Testing)
9. → Verify and create PR

---

## Plan Approval
- [ ] Reviewed by tech lead
- [ ] Approved for implementation

