"""Pytest configuration and fixtures for temporal tests."""
import sys
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from temporalio.testing import WorkflowEnvironment
from httpx import AsyncClient
from unittest.mock import Mock, AsyncMock
import os


@pytest.fixture
async def temporal_env():
    """Temporal test environment with time skipping."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        yield env


@pytest.fixture
def supabase_test_client():
    """Mock Supabase client for testing."""
    try:
        from supabase_client import SupabaseClient
        client = Mock(spec=SupabaseClient)
        client._request = AsyncMock()
        return client
    except ImportError:
        # Return a simple mock if import fails
        client = Mock()
        client._request = AsyncMock()
        return client


@pytest.fixture
async def api_client():
    """FastAPI test client."""
    try:
        from api.workflow_trigger import app
        async with AsyncClient(base_url="http://test") as client:
            yield client
    except ImportError:
        # If API module doesn't exist yet, skip
        pytest.skip("API module not found")


@pytest.fixture
def mock_model_response():
    """Mock AI model response for action item extraction."""
    return {
        "action_items": [
            {
                "description": "Follow up with Sarah about project timeline",
                "owner": "John",
                "due_date": "2026-07-15",
                "confidence": 0.95
            },
            {
                "description": "Review design document",
                "owner": "Mike",
                "due_date": "2026-07-10",
                "confidence": 0.87
            }
        ]
    }


@pytest.fixture
def sample_meeting_notes():
    """Sample meeting notes for testing."""
    return {
        "simple": {
            "notes_text": "John to follow up with Sarah by July 15",
            "expected_items": 1,
            "expected_owner": "John"
        },
        "multiple": {
            "notes_text": """Team Standup - July 7, 2026
            Action Items:
            1. John to follow up with Sarah by July 15
            2. Mike to review design doc by July 10
            3. Sarah to update documentation next week
            """,
            "expected_items": 3,
            "expected_owner": "John"
        },
        "no_actions": {
            "notes_text": "We discussed the project timeline and budget.",
            "expected_items": 0,
            "expected_owner": None
        }
    }


@pytest.fixture
def mock_azure_client():
    """Mock Azure OpenAI client."""
    try:
        from model_client.azure_client import AzureOpenAIClient
        client = Mock(spec=AzureOpenAIClient)
        client.extract_action_items = AsyncMock()
        return client
    except ImportError:
        client = Mock()
        client.extract_action_items = AsyncMock()
        return client


@pytest.fixture
def mock_bedrock_client():
    """Mock AWS Bedrock client."""
    try:
        from model_client.bedrock_client import BedrockClient
        client = Mock(spec=BedrockClient)
        client.extract_action_items = AsyncMock()
        return client
    except ImportError:
        client = Mock()
        client.extract_action_items = AsyncMock()
        return client


@pytest.fixture
async def clean_database():
    """Clean test database before/after tests."""
    # This fixture would connect to a test database and clean it
    # For now, we'll use a mock implementation
    yield
    # Cleanup code would go here


@pytest.fixture
def env_vars(monkeypatch):
    """Set up test environment variables."""
    test_env = {
        "SUPABASE_URL": "http://localhost:54321",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        "TEMPORAL_HOST": "localhost",
        "TEMPORAL_PORT": "7233",
        "MODEL_PROVIDER": "azure",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_DEPLOYMENT": "test-deployment"
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    return test_env
