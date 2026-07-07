# Frontend Guide

## 📍 Location
```
C:\Users\Ollie.Olwage\day2\frontend\
```

## 🌐 Access URLs

### Once Started:
- **Frontend Application**: http://localhost:3000
- **Supabase Studio**: http://localhost:54323 (Database UI)
- **Temporal UI**: http://localhost:8080 (Workflows)

## 🚀 Quick Start

### Option 1: Run with Full Stack (Recommended)
The frontend runs automatically when you start the full stack:
```bash
cd C:\Users\Ollie.Olwage\day2
./start.sh
```

### Option 2: Run Frontend Only (Development)
```bash
cd C:\Users\Ollie.Olwage\day2\frontend
npm install
npm run dev
```
Frontend will be at: http://localhost:5173

## 📂 Key Files & Folders

### Configuration
- `package.json` - Dependencies and scripts
- `vite.config.ts` - Vite build configuration
- `tsconfig.json` - TypeScript configuration
- `tailwind.config.js` - Tailwind CSS setup

### Source Code (`src/`)

#### Database Integration (`src/lib/`)
```
src/lib/
├── supabase.ts          ← Main Supabase client
├── hooks/
│   ├── index.ts         ← Export all hooks
│   ├── useEntities.ts   ← Entity CRUD hooks
│   └── useEntityFacts.ts ← Facts CRUD hooks
└── utils.ts             ← Utility functions
```

#### Pages (`src/pages/`)
```
src/pages/
└── Dashboard.tsx        ← Main dashboard (example)
```

#### Components (`src/components/`)
React components (UI building blocks)

#### Routes (`src/routes/`)
TanStack Router route definitions

## 🔧 Available Hooks

### Entity Hooks (`useEntities.ts`)

```typescript
import { 
  useEntities, 
  useEntity, 
  useCreateEntity,
  useUpdateEntity,
  useDeleteEntity 
} from '@/lib/hooks';

// Get all entities
const { data: entities, isLoading } = useEntities();

// Get single entity
const { data: entity } = useEntity('entity-id');

// Create entity
const createEntity = useCreateEntity();
await createEntity.mutateAsync({ 
  entity_type: 'user' 
});

// Update entity
const updateEntity = useUpdateEntity();
await updateEntity.mutateAsync({ 
  id: 'entity-id', 
  updates: { entity_type: 'admin' } 
});

// Delete entity
const deleteEntity = useDeleteEntity();
await deleteEntity.mutateAsync('entity-id');
```

### Fact Hooks (`useEntityFacts.ts`)

```typescript
import { 
  useEntityFacts,
  useUpsertEntityFact 
} from '@/lib/hooks';

// Get all facts for an entity
const { data: facts } = useEntityFacts('entity-id');

// Upsert fact
const upsertFact = useUpsertEntityFact();
await upsertFact.mutateAsync({
  entity_id: 'entity-id',
  fact_type_id: 'fact-type-id',
  value: 42
});
```

## 💻 Example Component

```typescript
// src/pages/MyPage.tsx
import { useEntities, useCreateEntity } from '@/lib/hooks';
import { useState } from 'react';

export function MyPage() {
  const [entityType, setEntityType] = useState('');
  const { data: entities, isLoading } = useEntities();
  const createEntity = useCreateEntity();

  const handleCreate = async () => {
    await createEntity.mutateAsync({ 
      entity_type: entityType 
    });
    setEntityType('');
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">My Page</h1>
      
      {/* Create Form */}
      <div className="mb-8">
        <input
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          placeholder="Entity type"
          className="border px-4 py-2 rounded"
        />
        <button 
          onClick={handleCreate}
          className="ml-2 bg-blue-500 text-white px-4 py-2 rounded"
        >
          Create
        </button>
      </div>

      {/* List */}
      <div>
        {entities?.map(entity => (
          <div key={entity.id} className="p-4 border rounded mb-2">
            <h3>{entity.entity_type}</h3>
            <p className="text-sm text-gray-500">{entity.id}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## 🎨 Styling

### Tailwind CSS
The project uses Tailwind CSS v4. Use utility classes:

```tsx
<div className="bg-white rounded-lg shadow p-6">
  <h1 className="text-2xl font-bold text-gray-900">Title</h1>
  <p className="text-gray-600 mt-2">Description</p>
</div>
```

### Component Library
Radix UI components are included for:
- Dialogs
- Dropdowns  
- Tooltips
- Tabs
- And more

## 🔌 API Connection

### Environment Variables
Create `.env` in frontend directory:

```env
VITE_SUPABASE_URL=http://localhost:54321
VITE_SUPABASE_ANON_KEY=your-anon-key-here
VITE_API_URL=http://localhost:54321/functions/v1
```

### Supabase Client
Located at `src/lib/supabase.ts`:

```typescript
import { supabase } from '@/lib/supabase';

// Direct query example
const { data, error } = await supabase
  .from('entities')
  .select('*')
  .eq('entity_type', 'user');
```

But prefer using hooks for automatic caching and updates!

## 📊 TypeScript Types

All database types are defined in `src/lib/supabase.ts`:

```typescript
import type { Database } from '@/lib/supabase';

type Entity = Database['public']['Tables']['entities']['Row'];
type EntityInsert = Database['public']['Tables']['entities']['Insert'];
type EntityUpdate = Database['public']['Tables']['entities']['Update'];
```

## 🛠️ Development Commands

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint

# Type check
npx tsc --noEmit
```

## 📦 Key Dependencies

| Package | Purpose |
|---------|---------|
| `react` | UI framework |
| `@tanstack/react-query` | Data fetching & caching |
| `@tanstack/react-router` | Routing |
| `@supabase/supabase-js` | Database client |
| `tailwindcss` | Styling |
| `typescript` | Type safety |
| `vite` | Build tool |

## 🎯 Common Tasks

### Add a New Page

1. Create file: `src/pages/NewPage.tsx`
```typescript
export function NewPage() {
  return <div>New Page Content</div>;
}
```

2. Add route in `src/routes/`

### Add a New Hook

1. Create file: `src/lib/hooks/useMyData.ts`
```typescript
import { useQuery } from '@tanstack/react-query';
import { supabase } from '../supabase';

export function useMyData() {
  return useQuery({
    queryKey: ['my-data'],
    queryFn: async () => {
      const { data } = await supabase
        .from('my_table')
        .select('*');
      return data;
    },
  });
}
```

2. Export in `src/lib/hooks/index.ts`

### Add Real-time Subscription

```typescript
import { useEffect } from 'react';
import { supabase } from '@/lib/supabase';

function MyComponent() {
  useEffect(() => {
    const channel = supabase
      .channel('entities-changes')
      .on('postgres_changes', {
        event: '*',
        schema: 'public',
        table: 'entities'
      }, (payload) => {
        console.log('Change received!', payload);
        // Update your state here
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  return <div>Listening for changes...</div>;
}
```

## 🐛 Troubleshooting

### Frontend won't start
```bash
# Clear node_modules and reinstall
rm -rf node_modules
npm install
```

### Can't connect to Supabase
- Check `.env` has correct `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
- Verify Supabase is running: `supabase status`
- Check browser console for errors

### TypeScript errors
```bash
# Regenerate types
npx supabase gen types typescript --local > src/lib/database.types.ts
```

### Hot reload not working
- Restart Vite dev server
- Check Vite config allows your file type
- Clear browser cache

## 📚 Learning Resources

- **React**: https://react.dev
- **TanStack Query**: https://tanstack.com/query
- **TanStack Router**: https://tanstack.com/router
- **Supabase JS**: https://supabase.com/docs/reference/javascript
- **Tailwind CSS**: https://tailwindcss.com/docs

## 🎉 Ready to Build!

The frontend is fully set up and ready for development. Start by:

1. Running the app: `npm run dev`
2. Opening http://localhost:5173
3. Editing `src/pages/Dashboard.tsx`
4. See changes instantly with hot reload!

Happy coding! 🚀
