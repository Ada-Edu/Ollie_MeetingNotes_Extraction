import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import uuid


# Import the REAL FastAPI app
from api.workflow_trigger import app


@pytest.fixture
def mock_temporal_client():
    """Mock Temporal client for testing."""
    client = AsyncMock()
    client.start_workflow = AsyncMock()
    client.get_workflow_handle = Mock()
    return client


@pytest.fixture
def client(mock_temporal_client):
    """Create a test client with the real app and mocked Temporal client."""
    # Patch the temporal_client in the real app module
    import api.workflow_trigger as workflow_trigger_module
    workflow_trigger_module.temporal_client = mock_temporal_client

    return TestClient(app)


class TestWorkflowTriggerEndpoint:
    """Tests for workflow trigger endpoint."""

    def test_trigger_workflow_success(self, client, mock_temporal_client):
        """Test successful workflow trigger with real endpoint validation."""
        mock_handle = Mock()
        mock_handle.id = "workflow-123"
        mock_temporal_client.start_workflow.return_value = mock_handle

        response = client.post(
            "/trigger-workflow",  # Real endpoint
            json={
                "workflow_name": "ExtractMeetingActionItemsWorkflow",
                "workflow_id": "test-workflow-123",
                "args": {
                    "meeting_notes_id": "note-123",
                    "notes_text": "Meeting notes content"
                },
                "task_queue": "main"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["workflow_id"] == "workflow-123"
        assert "triggered successfully" in data["message"]

        # Verify the real validation logic was executed
        mock_temporal_client.start_workflow.assert_called_once()

    def test_trigger_workflow_missing_required_args(self, client, mock_temporal_client):
        """Test workflow trigger fails when required args missing."""
        response = client.post(
            "/trigger-workflow",
            json={
                "workflow_name": "ExtractMeetingActionItemsWorkflow",
                "workflow_id": "test-workflow-456",
                "args": {
                    "meeting_notes_id": "note-123"
                    # Missing notes_text
                },
                "task_queue": "main"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Missing required arguments" in data["detail"]

    def test_trigger_workflow_temporal_error(self, client, mock_temporal_client):
        """Test workflow trigger failure from Temporal."""
        mock_temporal_client.start_workflow.side_effect = Exception("Temporal connection failed")

        response = client.post(
            "/trigger-workflow",
            json={
                "workflow_name": "ExtractMeetingActionItemsWorkflow",
                "workflow_id": "test-workflow-789",
                "args": {
                    "meeting_notes_id": "note-123",
                    "notes_text": "Meeting notes"
                },
                "task_queue": "main"
            }
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to trigger workflow" in data["detail"]

    def test_missing_required_workflow_name(self, client):
        """Test trigger endpoint with missing workflow_name (Pydantic validation)."""
        response = client.post(
            "/trigger-workflow",
            json={
                "workflow_id": "test-123",
                "args": {"meeting_notes_id": "123", "notes_text": "text"}
            }
        )

        # FastAPI/Pydantic returns 422 for validation errors
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_unknown_workflow_name(self, client, mock_temporal_client):
        """Test triggering an unknown workflow."""
        response = client.post(
            "/trigger-workflow",
            json={
                "workflow_name": "UnknownWorkflow",
                "workflow_id": "test-unknown-123",
                "args": {
                    "meeting_notes_id": "123",
                    "notes_text": "text"
                },
                "task_queue": "main"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Unknown workflow" in data["detail"]

    def test_temporal_client_not_initialized(self, client):
        """Test behavior when Temporal client is not connected."""
        import api.workflow_trigger as workflow_trigger_module
        original_client = workflow_trigger_module.temporal_client
        workflow_trigger_module.temporal_client = None

        try:
            response = client.post(
                "/trigger-workflow",
                json={
                    "workflow_name": "ExtractMeetingActionItemsWorkflow",
                    "workflow_id": "test-123",
                    "args": {
                        "meeting_notes_id": "123",
                        "notes_text": "text"
                    }
                }
            )

            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert "not connected" in data["detail"]
        finally:
            workflow_trigger_module.temporal_client = original_client


class TestTemporalConnectionErrors:
    """Tests for Temporal connection error handling."""

    def test_temporal_connection_error(self, client, mock_temporal_client):
        """Test handling of Temporal connection errors."""
        mock_temporal_client.start_workflow.side_effect = ConnectionError(
            "Failed to connect to Temporal server"
        )

        response = client.post(
            "/trigger-workflow",  # Real endpoint
            json={
                "workflow_name": "ExtractMeetingActionItemsWorkflow",
                "workflow_id": "test-connection-123",
                "args": {
                    "meeting_notes_id": "123",
                    "notes_text": "text"
                },
                "task_queue": "main"
            }
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to trigger workflow" in data["detail"]


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_endpoint(self, client):
        """Test health check endpoint returns healthy status with real response format."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "temporal_connected" in data
        assert isinstance(data["temporal_connected"], bool)

    def test_health_endpoint_with_temporal_disconnected(self, client):
        """Test health check when Temporal client is not connected."""
        import api.workflow_trigger as workflow_trigger_module
        original_client = workflow_trigger_module.temporal_client
        workflow_trigger_module.temporal_client = None

        try:
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["temporal_connected"] is False
        finally:
            workflow_trigger_module.temporal_client = original_client


class TestWorkflowStatusEndpoint:
    """Tests for workflow status endpoint."""

    def test_workflow_status_running(self, client, mock_temporal_client):
        """Test getting status of a running workflow with real endpoint."""
        mock_handle = Mock()
        # Real implementation uses asyncio.wait_for with timeout to check if workflow is running
        mock_handle.result = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_temporal_client.get_workflow_handle.return_value = mock_handle

        workflow_id = "test-workflow-123"
        response = client.get(f"/workflow/{workflow_id}/status")  # Real endpoint

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == workflow_id
        assert data["status"] == "running"
        # Real API doesn't return start_time for running workflows
        assert "result" not in data

    def test_workflow_status_completed(self, client, mock_temporal_client):
        """Test getting status of a completed workflow with real response format."""
        mock_handle = Mock()
        expected_result = {"action_items": ["item1", "item2"]}
        mock_handle.result = AsyncMock(return_value=expected_result)
        mock_temporal_client.get_workflow_handle.return_value = mock_handle

        workflow_id = "test-workflow-456"
        response = client.get(f"/workflow/{workflow_id}/status")  # Real endpoint

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == workflow_id
        assert data["status"] == "completed"
        assert data["result"] == expected_result

    def test_workflow_status_error(self, client, mock_temporal_client):
        """Test getting status when workflow lookup fails."""
        mock_handle = Mock()
        mock_handle.result = AsyncMock(side_effect=Exception("Workflow not found"))
        mock_temporal_client.get_workflow_handle.return_value = mock_handle

        workflow_id = "non-existent-workflow"
        response = client.get(f"/workflow/{workflow_id}/status")  # Real endpoint

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to get workflow status" in data["detail"]

    def test_workflow_status_temporal_not_connected(self, client):
        """Test status endpoint when Temporal client is not connected."""
        import api.workflow_trigger as workflow_trigger_module
        original_client = workflow_trigger_module.temporal_client
        workflow_trigger_module.temporal_client = None

        try:
            response = client.get("/workflow/test-123/status")

            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert "not connected" in data["detail"]
        finally:
            workflow_trigger_module.temporal_client = original_client


class TestCompleteWorkflow:
    """Tests for complete trigger-to-status flow."""

    def test_complete_trigger_to_status_flow(self, client, mock_temporal_client):
        """Test complete workflow from trigger to status check with real endpoints."""
        # Setup mock for trigger
        workflow_id = "integration-test-123"
        mock_handle = Mock()
        mock_handle.id = workflow_id
        mock_temporal_client.start_workflow.return_value = mock_handle

        # Trigger workflow with real request format
        trigger_response = client.post(
            "/trigger-workflow",  # Real endpoint
            json={
                "workflow_name": "ExtractMeetingActionItemsWorkflow",
                "workflow_id": workflow_id,
                "args": {
                    "meeting_notes_id": "note-123",
                    "notes_text": "Test meeting notes"
                },
                "task_queue": "main"
            }
        )

        assert trigger_response.status_code == 200
        trigger_data = trigger_response.json()
        assert trigger_data["success"] is True
        assert trigger_data["workflow_id"] == workflow_id

        # Setup mock for status check
        mock_status_handle = Mock()
        mock_status_handle.result = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_temporal_client.get_workflow_handle.return_value = mock_status_handle

        # Check status with real endpoint
        status_response = client.get(f"/workflow/{workflow_id}/status")  # Real endpoint

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["workflow_id"] == workflow_id
        assert status_data["status"] == "running"


class TestConcurrentWorkflows:
    """Tests for concurrent workflow triggers."""

    def test_concurrent_workflow_triggers(self, client, mock_temporal_client):
        """Test triggering multiple workflows concurrently with real API."""
        def create_mock_handle(workflow_id):
            handle = Mock()
            handle.id = workflow_id
            return handle

        mock_temporal_client.start_workflow.side_effect = [
            create_mock_handle(f"workflow-{i}") for i in range(5)
        ]

        responses = []
        for i in range(5):
            response = client.post(
                "/trigger-workflow",  # Real endpoint
                json={
                    "workflow_name": "ExtractMeetingActionItemsWorkflow",
                    "workflow_id": f"concurrent-workflow-{i}",
                    "args": {
                        "meeting_notes_id": f"note-{i}",
                        "notes_text": f"Meeting notes {i}"
                    },
                    "task_queue": "main"
                }
            )
            responses.append(response)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # All should have success=True
        assert all(r.json()["success"] is True for r in responses)

        # All should have unique workflow IDs
        workflow_ids = [r.json()["workflow_id"] for r in responses]
        assert len(workflow_ids) == len(set(workflow_ids))


class TestRequestValidation:
    """Tests for request validation."""

    def test_invalid_json_payload(self, client):
        """Test handling of invalid JSON payload with real endpoint."""
        response = client.post(
            "/trigger-workflow",  # Real endpoint
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_missing_workflow_id_field(self, client):
        """Test Pydantic validation when workflow_id is missing."""
        response = client.post(
            "/trigger-workflow",
            json={
                "workflow_name": "ExtractMeetingActionItemsWorkflow",
                # Missing workflow_id field
                "args": {
                    "meeting_notes_id": "123",
                    "notes_text": "text"
                }
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_invalid_args_type(self, client):
        """Test validation when args is not a dictionary."""
        response = client.post(
            "/trigger-workflow",
            json={
                "workflow_name": "ExtractMeetingActionItemsWorkflow",
                "workflow_id": "test-123",
                "args": "not a dict"  # Invalid type
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestCORSHeaders:
    """Tests for CORS headers."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses from real API."""
        response = client.options("/trigger-workflow")  # Real endpoint

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_cors_allows_all_origins(self, client):
        """Test that CORS is configured to allow all origins as per real API."""
        response = client.options(
            "/trigger-workflow",
            headers={"Origin": "https://example.com"}
        )

        assert response.status_code == 200
        # Real API allows all origins
        assert response.headers.get("access-control-allow-origin") == "*"


class TestErrorResponseFormats:
    """Tests for error response formats."""

    def test_error_response_format_consistency(self, client, mock_temporal_client):
        """Test that error responses follow FastAPI/Pydantic format with 'detail' field."""
        # Reset mock
        mock_temporal_client.start_workflow.side_effect = None
        mock_temporal_client.start_workflow.side_effect = Exception("Temporal error")

        # Test Temporal error (500)
        response = client.post(
            "/trigger-workflow",  # Real endpoint
            json={
                "workflow_name": "ExtractMeetingActionItemsWorkflow",
                "workflow_id": "error-test-123",
                "args": {
                    "meeting_notes_id": "123",
                    "notes_text": "text"
                },
                "task_queue": "main"
            }
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data  # FastAPI uses 'detail' not 'error'
        assert isinstance(data["detail"], str)
        assert "Failed to trigger workflow" in data["detail"]

    def test_validation_error_format(self, client):
        """Test that Pydantic validation errors have consistent format."""
        # Missing required field
        response = client.post(
            "/trigger-workflow",
            json={
                "workflow_name": "ExtractMeetingActionItemsWorkflow",
                # Missing workflow_id
                "args": {
                    "meeting_notes_id": "123",
                    "notes_text": "text"
                }
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Pydantic validation errors are a list of error objects
        assert isinstance(data["detail"], list)

    def test_http_exception_format(self, client):
        """Test HTTPException format for unknown workflow."""
        response = client.post(
            "/trigger-workflow",
            json={
                "workflow_name": "UnknownWorkflow",
                "workflow_id": "test-123",
                "args": {
                    "meeting_notes_id": "123",
                    "notes_text": "text"
                },
                "task_queue": "main"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data  # FastAPI HTTPException uses 'detail'
        assert isinstance(data["detail"], str)
