# Quick Start Guide

Get your full-stack application running in minutes!

## Prerequisites Check

Before starting, ensure you have:

- [ ] **Docker Desktop** - Download from [docker.com](https://www.docker.com/products/docker-desktop/)
- [ ] **Node.js 18+** - Download from [nodejs.org](https://nodejs.org/)
- [ ] **Supabase CLI** - Install with `npm install -g supabase`
- [ ] **Python 3.11+** - Download from [python.org](https://www.python.org/)

Verify installations:
```bash
docker --version
node --version
supabase --version
python --version
```

## Option 1: Automated Start (Recommended)

### Using the Start Script

```bash
# Start everything automatically
./start.sh

# Or start in development mode (with live reload)
./start.sh dev
```

The script will:
1. Check Docker is running
2. Start Supabase
3. Extract and configure API keys
4. Start all services (Temporal + Frontend)
5. Display access URLs

## Option 2: Manual Start

### Step 1: Start Docker Desktop

Make sure Docker Desktop is running. Check with:
```bash
docker ps
```

### Step 2: Start Supabase

```bash
supabase start
```

**First time?** This will download Docker images (~2GB). Grab a coffee ☕

Expected output:
```
Started supabase local development setup.

         API URL: http://localhost:54321
          DB URL: postgresql://postgres:postgres@localhost:54322/postgres
      Studio URL: http://localhost:54323
    Inbucket URL: http://localhost:54324
        anon key: eyJhbG...
service_role key: eyJhbG...
```

### Step 3: Configure Environment

Copy the keys from `supabase status` output:

```bash
# View keys again
supabase status

# Update .env file with the actual keys
# Replace 'your-anon-key' with the actual key from supabase status
```

Edit `.env` and update:
```env
SUPABASE_ANON_KEY=eyJhbG... (paste your anon key)
SUPABASE_SERVICE_ROLE_KEY=eyJhbG... (paste your service_role key)
VITE_SUPABASE_ANON_KEY=eyJhbG... (paste your anon key)
```

### Step 4: Start Services

```bash
# Production mode
make up

# OR development mode (live reload)
USE_DEV=1 make up
```

### Step 5: Verify Everything Works

Open in your browser:
- Frontend: http://localhost:3000
- Supabase Studio: http://localhost:54323
- Temporal UI: http://localhost:8080

## Usage Examples

### 1. Create an Entity via Frontend

1. Open http://localhost:3000
2. Enter an entity type (e.g., `user`, `company`, `room`)
3. Click "Create"
4. The entity appears in the list below

### 2. View Database in Supabase Studio

1. Open http://localhost:54323
2. Click "Table Editor" in sidebar
3. Select `entities` table
4. See your created entities

### 3. Create Entity via API

```bash
curl -X POST http://localhost:54321/rest/v1/entities \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "product",
    "source_record_id": "prod-123"
  }'
```

### 4. Query Entities

```bash
# Get all entities
curl http://localhost:54321/rest/v1/entities \
  -H "apikey: YOUR_ANON_KEY"

# Get entities by type
curl "http://localhost:54321/rest/v1/entities?entity_type=eq.user" \
  -H "apikey: YOUR_ANON_KEY"
```

### 5. Create Entity with Version (SCD2)

```bash
# 1. Create entity
ENTITY_ID=$(curl -X POST http://localhost:54321/rest/v1/entities \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entity_type": "room"}' | jq -r '.[0].id')

# 2. Create initial version
curl -X POST http://localhost:54321/rest/v1/entity_versions \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"$ENTITY_ID\",
    \"version_number\": 1,
    \"data\": {
      \"name\": \"Conference Room A\",
      \"capacity\": 10,
      \"floor\": 1
    }
  }"

# 3. Update (creates version 2, closes version 1)
curl -X POST http://localhost:54321/rest/v1/entity_versions \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"$ENTITY_ID\",
    \"version_number\": 2,
    \"data\": {
      \"name\": \"Conference Room A\",
      \"capacity\": 12,
      \"floor\": 1
    }
  }"
```

### 6. Create Time Series Data

```bash
# 1. Create fact type
curl -X POST http://localhost:54321/rest/v1/fact_types \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "temperature",
    "label": "Temperature",
    "unit": "celsius"
  }'

# 2. Insert time series point
curl -X POST http://localhost:54321/rest/v1/time_series_points \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "YOUR_ENTITY_ID",
    "fact_type_id": "YOUR_FACT_TYPE_ID",
    "observed_at": "2024-01-15T10:30:00Z",
    "data_payload": {
      "value": 23.5,
      "sensor_id": "temp-001"
    }
  }'
```

### 7. Run Temporal Workflow (Python)

Create a workflow trigger:

```python
# example_workflow_trigger.py
import asyncio
from temporalio.client import Client
from src.workflows.example.approval_workflow import ApprovalWorkflow

async def main():
    client = await Client.connect("localhost:7234")
    
    result = await client.execute_workflow(
        ApprovalWorkflow.run,
        args=["example-request-id"],
        id="approval-workflow-1",
        task_queue="main",
    )
    
    print(f"Workflow result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Common Tasks

### View Logs

```bash
# All services
make logs

# Specific service
make logs-frontend
make logs-temporal
docker compose logs temporal-worker -f
```

### Stop Services

```bash
# Stop all
make down

# Stop Supabase
supabase stop
```

### Reset Database

```bash
# Reset and reapply migrations
make reset

# Or manually
supabase db reset
```

### Restart a Service

```bash
# Restart worker after code changes
docker compose restart temporal-worker

# View worker logs
docker compose logs temporal-worker -f
```

### Access Database Directly

```bash
# Via psql
psql postgresql://postgres:postgres@localhost:54322/postgres

# Example queries
SELECT * FROM entities;
SELECT * FROM entity_versions WHERE is_current = true;
SELECT * FROM fact_types;
```

## Frontend Development

### Install Dependencies

```bash
cd frontend
npm install
```

### Run Frontend Locally (outside Docker)

```bash
cd frontend
npm run dev
```

Frontend will be available at http://localhost:5173 (Vite default) or http://localhost:3000

### Build for Production

```bash
cd frontend
npm run build
npm run preview
```

## Temporal Worker Development

### Install Python Dependencies

```bash
cd temporal
pip install -r requirements.txt
```

### Run Worker Locally (outside Docker)

```bash
cd temporal
python -m src.worker
```

### Create New Activity

```python
# temporal/src/activities/my_activity.py
from temporalio import activity

@activity.defn
async def my_new_activity(param: str) -> str:
    # Your logic here
    return f"Processed: {param}"
```

Register in `temporal/src/worker.py`:
```python
activities=[
    # ... existing activities
    my_activity.my_new_activity,
]
```

## Troubleshooting

### Docker not running
```
Error: failed to connect to the docker API
```
**Solution**: Start Docker Desktop

### Port already in use
```
Error: port 54321 already allocated
```
**Solution**: Stop other Supabase instances
```bash
supabase stop
# Then start again
supabase start
```

### Frontend can't connect to Supabase
**Solution**: Check environment variables
```bash
cat .env | grep VITE_SUPABASE
# Ensure VITE_SUPABASE_ANON_KEY is set correctly
```

### Temporal worker crashes
**Solution**: Check logs
```bash
docker compose logs temporal-worker
# Common issue: Supabase keys not set
```

### Database migration errors
**Solution**: Reset database
```bash
supabase db reset
```

## Next Steps

1. **Explore the Schema**: Open Supabase Studio and examine the tables
2. **Read the Guides**:
   - `Guide_for_agents_using_supabase_template.md` - Implementation patterns
   - `DATABASE.md` - Schema details
   - `Generalisable_schema.md` - Data modeling
3. **Build Your Domain**: Add your entities, facts, and workflows
4. **Customize Frontend**: Modify `frontend/src/pages/Dashboard.tsx`

## Need Help?

- Check `SETUP.md` for detailed architecture
- Review example code in `temporal/src/activities/`
- Examine `frontend/src/lib/hooks/` for data fetching patterns
- Look at existing migrations in `supabase/migrations/`

Happy Building! 🚀
