import { createClient } from '@supabase/supabase-js';

// Get environment variables
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing Supabase environment variables. Please ensure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are set in .env'
  );
}

// Create Supabase client
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
  },
  db: {
    schema: 'public',
  },
  global: {
    headers: {
      'x-application-name': 'boilerplate-frontend',
    },
  },
});

// Type definitions for database schema
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export interface Database {
  public: {
    Tables: {
      entities: {
        Row: {
          id: string;
          entity_type: string;
          source_record_id: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          entity_type: string;
          source_record_id?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          entity_type?: string;
          source_record_id?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      entity_versions: {
        Row: {
          id: string;
          entity_id: string;
          version_number: number;
          data: Json;
          is_current: boolean;
          valid_from: string;
          valid_to: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          entity_id: string;
          version_number: number;
          data?: Json;
          is_current?: boolean;
          valid_from?: string;
          valid_to?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          entity_id?: string;
          version_number?: number;
          data?: Json;
          is_current?: boolean;
          valid_from?: string;
          valid_to?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      relationships_v2: {
        Row: {
          id: string;
          relationship_type: string;
          parent_id: string;
          child_id: string;
          metadata: Json;
          is_current: boolean;
          valid_from: string;
          valid_to: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          relationship_type: string;
          parent_id: string;
          child_id: string;
          metadata?: Json;
          is_current?: boolean;
          valid_from?: string;
          valid_to?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          relationship_type?: string;
          parent_id?: string;
          child_id?: string;
          metadata?: Json;
          is_current?: boolean;
          valid_from?: string;
          valid_to?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      fact_types: {
        Row: {
          id: string;
          key: string;
          label: string;
          description: string | null;
          unit: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          key: string;
          label: string;
          description?: string | null;
          unit?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          key?: string;
          label?: string;
          description?: string | null;
          unit?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      entity_facts: {
        Row: {
          id: string;
          entity_id: string;
          fact_type_id: string;
          value: number;
          dimension_type: string | null;
          dimension_id: string | null;
          source_id: string | null;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          entity_id: string;
          fact_type_id: string;
          value: number;
          dimension_type?: string | null;
          dimension_id?: string | null;
          source_id?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          entity_id?: string;
          fact_type_id?: string;
          value?: number;
          dimension_type?: string | null;
          dimension_id?: string | null;
          source_id?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };
      time_series_points: {
        Row: {
          id: string;
          entity_id: string;
          fact_type_id: string;
          observed_at: string;
          data_payload: Json;
          source_id: string | null;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          entity_id: string;
          fact_type_id: string;
          observed_at: string;
          data_payload: Json;
          source_id?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          entity_id?: string;
          fact_type_id?: string;
          observed_at?: string;
          data_payload?: Json;
          source_id?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
  };
}
