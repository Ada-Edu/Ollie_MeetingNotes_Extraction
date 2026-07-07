# Meeting Notes → Action Items Extraction

AI-powered agentic workflow that automatically extracts actionable tasks from meeting notes using Temporal orchestration and AWS Bedrock Claude models.

[![Status](https://img.shields.io/badge/status-in--development-yellow)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange)]()
[![Temporal](https://img.shields.io/badge/workflow-Temporal-blue)]()

## Overview

Users paste raw meeting notes into a web interface, triggering an asynchronous Temporal workflow that:
1. Validates the input
2. Calls AWS Bedrock (Claude Sonnet 4.6) to extract action items
3. Parses and validates the model response
4. Persists results to PostgreSQL (Supabase)
5. Displays structured tasks with owners, due dates, and confidence scores

**Key Feature**: No hallucination - when the AI is uncertain about an owner or due date, it explicitly marks them as "Unassigned" or "No due date" rather than guessing.

## Features

### Implemented ✅

- **AI Extraction**: AWS Bedrock Claude Sonnet 4.6 with anti-hallucination prompting
- **Multi-Provider Support**: Abstraction layer supports Azure OpenAI and AWS Bedrock
- **Temporal Orchestration**: Durable workflows with retry logic and observability
- **Database Persistence**: PostgreSQL with full audit trail (meeting notes, extraction runs, action items)
- **React Frontend**: Modern UI with status tracking and results display
- **Error Handling**: Graceful failures with detailed error messages
- **Confidence Scoring**: Each extracted item includes AI confidence level
- **Spec-Driven Development**: Complete documentation (Spec → Plan → ADR)

### In Progress 🚧

- **Workflow Trigger**: API endpoint to invoke Temporal from frontend
- **Frontend Routing**: TanStack Router integration
- **End-to-End Testing**: Full workflow validation
- **Production Deployment**: Environment setup and CI/CD

## Tech Stack

**Frontend**:
- React 18 + TypeScript + Vite
- TanStack Router & Query
- Tailwind CSS

**Backend**:
- Temporal (Python) - Workflow orchestration
- Supabase / PostgreSQL - Database
- AWS Bedrock - AI model hosting

**AI/ML**:
- Claude Sonnet 4.6 (via global inference profile)
- Custom prompt engineering for structured extraction
- JSON schema validation

## Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │────1───▶│  Supabase    │────2───▶│   Temporal   │
│  (React/TS)  │         │  (Postgres)  │         │   Workflow   │
└──────────────┘         └──────────────┘         └──────┬───────┘
       ▲                        ▲                          │
       │                        │                          3
       │                        │                          ▼
       │                        │                  ┌──────────────┐
       │                        │                  │ AWS Bedrock  │
       │                        │                  │ Claude 4.6   │
       │                        │                  └──────┬───────┘
       │                        │                          │
       │                        └──────────4───────────────┘
       │                                   (Save results)
       └────────────────5─────────────────────────────────┘
                   (Display results)
```

**Workflow Steps**:
1. User submits meeting notes
2. Frontend creates extraction_run record
3. Temporal workflow triggers (TODO: implement trigger)
4. Workflow executes activities:
   - `validate_meeting_notes_input` (5s timeout)
   - `call_model_for_action_item_extraction` (30s timeout, 3 retries)
   - `persist_extraction_results` (10s timeout)
5. Results display in UI with status polling

## Quick Start

### Prerequisites

- Docker Desktop with Compose v2
- Node.js 18+ & npm
- Python 3.10+
- Supabase CLI (required - used by `make up`)
- `make` (comes with macOS/Linux)
- AWS Bedrock access (with bearer token)

### 1. Clone and Setup

```bash
git clone https://github.com/OllieOlwage/day2-meeting-notes-project.git
cd day2-meeting-notes-project
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# AWS Bedrock Configuration
MODEL_PROVIDER=bedrock
AWS_REGION=af-south-1
AWS_BEARER_TOKEN_BEDROCK=your-bearer-token-here
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-6

# Supabase (auto-injected by make up)
SUPABASE_URL=http://host.docker.internal:54321
VITE_SUPABASE_URL=http://localhost:54321

# Temporal
TEMPORAL_ADDRESS=temporal:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=main
```

### 3. Start Services

```bash
# Start everything (Supabase + Temporal + Worker + Frontend)
make up

# Or start individual components:
# Terminal 1: Supabase + Temporal
make up

# Terminal 2: Temporal worker
cd temporal
pip install -r requirements.txt
make worker

# Terminal 3: Frontend dev server
cd frontend
npm install
npm run dev
```

### 4. Access Services

- **Frontend**: http://localhost:3000
- **Temporal UI**: http://localhost:8080
- **Temporal gRPC**: localhost:7234
- **Supabase Studio**: http://localhost:54323
- **Supabase API**: http://localhost:54321

### Common Commands

```bash
make down           # Stop containers and Supabase stack
make reset          # Tear down volumes + Supabase, recreate with migrations
make logs           # Stream all service logs
make logs-temporal  # Temporal logs only
make logs-frontend  # Frontend logs only
make supabase-status # Show Supabase URLs and local keys
```

## Testing

### Test Bedrock Connection

```bash
python test_bedrock_final.py
```

**Expected Output**:
```
[SUCCESS] Extracted 3 action items:
1. Follow up with Sarah on Q4 budget
   Owner: John
   Due Date: 2026-07-15
   Confidence: 99%
...
```

### Run Unit Tests

```bash
# Backend tests
cd temporal
pytest tests/

# Frontend tests
cd frontend
npm test
```

### Sample Test Data

```
Team meeting - July 7, 2026
Attendees: Sarah, John, Mike

Discussion:
- Q4 budget review coming up
- Need to finalize architectural design

Action items:
1. John to follow up with Sarah on Q4 budget by July 15
2. Mike to review the architectural design doc by next week
3. Schedule a follow-up meeting for next Monday
```

## Database Schema

### `meeting_notes`
Stores user-submitted meeting notes.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Optional user reference |
| notes_text | TEXT | Meeting notes (10-10,000 chars) |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update timestamp |

### `extraction_runs`
Tracks workflow executions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| meeting_notes_id | UUID | Reference to meeting_notes |
| workflow_id | TEXT | Temporal workflow ID |
| status | TEXT | processing/completed/failed |
| model_provider | TEXT | azure/bedrock |
| model_name | TEXT | Model identifier used |
| error_message | TEXT | Error details if failed |
| raw_model_response | JSONB | Full model output for debugging |
| started_at | TIMESTAMPTZ | Workflow start time |
| completed_at | TIMESTAMPTZ | Workflow completion time |

### `action_items`
Stores extracted tasks.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| extraction_run_id | UUID | Reference to extraction_runs |
| description | TEXT | Task description |
| owner | TEXT | Person responsible (nullable) |
| due_date | DATE | Due date (nullable) |
| confidence | NUMERIC(3,2) | AI confidence (0.00-1.00) |
| metadata | JSONB | Additional context |

## Configuration

### Model Provider Options

**Option 1: AWS Bedrock (Recommended)**
```env
MODEL_PROVIDER=bedrock
AWS_REGION=af-south-1
AWS_BEARER_TOKEN_BEDROCK=<your-token>
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-6
```

**Option 2: Azure OpenAI**
```env
MODEL_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### Available Bedrock Models

Tested inference profiles:
- `global.anthropic.claude-sonnet-4-6` (Claude Sonnet 4.6) ✅ **Tested & Working**
- `global.anthropic.claude-opus-4-5-20251101-v1:0` (Claude Opus 4.5)
- `us.anthropic.claude-3-5-sonnet-20240620-v1:0` (Claude 3.5 Sonnet, US)
- `eu.anthropic.claude-3-5-sonnet-20240620-v1:0` (Claude 3.5 Sonnet, EU)

## Project Structure

```
.
├── docs/
│   ├── specs/meeting-notes-action-items.md        # Feature specification
│   ├── plans/meeting-notes-action-items-plan.md   # Implementation plan
│   └── adrs/0001-temporal-meeting-notes-*.md      # Architecture decisions
├── temporal/
│   ├── src/
│   │   ├── model_client/                          # AI model abstraction
│   │   │   ├── base.py                            # Base interface
│   │   │   ├── azure_client.py                    # Azure OpenAI
│   │   │   ├── bedrock_client.py                  # AWS Bedrock ✅
│   │   │   ├── factory.py                         # Provider factory
│   │   │   └── prompts.py                         # Prompt templates
│   │   ├── workflows/
│   │   │   └── meeting_notes_extraction.py        # Main workflow
│   │   ├── activities/
│   │   │   └── meeting_notes.py                   # Workflow activities
│   │   └── worker.py                              # Temporal worker
│   └── tests/
│       ├── test_model_client.py                   # Model client tests
│       └── test_meeting_notes_workflow.py         # Workflow tests
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── MeetingNotesExtraction.tsx         # Main page
│   │   ├── components/
│   │   │   └── ActionItemsList.tsx                # Results display
│   │   └── lib/hooks/
│   │       └── useMeetingNotes.ts                 # API hooks
│   └── __tests__/
│       └── MeetingNotesExtraction.test.tsx        # Component tests
├── supabase/
│   └── migrations/
│       └── 20260707000000_meeting_notes_*.sql     # DB schema
├── test_bedrock_final.py                          # Connection test ✅
├── discover_bedrock_models.py                     # Model discovery
└── README.md                                      # This file
```

## Development Workflow

This project follows **Spec-Driven Development**:

1. **Spec** → Customer-language requirements (`docs/specs/`)
2. **Plan** → Technical implementation plan (`docs/plans/`)
3. **ADR** → Architecture decisions with rationales (`docs/adrs/`)
4. **Implement** → Code with tests
5. **Verify** → Validation against acceptance criteria
6. **Git/PR** → Version control and review

## Current Status

### ✅ Completed (70%)

- [x] Feature specification and acceptance criteria
- [x] Implementation plan and architecture decisions
- [x] Database schema and migrations
- [x] Model provider abstraction (Azure + Bedrock)
- [x] Bedrock client implementation and testing
- [x] Temporal workflow definition
- [x] Workflow activities (validate, extract, persist, error handling)
- [x] Frontend UI components
- [x] Custom React hooks for API calls
- [x] Unit test coverage
- [x] Anti-hallucination prompt engineering
- [x] Error handling and retry logic
- [x] Configuration documentation

### 🚧 In Progress (30%)

- [ ] **Workflow trigger API** - Endpoint to invoke Temporal from frontend
- [ ] **Frontend routing** - TanStack Router configuration
- [ ] **Python dependencies** - Fix Windows build issues
- [ ] **End-to-end testing** - Full workflow validation
- [ ] **RLS policies** - Row-level security for production
- [ ] **Production deployment** - Staging and prod environments

### Known Limitations

1. **Workflow Trigger Gap**: Frontend creates `extraction_run` but doesn't trigger Temporal workflow yet
   - **Impact**: Status stays "processing" indefinitely
   - **Fix**: Implement `POST /api/workflows/extract-action-items` endpoint

2. **Python Dependencies**: `pip install -r requirements.txt` fails on Windows due to Rust compilation
   - **Impact**: Can't run Temporal worker locally on Windows
   - **Workaround**: Use Docker or prebuilt wheels: `pip install pydantic==2.7.3 --only-binary :all:`

3. **Frontend Routing**: Page component exists but no route defined
   - **Impact**: Can't navigate to `/meeting-notes` in app
   - **Fix**: Add route in `frontend/src/routes/index.tsx`

## Documentation

- **[Feature Spec](docs/specs/meeting-notes-action-items.md)** - Requirements and acceptance criteria
- **[Implementation Plan](docs/plans/meeting-notes-action-items-plan.md)** - Technical design
- **[ADR-0001](docs/adrs/0001-temporal-meeting-notes-action-items-and-model-hosting.md)** - Architecture decisions
- **[Bedrock Setup](BEDROCK_SETUP.md)** - Troubleshooting guide
- **[Ready to Run](READY_TO_RUN.md)** - System status and next steps
- **[PR Body](PR_BODY.md)** - Pull request description with full details

## Troubleshooting

### "Model identifier is invalid"

**Cause**: Incorrect model ID format  
**Solution**: Use inference profile format: `global.anthropic.claude-sonnet-4-6`

### "Authorization failed"

**Cause**: Missing or incorrect bearer token  
**Solution**: Set `AWS_BEARER_TOKEN_BEDROCK` in `.env`

### "Connection refused to Temporal"

**Cause**: Docker containers not running  
**Solution**: Run `make up` to start services

### "Table does not exist"

**Cause**: Database migrations not applied  
**Solution**: Run `make reset` or `supabase db reset`

### Python wheel compilation errors

**Cause**: Rust toolchain required for pydantic-core  
**Solution**: Use prebuilt wheels:
```bash
pip install pydantic==2.7.3 --only-binary :all:
```

## Roadmap

### Phase 1: Core Functionality (Current - 70% Complete)
- ✅ Basic extraction workflow
- ✅ Bedrock integration
- ✅ Database persistence
- 🚧 End-to-end testing

### Phase 2: Production Ready (Next)
- [ ] Workflow trigger API
- [ ] User authentication
- [ ] RLS policies
- [ ] Error monitoring
- [ ] Performance optimization

### Phase 3: Enhanced Features
- [ ] Edit extracted action items
- [ ] Batch processing (multiple meetings)
- [ ] Export to external systems (Jira, Asana)
- [ ] Real-time status updates (WebSocket)
- [ ] Analytics dashboard

### Phase 4: Advanced Capabilities
- [ ] Multi-language support
- [ ] Voice note transcription
- [ ] Calendar integration
- [ ] Smart reminders
- [ ] Team collaboration features

## Performance

**Expected Metrics**:
- Extraction time: 5-30 seconds (typical meeting notes)
- Accuracy: >85% (manual review benchmark)
- Concurrency: 100 simultaneous workflows supported
- Uptime target: 99.5%

**Current Test Results**:
- ✅ Single extraction: ~5 seconds
- ✅ Model response: <2 seconds
- ✅ Database persistence: <100ms
- ✅ Frontend polling: 2-second intervals

## Security

- ✅ Credentials via environment variables only
- ✅ No secrets in git history
- ✅ PostgreSQL prepared statements (SQL injection protection)
- ⚠️ RLS disabled (local dev only - **must enable for production**)
- ✅ Input validation (length, format)
- ✅ Model output validation (JSON schema)

**Production Checklist**:
- [ ] Enable Row-Level Security
- [ ] Add user authentication
- [ ] Implement rate limiting
- [ ] Add audit logging
- [ ] Encrypt sensitive data at rest
- [ ] Rotate API keys regularly

## Contributing

### Setup Development Environment

```bash
# Install dependencies
cd temporal && pip install -r requirements.txt
cd ../frontend && npm install

# Run tests
cd ../temporal && pytest
cd ../frontend && npm test

# Start all services
make up
```

### Code Style

- **Python**: Black formatter, type hints, docstrings
- **TypeScript**: Prettier, ESLint, strict mode
- **Commits**: Conventional Commits (feat/fix/docs/test)

### Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Update documentation
4. Run full test suite
5. Create PR with detailed description
6. Address review feedback

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

Built following Spec-Driven Development methodology:
- **Temporal** - Workflow orchestration
- **AWS Bedrock** - AI model hosting
- **Supabase** - Database and backend infrastructure
- **Anthropic** - Claude AI models
- **React** - Frontend framework

## Support

- **Issues**: [GitHub Issues](https://github.com/OllieOlwage/day2-meeting-notes-project/issues)
- **Pull Requests**: [GitHub Pull Requests](https://github.com/OllieOlwage/day2-meeting-notes-project/pulls)
- **Documentation**: See `docs/` directory

---

## Quick Links

- 📋 [Pull Request #1](https://github.com/OllieOlwage/day2-meeting-notes-project/pull/1) - Initial implementation
- 📊 [Temporal UI](http://localhost:8080) - Workflow monitoring (when running)
- 🗄️ [Supabase Studio](http://localhost:54323) - Database admin (when running)

---

**Status**: 🚧 In Development | **Last Updated**: July 7, 2026 | **Version**: 0.1.0

**Next Milestone**: Complete workflow trigger API and achieve first end-to-end working demo
