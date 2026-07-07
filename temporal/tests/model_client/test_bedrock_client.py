"""Unit tests for BedrockModelClient."""
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from model_client.bedrock_client import BedrockModelClient
from model_client.base import ActionItem, ModelAPIError, InvalidResponseError


class TestBedrockModelClient:
    """Tests for AWS Bedrock model client."""

    @pytest.fixture
    def mock_env_vars(self, monkeypatch):
        """Set up test environment variables."""
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key-id")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")

    @pytest.fixture
    def bedrock_client(self, mock_env_vars):
        """Create Bedrock client for testing."""
        with patch('boto3.client'):
            client = BedrockModelClient()
            return client

    def test_initialization_with_credentials(self, mock_env_vars):
        """Test client initialization with AWS credentials."""
        with patch('boto3.client') as mock_boto_client:
            client = BedrockModelClient()
            assert client.region == "us-east-1"
            assert client.model_id == "anthropic.claude-v2"
            assert not client.use_api_key
            mock_boto_client.assert_called_once()

    def test_initialization_with_api_key(self, monkeypatch):
        """Test client initialization with API key."""
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
        monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-api-key")

        client = BedrockModelClient()
        assert client.use_api_key
        assert client.api_key == "test-api-key"

    def test_get_model_name(self, bedrock_client):
        """Test getting model name."""
        assert bedrock_client.get_model_name() == "anthropic.claude-v2"

    def test_get_provider_name(self, bedrock_client):
        """Test getting provider name."""
        assert bedrock_client.get_provider_name() == "bedrock"

    @pytest.mark.asyncio
    async def test_extract_action_items_success(self, bedrock_client):
        """Test successful action item extraction."""
        mock_response = {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "action_items": [
                        {
                            "description": "Follow up with Sarah",
                            "owner": "John",
                            "due_date": "2026-07-15",
                            "confidence": 0.95
                        }
                    ]
                })
            }]
        }

        mock_boto_response = {
            "body": MagicMock()
        }
        mock_boto_response["body"].read.return_value = json.dumps(mock_response).encode()

        bedrock_client.client = Mock()
        bedrock_client.client.invoke_model = Mock(return_value=mock_boto_response)

        notes = "John needs to follow up with Sarah by July 15"
        result = await bedrock_client.extract_action_items(notes)

        assert len(result) == 1
        assert isinstance(result[0], ActionItem)
        assert result[0].description == "Follow up with Sarah"
        assert result[0].owner == "John"
        assert result[0].due_date == "2026-07-15"
        assert result[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_extract_action_items_old_format(self, bedrock_client):
        """Test extraction with old completion format."""
        mock_response = {
            "completion": json.dumps({
                "action_items": [
                    {
                        "description": "Review document",
                        "owner": "Mike",
                        "due_date": "2026-07-20",
                        "confidence": 0.87
                    }
                ]
            })
        }

        mock_boto_response = {
            "body": MagicMock()
        }
        mock_boto_response["body"].read.return_value = json.dumps(mock_response).encode()

        bedrock_client.client = Mock()
        bedrock_client.client.invoke_model = Mock(return_value=mock_boto_response)

        notes = "Mike should review the document by July 20"
        result = await bedrock_client.extract_action_items(notes)

        assert len(result) == 1
        assert result[0].description == "Review document"
        assert result[0].owner == "Mike"

    @pytest.mark.asyncio
    async def test_extract_action_items_no_items(self, bedrock_client):
        """Test extraction when no action items found."""
        mock_response = {
            "content": [{
                "type": "text",
                "text": json.dumps({"action_items": []})
            }]
        }

        mock_boto_response = {
            "body": MagicMock()
        }
        mock_boto_response["body"].read.return_value = json.dumps(mock_response).encode()

        bedrock_client.client = Mock()
        bedrock_client.client.invoke_model = Mock(return_value=mock_boto_response)

        notes = "We discussed the project timeline"
        result = await bedrock_client.extract_action_items(notes)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_extract_action_items_invalid_json(self, bedrock_client):
        """Test extraction with invalid JSON response."""
        mock_response = {
            "content": [{
                "type": "text",
                "text": "This is not valid JSON"
            }]
        }

        mock_boto_response = {
            "body": MagicMock()
        }
        mock_boto_response["body"].read.return_value = json.dumps(mock_response).encode()

        bedrock_client.client = Mock()
        bedrock_client.client.invoke_model = Mock(return_value=mock_boto_response)

        with pytest.raises(InvalidResponseError, match="No JSON found in model response"):
            await bedrock_client.extract_action_items("Test notes")

    @pytest.mark.asyncio
    async def test_extract_action_items_missing_action_items_key(self, bedrock_client):
        """Test extraction with missing action_items key."""
        mock_response = {
            "content": [{
                "type": "text",
                "text": json.dumps({"tasks": []})
            }]
        }

        mock_boto_response = {
            "body": MagicMock()
        }
        mock_boto_response["body"].read.return_value = json.dumps(mock_response).encode()

        bedrock_client.client = Mock()
        bedrock_client.client.invoke_model = Mock(return_value=mock_boto_response)

        with pytest.raises(InvalidResponseError, match="missing 'action_items' array"):
            await bedrock_client.extract_action_items("Test notes")

    @pytest.mark.asyncio
    async def test_extract_action_items_invalid_action_items_type(self, bedrock_client):
        """Test extraction when action_items is not a list."""
        mock_response = {
            "content": [{
                "type": "text",
                "text": json.dumps({"action_items": "not a list"})
            }]
        }

        mock_boto_response = {
            "body": MagicMock()
        }
        mock_boto_response["body"].read.return_value = json.dumps(mock_response).encode()

        bedrock_client.client = Mock()
        bedrock_client.client.invoke_model = Mock(return_value=mock_boto_response)

        with pytest.raises(InvalidResponseError, match="must be an array"):
            await bedrock_client.extract_action_items("Test notes")

    @pytest.mark.asyncio
    async def test_extract_action_items_skips_invalid_items(self, bedrock_client):
        """Test that invalid items are skipped."""
        mock_response = {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "action_items": [
                        {
                            "description": "Valid task",
                            "owner": "John"
                        },
                        "not a dict",
                        {
                            "owner": "Mike"  # Missing description
                        },
                        {
                            "description": "Another valid task"
                        }
                    ]
                })
            }]
        }

        mock_boto_response = {
            "body": MagicMock()
        }
        mock_boto_response["body"].read.return_value = json.dumps(mock_response).encode()

        bedrock_client.client = Mock()
        bedrock_client.client.invoke_model = Mock(return_value=mock_boto_response)

        result = await bedrock_client.extract_action_items("Test notes")

        assert len(result) == 2
        assert result[0].description == "Valid task"
        assert result[1].description == "Another valid task"

    @pytest.mark.asyncio
    async def test_extract_action_items_with_api_key(self, monkeypatch):
        """Test extraction using API key authentication."""
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
        monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-api-key")

        client = BedrockModelClient()

        mock_response = {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "action_items": [{
                        "description": "Test task",
                        "owner": "John"
                    }]
                })
            }]
        }

        with patch('httpx.AsyncClient') as mock_httpx:
            mock_post = AsyncMock(return_value=Mock(
                status_code=200,
                json=Mock(return_value=mock_response)
            ))
            mock_httpx.return_value.__aenter__.return_value.post = mock_post

            result = await client.extract_action_items("Test notes")

            assert len(result) == 1
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_action_items_api_error(self, bedrock_client):
        """Test extraction when API call fails."""
        bedrock_client.client = Mock()
        bedrock_client.client.invoke_model = Mock(
            side_effect=Exception("API connection failed")
        )

        with pytest.raises(ModelAPIError, match="Bedrock API call failed"):
            await bedrock_client.extract_action_items("Test notes")

    @pytest.mark.asyncio
    async def test_extract_action_items_with_optional_fields(self, bedrock_client):
        """Test extraction with all optional fields present."""
        mock_response = {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "action_items": [
                        {
                            "description": "Complete task",
                            "owner": "Alice",
                            "due_date": "2026-08-01",
                            "confidence": 0.92
                        }
                    ]
                })
            }]
        }

        mock_boto_response = {
            "body": MagicMock()
        }
        mock_boto_response["body"].read.return_value = json.dumps(mock_response).encode()

        bedrock_client.client = Mock()
        bedrock_client.client.invoke_model = Mock(return_value=mock_boto_response)

        result = await bedrock_client.extract_action_items("Test notes")

        assert len(result) == 1
        item = result[0]
        assert item.description == "Complete task"
        assert item.owner == "Alice"
        assert item.due_date == "2026-08-01"
        assert item.confidence == 0.92

    @pytest.mark.asyncio
    async def test_extract_action_items_without_optional_fields(self, bedrock_client):
        """Test extraction with only required fields."""
        mock_response = {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "action_items": [
                        {
                            "description": "Minimal task"
                        }
                    ]
                })
            }]
        }

        mock_boto_response = {
            "body": MagicMock()
        }
        mock_boto_response["body"].read.return_value = json.dumps(mock_response).encode()

        bedrock_client.client = Mock()
        bedrock_client.client.invoke_model = Mock(return_value=mock_boto_response)

        result = await bedrock_client.extract_action_items("Test notes")

        assert len(result) == 1
        item = result[0]
        assert item.description == "Minimal task"
        assert item.owner is None
        assert item.due_date is None
        assert item.confidence is None
