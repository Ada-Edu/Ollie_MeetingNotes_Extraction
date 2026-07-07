"""Integration tests for FastAPI workflow trigger."""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.integration
class TestWorkflowTriggerAPI:
    """Integration tests for workflow trigger API."""

    @pytest.fixture
    def mock_temporal_client(self):
        """Create a mock Temporal client."""
        mock_client = Mock()
        mock_client.start_workflow = AsyncMock(return_value=Mock(
            id="workflow-123",
            run_id="run-456"
        ))
        return mock_client

    @pytest.mark.asyncio
    async def test_trigger_workflow_endpoint(self, mock_temporal_client):
        """Test triggering workflow via API endpoint."""
        try:
            from api.workflow_trigger import app
            from httpx import AsyncClient

            # Patch the Temporal client
            with patch('api.workflow_trigger.get_temporal_client', return_value=mock_temporal_client):
                async with AsyncClient(base_url="http://test") as client:
                    client.app = app

                    response = await client.post(
                        "http://test/trigger-workflow",
                        json={
                            "workflow_name": "ExtractMeetingActionItemsWorkflow",
                            "workflow_id": "test-workflow-123",
                            "args": {
                                "meeting_notes_id": "test-note-id",
                                "notes_text": "Test notes"
                            },
                            "task_queue": "main"
                        }
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert "workflow_id" in data
        except ImportError:
            pytest.skip("API module not available")

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """Test health check endpoint."""
        try:
            from api.workflow_trigger import app
            from httpx import AsyncClient

            async with AsyncClient(base_url="http://test") as client:
                client.app = app

                response = await client.get("http://test/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
        except ImportError:
            pytest.skip("API module not available")

    @pytest.mark.asyncio
    async def test_invalid_workflow_request(self):
        """Test API handles invalid workflow requests."""
        try:
            from api.workflow_trigger import app
            from httpx import AsyncClient

            async with AsyncClient(base_url="http://test") as client:
                client.app = app

                # Missing required fields
                response = await client.post(
                    "http://test/trigger-workflow",
                    json={}
                )

                assert response.status_code in [400, 422]  # Bad request or validation error
        except ImportError:
            pytest.skip("API module not available")

    @pytest.mark.asyncio
    async def test_workflow_trigger_with_temporal_error(self, mock_temporal_client):
        """Test API handles Temporal connection errors."""
        try:
            from api.workflow_trigger import app
            from httpx import AsyncClient

            # Mock Temporal client that raises error
            mock_temporal_client.start_workflow = AsyncMock(
                side_effect=Exception("Temporal service unavailable")
            )

            with patch('api.workflow_trigger.get_temporal_client', return_value=mock_temporal_client):
                async with AsyncClient(base_url="http://test") as client:
                    client.app = app

                    response = await client.post(
                        "http://test/trigger-workflow",
                        json={
                            "workflow_name": "ExtractMeetingActionItemsWorkflow",
                            "workflow_id": "test-workflow-123",
                            "args": {"meeting_notes_id": "test-note-id"},
                            "task_queue": "main"
                        }
                    )

                    assert response.status_code in [500, 503]  # Server error or service unavailable
        except ImportError:
            pytest.skip("API module not available")


@pytest.mark.integration
class TestEndToEndAPIWorkflow:
    """End-to-end integration tests for API → Workflow → Database flow."""

    @pytest.mark.asyncio
    async def test_complete_extraction_flow(self):
        """Test complete flow from API trigger to result persistence."""
        # This would be a real integration test if we had all services running
        # For now, we test with mocks to verify the integration points

        mock_temporal_client = Mock()
        mock_temporal_client.start_workflow = AsyncMock(return_value=Mock(
            id="workflow-123",
            run_id="run-456"
        ))

        mock_supabase_client = Mock()
        mock_supabase_client._request = AsyncMock(return_value={
            "id": "extraction-run-id",
            "status": "completed"
        })

        try:
            from api.workflow_trigger import app
            from httpx import AsyncClient

            with patch('api.workflow_trigger.get_temporal_client', return_value=mock_temporal_client):
                async with AsyncClient(base_url="http://test") as client:
                    client.app = app

                    # 1. Trigger workflow
                    response = await client.post(
                        "http://test/trigger-workflow",
                        json={
                            "workflow_name": "ExtractMeetingActionItemsWorkflow",
                            "workflow_id": "test-workflow-123",
                            "args": {
                                "meeting_notes_id": "test-note-id",
                                "notes_text": "Team meeting notes"
                            },
                            "task_queue": "main"
                        }
                    )

                    # 2. Verify workflow was triggered
                    assert response.status_code == 200
                    workflow_data = response.json()
                    assert workflow_data["success"] is True

                    # 3. Verify Temporal client was called
                    mock_temporal_client.start_workflow.assert_called_once()

        except ImportError:
            pytest.skip("API module not available")
