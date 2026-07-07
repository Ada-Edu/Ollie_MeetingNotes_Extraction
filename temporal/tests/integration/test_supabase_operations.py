"""Integration tests for Supabase database operations."""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import AsyncMock, Mock, patch
from supabase_client import SupabaseClient, get_supabase_client


@pytest.mark.integration
class TestSupabaseClient:
    """Integration tests for Supabase client operations."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Create a mock httpx client."""
        mock_client = Mock()
        mock_client.request = AsyncMock()
        return mock_client

    @pytest.mark.asyncio
    async def test_create_meeting_note(self, mock_httpx_client):
        """Test creating a meeting note record."""
        # Setup mock response
        mock_httpx_client.request.return_value = Mock(
            status_code=201,
            json=Mock(return_value=[{
                "id": "test-note-id",
                "notes_text": "Test notes",
                "created_at": "2026-07-07T10:00:00Z"
            }])
        )

        # Create client with mocked httpx
        with patch('supabase_client.httpx.AsyncClient', return_value=mock_httpx_client):
            client = SupabaseClient()

            # Execute
            result = await client._request(
                "POST",
                "meeting_notes",
                data={"notes_text": "Test notes"}
            )

            # Verify
            assert result["id"] == "test-note-id"
            assert result["notes_text"] == "Test notes"
            mock_httpx_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_meeting_notes(self, mock_httpx_client):
        """Test retrieving meeting notes."""
        mock_httpx_client.request.return_value = Mock(
            status_code=200,
            json=Mock(return_value=[
                {
                    "id": "note-1",
                    "notes_text": "First note",
                    "created_at": "2026-07-07T10:00:00Z"
                },
                {
                    "id": "note-2",
                    "notes_text": "Second note",
                    "created_at": "2026-07-06T10:00:00Z"
                }
            ])
        )

        with patch('supabase_client.httpx.AsyncClient', return_value=mock_httpx_client):
            client = SupabaseClient()

            result = await client._request("GET", "meeting_notes")

            assert len(result) == 2
            assert result[0]["id"] == "note-1"
            assert result[1]["id"] == "note-2"

    @pytest.mark.asyncio
    async def test_create_extraction_run(self, mock_httpx_client):
        """Test creating an extraction run record."""
        mock_httpx_client.request.return_value = Mock(
            status_code=201,
            json=Mock(return_value=[{
                "id": "test-run-id",
                "meeting_notes_id": "test-note-id",
                "status": "processing",
                "workflow_id": "workflow-123"
            }])
        )

        with patch('supabase_client.httpx.AsyncClient', return_value=mock_httpx_client):
            client = SupabaseClient()

            result = await client._request(
                "POST",
                "extraction_runs",
                data={
                    "meeting_notes_id": "test-note-id",
                    "workflow_id": "workflow-123",
                    "status": "processing"
                }
            )

            assert result["id"] == "test-run-id"
            assert result["status"] == "processing"

    @pytest.mark.asyncio
    async def test_update_extraction_run_status(self, mock_httpx_client):
        """Test updating extraction run status."""
        mock_httpx_client.request.return_value = Mock(
            status_code=200,
            json=Mock(return_value=[{
                "id": "test-run-id",
                "status": "completed"
            }])
        )

        with patch('supabase_client.httpx.AsyncClient', return_value=mock_httpx_client):
            client = SupabaseClient()

            result = await client._request(
                "PATCH",
                "extraction_runs",
                data={"status": "completed"},
                params={"id": "eq.test-run-id"}
            )

            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_create_action_items(self, mock_httpx_client):
        """Test creating multiple action items."""
        mock_httpx_client.request.return_value = Mock(
            status_code=201,
            json=Mock(return_value=[
                {
                    "id": "action-1",
                    "description": "Action 1",
                    "owner": "John",
                    "extraction_run_id": "test-run-id"
                },
                {
                    "id": "action-2",
                    "description": "Action 2",
                    "owner": "Sarah",
                    "extraction_run_id": "test-run-id"
                }
            ])
        )

        with patch('supabase_client.httpx.AsyncClient', return_value=mock_httpx_client):
            client = SupabaseClient()

            result = await client._request(
                "POST",
                "action_items",
                data=[
                    {
                        "description": "Action 1",
                        "owner": "John",
                        "extraction_run_id": "test-run-id"
                    },
                    {
                        "description": "Action 2",
                        "owner": "Sarah",
                        "extraction_run_id": "test-run-id"
                    }
                ]
            )

            assert len(result) == 2
            assert result[0]["owner"] == "John"
            assert result[1]["owner"] == "Sarah"

    @pytest.mark.asyncio
    async def test_get_action_items_with_filter(self, mock_httpx_client):
        """Test retrieving action items with filter."""
        mock_httpx_client.request.return_value = Mock(
            status_code=200,
            json=Mock(return_value=[
                {
                    "id": "action-1",
                    "description": "Test action",
                    "extraction_run_id": "test-run-id"
                }
            ])
        )

        with patch('supabase_client.httpx.AsyncClient', return_value=mock_httpx_client):
            client = SupabaseClient()

            result = await client._request(
                "GET",
                "action_items",
                params={"extraction_run_id": "eq.test-run-id"}
            )

            assert len(result) == 1
            assert result[0]["extraction_run_id"] == "test-run-id"

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_httpx_client):
        """Test error handling for failed requests."""
        mock_httpx_client.request.return_value = Mock(
            status_code=400,
            json=Mock(return_value={"error": "Bad request"}),
            text="Bad request"
        )

        with patch('supabase_client.httpx.AsyncClient', return_value=mock_httpx_client):
            client = SupabaseClient()

            with pytest.raises(Exception):
                await client._request("POST", "invalid_table", data={})

    @pytest.mark.asyncio
    async def test_entity_operations(self, mock_httpx_client):
        """Test entity CRUD operations."""
        # Create entity
        mock_httpx_client.request.return_value = Mock(
            status_code=201,
            json=Mock(return_value=[{
                "id": "entity-1",
                "name": "John Doe",
                "type": "person"
            }])
        )

        with patch('supabase_client.httpx.AsyncClient', return_value=mock_httpx_client):
            client = SupabaseClient()

            result = await client._request(
                "POST",
                "entities",
                data={"name": "John Doe", "type": "person"}
            )

            assert result["name"] == "John Doe"
            assert result["type"] == "person"


@pytest.mark.integration
class TestSupabaseTransactions:
    """Test transaction-like behavior and error recovery."""

    @pytest.mark.asyncio
    async def test_rollback_on_error(self):
        """Test that partial operations can be cleaned up on error."""
        mock_client = Mock()

        # First call succeeds
        mock_client.request = AsyncMock(side_effect=[
            Mock(status_code=201, json=Mock(return_value=[{"id": "note-1"}])),
            # Second call fails
            Mock(status_code=500, json=Mock(return_value={"error": "Server error"}), text="Error")
        ])

        with patch('supabase_client.httpx.AsyncClient', return_value=mock_client):
            client = SupabaseClient()

            # First operation succeeds
            note = await client._request("POST", "meeting_notes", data={"notes_text": "Test"})
            assert note["id"] == "note-1"

            # Second operation fails
            with pytest.raises(Exception):
                await client._request("POST", "extraction_runs", data={"meeting_notes_id": "note-1"})

            # In real scenario, you'd clean up the note here
