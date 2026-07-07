import { useState } from 'react';
import { useEntities, useCreateEntity, useEntityFacts } from '@/lib/hooks';

export function Dashboard() {
  const { data: entities, isLoading, error } = useEntities();
  const createEntity = useCreateEntity();
  const [newEntityType, setNewEntityType] = useState('');

  const handleCreateEntity = async () => {
    if (!newEntityType.trim()) return;

    try {
      await createEntity.mutateAsync({
        entity_type: newEntityType,
      });
      setNewEntityType('');
    } catch (err) {
      console.error('Failed to create entity:', err);
    }
  };

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

      {/* Create Entity Section */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Create New Entity</h2>
        <div className="flex gap-4">
          <input
            type="text"
            value={newEntityType}
            onChange={(e) => setNewEntityType(e.target.value)}
            placeholder="Entity type (e.g., user, company, room)"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleCreateEntity}
            disabled={!newEntityType.trim() || createEntity.isPending}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {createEntity.isPending ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>

      {/* Entities List */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Entities</h2>

        {isLoading && (
          <div className="text-gray-500">Loading entities...</div>
        )}

        {error && (
          <div className="text-red-500">
            Error loading entities: {error.message}
          </div>
        )}

        {entities && entities.length === 0 && (
          <div className="text-gray-500">
            No entities yet. Create one to get started!
          </div>
        )}

        {entities && entities.length > 0 && (
          <div className="space-y-4">
            {entities.map((entity) => (
              <EntityCard key={entity.id} entity={entity} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function EntityCard({ entity }: { entity: any }) {
  const { data: facts } = useEntityFacts(entity.id);

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:border-blue-500 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-semibold text-lg">{entity.entity_type}</h3>
          <p className="text-sm text-gray-500">ID: {entity.id}</p>
          {entity.source_record_id && (
            <p className="text-sm text-gray-500">
              Source: {entity.source_record_id}
            </p>
          )}
        </div>
        <span className="text-xs text-gray-400">
          {new Date(entity.created_at).toLocaleDateString()}
        </span>
      </div>

      {facts && facts.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Facts:</h4>
          <div className="space-y-1">
            {facts.map((fact: any) => (
              <div key={fact.id} className="text-sm text-gray-600">
                {fact.fact_types?.label || 'Unknown'}: {fact.value}
                {fact.fact_types?.unit && ` ${fact.fact_types.unit}`}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
