from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict
from temporalio import activity
from supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

@dataclass
class EntityResult:
    entity_id: str
    version_id: str | None = None
    success: bool = True
    error: str | None = None


@activity.defn
async def create_entity(entity_type: str, attributes: Dict[str, Any], created_by: str | None = None) -> EntityResult:
    """Create a new entity with initial version."""
    logger.info("create_entity", extra={"entity_type": entity_type, "created_by": created_by})

    try:
        client = get_supabase_client()

        # Create entity
        entity = await client.create_entity(entity_type=entity_type)
        entity_id = entity["id"]

        # Create initial version
        version = await client.create_entity_version(
            entity_id=entity_id,
            version_number=1,
            data=attributes,
        )

        logger.info(f"Created entity {entity_id} with version {version['id']}")
        return EntityResult(entity_id=entity_id, version_id=version["id"])

    except Exception as e:
        logger.error(f"Failed to create entity: {str(e)}")
        return EntityResult(entity_id="", version_id=None, success=False, error=str(e))


@activity.defn
async def update_entity_scd2(entity_id: str, attributes: Dict[str, Any], updated_by: str | None = None) -> EntityResult:
    """Update entity by creating a new SCD2 version."""
    logger.info("update_entity_scd2", extra={"entity_id": entity_id, "updated_by": updated_by})

    try:
        client = get_supabase_client()

        # Get current version to determine next version number
        current = await client.get_current_entity_version(entity_id)
        next_version = (current["version_number"] + 1) if current else 1

        # Create new version (trigger will close old one)
        version = await client.create_entity_version(
            entity_id=entity_id,
            version_number=next_version,
            data=attributes,
        )

        logger.info(f"Updated entity {entity_id} to version {version['id']}")
        return EntityResult(entity_id=entity_id, version_id=version["id"])

    except Exception as e:
        logger.error(f"Failed to update entity: {str(e)}")
        return EntityResult(entity_id=entity_id, version_id=None, success=False, error=str(e))


@activity.defn
async def get_entity(entity_id: str) -> Dict[str, Any]:
    """Get entity with its current version."""
    logger.info("get_entity", extra={"entity_id": entity_id})

    try:
        client = get_supabase_client()

        entity = await client.get_entity(entity_id)
        if not entity:
            return {"error": "Entity not found"}

        current_version = await client.get_current_entity_version(entity_id)

        return {
            "entity": entity,
            "current_version": current_version,
        }

    except Exception as e:
        logger.error(f"Failed to get entity: {str(e)}")
        return {"error": str(e)}


@activity.defn
async def append_event(
    entity_id: str,
    fact_type_key: str,
    observed_at: str,
    event_data: Dict[str, Any],
    source_id: str | None = None,
) -> bool:
    """Append a time series event."""
    logger.info("append_event", extra={"entity_id": entity_id, "fact_type_key": fact_type_key})

    try:
        client = get_supabase_client()

        # Get or create fact type
        fact_type = await client.get_fact_type_by_key(fact_type_key)
        if not fact_type:
            fact_type = await client.create_fact_type(
                key=fact_type_key,
                label=fact_type_key.replace("_", " ").title(),
            )

        # Insert time series point
        await client.insert_time_series_point(
            entity_id=entity_id,
            fact_type_id=fact_type["id"],
            observed_at=observed_at,
            data_payload=event_data,
            source_id=source_id,
        )

        logger.info(f"Appended event for entity {entity_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to append event: {str(e)}")
        return False


@activity.defn
async def create_relationship(
    from_entity_id: str,
    to_entity_id: str,
    relationship_type: str,
    attributes: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Create a relationship between two entities."""
    logger.info(
        "create_relationship",
        extra={"from": from_entity_id, "to": to_entity_id, "relationship_type": relationship_type},
    )

    try:
        client = get_supabase_client()

        relationship = await client.create_relationship(
            relationship_type=relationship_type,
            parent_id=from_entity_id,
            child_id=to_entity_id,
            metadata=attributes,
        )

        logger.info(f"Created relationship {relationship['id']}")
        return {"relationship_id": relationship["id"], "success": True}

    except Exception as e:
        logger.error(f"Failed to create relationship: {str(e)}")
        return {"relationship_id": None, "success": False, "error": str(e)}
