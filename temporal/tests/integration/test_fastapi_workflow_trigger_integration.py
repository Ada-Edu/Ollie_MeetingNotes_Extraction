"""
Integration tests for FastAPI workflow trigger API.
Tests /trigger-workflow, /workflow/{id}/status, and /health endpoints with integration flows.

@group integration
"""

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, Mock, patch
import asyncio

from api.workflow_trigger import app, WorkflowTriggerRequest


@pytest.mark.integration
class TestFastAPIWorkflowTriggerIntegration:
    """Integration tests for FastAPI endpoints."""

    @pytest.fixture
    def mock_temporal_client(self):
        """Create mock Temporal client."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.id = "test-workflow-123"
        mock_handle.run_id = "test-run-456"
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)
        mock_client.get_workflow_handle = Mock(return_value=mock_handle)
        return mock_client

    @pytest.mark.asyncio
    async def test_trigger_workflow_endpoint_success(self, mock_temporal_client):
        """Test successful workflow trigger via API."""
        # Patch temporal client at module level
        with patch('api.workflow_trigger.temporal_client', mock_temporal_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/trigger-workflow",
                    json={
                        "workflow_name": "ExtractMeetingActionItemsWorkflow",
                        "workflow_id": "test-workflow-123",
                        "args": {
                            "meeting_notes_id": "note-123",
                            "notes_text": "Team meeting: Alice to review docs by Friday"
                        },
                        "task_queue": "main"
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["workflow_id"] == "test-workflow-123"
                assert "message" in data

                # Verify Temporal client was called
                mock_temporal_client.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_workflow_missing_required_args(self, mock_temporal_client):
        """Test API validates required arguments."""
        with patch('api.workflow_trigger.temporal_client', mock_temporal_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/trigger-workflow",
                    json={
                        "workflow_name": "ExtractMeetingActionItemsWorkflow",
                        "workflow_id": "test-workflow-123",
                        "args": {
                            # Missing notes_text
                            "meeting_notes_id": "note-123"
                        },
                        "task_queue": "main"
                    }
                )

                assert response.status_code == 400
                data = response.json()
                assert "Missing required arguments" in data["detail"]

    @pytest.mark.asyncio
    async def test_trigger_workflow_unknown_workflow_name(self, mock_temporal_client):
        """Test API rejects unknown workflow names."""
        with patch('api.workflow_trigger.temporal_client', mock_temporal_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/trigger-workflow",
                    json={
                        "workflow_name": "UnknownWorkflow",
                        "workflow_id": "test-123",
                        "args": {"meeting_notes_id": "note-123", "notes_text": "test"},
                        "task_queue": "main"
                    }
                )

                assert response.status_code == 400
                data = response.json()
                assert "Unknown workflow" in data["detail"]

    @pytest.mark.asyncio
    async def test_trigger_workflow_temporal_connection_error(self):
        """Test API handles Temporal connection errors."""
        mock_client = Mock()
        mock_client.start_workflow = AsyncMock(
            side_effect=Exception("Connection refused: Temporal not available")
        )

        with patch('api.workflow_trigger.temporal_client', mock_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/trigger-workflow",
                    json={
                        "workflow_name": "ExtractMeetingActionItemsWorkflow",
                        "workflow_id": "test-123",
                        "args": {"meeting_notes_id": "note-123", "notes_text": "test"},
                        "task_queue": "main"
                    }
                )

                assert response.status_code == 500
                data = response.json()
                assert "Failed to trigger workflow" in data["detail"]

    @pytest.mark.asyncio
    async def test_health_endpoint_when_connected(self, mock_temporal_client):
        """Test health endpoint reports healthy when Temporal is connected."""
        with patch('api.workflow_trigger.temporal_client', mock_temporal_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["temporal_connected"] is True

    @pytest.mark.asyncio
    async def test_health_endpoint_when_disconnected(self):
        """Test health endpoint reports when Temporal is disconnected."""
        with patch('api.workflow_trigger.temporal_client', None):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["temporal_connected"] is False

    @pytest.mark.asyncio
    async def test_workflow_status_endpoint_running(self, mock_temporal_client):
        """Test workflow status endpoint for running workflow."""
        mock_handle = Mock()
        mock_handle.result = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_temporal_client.get_workflow_handle.return_value = mock_handle

        with patch('api.workflow_trigger.temporal_client', mock_temporal_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/workflow/test-workflow-123/status")

                assert response.status_code == 200
                data = response.json()
                assert data["workflow_id"] == "test-workflow-123"
                assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_workflow_status_endpoint_completed(self, mock_temporal_client):
        """Test workflow status endpoint for completed workflow."""
        mock_handle = Mock()
        mock_result = {
            "status": "completed",
            "extraction_run_id": "run-123",
            "action_items_count": 3
        }

        async def get_result_immediate():
            return mock_result

        mock_handle.result = get_result_immediate
        mock_temporal_client.get_workflow_handle.return_value = mock_handle

        with patch('api.workflow_trigger.temporal_client', mock_temporal_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/workflow/test-workflow-123/status")

                assert response.status_code == 200
                data = response.json()
                assert data["workflow_id"] == "test-workflow-123"
                assert data["status"] == "completed"
                assert data["result"] == mock_result


@pytest.mark.integration
class TestAPIWorkflowIntegrationFlow:
    """End-to-end integration tests for API → Workflow flow."""

    @pytest.mark.asyncio
    async def test_complete_trigger_to_status_flow(self):
        """Test complete flow from trigger to status check."""
        # Setup mocks
        mock_temporal_client = Mock()
        mock_handle = Mock()
        mock_handle.id = "flow-test-123"
        mock_handle.run_id = "run-456"

        workflow_status = {"running": True}

        async def get_result_with_state():
            if workflow_status["running"]:
                raise asyncio.TimeoutError()
            return {
                "status": "completed",
                "extraction_run_id": "test-run-id",
                "action_items_count": 2
            }

        mock_handle.result = get_result_with_state
        mock_temporal_client.start_workflow = AsyncMock(return_value=mock_handle)
        mock_temporal_client.get_workflow_handle.return_value = mock_handle

        with patch('api.workflow_trigger.temporal_client', mock_temporal_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Step 1: Trigger workflow
                trigger_response = await client.post(
                    "/trigger-workflow",
                    json={
                        "workflow_name": "ExtractMeetingActionItemsWorkflow",
                        "workflow_id": "flow-test-123",
                        "args": {
                            "meeting_notes_id": "note-456",
                            "notes_text": "Team meeting with action items"
                        },
                        "task_queue": "main"
                    }
                )

                assert trigger_response.status_code == 200
                trigger_data = trigger_response.json()
                workflow_id = trigger_data["workflow_id"]

                # Step 2: Check status while running
                status_response = await client.get(f"/workflow/{workflow_id}/status")
                assert status_response.status_code == 200
                status_data = status_response.json()
                assert status_data["status"] == "running"

                # Step 3: Mark workflow as completed
                workflow_status["running"] = False

                # Step 4: Check status after completion
                final_response = await client.get(f"/workflow/{workflow_id}/status")
                assert final_response.status_code == 200
                final_data = final_response.json()
                assert final_data["status"] == "completed"
                assert "result" in final_data
                assert final_data["result"]["extraction_run_id"] == "test-run-id"

    @pytest.mark.asyncio
    async def test_concurrent_workflow_triggers(self):
        """Test API handles concurrent workflow triggers."""
        mock_temporal_client = Mock()
        triggered_workflows = []

        async def track_workflow_start(workflow_fn, args, id, task_queue):
            triggered_workflows.append(id)
            mock_handle = Mock()
            mock_handle.id = id
            mock_handle.run_id = f"run-{id}"
            return mock_handle

        mock_temporal_client.start_workflow = track_workflow_start

        with patch('api.workflow_trigger.temporal_client', mock_temporal_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Trigger multiple workflows concurrently
                requests = [
                    client.post(
                        "/trigger-workflow",
                        json={
                            "workflow_name": "ExtractMeetingActionItemsWorkflow",
                            "workflow_id": f"concurrent-test-{i}",
                            "args": {
                                "meeting_notes_id": f"note-{i}",
                                "notes_text": f"Meeting notes {i}"
                            },
                            "task_queue": "main"
                        }
                    )
                    for i in range(5)
                ]

                responses = await asyncio.gather(*requests)

                # Verify all succeeded
                assert all(r.status_code == 200 for r in responses)
                assert len(triggered_workflows) == 5
                assert all(f"concurrent-test-{i}" in triggered_workflows for i in range(5))

    @pytest.mark.asyncio
    async def test_api_request_validation(self):
        """Test API validates request payloads."""
        mock_temporal_client = Mock()

        with patch('api.workflow_trigger.temporal_client', mock_temporal_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Test with missing workflow_name
                response = await client.post(
                    "/trigger-workflow",
                    json={
                        "workflow_id": "test-123",
                        "args": {},
                        "task_queue": "main"
                    }
                )
                assert response.status_code == 422  # Validation error

                # Test with missing workflow_id
                response = await client.post(
                    "/trigger-workflow",
                    json={
                        "workflow_name": "ExtractMeetingActionItemsWorkflow",
                        "args": {},
                        "task_queue": "main"
                    }
                )
                assert response.status_code == 422

                # Test with missing args
                response = await client.post(
                    "/trigger-workflow",
                    json={
                        "workflow_name": "ExtractMeetingActionItemsWorkflow",
                        "workflow_id": "test-123",
                        "task_queue": "main"
                    }
                )
                assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_api_cors_headers(self):
        """Test API includes CORS headers."""
        mock_temporal_client = Mock()

        with patch('api.workflow_trigger.temporal_client', mock_temporal_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")

                # Check CORS headers are present
                assert "access-control-allow-origin" in response.headers
                assert response.headers["access-control-allow-origin"] == "*"

    @pytest.mark.asyncio
    async def test_api_error_response_format(self):
        """Test API returns consistent error response format."""
        mock_temporal_client = Mock()
        mock_temporal_client.start_workflow = AsyncMock(
            side_effect=Exception("Test error")
        )

        with patch('api.workflow_trigger.temporal_client', mock_temporal_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/trigger-workflow",
                    json={
                        "workflow_name": "ExtractMeetingActionItemsWorkflow",
                        "workflow_id": "test-123",
                        "args": {
                            "meeting_notes_id": "note-123",
                            "notes_text": "test"
                        },
                        "task_queue": "main"
                    }
                )

                assert response.status_code == 500
                data = response.json()
                assert "detail" in data
                assert isinstance(data["detail"], str)
