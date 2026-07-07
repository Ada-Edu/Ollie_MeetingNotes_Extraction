# Project Setup Guide

This guide walks you through setting up the full backend and frontend stack.

## Prerequisites

Before starting, ensure you have:
- ✅ Docker Desktop installed and **running**
- ✅ Node.js 18+ installed
- ✅ Supabase CLI installed (already confirmed)
- ✅ Python 3.11+ for Temporal worker
- ✅ Make utility (Git Bash includes it)

## Step-by-Step Setup

### 1. Start Docker Desktop

**IMPORTANT:** Docker Desktop must be running before proceeding.

```bash
# Check if Docker is running:
docker ps
```

If you see an error, start Docker Desktop and wait for it to fully initialize.

### 2. Initialize Supabase Backend

```bash
# Start Supabase local stack (Postgres + API + Auth + Studio)
supabase start

# This will:
# - Pull required Docker images
# - Start PostgreSQL database
# - Apply migrations from supabase/migrations/
# - Run seed data from supabase/seed.sql
# - Start Studio UI at http://localhost:54323
```

### 3. Get Supabase Credentials

After `supabase start` completes, you'll see output with URLs and keys:

```bash
# View status and credentials:
supabase status

# Expected output includes:
# - API URL: http://localhost:54321
# - DB URL: postgresql://postgres:postgres@localhost:54322/postgres
# - Studio URL: http://localhost:54323
# - anon key: eyJ... (copy this)
# - service_role key: eyJ... (copy this)
```

### 4. Update Environment Variables

Edit `.env` and update these values with the **actual keys** from `supabase status`:

```bash
# Update these lines in .env:
SUPABASE_ANON_KEY=<paste anon key from supabase status>
SUPABASE_SERVICE_ROLE_KEY=<paste service_role key>
VITE_SUPABASE_ANON_KEY=<paste anon key>
```

Or use the automated script:

```bash
make supabase-status
```

### 5. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 6. Install Temporal Worker Dependencies

```bash
cd temporal
pip install -r requirements.txt
# Or if you use virtual environments:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 7. Start All Services

#### Option A: Using Make (Recommended)

```bash
# Start everything (production mode)
make up

# OR start with live-reload for development
USE_DEV=1 make up
```

#### Option B: Manual Docker Compose

```bash
# Production mode
docker compose up

# Development mode with live reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 8. Verify Services

Open these URLs in your browser:

- **Frontend**: http://localhost:3000
- **Supabase Studio**: http://localhost:54323
- **Temporal UI**: http://localhost:8080
- **Supabase API**: http://localhost:54321

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Browser                           │
│                                                     │
│  Frontend (React + Vite) - http://localhost:3000   │
│  │                                                  │
│  └─> Supabase Client ──────────────────────┐       │
└──────────────────────────────────────────────┼──────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────┐
│              Supabase (localhost:54321)             │
│  ┌─────────────────────────────────────────────┐   │
│  │  PostgreSQL Database (port 54322)           │   │
│  │  - entities                                 │   │
│  │  - entity_versions (SCD2)                   │   │
│  │  - relationships_v2                         │   │
│  │  - fact_types                               │   │
│  │  - entity_facts                             │   │
│  │  - time_series_points                       │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  REST API + Auth + Realtime + Storage               │
└─────────────────────────────────────────────────────┘
                    ▲
                    │
┌───────────────────┼─────────────────────────────────┐
│  Docker Network   │                                 │
│                   │                                 │
│  ┌────────────────▼──────────────┐                 │
│  │  Temporal Worker (Python)     │                 │
│  │  - Workflows                  │                 │
│  │  - Activities                 │                 │
│  │  - Supabase integration       │                 │
│  └───────────────┬───────────────┘                 │
│                  │                                  │
│  ┌───────────────▼───────────────┐                 │
│  │  Temporal Server               │                 │
│  │  - Workflow engine             │                 │
│  │  - UI: http://localhost:8080   │                 │
│  └────────────────────────────────┘                 │
└─────────────────────────────────────────────────────┘
```

## Database Schema

### Core Entity Model

- **entities**: Identity layer for any business object
  - `entity_type`: Type of entity (e.g., 'user', 'company', 'room')
  - `source_record_id`: Optional link to upstream system

- **entity_versions**: SCD2 (Slowly Changing Dimension Type 2) snapshots
  - Tracks historical changes to entity data
  - JSONB `data` column for flexible schema
  - `is_current` flag for active version

- **relationships_v2**: Typed graph edges between entities
  - Parent-child relationships with metadata
  - Historical tracking with `is_current` flag

### Analytics Foundation

- **fact_types**: Registry of all metrics/measurements
  - Defines what can be measured
  - Units and descriptions

- **entity_facts**: Current numeric facts about entities
  - Numeric-only values
  - Optional dimension references
  - One current fact per (entity, fact_type, dimension)

- **time_series_points**: Event stream
  - JSONB payload for flexible event data
  - Historical measurements
  - Used to derive entity_facts

## Common Commands

```bash
# View all service logs
make logs

# View specific service logs
make logs-temporal
make logs-frontend

# Stop all services
make down

# Reset database (drops all data and reapplies migrations)
make reset

# Check Supabase status and credentials
make supabase-status

# Run frontend tests
cd frontend && npm test

# Access PostgreSQL directly
psql postgresql://postgres:postgres@localhost:54322/postgres
```

## Troubleshooting

### Docker not running
```
Error: failed to connect to the docker API
```
**Solution**: Start Docker Desktop and wait for it to fully initialize.

### Port already in use
```
Error: port 54321 already in use
```
**Solution**: Check if another Supabase instance is running:
```bash
supabase stop
# Then restart
supabase start
```

### Frontend can't connect to Supabase
**Solution**: Verify environment variables are set correctly:
```bash
# Check that VITE_SUPABASE_ANON_KEY is set in .env
cat .env | grep VITE_SUPABASE
```

### Migrations not applying
**Solution**: Reset the database:
```bash
supabase db reset
```

## Next Steps

1. **Explore the Database**: Open Supabase Studio at http://localhost:54323
2. **Review Documentation**: 
   - `Guide_for_agents_using_supabase_template.md` - Implementation patterns
   - `DATABASE.md` - Schema details
   - `Generalisable_schema.md` - Data modeling guide
3. **Start Building**: Add your domain-specific entities and facts
4. **Create Workflows**: Implement Temporal workflows in `temporal/src/`

## Project Structure

```
.
├── frontend/              # React + Vite frontend
│   ├── src/
│   │   ├── engine/       # JSON-driven UI engine
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   └── lib/          # Utilities (Supabase client)
│   └── package.json
│
├── supabase/             # Supabase configuration
│   ├── config.toml       # Supabase CLI config
│   ├── migrations/       # Database migrations
│   │   ├── 20251202090000_core_entity_model.sql
│   │   └── 20251203090000_analytics_foundation.sql
│   └── seed.sql          # Seed data
│
├── temporal/             # Temporal worker (Python)
│   ├── src/              # Worker implementation
│   └── pyproject.toml
│
├── docker-compose.yml    # Production services
├── docker-compose.dev.yml # Development overrides
├── Makefile              # Convenience commands
└── .env                  # Environment variables
```
