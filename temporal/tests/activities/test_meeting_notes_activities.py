"""Unit tests for meeting notes activities."""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import Mock, AsyncMock, patch
from activities.meeting_notes import (
    validate_meeting_notes_input,
    call_model_for_action_item_extraction,
    persist_extraction_results
)


class TestValidateMeetingNotesInput:
    """Tests for validate_meeting_notes_input activity."""

    @pytest.mark.asyncio
    async def test_valid_input(self):
        """Test validation with valid input."""
        notes = "This is a valid meeting note with sufficient length."
        # Should not raise any exception
        await validate_meeting_notes_input(notes)

    @pytest.mark.asyncio
    async def test_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Meeting notes cannot be empty"):
            await validate_meeting_notes_input("")

    @pytest.mark.asyncio
    async def test_whitespace_only_raises_error(self):
        """Test that whitespace-only input raises ValueError."""
        with pytest.raises(ValueError, match="Meeting notes cannot be empty"):
            await validate_meeting_notes_input("   \n\t  ")

    @pytest.mark.asyncio
    async def test_too_short_raises_error(self):
        """Test that input less than 10 characters raises ValueError."""
        with pytest.raises(ValueError, match="Meeting notes too short"):
            await validate_meeting_notes_input("Short")

    @pytest.mark.asyncio
    async def test_too_long_raises_error(self):
        """Test that input exceeding 10000 characters raises ValueError."""
        long_notes = "a" * 10001
        with pytest.raises(ValueError, match="exceed 10,000 character limit"):
            await validate_meeting_notes_input(long_notes)

    @pytest.mark.asyncio
    async def test_exactly_10_characters(self):
        """Test that exactly 10 characters is valid."""
        notes = "1234567890"
        await validate_meeting_notes_input(notes)

    @pytest.mark.asyncio
    async def test_exactly_10000_characters(self):
        """Test that exactly 10000 characters is valid."""
        notes = "a" * 10000
        await validate_meeting_notes_input(notes)


class TestCallModelForActionItemExtraction:
    """Tests for call_model_for_action_item_extraction activity."""

    @pytest.mark.asyncio
    async def test_successful_extraction(self, mock_model_response):
        """Test successful action item extraction."""
        mock_client = Mock()
        mock_client.get_provider_name.return_value = "azure"
        mock_client.get_model_name.return_value = "gpt-4"

        # Create mock action items
        mock_action_item = Mock()
        mock_action_item.to_dict.return_value = mock_model_response["action_items"][0]
        mock_client.extract_action_items = AsyncMock(return_value=[mock_action_item])

        with patch('activities.meeting_notes.get_model_client', return_value=mock_client):
            result = await call_model_for_action_item_extraction("Test meeting notes")

        assert "action_items" in result
        assert "model_provider" in result
        assert "model_name" in result
        assert result["model_provider"] == "azure"
        assert result["model_name"] == "gpt-4"
        assert len(result["action_items"]) == 1
        mock_client.extract_action_items.assert_called_once_with("Test meeting notes")

    @pytest.mark.asyncio
    async def test_extraction_with_multiple_items(self, mock_model_response):
        """Test extraction with multiple action items."""
        mock_client = Mock()
        mock_client.get_provider_name.return_value = "bedrock"
        mock_client.get_model_name.return_value = "claude-v2"

        # Create multiple mock action items
        mock_items = []
        for item_data in mock_model_response["action_items"]:
            mock_item = Mock()
            mock_item.to_dict.return_value = item_data
            mock_items.append(mock_item)

        mock_client.extract_action_items = AsyncMock(return_value=mock_items)

        with patch('activities.meeting_notes.get_model_client', return_value=mock_client):
            result = await call_model_for_action_item_extraction("Test meeting notes")

        assert len(result["action_items"]) == 2
        assert result["model_provider"] == "bedrock"
        assert result["model_name"] == "claude-v2"

    @pytest.mark.asyncio
    async def test_extraction_with_no_items(self):
        """Test extraction when no action items are found."""
        mock_client = Mock()
        mock_client.get_provider_name.return_value = "azure"
        mock_client.get_model_name.return_value = "gpt-4"
        mock_client.extract_action_items = AsyncMock(return_value=[])

        with patch('activities.meeting_notes.get_model_client', return_value=mock_client):
            result = await call_model_for_action_item_extraction("Meeting with no actions")

        assert len(result["action_items"]) == 0
        assert result["model_provider"] == "azure"

    @pytest.mark.asyncio
    async def test_model_api_error_propagates(self):
        """Test that model API errors are propagated."""
        mock_client = Mock()
        mock_client.get_provider_name.return_value = "azure"
        mock_client.get_model_name.return_value = "gpt-4"
        mock_client.extract_action_items = AsyncMock(
            side_effect=Exception("API connection failed")
        )

        with patch('activities.meeting_notes.get_model_client', return_value=mock_client):
            with pytest.raises(Exception, match="API connection failed"):
                await call_model_for_action_item_extraction("Test notes")


class TestPersistExtractionResults:
    """Tests for persist_extraction_results activity."""

    @pytest.mark.asyncio
    async def test_successful_persistence(self):
        """Test successful persistence of extraction results."""
        mock_supabase = Mock()
        mock_supabase._request = AsyncMock(
            return_value={"id": "test-run-id", "status": "completed"}
        )

        meeting_notes_id = "test-note-id"
        workflow_id = "test-workflow-id"
        action_items = [
            {
                "description": "Test action",
                "owner": "John",
                "due_date": "2026-07-15",
                "confidence": 0.95
            }
        ]
        model_info = {
            "provider": "azure",
            "model_name": "gpt-4"
        }
        raw_response = {"action_items": action_items}

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            result = await persist_extraction_results(
                meeting_notes_id,
                workflow_id,
                action_items,
                model_info,
                raw_response
            )

        # Verify supabase client was called
        assert mock_supabase._request.called

    @pytest.mark.asyncio
    async def test_persistence_with_empty_action_items(self):
        """Test persistence when no action items were extracted."""
        mock_supabase = Mock()
        mock_supabase._request = AsyncMock(
            return_value={"id": "test-run-id", "status": "completed"}
        )

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            result = await persist_extraction_results(
                "test-note-id",
                "test-workflow-id",
                [],
                {"provider": "azure", "model_name": "gpt-4"},
                {"action_items": []}
            )

        assert mock_supabase._request.called

    @pytest.mark.asyncio
    async def test_persistence_database_error(self):
        """Test that database errors are propagated."""
        mock_supabase = Mock()
        mock_supabase._request = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            with pytest.raises(Exception, match="Database connection failed"):
                await persist_extraction_results(
                    "test-note-id",
                    "test-workflow-id",
                    [],
                    {"provider": "azure", "model_name": "gpt-4"},
                    {}
                )

    @pytest.mark.asyncio
    async def test_persistence_with_multiple_action_items(self):
        """Test persistence with multiple action items."""
        mock_supabase = Mock()
        mock_supabase._request = AsyncMock(
            return_value={"id": "test-run-id", "status": "completed"}
        )

        action_items = [
            {
                "description": "Action 1",
                "owner": "John",
                "due_date": "2026-07-15",
                "confidence": 0.95
            },
            {
                "description": "Action 2",
                "owner": "Sarah",
                "due_date": "2026-07-20",
                "confidence": 0.87
            },
            {
                "description": "Action 3",
                "owner": None,
                "due_date": None,
                "confidence": 0.65
            }
        ]

        with patch('activities.meeting_notes.get_supabase_client', return_value=mock_supabase):
            result = await persist_extraction_results(
                "test-note-id",
                "test-workflow-id",
                action_items,
                {"provider": "bedrock", "model_name": "claude-v2"},
                {"action_items": action_items}
            )

        assert mock_supabase._request.called
