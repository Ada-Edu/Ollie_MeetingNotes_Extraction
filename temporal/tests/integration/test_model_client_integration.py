"""
Integration tests for Model Client integration with AWS Bedrock and Azure OpenAI.
Tests real API interaction patterns without mocking the model clients themselves.

@group integration
"""

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import AsyncMock, Mock, patch
import json

from model_client.factory import get_model_client, get_model_info
from model_client.base import ActionItem, ModelAPIError, InvalidResponseError
from model_client.bedrock_client import BedrockClient
from model_client.azure_client import AzureOpenAIClient


@pytest.mark.integration
class TestBedrockClientIntegration:
    """Integration tests for Bedrock client with mocked boto3."""

    @pytest.mark.asyncio
    async def test_bedrock_client_successful_extraction(self):
        """Test Bedrock client extracts action items from response."""
        # Mock boto3 client
        mock_bedrock = Mock()
        mock_response = {
            "body": Mock()
        }

        # Simulate streaming response
        response_data = {
            "content": [{
                "text": json.dumps({
                    "action_items": [
                        {
                            "description": "Review Q4 budget",
                            "owner": "Finance Team",
                            "due_date": "2026-07-20",
                            "confidence": 0.95
                        },
                        {
                            "description": "Schedule follow-up meeting",
                            "owner": "Project Manager",
                            "due_date": None,
                            "confidence": 0.88
                        }
                    ]
                })
            }]
        }

        mock_response["body"].read.return_value = json.dumps(response_data).encode()

        mock_bedrock.invoke_model.return_value = mock_response

        with patch('model_client.bedrock_client.boto3') as mock_boto3:
            mock_boto3.client.return_value = mock_bedrock

            client = BedrockClient()
            result = await client.extract_action_items(
                "Team meeting: Finance team to review Q4 budget by July 20th. PM will schedule follow-up."
            )

            # Verify results
            assert len(result) == 2
            assert isinstance(result[0], ActionItem)
            assert result[0].description == "Review Q4 budget"
            assert result[0].owner == "Finance Team"
            assert result[0].due_date == "2026-07-20"
            assert result[0].confidence == 0.95

            assert result[1].description == "Schedule follow-up meeting"
            assert result[1].owner == "Project Manager"
            assert result[1].due_date is None

            # Verify boto3 was called correctly
            mock_bedrock.invoke_model.assert_called_once()
            call_args = mock_bedrock.invoke_model.call_args
            assert "modelId" in call_args[1]
            assert "body" in call_args[1]

    @pytest.mark.asyncio
    async def test_bedrock_client_handles_api_error(self):
        """Test Bedrock client handles API errors gracefully."""
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.side_effect = Exception("ServiceUnavailable: Bedrock is down")

        with patch('model_client.bedrock_client.boto3') as mock_boto3:
            mock_boto3.client.return_value = mock_bedrock

            client = BedrockClient()

            with pytest.raises(ModelAPIError) as exc_info:
                await client.extract_action_items("Test meeting notes")

            assert "ServiceUnavailable" in str(exc_info.value) or "Bedrock" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_bedrock_client_handles_invalid_response(self):
        """Test Bedrock client handles malformed responses."""
        mock_bedrock = Mock()
        mock_response = {
            "body": Mock()
        }

        # Invalid JSON response
        mock_response["body"].read.return_value = b"Not valid JSON"
        mock_bedrock.invoke_model.return_value = mock_response

        with patch('model_client.bedrock_client.boto3') as mock_boto3:
            mock_boto3.client.return_value = mock_bedrock

            client = BedrockClient()

            with pytest.raises(InvalidResponseError):
                await client.extract_action_items("Test notes")

    @pytest.mark.asyncio
    async def test_bedrock_client_handles_missing_action_items_field(self):
        """Test Bedrock client handles response without action_items field."""
        mock_bedrock = Mock()
        mock_response = {
            "body": Mock()
        }

        response_data = {
            "content": [{
                "text": json.dumps({"other_field": "value"})
            }]
        }

        mock_response["body"].read.return_value = json.dumps(response_data).encode()
        mock_bedrock.invoke_model.return_value = mock_response

        with patch('model_client.bedrock_client.boto3') as mock_boto3:
            mock_boto3.client.return_value = mock_bedrock

            client = BedrockClient()

            with pytest.raises(InvalidResponseError) as exc_info:
                await client.extract_action_items("Test notes")

            assert "action_items" in str(exc_info.value).lower()


@pytest.mark.integration
class TestAzureOpenAIClientIntegration:
    """Integration tests for Azure OpenAI client."""

    @pytest.mark.asyncio
    async def test_azure_client_successful_extraction(self):
        """Test Azure OpenAI client extracts action items."""
        # Mock OpenAI client
        mock_openai = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()

        mock_message.content = json.dumps({
            "action_items": [
                {
                    "description": "Update project timeline",
                    "owner": "Sarah Johnson",
                    "due_date": "2026-07-18",
                    "confidence": 0.91
                }
            ]
        })

        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch('model_client.azure_client.AsyncAzureOpenAI') as mock_azure_class:
            mock_azure_class.return_value = mock_openai

            client = AzureOpenAIClient()
            result = await client.extract_action_items(
                "Project meeting: Sarah to update timeline by Friday July 18th"
            )

            assert len(result) == 1
            assert isinstance(result[0], ActionItem)
            assert result[0].description == "Update project timeline"
            assert result[0].owner == "Sarah Johnson"
            assert result[0].due_date == "2026-07-18"
            assert result[0].confidence == 0.91

            # Verify API was called
            mock_openai.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_azure_client_handles_rate_limit(self):
        """Test Azure client handles rate limiting errors."""
        mock_openai = Mock()

        # Simulate rate limit error
        from openai import RateLimitError

        mock_openai.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                "Rate limit exceeded",
                response=Mock(status_code=429),
                body=None
            )
        )

        with patch('model_client.azure_client.AsyncAzureOpenAI') as mock_azure_class:
            mock_azure_class.return_value = mock_openai

            client = AzureOpenAIClient()

            with pytest.raises(ModelAPIError) as exc_info:
                await client.extract_action_items("Test notes")

            assert "rate limit" in str(exc_info.value).lower() or "429" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_azure_client_handles_authentication_error(self):
        """Test Azure client handles authentication errors."""
        mock_openai = Mock()

        from openai import AuthenticationError

        mock_openai.chat.completions.create = AsyncMock(
            side_effect=AuthenticationError(
                "Invalid API key",
                response=Mock(status_code=401),
                body=None
            )
        )

        with patch('model_client.azure_client.AsyncAzureOpenAI') as mock_azure_class:
            mock_azure_class.return_value = mock_openai

            client = AzureOpenAIClient()

            with pytest.raises(ModelAPIError) as exc_info:
                await client.extract_action_items("Test notes")

            assert "authentication" in str(exc_info.value).lower() or "401" in str(exc_info.value)


@pytest.mark.integration
class TestModelClientFactory:
    """Integration tests for model client factory."""

    def test_factory_returns_correct_client_based_on_env(self):
        """Test factory returns correct client based on MODEL_PROVIDER env var."""
        with patch.dict('os.environ', {'MODEL_PROVIDER': 'bedrock'}):
            with patch('model_client.factory.BedrockClient') as mock_bedrock:
                mock_instance = Mock()
                mock_bedrock.return_value = mock_instance

                client = get_model_client()

                mock_bedrock.assert_called_once()
                assert client == mock_instance

        with patch.dict('os.environ', {'MODEL_PROVIDER': 'azure'}):
            with patch('model_client.factory.AzureOpenAIClient') as mock_azure:
                mock_instance = Mock()
                mock_azure.return_value = mock_instance

                client = get_model_client()

                mock_azure.assert_called_once()
                assert client == mock_instance

    def test_factory_returns_singleton_instance(self):
        """Test factory returns same instance on multiple calls."""
        with patch.dict('os.environ', {'MODEL_PROVIDER': 'bedrock'}):
            with patch('model_client.factory.BedrockClient') as mock_bedrock:
                mock_instance = Mock()
                mock_bedrock.return_value = mock_instance

                client1 = get_model_client()
                client2 = get_model_client()

                # Should only create once
                assert mock_bedrock.call_count == 1
                assert client1 is client2

    def test_get_model_info_returns_correct_info(self):
        """Test get_model_info returns provider and model details."""
        mock_client = Mock()
        mock_client.get_provider_name.return_value = "bedrock"
        mock_client.get_model_name.return_value = "anthropic.claude-3-sonnet-v1"

        with patch('model_client.factory.get_model_client', return_value=mock_client):
            info = get_model_info()

            assert info["provider"] == "bedrock"
            assert info["model_name"] == "anthropic.claude-3-sonnet-v1"


@pytest.mark.integration
class TestModelClientDataTransformation:
    """Integration tests for data transformation between model responses and database format."""

    @pytest.mark.asyncio
    async def test_action_item_to_dict_transformation(self):
        """Test ActionItem.to_dict() produces correct format for database."""
        action_item = ActionItem(
            description="Complete code review",
            owner="Alice Smith",
            due_date="2026-07-25",
            confidence=0.93
        )

        result = action_item.to_dict()

        assert isinstance(result, dict)
        assert result["description"] == "Complete code review"
        assert result["owner"] == "Alice Smith"
        assert result["due_date"] == "2026-07-25"
        assert result["confidence"] == 0.93

    @pytest.mark.asyncio
    async def test_action_item_with_none_values(self):
        """Test ActionItem handles None values correctly."""
        action_item = ActionItem(
            description="Review documentation",
            owner=None,
            due_date=None,
            confidence=None
        )

        result = action_item.to_dict()

        assert result["description"] == "Review documentation"
        assert result["owner"] is None
        assert result["due_date"] is None
        assert result["confidence"] is None

    @pytest.mark.asyncio
    async def test_model_response_to_action_items_list(self):
        """Test converting model response to list of ActionItem objects."""
        mock_bedrock = Mock()
        mock_response = {"body": Mock()}

        response_data = {
            "content": [{
                "text": json.dumps({
                    "action_items": [
                        {
                            "description": "Item 1",
                            "owner": "Person 1",
                            "due_date": "2026-07-10",
                            "confidence": 0.9
                        },
                        {
                            "description": "Item 2",
                            "owner": None,
                            "due_date": None,
                            "confidence": 0.7
                        }
                    ]
                })
            }]
        }

        mock_response["body"].read.return_value = json.dumps(response_data).encode()
        mock_bedrock.invoke_model.return_value = mock_response

        with patch('model_client.bedrock_client.boto3') as mock_boto3:
            mock_boto3.client.return_value = mock_bedrock

            client = BedrockClient()
            result = await client.extract_action_items("Test notes")

            # Verify list of ActionItem objects
            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(item, ActionItem) for item in result)

            # Verify conversion to dict format
            dict_list = [item.to_dict() for item in result]
            assert dict_list[0]["description"] == "Item 1"
            assert dict_list[1]["owner"] is None


@pytest.mark.integration
class TestModelClientRetryBehavior:
    """Integration tests for retry behavior on transient failures."""

    @pytest.mark.asyncio
    async def test_client_retries_on_transient_error(self):
        """Test that activities can retry model client calls."""
        call_count = {"count": 0}

        mock_bedrock = Mock()

        def invoke_with_retry(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise Exception("Temporary network error")

            # Success on second try
            mock_response = {"body": Mock()}
            response_data = {
                "content": [{
                    "text": json.dumps({
                        "action_items": [
                            {"description": "Retry succeeded", "owner": "Test"}
                        ]
                    })
                }]
            }
            mock_response["body"].read.return_value = json.dumps(response_data).encode()
            return mock_response

        mock_bedrock.invoke_model.side_effect = invoke_with_retry

        with patch('model_client.bedrock_client.boto3') as mock_boto3:
            mock_boto3.client.return_value = mock_bedrock

            client = BedrockClient()

            # First call should fail
            with pytest.raises(ModelAPIError):
                await client.extract_action_items("Test notes")

            # Reset for retry
            call_count["count"] = 0

            # Simulate retry logic at activity level
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = await client.extract_action_items("Test notes")
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    continue

            # Should succeed on retry
            assert len(result) == 1
            assert result[0].description == "Retry succeeded"
