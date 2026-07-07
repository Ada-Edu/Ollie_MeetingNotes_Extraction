"""Unit tests for model client factory."""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import patch, Mock
from model_client.factory import get_model_client, get_model_info


class TestGetModelClient:
    """Tests for get_model_client factory function."""

    @patch('model_client.factory.os.getenv')
    def test_returns_azure_client_for_azure_provider(self, mock_getenv):
        """Test that azure client is returned when MODEL_PROVIDER is azure."""
        mock_getenv.side_effect = lambda key, default='': {
            'MODEL_PROVIDER': 'azure',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com',
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-4'
        }.get(key, default)

        with patch('model_client.factory.AzureModelClient') as MockAzureClient:
            client = get_model_client()
            MockAzureClient.assert_called_once()

    @patch('model_client.factory.os.getenv')
    def test_returns_bedrock_client_for_bedrock_provider(self, mock_getenv):
        """Test that bedrock client is returned when MODEL_PROVIDER is bedrock."""
        mock_getenv.side_effect = lambda key, default='': {
            'MODEL_PROVIDER': 'bedrock',
            'AWS_REGION': 'us-east-1',
            'BEDROCK_MODEL_ID': 'anthropic.claude-v2'
        }.get(key, default)

        with patch('model_client.factory.BedrockModelClient') as MockBedrockClient:
            client = get_model_client()
            MockBedrockClient.assert_called_once()

    @patch('model_client.factory.os.getenv')
    def test_raises_error_for_invalid_provider(self, mock_getenv):
        """Test that ValueError is raised for invalid MODEL_PROVIDER."""
        mock_getenv.side_effect = lambda key, default='': {
            'MODEL_PROVIDER': 'invalid_provider'
        }.get(key, default)

        with pytest.raises(ValueError, match="Invalid MODEL_PROVIDER"):
            get_model_client()

    @patch('model_client.factory.os.getenv')
    def test_raises_error_for_missing_provider(self, mock_getenv):
        """Test that ValueError is raised when MODEL_PROVIDER is not set."""
        mock_getenv.return_value = ''

        with pytest.raises(ValueError, match="MODEL_PROVIDER environment variable not set"):
            get_model_client()

    @patch('model_client.factory.os.getenv')
    def test_provider_name_case_insensitive(self, mock_getenv):
        """Test that provider name matching is case-insensitive."""
        mock_getenv.side_effect = lambda key, default='': {
            'MODEL_PROVIDER': 'AZURE',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com',
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-4'
        }.get(key, default)

        with patch('model_client.factory.AzureModelClient') as MockAzureClient:
            client = get_model_client()
            MockAzureClient.assert_called_once()


class TestGetModelInfo:
    """Tests for get_model_info function."""

    @patch('model_client.factory.get_model_client')
    def test_returns_provider_and_model_name(self, mock_get_client):
        """Test that model info contains provider and model name."""
        mock_client = Mock()
        mock_client.get_provider_name.return_value = "azure"
        mock_client.get_model_name.return_value = "gpt-4"
        mock_get_client.return_value = mock_client

        info = get_model_info()

        assert info["provider"] == "azure"
        assert info["model_name"] == "gpt-4"

    @patch('model_client.factory.get_model_client')
    def test_calls_client_methods(self, mock_get_client):
        """Test that get_model_info calls client methods."""
        mock_client = Mock()
        mock_client.get_provider_name.return_value = "bedrock"
        mock_client.get_model_name.return_value = "claude-v2"
        mock_get_client.return_value = mock_client

        info = get_model_info()

        mock_client.get_provider_name.assert_called_once()
        mock_client.get_model_name.assert_called_once()
