# Full Stack Integration Example

This document demonstrates how the backend and frontend work together in a complete workflow.

## Use Case: Room Monitoring System

We'll build a simple room monitoring system that:
1. Creates room entities
2. Tracks temperature readings via time series
3. Derives comfort states as facts
4. Displays everything in the frontend

## Backend Setup (Database)

### 1. Create Fact Types

```sql
-- Connect to database
-- psql postgresql://postgres:postgres@localhost:54322/postgres

-- Define our metric types
INSERT INTO fact_types (key, label, description, unit)
VALUES 
  ('room_temperature_c', 'Room Temperature', 'Temperature in Celsius', 'celsius'),
  ('room_comfort_state', 'Comfort State', 'Current comfort level', 'state')
ON CONFLICT (key) DO NOTHING;
```

### 2. Create Dimension Table for States

```sql
-- Create dimension table for comfort states
CREATE TABLE IF NOT EXISTS dim_room_state (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  label text NOT NULL,
  sort_order int,
  description text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Seed comfort states
INSERT INTO dim_room_state (key, label, sort_order, description)
VALUES 
  ('too_cold', 'Too Cold', 1, 'Temperature below comfortable range'),
  ('comfortable', 'Comfortable', 2, 'Temperature in comfortable range'),
  ('too_warm', 'Too Warm', 3, 'Temperature above comfortable range')
ON CONFLICT (key) DO NOTHING;
```

## Backend Implementation (Temporal Worker)

### 1. Create Room Activity

```python
# temporal/src/activities/room_monitoring.py
from temporalio import activity
from ..supabase_client import get_supabase_client
from datetime import datetime

@activity.defn
async def create_room(name: str, capacity: int, floor: int) -> dict:
    """Create a room entity with initial configuration."""
    client = get_supabase_client()
    
    # Create entity
    entity = await client.create_entity(entity_type="room")
    
    # Create initial version with configuration
    version = await client.create_entity_version(
        entity_id=entity["id"],
        version_number=1,
        data={
            "name": name,
            "capacity": capacity,
            "floor": floor,
        }
    )
    
    return {
        "entity_id": entity["id"],
        "version_id": version["id"],
        "name": name,
    }


@activity.defn
async def record_temperature(entity_id: str, temperature: float) -> dict:
    """Record a temperature reading and update comfort state."""
    client = get_supabase_client()
    
    # Get fact types
    temp_fact = await client.get_fact_type_by_key("room_temperature_c")
    state_fact = await client.get_fact_type_by_key("room_comfort_state")
    
    # Insert time series point
    await client.insert_time_series_point(
        entity_id=entity_id,
        fact_type_id=temp_fact["id"],
        observed_at=datetime.utcnow().isoformat(),
        data_payload={"value": temperature},
        source_id="sensor-001",
    )
    
    # Determine comfort state
    if temperature < 18:
        state_key = "too_cold"
        state_code = 1
    elif temperature > 26:
        state_key = "too_warm"
        state_code = 3
    else:
        state_key = "comfortable"
        state_code = 2
    
    # Get dimension ID
    from httpx import AsyncClient
    async with AsyncClient() as http:
        response = await http.get(
            f"{client.rest_url}/dim_room_state",
            headers=client.headers,
            params={"key": f"eq.{state_key}"},
        )
        dim_state = response.json()[0]
    
    # Upsert current temperature fact
    await client.upsert_entity_fact(
        entity_id=entity_id,
        fact_type_id=temp_fact["id"],
        value=temperature,
        source_id="sensor-001",
        metadata={"observed_at": datetime.utcnow().isoformat()},
    )
    
    # Upsert comfort state fact
    await client.upsert_entity_fact(
        entity_id=entity_id,
        fact_type_id=state_fact["id"],
        value=state_code,
        dimension_type="room_state",
        dimension_id=dim_state["id"],
        source_id="comfort-service",
        metadata={"observed_at": datetime.utcnow().isoformat()},
    )
    
    return {
        "temperature": temperature,
        "state": state_key,
        "state_code": state_code,
    }
```

### 2. Create Workflow

```python
# temporal/src/workflows/room_monitoring.py
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from ..activities.room_monitoring import create_room, record_temperature


@workflow.defn
class RoomMonitoringWorkflow:
    """Workflow to monitor room temperature."""
    
    @workflow.run
    async def run(self, room_config: dict) -> dict:
        """
        Args:
            room_config: {"name": str, "capacity": int, "floor": int}
        """
        
        # Create room entity
        room = await workflow.execute_activity(
            create_room,
            args=[
                room_config["name"],
                room_config["capacity"],
                room_config["floor"],
            ],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        
        workflow.logger.info(f"Room created: {room['entity_id']}")
        
        # Simulate temperature readings over time
        for temp in [20.5, 22.0, 24.5, 27.0, 25.5]:
            result = await workflow.execute_activity(
                record_temperature,
                args=[room["entity_id"], temp],
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            workflow.logger.info(
                f"Temperature: {temp}°C, State: {result['state']}"
            )
            
            # Wait between readings
            await workflow.sleep_async(timedelta(seconds=2))
        
        return {
            "room_id": room["entity_id"],
            "readings_count": 5,
            "status": "complete",
        }
```

### 3. Register Activities and Workflows

```python
# temporal/src/worker.py
from .activities import room_monitoring
from .workflows.room_monitoring import RoomMonitoringWorkflow

worker = Worker(
    client,
    task_queue=settings.temporal_task_queue,
    workflows=[
        ApprovalWorkflow,
        RoomMonitoringWorkflow,  # Add this
    ],
    activities=[
        # ... existing activities
        room_monitoring.create_room,
        room_monitoring.record_temperature,
    ],
    activity_executor=activity_executor,
)
```

## Frontend Implementation

### 1. Create Room Monitoring Hook

```typescript
// frontend/src/lib/hooks/useRoomMonitoring.ts
import { useQuery } from '@tanstack/react-query';
import { supabase } from '../supabase';

export function useRoomWithTemperature(roomId: string) {
  return useQuery({
    queryKey: ['room-monitoring', roomId],
    queryFn: async () => {
      // Get room entity with current version
      const { data: room, error: roomError } = await supabase
        .from('entities')
        .select(`
          *,
          entity_versions!inner (
            id,
            data,
            is_current
          )
        `)
        .eq('id', roomId)
        .eq('entity_type', 'room')
        .eq('entity_versions.is_current', true)
        .single();

      if (roomError) throw roomError;

      // Get current temperature fact
      const { data: tempFact, error: tempError } = await supabase
        .from('entity_facts')
        .select(`
          *,
          fact_types!inner (
            key,
            label,
            unit
          )
        `)
        .eq('entity_id', roomId)
        .eq('fact_types.key', 'room_temperature_c')
        .single();

      // Get comfort state fact with dimension
      const { data: stateFact, error: stateError } = await supabase
        .from('entity_facts')
        .select('*')
        .eq('entity_id', roomId)
        .eq('dimension_type', 'room_state')
        .single();

      let comfortState = null;
      if (stateFact && stateFact.dimension_id) {
        const { data: dimState } = await supabase
          .from('dim_room_state')
          .select('*')
          .eq('id', stateFact.dimension_id)
          .single();
        
        comfortState = dimState;
      }

      // Get temperature history (last 10 readings)
      const { data: history, error: historyError } = await supabase
        .from('time_series_points')
        .select('observed_at, data_payload')
        .eq('entity_id', roomId)
        .order('observed_at', { ascending: false })
        .limit(10);

      return {
        room,
        currentTemperature: tempFact?.value || null,
        comfortState,
        history: history || [],
      };
    },
    enabled: !!roomId,
    refetchInterval: 5000, // Refresh every 5 seconds
  });
}
```

### 2. Create Room Monitoring Component

```typescript
// frontend/src/components/RoomMonitor.tsx
import { useRoomWithTemperature } from '@/lib/hooks/useRoomMonitoring';

interface RoomMonitorProps {
  roomId: string;
}

export function RoomMonitor({ roomId }: RoomMonitorProps) {
  const { data, isLoading, error } = useRoomWithTemperature(roomId);

  if (isLoading) return <div>Loading room data...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!data) return <div>Room not found</div>;

  const roomData = data.room.entity_versions[0]?.data;

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-bold mb-4">{roomData.name}</h2>
      
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <p className="text-sm text-gray-500">Capacity</p>
          <p className="text-lg font-semibold">{roomData.capacity} people</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Floor</p>
          <p className="text-lg font-semibold">Floor {roomData.floor}</p>
        </div>
      </div>

      {/* Current Temperature */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold">Current Temperature</h3>
          {data.comfortState && (
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                data.comfortState.key === 'comfortable'
                  ? 'bg-green-100 text-green-800'
                  : data.comfortState.key === 'too_cold'
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {data.comfortState.label}
            </span>
          )}
        </div>
        <p className="text-4xl font-bold">
          {data.currentTemperature?.toFixed(1) || '--'}°C
        </p>
      </div>

      {/* Temperature History */}
      <div>
        <h3 className="text-lg font-semibold mb-2">Recent Readings</h3>
        <div className="space-y-2">
          {data.history.map((point, index) => (
            <div
              key={index}
              className="flex justify-between items-center py-2 border-b border-gray-100"
            >
              <span className="text-sm text-gray-600">
                {new Date(point.observed_at).toLocaleTimeString()}
              </span>
              <span className="font-medium">
                {point.data_payload.value}°C
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

## Testing the Integration

### 1. Start the Stack

```bash
./start.sh
```

### 2. Run the Workflow

```python
# test_room_workflow.py
import asyncio
from temporalio.client import Client
from temporal.src.workflows.room_monitoring import RoomMonitoringWorkflow

async def main():
    client = await Client.connect("localhost:7234")
    
    result = await client.execute_workflow(
        RoomMonitoringWorkflow.run,
        args=[{
            "name": "Conference Room A",
            "capacity": 12,
            "floor": 3
        }],
        id="room-monitoring-test-1",
        task_queue="main",
    )
    
    print(f"Workflow completed: {result}")
    print(f"Room ID: {result['room_id']}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
cd temporal
python test_room_workflow.py
```

### 3. View in Frontend

Add to `frontend/src/pages/Dashboard.tsx`:

```typescript
import { RoomMonitor } from '@/components/RoomMonitor';

// In your component:
<RoomMonitor roomId="YOUR_ROOM_ID_FROM_WORKFLOW" />
```

### 4. Query via SQL

```sql
-- View room entity
SELECT * FROM entities WHERE entity_type = 'room';

-- View current temperature
SELECT 
  e.id,
  ev.data->>'name' as room_name,
  ef.value as temperature,
  ft.label,
  ft.unit
FROM entities e
JOIN entity_versions ev ON e.id = ev.entity_id AND ev.is_current = true
JOIN entity_facts ef ON e.id = ef.entity_id
JOIN fact_types ft ON ef.fact_type_id = ft.id
WHERE e.entity_type = 'room'
  AND ft.key = 'room_temperature_c';

-- View comfort state with dimension
SELECT 
  e.id,
  ev.data->>'name' as room_name,
  ef.value as state_code,
  drs.label as comfort_state,
  drs.description
FROM entities e
JOIN entity_versions ev ON e.id = ev.entity_id AND ev.is_current = true
JOIN entity_facts ef ON e.id = ef.entity_id
JOIN fact_types ft ON ef.fact_type_id = ft.id
JOIN dim_room_state drs ON ef.dimension_id = drs.id
WHERE e.entity_type = 'room'
  AND ft.key = 'room_comfort_state';

-- View temperature history
SELECT 
  tsp.observed_at,
  tsp.data_payload->>'value' as temperature,
  ev.data->>'name' as room_name
FROM time_series_points tsp
JOIN entities e ON tsp.entity_id = e.id
JOIN entity_versions ev ON e.id = ev.entity_id AND ev.is_current = true
JOIN fact_types ft ON tsp.fact_type_id = ft.id
WHERE e.entity_type = 'room'
  AND ft.key = 'room_temperature_c'
ORDER BY tsp.observed_at DESC
LIMIT 20;
```

## Data Flow Summary

```
┌─────────────────────────────────────────────────────┐
│  Temporal Workflow (RoomMonitoringWorkflow)         │
│  - Orchestrates the entire process                  │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  Activity: create_room                               │
│  1. Creates entity (type: room)                     │
│  2. Creates entity_version (name, capacity, floor)  │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  Activity: record_temperature                        │
│  1. Inserts time_series_point (raw reading)         │
│  2. Upserts entity_fact (current temperature)       │
│  3. Calculates comfort state                        │
│  4. Upserts entity_fact (comfort state + dimension) │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  Database (PostgreSQL via Supabase)                 │
│  - entities: room identity                          │
│  - entity_versions: room config (SCD2)              │
│  - time_series_points: all temperature readings     │
│  - entity_facts: current temp + state               │
│  - dim_room_state: state meanings                   │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  Frontend (React)                                    │
│  1. Queries via Supabase client                     │
│  2. Joins entities + facts + dimensions             │
│  3. Displays real-time dashboard                    │
│  4. Auto-refreshes every 5 seconds                  │
└─────────────────────────────────────────────────────┘
```

This demonstrates the complete integration from workflow execution through data storage to frontend visualization!
