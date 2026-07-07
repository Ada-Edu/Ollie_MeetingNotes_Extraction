"""Supabase client for Temporal activities."""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx
from config import settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Simple HTTP-based Supabase client for Temporal worker."""

    def __init__(self):
        self.base_url = settings.supabase_url
        self.service_role_key = settings.supabase_service_role_key
        self.rest_url = f"{self.base_url}/rest/v1"

        self.headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        """Make HTTP request to Supabase REST API."""
        url = f"{self.rest_url}/{endpoint}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Request failed: {str(e)}")
                raise

    async def create_entity(
        self,
        entity_type: str,
        source_record_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new entity."""
        data = {
            "entity_type": entity_type,
            "source_record_id": source_record_id,
        }
        result = await self._request("POST", "entities", data=data)
        if isinstance(result, list):
            return result[0]
        return result

    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        params = {"id": f"eq.{entity_id}"}
        result = await self._request("GET", "entities", params=params)
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    async def create_entity_version(
        self,
        entity_id: str,
        version_number: int,
        data: Dict[str, Any],
        valid_from: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new entity version (SCD2)."""
        version_data = {
            "entity_id": entity_id,
            "version_number": version_number,
            "data": data,
            "is_current": True,
            "valid_from": valid_from or datetime.utcnow().isoformat(),
        }
        result = await self._request("POST", "entity_versions", data=version_data)
        if isinstance(result, list):
            return result[0]
        return result

    async def get_current_entity_version(
        self, entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current version of an entity."""
        params = {
            "entity_id": f"eq.{entity_id}",
            "is_current": "eq.true",
        }
        result = await self._request("GET", "entity_versions", params=params)
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    async def create_relationship(
        self,
        relationship_type: str,
        parent_id: str,
        child_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a relationship between entities."""
        rel_data = {
            "relationship_type": relationship_type,
            "parent_id": parent_id,
            "child_id": child_id,
            "metadata": metadata or {},
            "is_current": True,
        }
        result = await self._request("POST", "relationships_v2", data=rel_data)
        if isinstance(result, list):
            return result[0]
        return result

    async def create_fact_type(
        self,
        key: str,
        label: str,
        description: Optional[str] = None,
        unit: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or get a fact type."""
        data = {
            "key": key,
            "label": label,
            "description": description,
            "unit": unit,
        }
        # Use upsert behavior
        result = await self._request("POST", "fact_types", data=data)
        if isinstance(result, list):
            return result[0]
        return result

    async def get_fact_type_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Get fact type by key."""
        params = {"key": f"eq.{key}"}
        result = await self._request("GET", "fact_types", params=params)
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    async def upsert_entity_fact(
        self,
        entity_id: str,
        fact_type_id: str,
        value: float,
        dimension_type: Optional[str] = None,
        dimension_id: Optional[str] = None,
        source_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Upsert an entity fact (insert or update)."""
        fact_data = {
            "entity_id": entity_id,
            "fact_type_id": fact_type_id,
            "value": value,
            "dimension_type": dimension_type,
            "dimension_id": dimension_id,
            "source_id": source_id,
            "metadata": metadata or {},
        }
        # Supabase upsert via POST with Prefer: resolution=merge-duplicates
        headers = {**self.headers, "Prefer": "resolution=merge-duplicates"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.rest_url}/entity_facts",
                headers=headers,
                json=fact_data,
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            if isinstance(result, list):
                return result[0]
            return result

    async def insert_time_series_point(
        self,
        entity_id: str,
        fact_type_id: str,
        observed_at: str,
        data_payload: Dict[str, Any],
        source_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Insert a time series data point."""
        ts_data = {
            "entity_id": entity_id,
            "fact_type_id": fact_type_id,
            "observed_at": observed_at,
            "data_payload": data_payload,
            "source_id": source_id,
            "metadata": metadata or {},
        }
        result = await self._request("POST", "time_series_points", data=ts_data)
        if isinstance(result, list):
            return result[0]
        return result


# Global client instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get or create the Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client
