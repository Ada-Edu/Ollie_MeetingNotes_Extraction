"""Temporal activities for meeting notes action item extraction."""

from __future__ import annotations
import logging
from temporalio import activity
from supabase_client import get_supabase_client
from model_client.factory import get_model_client, get_model_info

logger = logging.getLogger(__name__)


@activity.defn
async def validate_meeting_notes_input(notes: str) -> None:
    """Validate meeting notes input.

    Args:
        notes: Meeting notes text

    Raises:
        ValueError: If notes are invalid
    """
    logger.info("Validating meeting notes input")

    if not notes or not notes.strip():
        raise ValueError("Meeting notes cannot be empty")

    if len(notes) < 10:
        raise ValueError("Meeting notes too short (minimum 10 characters)")

    if len(notes) > 10000:
        raise ValueError(f"Meeting notes exceed 10,000 character limit (got {len(notes)})")

    logger.info(f"Validation passed (length: {len(notes)} characters)")


@activity.defn
async def call_model_for_action_item_extraction(notes: str) -> dict:
    """Call AI model to extract action items.

    Args:
        notes: Meeting notes text

    Returns:
        Dict with action_items list and model info

    Raises:
        ModelAPIError: If model call fails
        InvalidResponseError: If response is invalid
    """
    logger.info("Starting model extraction")

    # Get model client
    client = get_model_client()
    model_info = {
        "provider": client.get_provider_name(),
        "model_name": client.get_model_name()
    }

    logger.info(f"Using model: {model_info['provider']}/{model_info['model_name']}")

    # Call model
    action_items = await client.extract_action_items(notes)

    logger.info(f"Model extracted {len(action_items)} action items")

    # Convert to dict format
    items_dict = [item.to_dict() for item in action_items]

    return {
        "action_items": items_dict,
        "model_provider": model_info["provider"],
        "model_name": model_info["model_name"]
    }


@activity.defn
async def persist_extraction_results(
    meeting_notes_id: str,
    workflow_id: str,
    action_items: list,
    model_info: dict,
    raw_response: dict
) -> str:
    """Persist extraction results to database.

    Args:
        meeting_notes_id: ID of meeting notes record
        workflow_id: Temporal workflow ID
        action_items: List of extracted action items
        model_info: Model provider and name
        raw_response: Full model response for debugging

    Returns:
        extraction_run_id: ID of created extraction run
    """
    logger.info(f"Persisting extraction results for meeting_notes_id: {meeting_notes_id}")

    client = get_supabase_client()

    # Find existing extraction_run with status='processing' for this workflow
    params = {
        "workflow_id": f"eq.{workflow_id}",
        "order": "created_at.desc",
        "limit": "1"
    }
    existing_runs = await client._request(
        "GET",
        "extraction_runs",
        params=params
    )

    if isinstance(existing_runs, list) and len(existing_runs) > 0:
        # Update existing extraction run
        extraction_run_id = existing_runs[0]["id"]
        logger.info(f"Updating existing extraction_run: {extraction_run_id}")

        update_data = {
            "status": "completed",
            "model_provider": model_info.get("provider"),
            "model_name": model_info.get("model_name"),
            "raw_model_response": raw_response,
            "completed_at": "now()"
        }

        params = {"id": f"eq.{extraction_run_id}"}
        await client._request(
            "PATCH",
            "extraction_runs",
            data=update_data,
            params=params
        )
    else:
        # No existing run found, create new one
        logger.info("No existing extraction_run found, creating new one")
        extraction_run_data = {
            "meeting_notes_id": meeting_notes_id,
            "workflow_id": workflow_id,
            "status": "completed",
            "model_provider": model_info.get("provider"),
            "model_name": model_info.get("model_name"),
            "raw_model_response": raw_response,
            "completed_at": "now()"
        }

        result = await client._request(
            "POST",
            "extraction_runs",
            data=extraction_run_data
        )

        if isinstance(result, list):
            extraction_run = result[0]
        else:
            extraction_run = result

        extraction_run_id = extraction_run["id"]
        logger.info(f"Created extraction_run: {extraction_run_id}")

    # Create action item records
    for item in action_items:
        action_item_data = {
            "extraction_run_id": extraction_run_id,
            "description": item["description"],
            "owner": item.get("owner"),
            "due_date": item.get("due_date"),
            "confidence": item.get("confidence"),
            "metadata": {}
        }

        await client._request(
            "POST",
            "action_items",
            data=action_item_data
        )

    logger.info(f"Created {len(action_items)} action items")

    return extraction_run_id


@activity.defn
async def record_extraction_failure(
    meeting_notes_id: str,
    workflow_id: str,
    error_message: str,
    model_info: dict
) -> str:
    """Record failed extraction attempt.

    Args:
        meeting_notes_id: ID of meeting notes record
        workflow_id: Temporal workflow ID
        error_message: Error description
        model_info: Model provider and name (may be None if error before model call)

    Returns:
        extraction_run_id: ID of created extraction run
    """
    logger.info(f"Recording extraction failure for meeting_notes_id: {meeting_notes_id}")
    logger.error(f"Failure reason: {error_message}")

    client = get_supabase_client()

    # Find existing extraction_run with status='processing' for this workflow
    params = {
        "workflow_id": f"eq.{workflow_id}",
        "order": "created_at.desc",
        "limit": "1"
    }
    existing_runs = await client._request(
        "GET",
        "extraction_runs",
        params=params
    )

    if isinstance(existing_runs, list) and len(existing_runs) > 0:
        # Update existing extraction run
        extraction_run_id = existing_runs[0]["id"]
        logger.info(f"Updating existing extraction_run to failed: {extraction_run_id}")

        update_data = {
            "status": "failed",
            "model_provider": model_info.get("provider") if model_info else None,
            "model_name": model_info.get("model_name") if model_info else None,
            "error_message": error_message,
            "completed_at": "now()"
        }

        params = {"id": f"eq.{extraction_run_id}"}
        await client._request(
            "PATCH",
            "extraction_runs",
            data=update_data,
            params=params
        )
    else:
        # No existing run found, create new one
        logger.info("No existing extraction_run found, creating failed run")
        extraction_run_data = {
            "meeting_notes_id": meeting_notes_id,
            "workflow_id": workflow_id,
            "status": "failed",
            "model_provider": model_info.get("provider") if model_info else None,
            "model_name": model_info.get("model_name") if model_info else None,
            "error_message": error_message,
            "completed_at": "now()"
        }

        result = await client._request(
            "POST",
            "extraction_runs",
            data=extraction_run_data
        )

        if isinstance(result, list):
            extraction_run = result[0]
        else:
            extraction_run = result

        extraction_run_id = extraction_run["id"]
        logger.info(f"Created failed extraction_run: {extraction_run_id}")

    return extraction_run_id
