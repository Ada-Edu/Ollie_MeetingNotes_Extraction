"""Integration tests for workflow execution with Temporal."""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

# Import workflow and activities
from workflows.meeting_notes_extraction import ExtractMeetingActionItemsWorkflow
from activities.meeting_notes import (
    validate_meeting_notes_input,
    call_model_for_action_item_extraction,
    persist_extraction_results
)


@pytest.mark.integration
class TestWorkflowExecution:
    """Integration tests for workflow execution."""

    @pytest.mark.asyncio
    async def test_successful_workflow_execution(self):
        """Test complete workflow execution with mocked activities."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock the activities
            async def mock_validate(notes: str) -> None:
                """Mock validation - just pass."""
                pass

            async def mock_extract(notes: str) -> dict:
                """Mock extraction with sample data."""
                return {
                    "action_items": [
                        {
                            "description": "Follow up with client",
                            "owner": "John",
                            "due_date": "2026-07-15",
                            "confidence": 0.95
                        }
                    ],
                    "model_provider": "azure",
                    "model_name": "gpt-4"
                }

            async def mock_persist(meeting_notes_id: str, workflow_id: str,
                                  action_items: list, model_info: dict,
                                  raw_response: dict) -> str:
                """Mock persistence."""
                return "test-extraction-run-id"

            # Register worker with mocked activities
            worker = Worker(
                env.client,
                task_queue="test",
                workflows=[ExtractMeetingActionItemsWorkflow],
                activities=[mock_validate, mock_extract, mock_persist]
            )

            async with worker:
                # Execute workflow
                result = await env.client.execute_workflow(
                    ExtractMeetingActionItemsWorkflow.run,
                    args=["test-note-id", "Test meeting notes content"],
                    id="test-workflow-123",
                    task_queue="test",
                    execution_timeout=timedelta(seconds=30)
                )

                # Verify result
                assert result is not None
                assert "extraction_run_id" in result or isinstance(result, str)

    @pytest.mark.asyncio
    async def test_workflow_with_validation_failure(self):
        """Test workflow handles validation failures."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            async def mock_validate_fail(notes: str) -> None:
                """Mock validation that fails."""
                raise ValueError("Notes too short")

            worker = Worker(
                env.client,
                task_queue="test",
                workflows=[ExtractMeetingActionItemsWorkflow],
                activities=[mock_validate_fail]
            )

            async with worker:
                # Execute workflow - should propagate error
                with pytest.raises(Exception):
                    await env.client.execute_workflow(
                        ExtractMeetingActionItemsWorkflow.run,
                        args=["test-note-id", "Bad"],
                        id="test-workflow-fail",
                        task_queue="test",
                        execution_timeout=timedelta(seconds=30)
                    )

    @pytest.mark.asyncio
    async def test_workflow_retry_on_activity_failure(self):
        """Test workflow retries failed activities."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            call_count = {"count": 0}

            async def mock_validate(notes: str) -> None:
                pass

            async def mock_extract_with_retry(notes: str) -> dict:
                """Mock that fails first time, succeeds second."""
                call_count["count"] += 1
                if call_count["count"] == 1:
                    raise Exception("Temporary failure")
                return {
                    "action_items": [],
                    "model_provider": "azure",
                    "model_name": "gpt-4"
                }

            async def mock_persist(meeting_notes_id: str, workflow_id: str,
                                  action_items: list, model_info: dict,
                                  raw_response: dict) -> str:
                return "test-run-id"

            worker = Worker(
                env.client,
                task_queue="test",
                workflows=[ExtractMeetingActionItemsWorkflow],
                activities=[mock_validate, mock_extract_with_retry, mock_persist]
            )

            async with worker:
                result = await env.client.execute_workflow(
                    ExtractMeetingActionItemsWorkflow.run,
                    args=["test-note-id", "Test notes"],
                    id="test-workflow-retry",
                    task_queue="test",
                    execution_timeout=timedelta(seconds=30)
                )

                # Should have retried and succeeded
                assert result is not None
                assert call_count["count"] >= 1


@pytest.mark.integration
class TestWorkflowWithRealActivities:
    """Integration tests using real activity implementations with mocks."""

    @pytest.mark.asyncio
    async def test_validation_activity(self):
        """Test real validation activity."""
        # Valid input
        await validate_meeting_notes_input("This is valid meeting notes content")

        # Invalid inputs
        with pytest.raises(ValueError, match="cannot be empty"):
            await validate_meeting_notes_input("")

        with pytest.raises(ValueError, match="too short"):
            await validate_meeting_notes_input("Short")

    @pytest.mark.asyncio
    @patch('activities.meeting_notes.get_model_client')
    async def test_extraction_activity_with_mock_client(self, mock_get_client):
        """Test extraction activity with mocked model client."""
        # Setup mock client
        mock_client = Mock()
        mock_client.get_provider_name.return_value = "azure"
        mock_client.get_model_name.return_value = "gpt-4"

        mock_item = Mock()
        mock_item.to_dict.return_value = {
            "description": "Test action",
            "owner": "John",
            "due_date": "2026-07-15",
            "confidence": 0.95
        }
        mock_client.extract_action_items = AsyncMock(return_value=[mock_item])
        mock_get_client.return_value = mock_client

        # Execute activity
        result = await call_model_for_action_item_extraction(
            "Team meeting: John to follow up with client by next week"
        )

        # Verify results
        assert "action_items" in result
        assert "model_provider" in result
        assert result["model_provider"] == "azure"
        assert len(result["action_items"]) == 1
        assert result["action_items"][0]["owner"] == "John"

    @pytest.mark.asyncio
    @patch('activities.meeting_notes.get_supabase_client')
    async def test_persistence_activity_with_mock_db(self, mock_get_client):
        """Test persistence activity with mocked Supabase."""
        # Setup mock Supabase client
        mock_client = Mock()
        mock_client._request = AsyncMock(return_value={
            "id": "test-run-id",
            "status": "completed"
        })
        mock_get_client.return_value = mock_client

        # Execute activity
        result = await persist_extraction_results(
            meeting_notes_id="test-note-id",
            workflow_id="test-workflow-id",
            action_items=[{
                "description": "Test action",
                "owner": "John",
                "due_date": "2026-07-15",
                "confidence": 0.95
            }],
            model_info={"provider": "azure", "model_name": "gpt-4"},
            raw_response={"action_items": []}
        )

        # Verify Supabase was called
        assert mock_client._request.called
