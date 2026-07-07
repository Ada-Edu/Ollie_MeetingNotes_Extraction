# Feature Specification: Meeting Notes → Action Items Extraction

## Overview
An agentic workflow that extracts actionable tasks from raw meeting notes using AI. Users paste meeting notes into a web form, and the system asynchronously extracts action items with owners and due dates, displaying them as a structured task list.

## Metadata
- **Feature Name**: Meeting Notes Action Items Extraction
- **Status**: Draft
- **Priority**: P1 - High
- **Target Release**: v1.1.0
- **Owner**: Development Team
- **Stakeholders**: Product Team, End Users
- **Epic/Initiative**: AI-Powered Productivity Tools
- **Created**: 2026-07-07
- **Last Updated**: 2026-07-07

## Problem Statement

### User Problem
After meetings, users manually copy action items from notes into task management systems. This is time-consuming, error-prone, and items are often missed or incorrectly interpreted.

### Business Problem
Manual action item extraction reduces productivity and leads to missed follow-ups, impacting project delivery and team coordination.

### Current State
Users read through meeting notes, manually identify action items, determine owners and due dates, then manually enter them into task systems.

### Desired State
Users paste meeting notes, the system automatically extracts action items with metadata (owner, due date), and displays them as actionable tasks that can be reviewed and refined.

## Goals and Non-Goals

### Goals
- Automatically extract action items from unstructured meeting notes
- Identify task owners and due dates where present
- Handle ambiguity gracefully (no hallucination)
- Provide async processing with status feedback
- Persist extracted items for later retrieval
- Support retries and error handling

### Non-Goals
- Real-time transcription during meetings
- Calendar integration for scheduling
- Email notifications to owners
- Advanced NLP features (sentiment analysis, topic modeling)
- Multi-language support (English only for v1)

### Success Metrics
- Extraction accuracy > 85% (manual review)
- Processing time < 30 seconds for typical meeting notes
- System uptime > 99.5%
- User satisfaction score > 4/5

## User Stories

### Primary User Story
```
As a meeting participant,
I want to paste my meeting notes and have action items automatically extracted,
So that I can quickly review and track what needs to be done without manual data entry.
```

**Acceptance Criteria:**
- [ ] Given I paste raw meeting notes, when I submit them, then the system starts an extraction workflow and shows extraction status
- [ ] Given the notes contain action items, when extraction completes, then I see a task list containing description, owner, due date, and status
- [ ] Given the notes contain an action item without an owner or due date, then the system marks owner as "Unassigned" and/or due date as "No due date" (no hallucination)
- [ ] Given model extraction fails, then I see a useful error message and the failed run is recorded
- [ ] Given extracted tasks are saved, when I refresh the page, then I still see my saved tasks
- [ ] Given the model returns invalid JSON, then the workflow validates, handles the error, and records a failed extraction rather than corrupting task data

### Secondary User Stories

```
As a user,
I want to see the processing status of my extraction,
So that I know when results are ready.
```

**Acceptance Criteria:**
- [ ] Extraction status shows: "Processing", "Completed", or "Failed"
- [ ] Status updates in real-time or on refresh
- [ ] Failed extractions show descriptive error messages

```
As a user,
I want to see confidence levels for extracted items,
So that I can prioritize review of uncertain extractions.
```

**Acceptance Criteria:**
- [ ] Each action item shows confidence score if available
- [ ] Low-confidence items are visually highlighted

## Requirements

### Functional Requirements

#### Must Have (P0)
- Accept meeting notes text input (up to 10,000 characters)
- Start Temporal workflow for extraction
- Call configured AI model (Azure OpenAI or AWS Bedrock)
- Extract action items with: description, owner, due date
- Validate model output (JSON schema)
- Handle missing owner/due date gracefully
- Store extraction runs and action items in database
- Display extraction status to user
- Display extracted action items in UI
- Handle model failures with retry logic
- Show error states clearly

#### Should Have (P1)
- Include confidence scores for extractions
- Support re-running extraction on same notes
- Filter/sort action items by owner or due date
- Show raw model response for debugging

#### Nice to Have (P2)
- Export action items to CSV/JSON
- Edit extracted action items before saving
- Bulk operations on action items

### Non-Functional Requirements
- **Performance**: Extraction completes in < 30 seconds for typical notes (500-2000 words)
- **Security**: Meeting notes contain sensitive data; enforce authentication and encryption at rest
- **Scalability**: Support 100 concurrent extraction workflows
- **Reliability**: 99.5% uptime; automatic retries on transient failures
- **Usability**: Simple UI - paste notes, click submit, see results
- **Observability**: All extraction runs logged in Temporal UI and database

### Constraints
- Must use team's own Azure OpenAI or AWS Bedrock endpoint (no public APIs)
- No credentials in source code (env vars only)
- Must work with existing Supabase + Temporal infrastructure
- Frontend must integrate with existing React + TypeScript codebase

## User Experience

### User Flows

#### Happy Path
1. User navigates to Meeting Notes page
2. User pastes meeting notes into textarea
3. User clicks "Extract Action Items" button
4. System shows "Processing..." status
5. System completes extraction (5-30 seconds)
6. System displays extracted action items as cards/list:
   - Task description
   - Owner name (or "Unassigned")
   - Due date (or "No due date")
   - Confidence score (optional)
7. User reviews action items
8. User can refresh page and still see results

#### Alternative Path: No Action Items Found
1-4. Same as happy path
5. Model completes but finds no action items
6. System shows: "No action items found in these notes"
7. User can try with different notes

#### Error Scenarios

**Model API Failure**
- System: "Extraction failed due to model service error. Please try again."
- Logged: Error details in extraction_runs table

**Invalid JSON from Model**
- System: "Extraction failed due to unexpected model response. Please try again."
- Logged: Raw response stored for debugging

**Timeout**
- System: "Extraction is taking longer than expected. Please try again later."
- Workflow: Continues in background; results saved if completed

**Empty Input**
- System: "Please enter meeting notes to extract action items."
- No workflow started

### Wire frames

```
┌─────────────────────────────────────────────────────────┐
│  Meeting Notes → Action Items                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Paste your meeting notes below:                        │
│  ┌───────────────────────────────────────────────────┐ │
│  │                                                   │ │
│  │  [Meeting notes textarea - 10 rows]              │ │
│  │                                                   │ │
│  │                                                   │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  ┌─────────────────────────┐                           │
│  │  Extract Action Items   │                           │
│  └─────────────────────────┘                           │
│                                                         │
│  Status: Processing... ⏳                               │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  Extracted Action Items (3):                            │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ✓ Follow up with Sarah on Q4 budget            │   │
│  │   Owner: John                                   │   │
│  │   Due: 2026-07-15                               │   │
│  │   Confidence: 92%                               │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ✓ Review architectural design doc              │   │
│  │   Owner: Unassigned                             │   │
│  │   Due: No due date                              │   │
│  │   Confidence: 78%                               │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Interaction Details
- **Submit button**: Disabled during processing
- **Status indicator**: Shows processing → completed/failed
- **Action items**: Displayed as cards with clear visual hierarchy
- **Error states**: Red text with actionable messages
- **Empty state**: Helpful prompt to paste notes

## Technical Design

### Architecture
```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │────1───▶│     API      │────2───▶│   Temporal   │
│  (React/TS)  │         │  (Supabase)  │         │   Workflow   │
└──────────────┘         └──────────────┘         └──────┬───────┘
       ▲                        ▲                          │
       │                        │                          │3
       │                        │                          ▼
       │                        │                  ┌──────────────┐
       │                        │                  │  AI Model    │
       │                        │                  │ Azure/Bedrock│
       │                        │                  └──────┬───────┘
       │                        │                          │
       │                        └──────────4───────────────┘
       │                                   (Save results)
       │
       └────────────────5─────────────────────────────────┘
                   (Display results)
```

Flow:
1. Frontend submits notes to API endpoint
2. API starts Temporal workflow
3. Workflow activity calls AI model
4. Workflow saves extraction + action items to DB
5. Frontend polls/fetches results

### API Endpoints

#### POST /api/meeting-notes/extract
Start extraction workflow.

**Request:**
```json
{
  "notes": "Meeting notes text here...",
  "user_id": "uuid" 
}
```

**Response:**
```json
{
  "extraction_run_id": "uuid",
  "status": "processing",
  "created_at": "2026-07-07T10:30:00Z"
}
```

#### GET /api/meeting-notes/extract/:run_id
Get extraction status and results.

**Response:**
```json
{
  "extraction_run_id": "uuid",
  "status": "completed",
  "action_items": [
    {
      "id": "uuid",
      "description": "Follow up with Sarah on Q4 budget",
      "owner": "John",
      "due_date": "2026-07-15",
      "confidence": 0.92,
      "created_at": "2026-07-07T10:30:15Z"
    }
  ],
  "error_message": null,
  "completed_at": "2026-07-07T10:30:15Z"
}
```

### Database Schema

#### New Tables

```sql
-- Meeting notes submissions
CREATE TABLE meeting_notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID, -- Optional: link to user if auth exists
  notes_text TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Extraction runs (workflow executions)
CREATE TABLE extraction_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_notes_id UUID NOT NULL REFERENCES meeting_notes(id) ON DELETE CASCADE,
  workflow_id TEXT NOT NULL, -- Temporal workflow ID
  status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'failed')),
  model_provider TEXT, -- 'azure' or 'bedrock'
  model_name TEXT,
  error_message TEXT,
  raw_model_response JSONB,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Extracted action items
CREATE TABLE action_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  extraction_run_id UUID NOT NULL REFERENCES extraction_runs(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  owner TEXT, -- Can be NULL (Unassigned)
  due_date DATE, -- Can be NULL
  confidence NUMERIC(3, 2), -- 0.00 to 1.00
  metadata JSONB, -- Additional context
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_extraction_runs_meeting_notes_id ON extraction_runs(meeting_notes_id);
CREATE INDEX idx_extraction_runs_status ON extraction_runs(status);
CREATE INDEX idx_action_items_extraction_run_id ON action_items(extraction_run_id);
```

### Security Considerations
- **Authentication**: Enforce user authentication for submitting notes
- **Authorization**: Users can only see their own extraction runs
- **Input validation**: Sanitize/validate meeting notes (max length, no scripts)
- **Data privacy**: Meeting notes may contain sensitive data - encrypt at rest
- **Rate limiting**: Limit extraction requests per user (e.g., 10/hour)
- **Model API keys**: Store in env vars, never in code

### Performance Considerations
- **Caching**: Cache model responses for identical notes (optional)
- **Database indexes**: On meeting_notes_id, extraction_run_id, status
- **Async processing**: Use Temporal to avoid blocking requests
- **Model timeout**: Set 30-second timeout on model calls
- **Pagination**: If many action items, paginate results

## Implementation Plan

### Temporal Workflow Shape

**Workflow**: `ExtractMeetingActionItemsWorkflow`

**Activities**:
1. `validate_meeting_notes_input` - Check notes length, format
2. `call_model_for_action_item_extraction` - Invoke Azure/Bedrock model
3. `validate_and_normalize_action_items` - Validate JSON schema, normalize data
4. `persist_extraction_run_and_tasks` - Save to Supabase
5. `handle_extraction_error` - Log and store error details

**Workflow Logic**:
```python
async def run(self, notes: str, meeting_notes_id: str):
    # 1. Validate input
    await workflow.execute_activity(validate_meeting_notes_input, args=[notes])
    
    # 2. Call model with retry
    raw_response = await workflow.execute_activity(
        call_model_for_action_item_extraction,
        args=[notes],
        retry_policy=RetryPolicy(maximum_attempts=3),
        start_to_close_timeout=timedelta(seconds=30)
    )
    
    # 3. Validate and normalize
    action_items = await workflow.execute_activity(
        validate_and_normalize_action_items,
        args=[raw_response]
    )
    
    # 4. Persist results
    extraction_run_id = await workflow.execute_activity(
        persist_extraction_run_and_tasks,
        args=[meeting_notes_id, action_items, raw_response]
    )
    
    return {"extraction_run_id": extraction_run_id, "status": "completed"}
```

**Error Handling**:
- Model call failure → Retry 3 times → Mark as failed
- Invalid JSON → Log raw response → Mark as failed
- Timeout → Mark as failed with timeout message
- All errors stored in extraction_runs.error_message

**Idempotency**:
- Each workflow has unique ID based on meeting_notes_id
- Retry on same notes creates new extraction_run record

### Phases

#### Phase 1: Foundation (This Implementation)
- [ ] Database migrations (meeting_notes, extraction_runs, action_items)
- [ ] Model provider abstraction (Azure + Bedrock)
- [ ] Temporal workflow + activities
- [ ] Basic unit tests

#### Phase 2: Integration (This Implementation)
- [ ] Frontend component (notes input + results display)
- [ ] API endpoints or server actions
- [ ] Integration with Supabase
- [ ] E2E workflow test

#### Phase 3: Polish (This Implementation)
- [ ] Error handling and display
- [ ] Loading states
- [ ] Confidence scores
- [ ] Documentation

### Dependencies
- Existing Supabase + Temporal infrastructure
- Azure OpenAI or AWS Bedrock account + API access
- Environment variables configured

### Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Model API downtime | High | Medium | Retry logic, graceful error messages |
| Model returns invalid JSON | Medium | Low | Strict validation, error recording |
| Extraction takes too long | Medium | Low | 30s timeout, async processing |
| Hallucinated owners/dates | High | Medium | Prompt engineering, validation logic |
| Secrets leaked to git | High | Low | Use env vars, .env.example only |

## Testing Strategy

### Unit Tests
- Input validation (empty, too long, special chars)
- JSON schema validation
- Normalization logic (handle NULL owner/date)
- Model client initialization
- Error message formatting

### Integration Tests
- Temporal workflow execution
- Model call with mock response
- Database persistence
- API endpoint responses

### E2E Tests
- Submit notes → workflow starts
- Workflow completes → results in DB
- Frontend displays results
- Error flow (model failure)

### Edge Cases to Test
- Notes with no action items
- Action items without owner
- Action items without due date
- Model returns invalid JSON
- Model returns empty array
- Very long meeting notes (>10k chars)
- Special characters in notes

## Documentation

### User Documentation
- [ ] How to use the feature (paste notes, submit, view results)
- [ ] What to expect (processing time, accuracy)
- [ ] How to interpret results (confidence scores)

### Developer Documentation
- [ ] Model provider setup (Azure vs Bedrock)
- [ ] Environment variable configuration
- [ ] Workflow architecture
- [ ] Adding new model providers

## Rollout Plan

### Feature Flags
- Flag: `meeting_notes_extraction_enabled`
- Rollout: Internal testing → Beta users → General availability

### Monitoring
- Extraction success rate
- Average processing time
- Model API error rate
- User adoption rate

### Rollback Plan
1. Disable feature flag
2. Database tables remain (no rollback needed)
3. Investigate and fix issues

## Open Questions
- [ ] Should we support editing extracted action items before saving?
- [ ] Do we need multi-user collaboration on the same notes?
- [ ] Should we integrate with calendar for due dates?

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-07 | Use Temporal for orchestration | Need retry logic, observability, async processing |
| 2026-07-07 | Support Azure + Bedrock | Team has both, need flexibility |
| 2026-07-07 | No hallucination | Show "Unassigned" / "No due date" rather than guess |

## References
- [Temporal Python SDK](https://docs.temporal.io/develop/python)
- [Azure OpenAI API](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [AWS Bedrock](https://docs.aws.amazon.com/bedrock/)

## Approval

### Sign-off Required
- [ ] Product Manager
- [ ] Engineering Lead
- [ ] Security Team

### Approval Date
TBD
