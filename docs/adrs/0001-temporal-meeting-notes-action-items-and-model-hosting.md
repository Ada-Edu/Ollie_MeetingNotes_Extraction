# ADR-0001: Temporal Workflow for Meeting Notes Action Item Extraction with Multi-Provider Model Support

- **Status:** Accepted
- **Date:** 2026-07-07
- **Deciders:** Development Team
- **Supersedes / Superseded by:** N/A (initial ADR for this feature)

## Context

We need to extract actionable tasks from unstructured meeting notes using AI models. The system must handle async processing, model failures, retries, and persistence while providing users with status feedback and extracted results.

### Requirements
1. **Async Processing**: Model calls can take 5-30 seconds; cannot block user requests
2. **Reliability**: Must handle transient failures (model API timeouts, rate limits)
3. **Observability**: Team needs to see extraction status, debug failures, and monitor success rates
4. **Auditability**: Record every extraction attempt with inputs, outputs, and errors
5. **Model Flexibility**: Team has access to both Azure OpenAI and AWS Bedrock; need to support both
6. **No Hallucination**: If model is uncertain about owner or due date, show "Unassigned"/"No due date" rather than guessing

### Constraints
- Existing infrastructure: Supabase (PostgreSQL), Temporal, React frontend
- Must use team's own model endpoints (Azure OpenAI or Bedrock)
- Cannot commit secrets to git
- Must integrate with existing codebase patterns

### Technical Factors
- Temporal already deployed and operational
- Supabase client patterns already established
- Frontend uses TanStack Query for async state
- Python-based Temporal worker

## Decision

**We use a Temporal workflow to orchestrate meeting notes extraction through a provider-agnostic model client abstraction.**

### Key Decisions

1. **Orchestration**: Temporal workflow (`ExtractMeetingActionItemsWorkflow`)
   - Coordinates validation → model call → normalization → persistence
   - Built-in retry policies for transient failures
   - Observable execution history in Temporal UI
   - Durable state survives worker restarts

2. **Model Provider Abstraction**: Provider factory pattern
   - Abstract `BaseModelClient` interface
   - Concrete implementations: `AzureModelClient`, `BedrockModelClient`
   - Factory selects provider based on `MODEL_PROVIDER` env var
   - Easy to add new providers (e.g., Vertex AI, Anthropic direct)

3. **Error Handling**: Explicit failure recording
   - Validation errors → fail fast (no model call)
   - Model API errors → retry 3x with exponential backoff
   - Invalid JSON → record failure with raw response
   - All errors stored in `extraction_runs` table with status='failed'

4. **Data Model**: Three tables
   - `meeting_notes`: User input
   - `extraction_runs`: Workflow executions with status tracking
   - `action_items`: Extracted tasks linked to extraction run

5. **No Hallucination Strategy**: Prompt engineering + validation
   - Prompt explicitly instructs: "Do NOT guess; omit field if unclear"
   - Validation normalizes: `owner=null` → "Unassigned", `due_date=null` → "No due date"
   - UI displays these states clearly

## Consequences

### Benefits (What Becomes Easier)
✅ **Reliability**: Automatic retries on transient failures  
✅ **Observability**: Every extraction visible in Temporal UI with full history  
✅ **Auditability**: Complete record of inputs, outputs, errors in database  
✅ **Async UX**: User gets immediate feedback; results appear when ready  
✅ **Testability**: Workflow and activities testable in isolation  
✅ **Provider Flexibility**: Switch between Azure/Bedrock via env var; add new providers easily  
✅ **Error Transparency**: Users see meaningful error messages, not generic failures  
✅ **Debugging**: Raw model responses stored for post-mortem analysis  

### Trade-offs (What Becomes Harder)
⚠️ **Complexity**: More moving parts than direct model call  
⚠️ **Latency**: Temporal adds ~100-300ms overhead vs direct API call  
⚠️ **Infrastructure**: Requires Temporal server + worker running  
⚠️ **Local Development**: Need Temporal running locally or use test server  
⚠️ **Workflow Versioning**: Changes to workflow require careful migration  

### New Obligations
📋 **Operational Burden**:
- Monitor Temporal worker health
- Set up alerts for failed extraction runs
- Monitor model API quota usage
- Rotate model API keys securely

📋 **Follow-up Work**:
- Implement Bedrock client (Phase 2)
- Add confidence score display in UI
- Set up Temporal dashboard monitoring
- Document model provider setup for team

## Alternatives Considered

### Alternative 1: Direct Frontend → Model API Call
**Rejected**: No retry logic, blocks UI, no audit trail, credentials exposed to frontend

**Why rejected**:
- Model calls can fail or timeout; frontend has no built-in retry
- 5-30 second blocking call = terrible UX
- Credentials must be frontend-accessible (security risk)
- No record of failed attempts for debugging

### Alternative 2: Backend API Single Call (No Temporal)
**Rejected**: No durable retry, limited observability, harder to debug failures

**Example**:
```
POST /api/extract-action-items
  → Call model directly
  → Save to DB
  → Return results
```

**Why rejected**:
- If model call fails mid-execution, request fails (no retry)
- No workflow state if server crashes
- Harder to track "in-progress" vs "failed" vs "completed"
- Limited visibility into where failures occur
- Complex to implement timeout handling

### Alternative 3: Queue-Based (e.g., Celery, BullMQ)
**Not rejected, but Temporal is superior**

**Why Temporal wins**:
- Temporal provides workflow state visibility out-of-the-box
- Built-in retry policies with exponential backoff
- Child workflows and signals for future features (e.g., approval flow)
- First-class support for long-running workflows
- Better debugging with Temporal UI
- Team already has Temporal deployed

### Alternative 4: Serverless Function (e.g., AWS Lambda, Supabase Edge Function)
**Rejected**: Timeout limits (typically 5-15min max), no built-in workflow orchestration

**Why rejected**:
- Lambda/Edge Function max execution time constraints
- Have to build retry logic manually
- No workflow state dashboard
- Harder to implement complex multi-step logic

## Evidence

### Files Created/Modified
- **Spec**: `docs/specs/meeting-notes-action-items.md`
- **Plan**: `docs/plans/meeting-notes-action-items-plan.md`
- **ADR**: `docs/adrs/0001-temporal-meeting-notes-action-items-and-model-hosting.md` (this file)

### Database Schema
- **Migration**: `supabase/migrations/20260707000000_meeting_notes_extraction.sql`
  - Tables: `meeting_notes`, `extraction_runs`, `action_items`
  - Indexes: `idx_extraction_runs_meeting_notes_id`, `idx_extraction_runs_status`, `idx_action_items_extraction_run_id`

### Temporal Implementation
- **Workflow**: `temporal/src/workflows/meeting_notes_extraction.py`
  - Workflow: `ExtractMeetingActionItemsWorkflow`
  - Timeout: 30s for model call
  - Retry: 3 attempts with exponential backoff
- **Activities**: `temporal/src/activities/meeting_notes.py`
  - `validate_meeting_notes_input`
  - `call_model_for_action_item_extraction`
  - `persist_extraction_results`
  - `record_extraction_failure`

### Model Provider Abstraction
- **Interface**: `temporal/src/model_client/base.py` - `BaseModelClient` ABC
- **Implementations**:
  - `temporal/src/model_client/azure_client.py` - Azure OpenAI via `openai` SDK
  - `temporal/src/model_client/bedrock_client.py` - AWS Bedrock via `boto3`
- **Factory**: `temporal/src/model_client/factory.py` - `get_model_client()`
- **Config**: `MODEL_PROVIDER` env var determines which client to use

### Prompt Strategy
- **File**: `temporal/src/model_client/prompts.py`
- **Approach**: Explicit instructions to avoid hallucination
- **JSON Schema**: Defined in system prompt for consistent model output

### Frontend Integration
- **Page**: `frontend/src/pages/MeetingNotesExtraction.tsx`
- **Hooks**: `frontend/src/lib/hooks/useMeetingNotes.ts`
- **Flow**: Submit notes → Poll extraction status → Display results

### Configuration
- **Env vars**: `.env.example` documents required variables
  - `MODEL_PROVIDER=azure|bedrock`
  - Azure: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`
  - Bedrock: `AWS_REGION`, `BEDROCK_MODEL_ID`, AWS credentials
- **Dependencies**: `temporal/pyproject.toml` adds `openai`, `boto3`

### Testing
- **Unit**: `temporal/tests/test_model_client.py` - Model client tests with mocked APIs
- **Integration**: `temporal/tests/test_meeting_notes_workflow.py` - Full workflow execution
- **Frontend**: `frontend/src/__tests__/MeetingNotesExtraction.test.tsx` - Component tests

## Monitoring and Success Criteria

### Metrics to Track
- **Success Rate**: % of extraction_runs with status='completed'
- **Processing Time**: Average time from workflow start to completion
- **Model API Errors**: Count of model API failures per hour
- **Retry Rate**: % of workflows that required retries

### Alerts
- Extraction success rate < 90% for 1 hour
- Model API error rate > 10/hour
- Temporal worker down
- Average processing time > 60 seconds

### Rollback Plan
1. Disable feature flag `meeting_notes_extraction_enabled` (if implemented)
2. Database tables remain (no data loss)
3. Investigate failures in Temporal UI
4. Review raw model responses in `extraction_runs.raw_model_response`
5. Fix issues and re-enable

## Future Considerations

### Possible Enhancements
1. **Real-time Status Updates**: WebSocket or Server-Sent Events instead of polling
2. **Human-in-the-Loop**: Approval step before saving action items
3. **Multi-Language Support**: Detect language and route to appropriate model
4. **Batch Processing**: Extract action items from multiple meetings at once
5. **Integration**: Export to Jira, Asana, Google Calendar
6. **Confidence Threshold**: Auto-flag low-confidence items for review
7. **Model Comparison**: Run multiple models in parallel and compare results

### Technical Debt
- Workflow triggering mechanism not fully designed (frontend → Temporal gap)
- May need Supabase Edge Function or separate API endpoint
- Bedrock client implementation deferred to Phase 2
- Frontend routing integration needs TanStack Router setup

### Questions for Future
- Should we cache identical notes to avoid redundant model calls?
- Do we need versioning for action items (user edits after extraction)?
- Should we support incremental extraction (add notes → re-extract)?
- Do we want to store raw meeting notes long-term or only extraction results?

---

## Approval & Review

**Approved by**: Development Team  
**Date**: 2026-07-07

**Reviewed by**:
- [ ] Tech Lead
- [ ] Security Team (for API key handling)
- [ ] Product Manager

**Next Review Date**: After feature launch (30 days post-deployment)

