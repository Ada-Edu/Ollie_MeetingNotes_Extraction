"""
End-to-end integration tests for the meeting notes extraction workflow.
Tests the complete flow from API trigger through Temporal workflow to database persistence.
"""

import asyncio
import os
import uuid
import pytest
import httpx
from temporalio.client import Client
from temporalio.worker import Worker

# Add src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from workflows.meeting_notes_extraction import ExtractMeetingActionItemsWorkflow
from activities.meeting_notes import (
    validate_meeting_notes_input,
    call_model_for_action_item_extraction,
    persist_extraction_results,
    record_extraction_failure
)
from supabase_client import get_supabase_client


@pytest.fixture
async def temporal_client():
    """Create Temporal client for tests."""
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    client = await Client.connect(temporal_address)
    yield client
    await client.close()


@pytest.fixture
async def supabase_client():
    """Create Supabase client for tests."""
    client = get_supabase_client()
    yield client
    # Cleanup handled by test functions


@pytest.fixture
async def test_meeting_notes_id(supabase_client):
    """Create a test meeting notes record."""
    notes_text = """
Team standup - Test meeting
Attendees: Alice, Bob, Charlie

Action items:
1. Alice to review the test documentation by Friday
2. Bob to update the test database schema by next week
3. Charlie to schedule a follow-up test meeting
    """.strip()

    # Insert meeting notes
    response = await supabase_client._request(
        "POST",
        "meeting_notes",
        data={"notes_text": notes_text}
    )

    if isinstance(response, list):
        meeting_note = response[0]
    else:
        meeting_note = response

    meeting_notes_id = meeting_note["id"]

    yield meeting_notes_id

    # Cleanup - delete meeting notes (cascade will delete extraction_runs and action_items)
    try:
        await supabase_client._request(
            "DELETE",
            "meeting_notes",
            params={"id": f"eq.{meeting_notes_id}"}
        )
    except Exception as e:
        print(f"Cleanup error: {e}")


class TestCompleteExtractionFlow:
    """Test the complete end-to-end extraction flow."""

    @pytest.mark.asyncio
    async def test_complete_workflow_execution(
        self,
        temporal_client,
        supabase_client,
        test_meeting_notes_id
    ):
        """
        Test complete workflow: trigger → validate → extract → persist → verify results.
        """
        # Get meeting notes
        meeting_notes = await supabase_client._request(
            "GET",
            "meeting_notes",
            params={"id": f"eq.{test_meeting_notes_id}"}
        )
        notes_text = meeting_notes[0]["notes_text"]

        # Start workflow
        workflow_id = f"test-extract-{uuid.uuid4()}"
        handle = await temporal_client.start_workflow(
            ExtractMeetingActionItemsWorkflow.run,
            args=[test_meeting_notes_id, notes_text],
            id=workflow_id,
            task_queue="main"
        )

        # Wait for completion (with timeout)
        result = await asyncio.wait_for(handle.result(), timeout=60.0)

        # Verify workflow result
        assert result["status"] == "completed"
        assert "extraction_run_id" in result
        assert result["action_items_count"] > 0

        # Verify extraction_run in database
        extraction_run_id = result["extraction_run_id"]
        extraction_runs = await supabase_client._request(
            "GET",
            "extraction_runs",
            params={"id": f"eq.{extraction_run_id}"}
        )

        assert len(extraction_runs) == 1
        extraction_run = extraction_runs[0]
        assert extraction_run["status"] == "completed"
        assert extraction_run["workflow_id"] == workflow_id
        assert extraction_run["model_provider"] is not None
        assert extraction_run["completed_at"] is not None

        # Verify action items in database
        action_items = await supabase_client._request(
            "GET",
            "action_items",
            params={"extraction_run_id": f"eq.{extraction_run_id}"}
        )

        assert len(action_items) >= 3  # Should extract at least 3 action items
        for item in action_items:
            assert item["description"] is not None
            assert len(item["description"]) > 0
            # confidence should be between 0 and 1
            if item["confidence"] is not None:
                assert 0.0 <= float(item["confidence"]) <= 1.0

    @pytest.mark.asyncio
    async def test_workflow_with_minimal_notes(self, temporal_client, supabase_client):
        """Test workflow with minimal valid notes."""
        notes_text = "Quick sync. John to call client. That's it."

        # Create meeting notes
        response = await supabase_client._request(
            "POST",
            "meeting_notes",
            data={"notes_text": notes_text}
        )
        meeting_notes_id = response[0]["id"] if isinstance(response, list) else response["id"]

        try:
            # Start workflow
            workflow_id = f"test-minimal-{uuid.uuid4()}"
            handle = await temporal_client.start_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=[meeting_notes_id, notes_text],
                id=workflow_id,
                task_queue="main"
            )

            # Wait for completion
            result = await asyncio.wait_for(handle.result(), timeout=60.0)

            # Should complete successfully (even if few/no action items)
            assert result["status"] in ["completed", "failed"]

        finally:
            # Cleanup
            await supabase_client._request(
                "DELETE",
                "meeting_notes",
                params={"id": f"eq.{meeting_notes_id}"}
            )

    @pytest.mark.asyncio
    async def test_workflow_with_unassigned_owners(
        self,
        temporal_client,
        supabase_client
    ):
        """Test that workflow correctly handles action items without clear owners."""
        notes_text = """
Meeting notes:
- Review the design document by next week
- Update the API documentation
- Schedule a team sync
        """.strip()

        # Create meeting notes
        response = await supabase_client._request(
            "POST",
            "meeting_notes",
            data={"notes_text": notes_text}
        )
        meeting_notes_id = response[0]["id"] if isinstance(response, list) else response["id"]

        try:
            # Start workflow
            workflow_id = f"test-unassigned-{uuid.uuid4()}"
            handle = await temporal_client.start_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=[meeting_notes_id, notes_text],
                id=workflow_id,
                task_queue="main"
            )

            result = await asyncio.wait_for(handle.result(), timeout=60.0)

            # Get action items
            extraction_run_id = result["extraction_run_id"]
            action_items = await supabase_client._request(
                "GET",
                "action_items",
                params={"extraction_run_id": f"eq.{extraction_run_id}"}
            )

            # Should have some items with NULL owners (no hallucination)
            unassigned_count = sum(1 for item in action_items if item["owner"] is None)
            assert unassigned_count > 0, "Should have unassigned items (no hallucination)"

        finally:
            # Cleanup
            await supabase_client._request(
                "DELETE",
                "meeting_notes",
                params={"id": f"eq.{meeting_notes_id}"}
            )

    @pytest.mark.asyncio
    async def test_workflow_with_no_due_dates(self, temporal_client, supabase_client):
        """Test that workflow correctly handles vague timing (no hallucinated dates)."""
        notes_text = """
Action items:
1. John to follow up with the team soon
2. Sarah to review the code when she has time
        """.strip()

        # Create meeting notes
        response = await supabase_client._request(
            "POST",
            "meeting_notes",
            data={"notes_text": notes_text}
        )
        meeting_notes_id = response[0]["id"] if isinstance(response, list) else response["id"]

        try:
            # Start workflow
            workflow_id = f"test-no-dates-{uuid.uuid4()}"
            handle = await temporal_client.start_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=[meeting_notes_id, notes_text],
                id=workflow_id,
                task_queue="main"
            )

            result = await asyncio.wait_for(handle.result(), timeout=60.0)

            # Get action items
            extraction_run_id = result["extraction_run_id"]
            action_items = await supabase_client._request(
                "GET",
                "action_items",
                params={"extraction_run_id": f"eq.{extraction_run_id}"}
            )

            # Should have items with NULL due_date (no hallucination)
            no_date_count = sum(1 for item in action_items if item["due_date"] is None)
            assert no_date_count > 0, "Should have items without due dates (no hallucination)"

        finally:
            # Cleanup
            await supabase_client._request(
                "DELETE",
                "meeting_notes",
                params={"id": f"eq.{meeting_notes_id}"}
            )


class TestErrorHandling:
    """Test error handling in the workflow."""

    @pytest.mark.asyncio
    async def test_workflow_with_too_short_notes(
        self,
        temporal_client,
        supabase_client
    ):
        """Test validation failure for too-short notes."""
        notes_text = "Short"  # Less than 10 characters

        # Create meeting notes
        response = await supabase_client._request(
            "POST",
            "meeting_notes",
            data={"notes_text": notes_text}
        )
        meeting_notes_id = response[0]["id"] if isinstance(response, list) else response["id"]

        try:
            # Start workflow
            workflow_id = f"test-short-{uuid.uuid4()}"
            handle = await temporal_client.start_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=[meeting_notes_id, notes_text],
                id=workflow_id,
                task_queue="main"
            )

            result = await asyncio.wait_for(handle.result(), timeout=60.0)

            # Should fail validation
            assert result["status"] == "failed"
            assert "error" in result
            assert "too short" in result["error"].lower() or "minimum" in result["error"].lower()

            # Should have failed extraction_run in database
            extraction_run_id = result["extraction_run_id"]
            extraction_runs = await supabase_client._request(
                "GET",
                "extraction_runs",
                params={"id": f"eq.{extraction_run_id}"}
            )

            assert len(extraction_runs) == 1
            assert extraction_runs[0]["status"] == "failed"
            assert extraction_runs[0]["error_message"] is not None

        finally:
            # Cleanup
            await supabase_client._request(
                "DELETE",
                "meeting_notes",
                params={"id": f"eq.{meeting_notes_id}"}
            )

    @pytest.mark.asyncio
    async def test_workflow_records_failure_in_database(
        self,
        temporal_client,
        supabase_client
    ):
        """Test that workflow failures are properly recorded in database."""
        notes_text = "X"  # Invalid - too short

        # Create meeting notes
        response = await supabase_client._request(
            "POST",
            "meeting_notes",
            data={"notes_text": notes_text}
        )
        meeting_notes_id = response[0]["id"] if isinstance(response, list) else response["id"]

        try:
            # Start workflow
            workflow_id = f"test-record-failure-{uuid.uuid4()}"
            handle = await temporal_client.start_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=[meeting_notes_id, notes_text],
                id=workflow_id,
                task_queue="main"
            )

            result = await asyncio.wait_for(handle.result(), timeout=60.0)

            # Verify failure is recorded
            assert result["status"] == "failed"
            extraction_run_id = result["extraction_run_id"]

            extraction_runs = await supabase_client._request(
                "GET",
                "extraction_runs",
                params={"id": f"eq.{extraction_run_id}"}
            )

            assert len(extraction_runs) == 1
            extraction_run = extraction_runs[0]
            assert extraction_run["status"] == "failed"
            assert extraction_run["error_message"] is not None
            assert extraction_run["completed_at"] is not None

        finally:
            # Cleanup
            await supabase_client._request(
                "DELETE",
                "meeting_notes",
                params={"id": f"eq.{meeting_notes_id}"}
            )


class TestAPIServerIntegration:
    """Test API server workflow trigger endpoint."""

    @pytest.mark.asyncio
    async def test_api_trigger_workflow(self, test_meeting_notes_id, supabase_client):
        """Test triggering workflow via API server."""
        api_url = os.getenv("API_URL", "http://localhost:8000")

        # Get meeting notes
        meeting_notes = await supabase_client._request(
            "GET",
            "meeting_notes",
            params={"id": f"eq.{test_meeting_notes_id}"}
        )
        notes_text = meeting_notes[0]["notes_text"]

        async with httpx.AsyncClient() as client:
            # Call trigger endpoint
            response = await client.post(
                f"{api_url}/trigger-workflow",
                json={
                    "workflow_name": "ExtractMeetingActionItemsWorkflow",
                    "workflow_id": f"test-api-{uuid.uuid4()}",
                    "args": {
                        "meeting_notes_id": test_meeting_notes_id,
                        "notes_text": notes_text
                    },
                    "task_queue": "main"
                },
                timeout=10.0
            )

            # Should succeed
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert "workflow_id" in result

            # Wait a moment for workflow to start
            await asyncio.sleep(2)

    @pytest.mark.asyncio
    async def test_api_health_check(self):
        """Test API health check endpoint."""
        api_url = os.getenv("API_URL", "http://localhost:8000")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/health", timeout=5.0)

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "healthy"
            assert "temporal_connected" in result

    @pytest.mark.asyncio
    async def test_api_trigger_invalid_workflow(self):
        """Test API rejects invalid workflow name."""
        api_url = os.getenv("API_URL", "http://localhost:8000")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/trigger-workflow",
                json={
                    "workflow_name": "InvalidWorkflow",
                    "workflow_id": f"test-invalid-{uuid.uuid4()}",
                    "args": {},
                    "task_queue": "main"
                },
                timeout=5.0
            )

            # Should return error
            assert response.status_code == 400
            result = response.json()
            assert "detail" in result
            assert "unknown workflow" in result["detail"].lower()

    @pytest.mark.asyncio
    async def test_api_trigger_missing_args(self):
        """Test API rejects requests with missing required arguments."""
        api_url = os.getenv("API_URL", "http://localhost:8000")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/trigger-workflow",
                json={
                    "workflow_name": "ExtractMeetingActionItemsWorkflow",
                    "workflow_id": f"test-missing-args-{uuid.uuid4()}",
                    "args": {},  # Missing required args
                    "task_queue": "main"
                },
                timeout=5.0
            )

            # Should return error
            assert response.status_code == 400
            result = response.json()
            assert "detail" in result


class TestDatabasePersistence:
    """Test database persistence of workflow results."""

    @pytest.mark.asyncio
    async def test_extraction_run_created_with_workflow_id(
        self,
        temporal_client,
        supabase_client,
        test_meeting_notes_id
    ):
        """Test that extraction_run is created with correct workflow_id."""
        meeting_notes = await supabase_client._request(
            "GET",
            "meeting_notes",
            params={"id": f"eq.{test_meeting_notes_id}"}
        )
        notes_text = meeting_notes[0]["notes_text"]

        workflow_id = f"test-workflow-id-{uuid.uuid4()}"
        handle = await temporal_client.start_workflow(
            ExtractMeetingActionItemsWorkflow.run,
            args=[test_meeting_notes_id, notes_text],
            id=workflow_id,
            task_queue="main"
        )

        result = await asyncio.wait_for(handle.result(), timeout=60.0)

        # Verify workflow_id matches
        extraction_run_id = result["extraction_run_id"]
        extraction_runs = await supabase_client._request(
            "GET",
            "extraction_runs",
            params={"id": f"eq.{extraction_run_id}"}
        )

        assert extraction_runs[0]["workflow_id"] == workflow_id

    @pytest.mark.asyncio
    async def test_action_items_linked_to_extraction_run(
        self,
        temporal_client,
        supabase_client,
        test_meeting_notes_id
    ):
        """Test that action items are properly linked to extraction_run."""
        meeting_notes = await supabase_client._request(
            "GET",
            "meeting_notes",
            params={"id": f"eq.{test_meeting_notes_id}"}
        )
        notes_text = meeting_notes[0]["notes_text"]

        workflow_id = f"test-linked-{uuid.uuid4()}"
        handle = await temporal_client.start_workflow(
            ExtractMeetingActionItemsWorkflow.run,
            args=[test_meeting_notes_id, notes_text],
            id=workflow_id,
            task_queue="main"
        )

        result = await asyncio.wait_for(handle.result(), timeout=60.0)

        extraction_run_id = result["extraction_run_id"]

        # Get action items
        action_items = await supabase_client._request(
            "GET",
            "action_items",
            params={"extraction_run_id": f"eq.{extraction_run_id}"}
        )

        # All action items should reference the extraction_run
        for item in action_items:
            assert item["extraction_run_id"] == extraction_run_id

    @pytest.mark.asyncio
    async def test_cascade_delete_extraction_run(
        self,
        temporal_client,
        supabase_client,
        test_meeting_notes_id
    ):
        """Test that deleting meeting_notes cascades to extraction_runs and action_items."""
        meeting_notes = await supabase_client._request(
            "GET",
            "meeting_notes",
            params={"id": f"eq.{test_meeting_notes_id}"}
        )
        notes_text = meeting_notes[0]["notes_text"]

        workflow_id = f"test-cascade-{uuid.uuid4()}"
        handle = await temporal_client.start_workflow(
            ExtractMeetingActionItemsWorkflow.run,
            args=[test_meeting_notes_id, notes_text],
            id=workflow_id,
            task_queue="main"
        )

        result = await asyncio.wait_for(handle.result(), timeout=60.0)
        extraction_run_id = result["extraction_run_id"]

        # Delete meeting notes
        await supabase_client._request(
            "DELETE",
            "meeting_notes",
            params={"id": f"eq.{test_meeting_notes_id}"}
        )

        # Extraction run should also be deleted (cascade)
        extraction_runs = await supabase_client._request(
            "GET",
            "extraction_runs",
            params={"id": f"eq.{extraction_run_id}"}
        )

        assert len(extraction_runs) == 0

        # Action items should also be deleted
        action_items = await supabase_client._request(
            "GET",
            "action_items",
            params={"extraction_run_id": f"eq.{extraction_run_id}"}
        )

        assert len(action_items) == 0
