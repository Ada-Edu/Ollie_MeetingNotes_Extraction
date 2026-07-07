# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                         │
│                     http://localhost:3000                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ HTTP/WebSocket
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    FRONTEND (Container)                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  React 18 + TypeScript + Vite                          │ │
│  │  - TanStack Router (routing)                           │ │
│  │  - TanStack Query (data fetching)                      │ │
│  │  - Supabase Client (database access)                   │ │
│  │  - Tailwind CSS (styling)                              │ │
│  └────────────────────────────────────────────────────────┘ │
│                          Port: 3000                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ REST API / Realtime
                      │
┌─────────────────────▼───────────────────────────────────────┐
│               SUPABASE (Local via CLI)                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  PostgreSQL 17                                         │ │
│  │  - entities (identity layer)                           │ │
│  │  - entity_versions (SCD2 history)                      │ │
│  │  - relationships_v2 (entity graph)                     │ │
│  │  - fact_types (metric registry)                        │ │
│  │  - entity_facts (current numeric facts)                │ │
│  │  - time_series_points (event stream)                   │ │
│  │  - dim_* tables (dimensions, as needed)                │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  PostgREST (Auto-generated REST API)                   │ │
│  │  - CRUD operations on all tables                       │ │
│  │  - Row-level security (RLS) ready                      │ │
│  │  - Automatic OpenAPI spec                              │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  GoTrue (Authentication - ready to use)                │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Realtime Server (WebSocket subscriptions)             │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Studio (Database management UI)                       │ │
│  │  http://localhost:54323                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                   API Port: 54321                            │
│                   DB Port: 54322                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ HTTP REST API
                      │ (from container)
                      │
┌─────────────────────▼───────────────────────────────────────┐
│           TEMPORAL WORKER (Python Container)                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Python 3.11+ Worker                                   │ │
│  │  - Workflows: Durable business logic                   │ │
│  │  - Activities: Short-lived tasks                       │ │
│  │  - Supabase HTTP Client (httpx)                        │ │
│  │  - Async/await throughout                              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Connects to:                                                │
│  - Temporal Server (workflow coordination)                   │
│  - Supabase API (data persistence)                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ gRPC
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              TEMPORAL SERVER (Container)                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Temporal Server                                       │ │
│  │  - Workflow state management                           │ │
│  │  - Task queue management                               │ │
│  │  - Event history storage                               │ │
│  │  - Retry & timeout handling                            │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Temporal UI                                           │ │
│  │  http://localhost:8080                                 │ │
│  │  - Workflow monitoring                                 │ │
│  │  - Task queue status                                   │ │
│  │  - Event history viewer                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                   gRPC Port: 7234 (external)                 │
│                              7233 (internal)                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ PostgreSQL protocol
                      │
┌─────────────────────▼───────────────────────────────────────┐
│          TEMPORAL DATABASE (Container)                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  PostgreSQL 15                                         │ │
│  │  - Stores workflow state                               │ │
│  │  - Event history                                       │ │
│  │  - Task queue metadata                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                   Port: 5433 (external)                      │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### Frontend Layer

**Technology**: React 18, TypeScript, Vite  
**Purpose**: User interface and interaction

**Key Files**:
- `frontend/src/lib/supabase.ts` - Database client
- `frontend/src/lib/hooks/` - Custom React hooks
- `frontend/src/pages/Dashboard.tsx` - Main dashboard

**Communication**:
- → Supabase API via REST (reads/writes)
- → Supabase Realtime via WebSocket (subscriptions)

### Supabase Layer

**Technology**: PostgreSQL 17, PostgREST, GoTrue  
**Purpose**: Database, API, and authentication

**Key Components**:
1. **PostgreSQL**: Core data storage
2. **PostgREST**: Auto-generated REST API
3. **GoTrue**: Authentication service
4. **Realtime**: WebSocket server for subscriptions
5. **Studio**: Web-based database management

**Key Files**:
- `supabase/config.toml` - Configuration
- `supabase/migrations/*.sql` - Schema definitions
- `supabase/seed.sql` - Initial data

**Communication**:
- ← Frontend via REST/WebSocket
- ← Temporal Worker via HTTP REST

### Temporal Worker Layer

**Technology**: Python 3.11+, Temporalio SDK  
**Purpose**: Execute workflows and activities

**Key Files**:
- `temporal/src/worker.py` - Worker entry point
- `temporal/src/activities/` - Activity definitions
- `temporal/src/workflows/` - Workflow definitions
- `temporal/src/supabase_client.py` - Database integration

**Communication**:
- → Temporal Server via gRPC
- → Supabase API via HTTP REST

### Temporal Server Layer

**Technology**: Temporal.io, Go  
**Purpose**: Workflow orchestration and state management

**Key Components**:
1. **Temporal Server**: Core workflow engine
2. **Temporal UI**: Web-based monitoring
3. **Temporal DB**: State persistence

**Communication**:
- ← Temporal Worker via gRPC
- → Temporal Database for persistence

## Data Flow Patterns

### 1. User Creates Entity (Frontend → Database)

```
User clicks "Create" in browser
    ↓
React component calls createEntity.mutateAsync()
    ↓
Supabase client sends POST /rest/v1/entities
    ↓
PostgREST receives request
    ↓
PostgreSQL INSERT executed
    ↓
Response returns to frontend
    ↓
TanStack Query invalidates cache
    ↓
UI auto-updates with new entity
```

### 2. Workflow Execution (Temporal → Database)

```
Workflow triggered via Temporal client
    ↓
Temporal Server schedules activities
    ↓
Worker picks up activity from task queue
    ↓
Activity executes (Python async function)
    ↓
Supabase HTTP client makes REST call
    ↓
PostgREST processes request
    ↓
PostgreSQL transaction executed
    ↓
Response returns to activity
    ↓
Workflow continues or completes
    ↓
Frontend can query updated data
```

### 3. SCD2 Version Update

```
Client inserts new entity_version row
    ↓
PostgreSQL BEFORE INSERT trigger fires
    ↓
Trigger function queries for current version
    ↓
Updates old version: is_current=false, valid_to=now()
    ↓
New version inserted with is_current=true
    ↓
Unique index ensures only one current version
    ↓
Historical versions preserved
```

### 4. Real-time Subscription

```
Frontend subscribes to entity changes
    ↓
WebSocket connection to Realtime server
    ↓
Database change occurs (INSERT/UPDATE/DELETE)
    ↓
PostgreSQL replication log monitored
    ↓
Realtime server broadcasts to subscribers
    ↓
Frontend receives event
    ↓
React Query updates cached data
    ↓
UI reflects change instantly
```

## Network Topology

```
┌───────────────────────────────────────────────────────┐
│                    Docker Network                     │
│                                                       │
│  ┌──────────────┐         ┌──────────────┐          │
│  │   Frontend   │────────▶│   Temporal   │          │
│  │  (port 3000) │         │  (port 7233) │          │
│  └──────────────┘         └──────┬───────┘          │
│         │                        │                   │
│         │                        │                   │
│         ▼                        ▼                   │
│  ┌──────────────┐         ┌──────────────┐          │
│  │ Temporal DB  │         │Temporal Worker│          │
│  │  (port 5433) │         │  (no ports)  │          │
│  └──────────────┘         └──────┬───────┘          │
│                                   │                   │
│                                   │                   │
└───────────────────────────────────┼───────────────────┘
                                    │
                       host.docker.internal
                                    │
┌───────────────────────────────────▼───────────────────┐
│                    Host Machine                       │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  Supabase (via CLI)                          │   │
│  │  - API:    localhost:54321                   │   │
│  │  - DB:     localhost:54322                   │   │
│  │  - Studio: localhost:54323                   │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**Key Network Details**:
- Frontend and Temporal Worker run **inside Docker**
- Supabase runs **on host** via CLI (separate Docker network)
- Worker uses `host.docker.internal` to reach Supabase
- Frontend browser uses `localhost` to reach Supabase
- All services communicate via HTTP/gRPC

## Deployment Considerations

### Local Development
- All services run on single machine
- Supabase via CLI for ease of migration management
- Volumes persist database data

### Production Deployment

**Supabase**:
- Option 1: Supabase Cloud (managed)
- Option 2: Self-hosted on Kubernetes
- Update URLs in environment variables

**Temporal**:
- Option 1: Temporal Cloud (managed)
- Option 2: Self-hosted cluster
- Scale workers horizontally

**Frontend**:
- Build with `npm run build`
- Deploy to Vercel, Netlify, or CDN
- Set production environment variables

**Database**:
- Supabase includes PostgreSQL
- Automatic backups on Supabase Cloud
- Connection pooling via Supavisor

## Security Architecture

### Authentication Flow (Ready to Implement)

```
User Login Request
    ↓
GoTrue (Supabase Auth)
    ↓
JWT Token Generated
    ↓
Frontend stores token
    ↓
All requests include: Authorization: Bearer <token>
    ↓
PostgREST validates JWT
    ↓
Row-Level Security (RLS) enforced
    ↓
User sees only their data
```

### Current Security State

✅ **Implemented**:
- Environment variables for secrets
- Service role key separate from anon key
- Docker network isolation

⚠️ **To Implement**:
- Row-level security (RLS) policies
- User authentication flows
- API rate limiting
- CORS configuration for production

## Scalability

### Horizontal Scaling

**Frontend**: Stateless, scales easily
- Add more container instances
- Use load balancer

**Temporal Workers**: Designed for horizontal scaling
- Add more worker processes
- Share same task queue
- Automatic work distribution

**Database**: Vertical scaling first
- Upgrade PostgreSQL instance
- Add read replicas for queries
- Connection pooling

**Temporal Server**: Cluster-ready
- Multi-node cluster
- Shared database
- High availability

### Performance Optimization

**Frontend**:
- Code splitting (Vite handles automatically)
- TanStack Query caching
- Lazy loading routes

**Database**:
- Indexes on foreign keys (already included)
- Query optimization via Studio
- Materialized views for complex queries

**Temporal**:
- Activity retries with exponential backoff
- Batch operations where possible
- Workflow versioning for updates

## Monitoring & Observability

### Built-in Monitoring

✅ **Temporal UI** (http://localhost:8080)
- Workflow execution status
- Activity logs
- Error tracking
- Performance metrics

✅ **Supabase Studio** (http://localhost:54323)
- Database query performance
- Table statistics
- Log viewer
- API usage

### Logging

**Frontend**: Browser console + error boundaries  
**Temporal**: Python logging to stdout  
**Supabase**: PostgREST logs + PostgreSQL logs

**View Logs**:
```bash
docker compose logs -f temporal-worker
docker compose logs -f frontend
```

## Technology Stack Summary

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend** | React | 18.3 | UI framework |
| | TypeScript | 5.5 | Type safety |
| | Vite | 5.3 | Build tool |
| | TanStack Query | 5.90 | Data fetching |
| | TanStack Router | 1.139 | Routing |
| | Tailwind CSS | 4.1 | Styling |
| **Backend** | PostgreSQL | 17 | Database |
| | PostgREST | (via Supabase) | REST API |
| | Supabase | Latest | Backend platform |
| **Workflows** | Temporal | 1.21 | Orchestration |
| | Temporalio SDK | 1.5 | Python SDK |
| | Python | 3.11+ | Worker language |
| **Infrastructure** | Docker | Latest | Containerization |
| | Docker Compose | v2 | Orchestration |

---

This architecture is designed for:
- ✅ Rapid development
- ✅ Easy local testing
- ✅ Production deployment
- ✅ Horizontal scaling
- ✅ Maintainability

**Ready to build on this foundation!**
