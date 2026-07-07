import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '../supabase';
import type { Database } from '../supabase';

type Entity = Database['public']['Tables']['entities']['Row'];
type EntityInsert = Database['public']['Tables']['entities']['Insert'];
type EntityUpdate = Database['public']['Tables']['entities']['Update'];

// Query key factory
export const entityKeys = {
  all: ['entities'] as const,
  lists: () => [...entityKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...entityKeys.lists(), filters] as const,
  details: () => [...entityKeys.all, 'detail'] as const,
  detail: (id: string) => [...entityKeys.details(), id] as const,
  byType: (type: string) => [...entityKeys.all, 'type', type] as const,
};

/**
 * Fetch all entities
 */
export function useEntities() {
  return useQuery({
    queryKey: entityKeys.lists(),
    queryFn: async () => {
      const { data, error } = await supabase
        .from('entities')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      return data;
    },
  });
}

/**
 * Fetch entities by type
 */
export function useEntitiesByType(entityType: string) {
  return useQuery({
    queryKey: entityKeys.byType(entityType),
    queryFn: async () => {
      const { data, error } = await supabase
        .from('entities')
        .select('*')
        .eq('entity_type', entityType)
        .order('created_at', { ascending: false });

      if (error) throw error;
      return data;
    },
  });
}

/**
 * Fetch single entity by ID
 */
export function useEntity(id: string) {
  return useQuery({
    queryKey: entityKeys.detail(id),
    queryFn: async () => {
      const { data, error } = await supabase
        .from('entities')
        .select('*')
        .eq('id', id)
        .single();

      if (error) throw error;
      return data;
    },
    enabled: !!id,
  });
}

/**
 * Fetch entity with its current version
 */
export function useEntityWithVersion(id: string) {
  return useQuery({
    queryKey: [...entityKeys.detail(id), 'with-version'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('entities')
        .select(`
          *,
          entity_versions!inner (
            id,
            version_number,
            data,
            valid_from,
            valid_to,
            is_current
          )
        `)
        .eq('id', id)
        .eq('entity_versions.is_current', true)
        .single();

      if (error) throw error;
      return data;
    },
    enabled: !!id,
  });
}

/**
 * Create new entity
 */
export function useCreateEntity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (entity: EntityInsert) => {
      const { data, error } = await supabase
        .from('entities')
        .insert(entity)
        .select()
        .single();

      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entityKeys.all });
    },
  });
}

/**
 * Update entity
 */
export function useUpdateEntity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: EntityUpdate }) => {
      const { data, error } = await supabase
        .from('entities')
        .update(updates)
        .eq('id', id)
        .select()
        .single();

      if (error) throw error;
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: entityKeys.all });
      queryClient.invalidateQueries({ queryKey: entityKeys.detail(data.id) });
    },
  });
}

/**
 * Delete entity
 */
export function useDeleteEntity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase
        .from('entities')
        .delete()
        .eq('id', id);

      if (error) throw error;
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: entityKeys.all });
    },
  });
}
