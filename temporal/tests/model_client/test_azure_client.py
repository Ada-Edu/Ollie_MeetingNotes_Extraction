"""Unit tests for AzureModelClient."""
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import Mock, patch
import json
from model_client.azure_client import AzureModelClient
from model_client.base import ActionItem, ModelAPIError, InvalidResponseError


class TestAzureModelClient:
    """Tests for Azure OpenAI model client."""

    @pytest.fixture
    def mock_env_vars(self, monkeypatch):
        """Set up test environment variables."""
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-api-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")

    @pytest.fixture
    def azure_client(self, mock_env_vars):
        """Create Azure client for testing."""
        with patch('model_client.azure_client.AzureOpenAI'):
            client = AzureModelClient()
            return client

    def test_initialization_success(self, mock_env_vars):
        """Test successful client initialization."""
        with patch('model_client.azure_client.AzureOpenAI') as mock_azure:
            client = AzureModelClient()
            assert client.deployment == "gpt-4"
            mock_azure.assert_called_once_with(
                api_key="test-api-key",
                api_version="2024-02-15-preview",
                azure_endpoint="https://test.openai.azure.com"
            )

    def test_initialization_missing_api_key(self, monkeypatch):
        """Test initialization fails without API key."""
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        with pytest.raises(ValueError, match="AZURE_OPENAI_API_KEY.*not set"):
            AzureModelClient()

    def test_initialization_missing_endpoint(self, monkeypatch):
        """Test initialization fails without endpoint."""
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)

        with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT.*not set"):
            AzureModelClient()

    def test_get_model_name(self, azure_client):
        """Test getting model name returns deployment."""
        assert azure_client.get_model_name() == "gpt-4"

    def test_get_provider_name(self, azure_client):
        """Test getting provider name."""
        assert azure_client.get_provider_name() == "azure"

    @pytest.mark.asyncio
    async def test_extract_action_items_success(self, azure_client):
        """Test successful action item extraction."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "action_items": [
                    {
                        "description": "Follow up with Sarah",
                        "owner": "John",
                        "due_date": "2026-07-15",
                        "confidence": 0.95
                    }
                ]
            })))
        ]

        azure_client.client.chat.completions.create = Mock(return_value=mock_response)

        notes = "John needs to follow up with Sarah by July 15"
        result = await azure_client.extract_action_items(notes)

        assert len(result) == 1
        assert isinstance(result[0], ActionItem)
        assert result[0].description == "Follow up with Sarah"
        assert result[0].owner == "John"
        assert result[0].due_date == "2026-07-15"
        assert result[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_extract_action_items_multiple(self, azure_client):
        """Test extraction with multiple action items."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "action_items": [
                    {
                        "description": "Task 1",
                        "owner": "Alice",
                        "due_date": "2026-07-15",
                        "confidence": 0.9
                    },
                    {
                        "description": "Task 2",
                        "owner": "Bob",
                        "due_date": "2026-07-20",
                        "confidence": 0.85
                    },
                    {
                        "description": "Task 3"
                    }
                ]
            })))
        ]

        azure_client.client.chat.completions.create = Mock(return_value=mock_response)

        result = await azure_client.extract_action_items("Multiple tasks")

        assert len(result) == 3
        assert result[0].description == "Task 1"
        assert result[1].description == "Task 2"
        assert result[2].description == "Task 3"
        assert result[2].owner is None

    @pytest.mark.asyncio
    async def test_extract_action_items_no_items(self, azure_client):
        """Test extraction when no action items found."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({"action_items": []})))
        ]

        azure_client.client.chat.completions.create = Mock(return_value=mock_response)

        notes = "We discussed the project timeline"
        result = await azure_client.extract_action_items(notes)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_extract_action_items_invalid_json(self, azure_client):
        """Test extraction with invalid JSON response."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="This is not valid JSON"))
        ]

        azure_client.client.chat.completions.create = Mock(return_value=mock_response)

        with pytest.raises(InvalidResponseError, match="Model returned invalid JSON"):
            await azure_client.extract_action_items("Test notes")

    @pytest.mark.asyncio
    async def test_extract_action_items_missing_key(self, azure_client):
        """Test extraction with missing action_items key."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({"tasks": []})))
        ]

        azure_client.client.chat.completions.create = Mock(return_value=mock_response)

        with pytest.raises(InvalidResponseError, match="missing 'action_items' array"):
            await azure_client.extract_action_items("Test notes")

    @pytest.mark.asyncio
    async def test_extract_action_items_invalid_array(self, azure_client):
        """Test extraction when action_items is not an array."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({"action_items": "not an array"})))
        ]

        azure_client.client.chat.completions.create = Mock(return_value=mock_response)

        with pytest.raises(InvalidResponseError, match="must be an array"):
            await azure_client.extract_action_items("Test notes")

    @pytest.mark.asyncio
    async def test_extract_action_items_skips_invalid_items(self, azure_client):
        """Test that invalid items are skipped."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "action_items": [
                    {
                        "description": "Valid task",
                        "owner": "John"
                    },
                    "not a dict",
                    {
                        "owner": "No description"
                    },
                    {
                        "description": "Another valid task"
                    }
                ]
            })))
        ]

        azure_client.client.chat.completions.create = Mock(return_value=mock_response)

        result = await azure_client.extract_action_items("Test notes")

        assert len(result) == 2
        assert result[0].description == "Valid task"
        assert result[1].description == "Another valid task"

    @pytest.mark.asyncio
    async def test_extract_action_items_api_error(self, azure_client):
        """Test extraction when API call fails."""
        azure_client.client.chat.completions.create = Mock(
            side_effect=Exception("API connection failed")
        )

        with pytest.raises(ModelAPIError, match="Azure OpenAI API call failed"):
            await azure_client.extract_action_items("Test notes")

    @pytest.mark.asyncio
    async def test_extract_action_items_request_parameters(self, azure_client):
        """Test that correct parameters are sent to API."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({"action_items": []})))
        ]

        mock_create = Mock(return_value=mock_response)
        azure_client.client.chat.completions.create = mock_create

        await azure_client.extract_action_items("Test notes")

        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args.kwargs['model'] == 'gpt-4'
        assert call_args.kwargs['temperature'] == 0.3
        assert call_args.kwargs['max_tokens'] == 2000
        assert call_args.kwargs['response_format'] == {"type": "json_object"}
        assert len(call_args.kwargs['messages']) == 1
        assert call_args.kwargs['messages'][0]['role'] == 'user'

    @pytest.mark.asyncio
    async def test_extract_action_items_with_all_fields(self, azure_client):
        """Test extraction with all optional fields present."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "action_items": [
                    {
                        "description": "Complete project",
                        "owner": "Alice",
                        "due_date": "2026-08-01",
                        "confidence": 0.98
                    }
                ]
            })))
        ]

        azure_client.client.chat.completions.create = Mock(return_value=mock_response)

        result = await azure_client.extract_action_items("Test notes")

        assert len(result) == 1
        item = result[0]
        assert item.description == "Complete project"
        assert item.owner == "Alice"
        assert item.due_date == "2026-08-01"
        assert item.confidence == 0.98

    @pytest.mark.asyncio
    async def test_extract_action_items_minimal_fields(self, azure_client):
        """Test extraction with only description field."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "action_items": [
                    {
                        "description": "Minimal task"
                    }
                ]
            })))
        ]

        azure_client.client.chat.completions.create = Mock(return_value=mock_response)

        result = await azure_client.extract_action_items("Test notes")

        assert len(result) == 1
        item = result[0]
        assert item.description == "Minimal task"
        assert item.owner is None
        assert item.due_date is None
        assert item.confidence is None

    @pytest.mark.asyncio
    async def test_extract_action_items_uses_default_api_version(self, monkeypatch):
        """Test that default API version is used when not specified."""
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)

        with patch('model_client.azure_client.AzureOpenAI') as mock_azure:
            client = AzureModelClient()
            mock_azure.assert_called_once()
            assert mock_azure.call_args.kwargs['api_version'] == "2024-02-15-preview"

    @pytest.mark.asyncio
    async def test_extract_action_items_uses_default_deployment(self, monkeypatch):
        """Test that default deployment is used when not specified."""
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)

        with patch('model_client.azure_client.AzureOpenAI'):
            client = AzureModelClient()
            assert client.deployment == "gpt-4"
