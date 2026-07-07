"""
Integration tests for Temporal workflow execution end-to-end.
Tests ExtractMeetingActionItemsWorkflow with real activities and mocked external services.

@group integration
"""

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
import uuid

from workflows.meeting_notes_extraction import ExtractMeetingActionItemsWorkflow
from activities.meeting_notes import (
    validate_meeting_notes_input,
    call_model_for_action_item_extraction,
    persist_extraction_results,
    record_extraction_failure
)


@pytest.mark.integration
class TestTemporalWorkflowIntegration:
    """Integration tests for Temporal workflow with activities."""

    @pytest.mark.asyncio
    async def test_complete_workflow_execution_success(self):
        """Test complete workflow from validation to persistence."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock model client
            mock_model_client = Mock()
            mock_model_client.get_provider_name.return_value = "azure"
            mock_model_client.get_model_name.return_value = "gpt-4"

            mock_action_item = Mock()
            mock_action_item.to_dict.return_value = {
                "description": "Follow up with stakeholders",
                "owner": "John Smith",
                "due_date": "2026-07-15",
                "confidence": 0.92
            }
            mock_model_client.extract_action_items = AsyncMock(
                return_value=[mock_action_item]
            )

            # Mock Supabase client
            mock_supabase_client = Mock()
            mock_supabase_client._request = AsyncMock(
                side_effect=[
                    # First call: GET to find existing extraction run
                    [{
                        "id": "test-extraction-run-id",
                        "status": "processing",
                        "workflow_id": "test-workflow-123"
                    }],
                    # Second call: PATCH to update extraction run
                    {
                        "id": "test-extraction-run-id",
                        "status": "completed"
                    },
                    # Subsequent calls: POST action items
                    {"id": "action-item-1"},
                ]
            )

            with patch('activities.meeting_notes.get_model_client', return_value=mock_model_client), \
                 patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase_client):

                worker = Worker(
                    env.client,
                    task_queue="test",
                    workflows=[ExtractMeetingActionItemsWorkflow],
                    activities=[
                        validate_meeting_notes_input,
                        call_model_for_action_item_extraction,
                        persist_extraction_results,
                        record_extraction_failure
                    ]
                )

                async with worker:
                    result = await env.client.execute_workflow(
                        ExtractMeetingActionItemsWorkflow.run,
                        args=[
                            "test-meeting-note-id",
                            "Team meeting: John needs to follow up with stakeholders by July 15th"
                        ],
                        id="test-workflow-123",
                        task_queue="test",
                        execution_timeout=timedelta(seconds=30)
                    )

                    # Verify result
                    assert result is not None
                    assert result["status"] == "completed"
                    assert result["extraction_run_id"] == "test-extraction-run-id"
                    assert result["action_items_count"] == 1
                    assert result["model_provider"] == "azure"
                    assert result["model_name"] == "gpt-4"

                    # Verify model client was called
                    mock_model_client.extract_action_items.assert_called_once()

                    # Verify Supabase was called to persist results
                    assert mock_supabase_client._request.called
                    assert mock_supabase_client._request.call_count >= 2

    @pytest.mark.asyncio
    async def test_workflow_validation_failure(self):
        """Test workflow handles validation failures correctly."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            mock_supabase_client = Mock()
            mock_supabase_client._request = AsyncMock(
                return_value=[{
                    "id": "test-extraction-run-id",
                    "workflow_id": "test-workflow-fail"
                }]
            )

            with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase_client):
                worker = Worker(
                    env.client,
                    task_queue="test",
                    workflows=[ExtractMeetingActionItemsWorkflow],
                    activities=[
                        validate_meeting_notes_input,
                        call_model_for_action_item_extraction,
                        persist_extraction_results,
                        record_extraction_failure
                    ]
                )

                async with worker:
                    # Execute with invalid input (too short)
                    result = await env.client.execute_workflow(
                        ExtractMeetingActionItemsWorkflow.run,
                        args=["test-meeting-note-id", "Short"],
                        id="test-workflow-fail",
                        task_queue="test",
                        execution_timeout=timedelta(seconds=30)
                    )

                    # Should return failed status
                    assert result["status"] == "failed"
                    assert "error" in result
                    assert "too short" in result["error"].lower()
                    assert result["extraction_run_id"] == "test-extraction-run-id"

    @pytest.mark.asyncio
    async def test_workflow_model_extraction_failure(self):
        """Test workflow handles model extraction failures."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock model client that fails
            mock_model_client = Mock()
            mock_model_client.get_provider_name.return_value = "bedrock"
            mock_model_client.get_model_name.return_value = "claude-3"
            mock_model_client.extract_action_items = AsyncMock(
                side_effect=Exception("Model API timeout")
            )

            mock_supabase_client = Mock()
            mock_supabase_client._request = AsyncMock(
                return_value=[{
                    "id": "test-extraction-run-id",
                    "workflow_id": "test-workflow-model-fail"
                }]
            )

            with patch('activities.meeting_notes.get_model_client', return_value=mock_model_client), \
                 patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase_client):

                worker = Worker(
                    env.client,
                    task_queue="test",
                    workflows=[ExtractMeetingActionItemsWorkflow],
                    activities=[
                        validate_meeting_notes_input,
                        call_model_for_action_item_extraction,
                        persist_extraction_results,
                        record_extraction_failure
                    ]
                )

                async with worker:
                    result = await env.client.execute_workflow(
                        ExtractMeetingActionItemsWorkflow.run,
                        args=[
                            "test-meeting-note-id",
                            "Valid meeting notes that will fail at model extraction"
                        ],
                        id="test-workflow-model-fail",
                        task_queue="test",
                        execution_timeout=timedelta(seconds=30)
                    )

                    # Should record failure
                    assert result["status"] == "failed"
                    assert "Model API timeout" in result["error"]
                    assert result["extraction_run_id"] is not None

    @pytest.mark.asyncio
    async def test_workflow_with_multiple_action_items(self):
        """Test workflow handling multiple action items."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock model client returning multiple items
            mock_model_client = Mock()
            mock_model_client.get_provider_name.return_value = "bedrock"
            mock_model_client.get_model_name.return_value = "claude-3-sonnet"

            mock_items = []
            for i in range(5):
                mock_item = Mock()
                mock_item.to_dict.return_value = {
                    "description": f"Action item {i+1}",
                    "owner": f"Person{i+1}",
                    "due_date": f"2026-07-{10+i}",
                    "confidence": 0.85 + (i * 0.02)
                }
                mock_items.append(mock_item)

            mock_model_client.extract_action_items = AsyncMock(return_value=mock_items)

            mock_supabase_client = Mock()
            mock_supabase_client._request = AsyncMock(
                side_effect=[
                    # GET existing run
                    [{"id": "test-run-multi", "workflow_id": "test-workflow-multi"}],
                    # PATCH update run
                    {"id": "test-run-multi"},
                    # POST action items (5 calls)
                    {"id": "item-1"},
                    {"id": "item-2"},
                    {"id": "item-3"},
                    {"id": "item-4"},
                    {"id": "item-5"},
                ]
            )

            with patch('activities.meeting_notes.get_model_client', return_value=mock_model_client), \
                 patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase_client):

                worker = Worker(
                    env.client,
                    task_queue="test",
                    workflows=[ExtractMeetingActionItemsWorkflow],
                    activities=[
                        validate_meeting_notes_input,
                        call_model_for_action_item_extraction,
                        persist_extraction_results,
                        record_extraction_failure
                    ]
                )

                async with worker:
                    result = await env.client.execute_workflow(
                        ExtractMeetingActionItemsWorkflow.run,
                        args=[
                            "test-meeting-note-id",
                            "Long meeting with many action items discussed"
                        ],
                        id="test-workflow-multi",
                        task_queue="test",
                        execution_timeout=timedelta(seconds=30)
                    )

                    assert result["status"] == "completed"
                    assert result["action_items_count"] == 5

                    # Verify all action items were persisted (1 GET + 1 PATCH + 5 POST = 7)
                    assert mock_supabase_client._request.call_count == 7

    @pytest.mark.asyncio
    async def test_workflow_retry_on_temporary_failure(self):
        """Test workflow retries on temporary failures."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            call_count = {"count": 0}

            # Mock model client that fails first time
            mock_model_client = Mock()
            mock_model_client.get_provider_name.return_value = "azure"
            mock_model_client.get_model_name.return_value = "gpt-4"

            async def extract_with_retry(notes: str):
                call_count["count"] += 1
                if call_count["count"] == 1:
                    raise Exception("Temporary network error")

                mock_item = Mock()
                mock_item.to_dict.return_value = {
                    "description": "Recovered action",
                    "owner": "Alice",
                    "due_date": None,
                    "confidence": 0.88
                }
                return [mock_item]

            mock_model_client.extract_action_items = extract_with_retry

            mock_supabase_client = Mock()
            mock_supabase_client._request = AsyncMock(
                side_effect=[
                    [{"id": "test-run-retry", "workflow_id": "test-workflow-retry"}],
                    {"id": "test-run-retry"},
                    {"id": "item-1"},
                ]
            )

            with patch('activities.meeting_notes.get_model_client', return_value=mock_model_client), \
                 patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase_client):

                worker = Worker(
                    env.client,
                    task_queue="test",
                    workflows=[ExtractMeetingActionItemsWorkflow],
                    activities=[
                        validate_meeting_notes_input,
                        call_model_for_action_item_extraction,
                        persist_extraction_results,
                        record_extraction_failure
                    ]
                )

                async with worker:
                    result = await env.client.execute_workflow(
                        ExtractMeetingActionItemsWorkflow.run,
                        args=["test-meeting-note-id", "Test meeting notes for retry"],
                        id="test-workflow-retry",
                        task_queue="test",
                        execution_timeout=timedelta(seconds=30)
                    )

                    # Should succeed after retry
                    assert result["status"] == "completed"
                    assert result["action_items_count"] == 1
                    assert call_count["count"] == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(self):
        """Test workflow handles activity timeouts."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock model client that takes too long
            mock_model_client = Mock()
            mock_model_client.get_provider_name.return_value = "azure"
            mock_model_client.get_model_name.return_value = "gpt-4"

            async def slow_extract(notes: str):
                await asyncio.sleep(100)  # Longer than timeout
                return []

            mock_model_client.extract_action_items = slow_extract

            mock_supabase_client = Mock()
            mock_supabase_client._request = AsyncMock(
                return_value=[{
                    "id": "test-run-timeout",
                    "workflow_id": "test-workflow-timeout"
                }]
            )

            with patch('activities.meeting_notes.get_model_client', return_value=mock_model_client), \
                 patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase_client):

                worker = Worker(
                    env.client,
                    task_queue="test",
                    workflows=[ExtractMeetingActionItemsWorkflow],
                    activities=[
                        validate_meeting_notes_input,
                        call_model_for_action_item_extraction,
                        persist_extraction_results,
                        record_extraction_failure
                    ]
                )

                async with worker:
                    result = await env.client.execute_workflow(
                        ExtractMeetingActionItemsWorkflow.run,
                        args=["test-meeting-note-id", "Test timeout handling"],
                        id="test-workflow-timeout",
                        task_queue="test",
                        execution_timeout=timedelta(seconds=30)
                    )

                    # Should fail and record error
                    assert result["status"] == "failed"
                    assert "error" in result

    @pytest.mark.asyncio
    async def test_workflow_with_empty_action_items(self):
        """Test workflow handles case where no action items are found."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Mock model client returning empty list
            mock_model_client = Mock()
            mock_model_client.get_provider_name.return_value = "bedrock"
            mock_model_client.get_model_name.return_value = "claude-3-haiku"
            mock_model_client.extract_action_items = AsyncMock(return_value=[])

            mock_supabase_client = Mock()
            mock_supabase_client._request = AsyncMock(
                side_effect=[
                    [{"id": "test-run-empty", "workflow_id": "test-workflow-empty"}],
                    {"id": "test-run-empty"},
                ]
            )

            with patch('activities.meeting_notes.get_model_client', return_value=mock_model_client), \
                 patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase_client):

                worker = Worker(
                    env.client,
                    task_queue="test",
                    workflows=[ExtractMeetingActionItemsWorkflow],
                    activities=[
                        validate_meeting_notes_input,
                        call_model_for_action_item_extraction,
                        persist_extraction_results,
                        record_extraction_failure
                    ]
                )

                async with worker:
                    result = await env.client.execute_workflow(
                        ExtractMeetingActionItemsWorkflow.run,
                        args=[
                            "test-meeting-note-id",
                            "This meeting had no actionable items, just discussion."
                        ],
                        id="test-workflow-empty",
                        task_queue="test",
                        execution_timeout=timedelta(seconds=30)
                    )

                    # Should succeed with 0 action items
                    assert result["status"] == "completed"
                    assert result["action_items_count"] == 0
                    assert result["extraction_run_id"] is not None


# Import asyncio for timeout test
import asyncio
