import pytest
import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch
from temporalio.client import Client, WorkflowFailureError
from temporalio.common import RetryPolicy
from temporalio.exceptions import TimeoutError, ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from workflows.meeting_notes_extraction import ExtractMeetingActionItemsWorkflow
from activities.meeting_notes import (
    validate_meeting_notes_input,
    call_model_for_action_item_extraction,
    persist_extraction_results,
    record_extraction_failure
)


class TestTemporalWorkflowIntegration:
    """Integration tests for Temporal workflow execution."""

    @pytest.fixture
    async def temporal_client(self):
        """Create a test Temporal client."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            yield env.client

    @pytest.fixture
    async def workflow_worker(self, temporal_client):
        """Create a worker for testing workflows."""
        worker = Worker(
            temporal_client,
            task_queue="test-task-queue",
            workflows=[ExtractMeetingActionItemsWorkflow],
            activities=[
                validate_meeting_notes_input,
                call_model_for_action_item_extraction,
                persist_extraction_results,
                record_extraction_failure
            ],
        )
        async with worker:
            yield worker

    @pytest.mark.asyncio
    async def test_complete_workflow_execution_success(self, temporal_client, workflow_worker):
        """Test successful completion of entire workflow execution."""
        workflow_id = "test-workflow-success"

        test_notes = "Team meeting notes: John will send the report by Friday. Sarah will schedule follow-up meeting."

        # Mock only external dependencies (model and database)
        with patch("activities.meeting_notes.get_model_client") as mock_model_client, \
             patch("activities.meeting_notes.get_supabase_client") as mock_supabase:

            # Mock model client
            mock_client_instance = AsyncMock()
            mock_client_instance.get_provider_name.return_value = "openai"
            mock_client_instance.get_model_name.return_value = "gpt-4"
            mock_action_item_1 = Mock()
            mock_action_item_1.to_dict.return_value = {
                "description": "Send report",
                "owner": "John",
                "due_date": "Friday",
                "confidence": 0.95
            }
            mock_action_item_2 = Mock()
            mock_action_item_2.to_dict.return_value = {
                "description": "Schedule follow-up meeting",
                "owner": "Sarah",
                "due_date": None,
                "confidence": 0.90
            }
            mock_client_instance.extract_action_items.return_value = [
                mock_action_item_1,
                mock_action_item_2
            ]
            mock_model_client.return_value = mock_client_instance

            # Mock supabase client
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                [],  # No existing runs
                [{"id": "extraction-run-123"}],  # Created extraction run
                None,  # Created action item 1
                None   # Created action item 2
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-123", test_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Verify result structure
            assert result["status"] == "completed"
            assert result["extraction_run_id"] == "extraction-run-123"
            assert result["action_items_count"] == 2
            assert result["model_provider"] == "openai"
            assert result["model_name"] == "gpt-4"

            # Verify model was called with correct notes
            mock_client_instance.extract_action_items.assert_called_once_with(test_notes)

            # Verify database interactions
            assert mock_supabase_instance._request.call_count == 4

    @pytest.mark.asyncio
    async def test_validation_failures(self, temporal_client, workflow_worker):
        """Test workflow handling of validation failures."""
        workflow_id = "test-workflow-validation-failure"

        # Test with empty notes - should fail validation
        empty_notes = ""

        with patch("activities.meeting_notes.get_supabase_client") as mock_supabase:
            # Mock supabase for failure recording
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                [],  # No existing runs
                [{"id": "extraction-run-failed-123"}]  # Created failure record
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow - it should handle validation error gracefully
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-456", empty_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Workflow should return failed status, not raise exception
            assert result["status"] == "failed"
            assert result["extraction_run_id"] == "extraction-run-failed-123"
            assert "empty" in result["error"].lower()

            # Verify failure was recorded in database
            assert mock_supabase_instance._request.call_count >= 2

    @pytest.mark.asyncio
    async def test_model_extraction_failures(self, temporal_client, workflow_worker):
        """Test workflow handling of model extraction failures."""
        workflow_id = "test-workflow-extraction-failure"

        test_notes = "Valid meeting notes with sufficient length for validation to pass."

        with patch("activities.meeting_notes.get_model_client") as mock_model_client, \
             patch("activities.meeting_notes.get_supabase_client") as mock_supabase:

            # Mock model client to fail
            mock_client_instance = AsyncMock()
            mock_client_instance.get_provider_name.return_value = "openai"
            mock_client_instance.get_model_name.return_value = "gpt-4"
            mock_client_instance.extract_action_items.side_effect = Exception(
                "API rate limit exceeded"
            )
            mock_model_client.return_value = mock_client_instance

            # Mock supabase for failure recording
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                [],  # No existing runs
                [{"id": "extraction-run-failed-456"}]  # Created failure record
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-789", test_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Workflow should handle failure gracefully
            assert result["status"] == "failed"
            assert result["extraction_run_id"] == "extraction-run-failed-456"
            assert "rate limit" in result["error"].lower()
            assert result["model_provider"] == "openai"
            assert result["model_name"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_multiple_action_items(self, temporal_client, workflow_worker):
        """Test workflow processing multiple action items successfully."""
        workflow_id = "test-workflow-multiple-items"

        test_notes = "Long meeting with many action items. " * 10  # Sufficient length

        with patch("activities.meeting_notes.get_model_client") as mock_model_client, \
             patch("activities.meeting_notes.get_supabase_client") as mock_supabase:

            # Mock model client to return 10 action items
            mock_client_instance = AsyncMock()
            mock_client_instance.get_provider_name.return_value = "openai"
            mock_client_instance.get_model_name.return_value = "gpt-4"

            action_items = []
            for i in range(1, 11):
                mock_item = Mock()
                mock_item.to_dict.return_value = {
                    "description": f"Task {i}",
                    "owner": f"Person{i}",
                    "due_date": None,
                    "confidence": 0.85
                }
                action_items.append(mock_item)

            mock_client_instance.extract_action_items.return_value = action_items
            mock_model_client.return_value = mock_client_instance

            # Mock supabase client
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                [],  # No existing runs
                [{"id": "extraction-run-multi-123"}],  # Created extraction run
                *[None for _ in range(10)]  # Created 10 action items
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-multi-123", test_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Verify result
            assert result["status"] == "completed"
            assert result["action_items_count"] == 10
            assert result["extraction_run_id"] == "extraction-run-multi-123"

            # Verify all 10 action items were persisted (1 run + 1 extraction record + 10 items = 12 calls)
            assert mock_supabase_instance._request.call_count == 12

    @pytest.mark.asyncio
    async def test_retry_on_temporary_failure(self, temporal_client, workflow_worker):
        """Test workflow retry mechanism on temporary failures."""
        workflow_id = "test-workflow-retry-temporary"

        test_notes = "Valid meeting notes for retry test with sufficient length."

        call_count = {"count": 0}

        def mock_extract_with_retry(notes):
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise Exception("Temporary network error")
            # Success on third attempt
            mock_item = Mock()
            mock_item.to_dict.return_value = {
                "description": "Success after retry",
                "owner": "Test",
                "due_date": None,
                "confidence": 0.90
            }
            return [mock_item]

        with patch("activities.meeting_notes.get_model_client") as mock_model_client, \
             patch("activities.meeting_notes.get_supabase_client") as mock_supabase:

            # Mock model client with retry behavior
            mock_client_instance = AsyncMock()
            mock_client_instance.get_provider_name.return_value = "openai"
            mock_client_instance.get_model_name.return_value = "gpt-4"
            mock_client_instance.extract_action_items.side_effect = mock_extract_with_retry
            mock_model_client.return_value = mock_client_instance

            # Mock supabase client
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                [],  # No existing runs
                [{"id": "extraction-run-retry-123"}],  # Created extraction run
                None  # Created action item
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-retry-123", test_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Verify workflow succeeded after retries
            assert result["status"] == "completed"
            assert result["action_items_count"] == 1
            assert call_count["count"] == 3  # Failed twice, succeeded on third attempt

    @pytest.mark.asyncio
    async def test_timeout_handling(self, temporal_client, workflow_worker):
        """Test workflow timeout handling."""
        workflow_id = "test-workflow-timeout"

        test_notes = "Valid meeting notes for timeout test with sufficient length."

        async def slow_extract(notes):
            await asyncio.sleep(100)  # Simulate long-running operation
            return []

        with patch("activities.meeting_notes.get_model_client") as mock_model_client:
            # Mock model client to be slow
            mock_client_instance = AsyncMock()
            mock_client_instance.get_provider_name.return_value = "openai"
            mock_client_instance.get_model_name.return_value = "gpt-4"
            mock_client_instance.extract_action_items.side_effect = slow_extract
            mock_model_client.return_value = mock_client_instance

            # Execute workflow with short timeout
            with pytest.raises(WorkflowFailureError) as exc_info:
                await temporal_client.execute_workflow(
                    ExtractMeetingActionItemsWorkflow.run,
                    args=["meeting-timeout-123", test_notes],
                    id=workflow_id,
                    task_queue="test-task-queue",
                    execution_timeout=timedelta(seconds=2),
                )

            # Verify timeout occurred
            assert "timeout" in str(exc_info.value).lower() or \
                   "time" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_empty_action_items(self, temporal_client, workflow_worker):
        """Test workflow handling when no action items are extracted."""
        workflow_id = "test-workflow-empty-items"

        test_notes = "Meeting notes with no actionable items, just general discussion."

        with patch("activities.meeting_notes.get_model_client") as mock_model_client, \
             patch("activities.meeting_notes.get_supabase_client") as mock_supabase:

            # Mock model client to return empty list
            mock_client_instance = AsyncMock()
            mock_client_instance.get_provider_name.return_value = "openai"
            mock_client_instance.get_model_name.return_value = "gpt-4"
            mock_client_instance.extract_action_items.return_value = []
            mock_model_client.return_value = mock_client_instance

            # Mock supabase client
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                [],  # No existing runs
                [{"id": "extraction-run-empty-123"}]  # Created extraction run
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-empty-123", test_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Verify result
            assert result["status"] == "completed"
            assert result["action_items_count"] == 0
            assert result["extraction_run_id"] == "extraction-run-empty-123"

    @pytest.mark.asyncio
    async def test_activity_retry_with_eventual_success(self, temporal_client, workflow_worker):
        """Test activity-level retry mechanism with eventual success."""
        workflow_id = "test-workflow-activity-retry"

        test_notes = "Valid meeting notes for activity retry test with sufficient length."

        call_count = {"count": 0}

        def mock_extract_with_retry(notes):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise Exception("First attempt fails")
            # Success on second attempt
            mock_item = Mock()
            mock_item.to_dict.return_value = {
                "description": "Task after retry",
                "owner": "Test",
                "due_date": None,
                "confidence": 0.88
            }
            return [mock_item]

        with patch("activities.meeting_notes.get_model_client") as mock_model_client, \
             patch("activities.meeting_notes.get_supabase_client") as mock_supabase:

            # Mock model client with retry behavior
            mock_client_instance = AsyncMock()
            mock_client_instance.get_provider_name.return_value = "openai"
            mock_client_instance.get_model_name.return_value = "gpt-4"
            mock_client_instance.extract_action_items.side_effect = mock_extract_with_retry
            mock_model_client.return_value = mock_client_instance

            # Mock supabase client
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                [],  # No existing runs
                [{"id": "extraction-run-activity-retry-123"}],  # Created extraction run
                None  # Created action item
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-activity-retry-123", test_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Verify workflow succeeded after activity retry
            assert result["status"] == "completed"
            assert result["action_items_count"] == 1
            assert call_count["count"] == 2  # Failed once, succeeded on second attempt


    @pytest.mark.asyncio
    async def test_validation_too_short_notes(self, temporal_client, workflow_worker):
        """Test workflow validation failure with notes that are too short."""
        workflow_id = "test-workflow-short-notes"

        # Less than 10 characters
        short_notes = "Too short"

        with patch("activities.meeting_notes.get_supabase_client") as mock_supabase:
            # Mock supabase for failure recording
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                [],  # No existing runs
                [{"id": "extraction-run-short-123"}]  # Created failure record
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-short-123", short_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Verify validation failure
            assert result["status"] == "failed"
            assert "too short" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_validation_too_long_notes(self, temporal_client, workflow_worker):
        """Test workflow validation failure with notes exceeding character limit."""
        workflow_id = "test-workflow-long-notes"

        # More than 10,000 characters
        long_notes = "x" * 10001

        with patch("activities.meeting_notes.get_supabase_client") as mock_supabase:
            # Mock supabase for failure recording
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                [],  # No existing runs
                [{"id": "extraction-run-long-123"}]  # Created failure record
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-long-123", long_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Verify validation failure
            assert result["status"] == "failed"
            assert "exceed" in result["error"].lower() or "10,000" in result["error"]

    @pytest.mark.asyncio
    async def test_database_persistence_failure(self, temporal_client, workflow_worker):
        """Test workflow handling of database persistence failures."""
        workflow_id = "test-workflow-db-failure"

        test_notes = "Meeting notes for database failure test with sufficient length."

        with patch("activities.meeting_notes.get_model_client") as mock_model_client, \
             patch("activities.meeting_notes.get_supabase_client") as mock_supabase:

            # Mock model client to succeed
            mock_client_instance = AsyncMock()
            mock_client_instance.get_provider_name.return_value = "openai"
            mock_client_instance.get_model_name.return_value = "gpt-4"
            mock_item = Mock()
            mock_item.to_dict.return_value = {
                "description": "Test task",
                "owner": "Test",
                "due_date": None,
                "confidence": 0.90
            }
            mock_client_instance.extract_action_items.return_value = [mock_item]
            mock_model_client.return_value = mock_client_instance

            # Mock supabase to fail during persistence
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                Exception("Database connection failed")
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-db-fail-123", test_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Verify workflow handles database failure
            assert result["status"] == "failed"
            assert "database" in result["error"].lower() or "connection" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_workflow_with_existing_extraction_run(self, temporal_client, workflow_worker):
        """Test workflow updating existing extraction run instead of creating new one."""
        workflow_id = "test-workflow-existing-run"

        test_notes = "Meeting notes for testing existing extraction run update."

        with patch("activities.meeting_notes.get_model_client") as mock_model_client, \
             patch("activities.meeting_notes.get_supabase_client") as mock_supabase:

            # Mock model client
            mock_client_instance = AsyncMock()
            mock_client_instance.get_provider_name.return_value = "anthropic"
            mock_client_instance.get_model_name.return_value = "claude-3-sonnet"
            mock_item = Mock()
            mock_item.to_dict.return_value = {
                "description": "Update existing run",
                "owner": "Test",
                "due_date": None,
                "confidence": 0.92
            }
            mock_client_instance.extract_action_items.return_value = [mock_item]
            mock_model_client.return_value = mock_client_instance

            # Mock supabase to return existing run
            existing_run_id = "existing-run-456"
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                [{"id": existing_run_id, "status": "processing"}],  # Found existing run
                None,  # Updated extraction run
                None   # Created action item
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-existing-123", test_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Verify result uses existing run
            assert result["status"] == "completed"
            assert result["extraction_run_id"] == existing_run_id
            assert result["action_items_count"] == 1

    @pytest.mark.asyncio
    async def test_workflow_with_different_model_provider(self, temporal_client, workflow_worker):
        """Test workflow execution with different model provider."""
        workflow_id = "test-workflow-different-provider"

        test_notes = "Meeting notes for testing different model provider support."

        with patch("activities.meeting_notes.get_model_client") as mock_model_client, \
             patch("activities.meeting_notes.get_supabase_client") as mock_supabase:

            # Mock model client with different provider
            mock_client_instance = AsyncMock()
            mock_client_instance.get_provider_name.return_value = "anthropic"
            mock_client_instance.get_model_name.return_value = "claude-3-opus"
            mock_item = Mock()
            mock_item.to_dict.return_value = {
                "description": "Task from Claude",
                "owner": "Alice",
                "due_date": "2026-07-15",
                "confidence": 0.96
            }
            mock_client_instance.extract_action_items.return_value = [mock_item]
            mock_model_client.return_value = mock_client_instance

            # Mock supabase client
            mock_supabase_instance = AsyncMock()
            mock_supabase_instance._request.side_effect = [
                [],  # No existing runs
                [{"id": "extraction-run-anthropic-123"}],  # Created extraction run
                None  # Created action item
            ]
            mock_supabase.return_value = mock_supabase_instance

            # Execute workflow
            result = await temporal_client.execute_workflow(
                ExtractMeetingActionItemsWorkflow.run,
                args=["meeting-anthropic-123", test_notes],
                id=workflow_id,
                task_queue="test-task-queue",
            )

            # Verify correct provider information
            assert result["status"] == "completed"
            assert result["model_provider"] == "anthropic"
            assert result["model_name"] == "claude-3-opus"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
