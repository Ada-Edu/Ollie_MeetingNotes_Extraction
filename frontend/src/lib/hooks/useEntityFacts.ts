import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '../supabase';
import type { Database } from '../supabase';

type EntityFactInsert = Database['public']['Tables']['entity_facts']['Insert'];

// Query key factory
export const entityFactKeys = {
  all: ['entity-facts'] as const,
  lists: () => [...entityFactKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...entityFactKeys.lists(), filters] as const,
  byEntity: (entityId: string) => [...entityFactKeys.all, 'entity', entityId] as const,
  byFactType: (factTypeId: string) => [...entityFactKeys.all, 'fact-type', factTypeId] as const,
};

/**
 * Fetch all facts for an entity
 */
export function useEntityFacts(entityId: string) {
  return useQuery({
    queryKey: entityFactKeys.byEntity(entityId),
    queryFn: async () => {
      const { data, error } = await supabase
        .from('entity_facts')
        .select(`
          *,
          fact_types (
            id,
            key,
            label,
            description,
            unit
          )
        `)
        .eq('entity_id', entityId)
        .order('created_at', { ascending: false });

      if (error) throw error;
      return data;
    },
    enabled: !!entityId,
  });
}

/**
 * Fetch facts by fact type across all entities
 */
export function useFactsByType(factTypeId: string) {
  return useQuery({
    queryKey: entityFactKeys.byFactType(factTypeId),
    queryFn: async () => {
      const { data, error } = await supabase
        .from('entity_facts')
        .select(`
          *,
          entities (
            id,
            entity_type,
            source_record_id
          )
        `)
        .eq('fact_type_id', factTypeId)
        .order('created_at', { ascending: false });

      if (error) throw error;
      return data;
    },
    enabled: !!factTypeId,
  });
}

/**
 * Upsert entity fact (insert or update if exists)
 */
export function useUpsertEntityFact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (fact: EntityFactInsert) => {
      const { data, error } = await supabase
        .from('entity_facts')
        .upsert(fact, {
          onConflict: 'entity_id,fact_type_id,dimension_id',
        })
        .select()
        .single();

      if (error) throw error;
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: entityFactKeys.all });
      queryClient.invalidateQueries({ queryKey: entityFactKeys.byEntity(data.entity_id) });
    },
  });
}

/**
 * Delete entity fact
 */
export function useDeleteEntityFact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase
        .from('entity_facts')
        .delete()
        .eq('id', id);

      if (error) throw error;
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entityFactKeys.all });
    },
  });
}
