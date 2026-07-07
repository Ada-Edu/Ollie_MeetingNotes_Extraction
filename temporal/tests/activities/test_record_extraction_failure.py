"""Unit tests for record_extraction_failure activity."""
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import Mock, AsyncMock, patch
from activities.meeting_notes import record_extraction_failure


class TestRecordExtractionFailure:
    """Tests for record_extraction_failure activity."""

    @pytest.mark.asyncio
    async def test_record_failure_updates_existing_run(self):
        """Test recording failure updates existing extraction run."""
        mock_supabase = Mock()

        # Mock finding existing run
        existing_run = [{
            "id": "run-123",
            "workflow_id": "test-workflow",
            "status": "processing"
        }]

        # Mock update response
        mock_supabase._request = AsyncMock(side_effect=[
            existing_run,  # GET returns existing run
            None  # PATCH returns success
        ])

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            result = await record_extraction_failure(
                "note-123",
                "test-workflow",
                "Model API failed",
                {"provider": "azure", "model_name": "gpt-4"}
            )

        assert result == "run-123"
        assert mock_supabase._request.call_count == 2

        # Verify GET call
        get_call = mock_supabase._request.call_args_list[0]
        assert get_call[0] == ("GET", "extraction_runs")
        assert "workflow_id" in get_call[1]["params"]

        # Verify PATCH call
        patch_call = mock_supabase._request.call_args_list[1]
        assert patch_call[0] == ("PATCH", "extraction_runs")
        assert patch_call[1]["data"]["status"] == "failed"
        assert patch_call[1]["data"]["error_message"] == "Model API failed"

    @pytest.mark.asyncio
    async def test_record_failure_creates_new_run(self):
        """Test recording failure creates new run when none exists."""
        mock_supabase = Mock()

        # Mock no existing run found
        new_run = {
            "id": "run-456",
            "workflow_id": "test-workflow",
            "status": "failed"
        }

        mock_supabase._request = AsyncMock(side_effect=[
            [],  # GET returns empty list
            new_run  # POST returns new run
        ])

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            result = await record_extraction_failure(
                "note-123",
                "test-workflow",
                "Validation error",
                {"provider": "bedrock", "model_name": "claude-v2"}
            )

        assert result == "run-456"
        assert mock_supabase._request.call_count == 2

        # Verify POST call
        post_call = mock_supabase._request.call_args_list[1]
        assert post_call[0] == ("POST", "extraction_runs")
        assert post_call[1]["data"]["meeting_notes_id"] == "note-123"
        assert post_call[1]["data"]["workflow_id"] == "test-workflow"
        assert post_call[1]["data"]["status"] == "failed"
        assert post_call[1]["data"]["error_message"] == "Validation error"

    @pytest.mark.asyncio
    async def test_record_failure_with_model_info(self):
        """Test recording failure includes model info."""
        mock_supabase = Mock()

        existing_run = [{"id": "run-123"}]
        mock_supabase._request = AsyncMock(side_effect=[existing_run, None])

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            await record_extraction_failure(
                "note-123",
                "test-workflow",
                "Error message",
                {"provider": "azure", "model_name": "gpt-4-turbo"}
            )

        patch_call = mock_supabase._request.call_args_list[1]
        assert patch_call[1]["data"]["model_provider"] == "azure"
        assert patch_call[1]["data"]["model_name"] == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_record_failure_without_model_info(self):
        """Test recording failure when model info is None."""
        mock_supabase = Mock()

        existing_run = [{"id": "run-123"}]
        mock_supabase._request = AsyncMock(side_effect=[existing_run, None])

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            await record_extraction_failure(
                "note-123",
                "test-workflow",
                "Error before model initialization",
                None
            )

        patch_call = mock_supabase._request.call_args_list[1]
        assert patch_call[1]["data"]["model_provider"] is None
        assert patch_call[1]["data"]["model_name"] is None

    @pytest.mark.asyncio
    async def test_record_failure_sets_completed_timestamp(self):
        """Test that failure record sets completed_at timestamp."""
        mock_supabase = Mock()

        existing_run = [{"id": "run-123"}]
        mock_supabase._request = AsyncMock(side_effect=[existing_run, None])

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            await record_extraction_failure(
                "note-123",
                "test-workflow",
                "Error",
                {"provider": "azure", "model_name": "gpt-4"}
            )

        patch_call = mock_supabase._request.call_args_list[1]
        assert "completed_at" in patch_call[1]["data"]
        assert patch_call[1]["data"]["completed_at"] == "now()"

    @pytest.mark.asyncio
    async def test_record_failure_handles_list_response(self):
        """Test handling when POST returns list."""
        mock_supabase = Mock()

        new_run = [{"id": "run-789", "status": "failed"}]
        mock_supabase._request = AsyncMock(side_effect=[[], new_run])

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            result = await record_extraction_failure(
                "note-123",
                "test-workflow",
                "Error",
                None
            )

        assert result == "run-789"

    @pytest.mark.asyncio
    async def test_record_failure_with_long_error_message(self):
        """Test recording failure with long error message."""
        mock_supabase = Mock()

        existing_run = [{"id": "run-123"}]
        mock_supabase._request = AsyncMock(side_effect=[existing_run, None])

        long_error = "A" * 1000
        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            await record_extraction_failure(
                "note-123",
                "test-workflow",
                long_error,
                None
            )

        patch_call = mock_supabase._request.call_args_list[1]
        assert patch_call[1]["data"]["error_message"] == long_error

    @pytest.mark.asyncio
    async def test_record_failure_database_error_propagates(self):
        """Test that database errors are propagated."""
        mock_supabase = Mock()
        mock_supabase._request = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            with pytest.raises(Exception, match="Database connection failed"):
                await record_extraction_failure(
                    "note-123",
                    "test-workflow",
                    "Error",
                    None
                )

    @pytest.mark.asyncio
    async def test_record_failure_query_parameters(self):
        """Test correct query parameters for finding existing run."""
        mock_supabase = Mock()

        existing_run = [{"id": "run-123"}]
        mock_supabase._request = AsyncMock(side_effect=[existing_run, None])

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            await record_extraction_failure(
                "note-123",
                "extract-note-123",
                "Error",
                None
            )

        get_call = mock_supabase._request.call_args_list[0]
        params = get_call[1]["params"]
        assert params["workflow_id"] == "eq.extract-note-123"
        assert params["order"] == "created_at.desc"
        assert params["limit"] == "1"

    @pytest.mark.asyncio
    async def test_record_failure_update_parameters(self):
        """Test correct parameters for updating existing run."""
        mock_supabase = Mock()

        existing_run = [{"id": "run-123"}]
        mock_supabase._request = AsyncMock(side_effect=[existing_run, None])

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            await record_extraction_failure(
                "note-123",
                "test-workflow",
                "Test error",
                {"provider": "azure", "model_name": "gpt-4"}
            )

        patch_call = mock_supabase._request.call_args_list[1]
        params = patch_call[1]["params"]
        assert params["id"] == "eq.run-123"

        data = patch_call[1]["data"]
        assert data["status"] == "failed"
        assert data["error_message"] == "Test error"
        assert data["model_provider"] == "azure"
        assert data["model_name"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_record_failure_create_parameters(self):
        """Test correct parameters for creating new run."""
        mock_supabase = Mock()

        new_run = {"id": "run-456"}
        mock_supabase._request = AsyncMock(side_effect=[[], new_run])

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            await record_extraction_failure(
                "note-456",
                "workflow-456",
                "Creation error",
                {"provider": "bedrock", "model_name": "claude-3"}
            )

        post_call = mock_supabase._request.call_args_list[1]
        data = post_call[1]["data"]
        assert data["meeting_notes_id"] == "note-456"
        assert data["workflow_id"] == "workflow-456"
        assert data["status"] == "failed"
        assert data["error_message"] == "Creation error"
        assert data["model_provider"] == "bedrock"
        assert data["model_name"] == "claude-3"
        assert data["completed_at"] == "now()"
