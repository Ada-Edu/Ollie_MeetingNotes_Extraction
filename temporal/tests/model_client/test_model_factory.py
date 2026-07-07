"""Unit tests for model client factory."""
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import patch
from model_client.factory import get_model_client, get_model_info
from model_client.azure_client import AzureModelClient
from model_client.bedrock_client import BedrockModelClient


class TestModelClientFactory:
    """Tests for model client factory."""

    def test_get_model_client_azure(self, monkeypatch):
        """Test getting Azure model client."""
        monkeypatch.setenv("MODEL_PROVIDER", "azure")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")

        with patch('model_client.azure_client.AzureOpenAI'):
            client = get_model_client()
            assert isinstance(client, AzureModelClient)

    def test_get_model_client_bedrock(self, monkeypatch):
        """Test getting Bedrock model client."""
        monkeypatch.setenv("MODEL_PROVIDER", "bedrock")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key-id")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")

        with patch('boto3.client'):
            client = get_model_client()
            assert isinstance(client, BedrockModelClient)

    def test_get_model_client_case_insensitive(self, monkeypatch):
        """Test that provider name is case insensitive."""
        monkeypatch.setenv("MODEL_PROVIDER", "AZURE")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")

        with patch('model_client.azure_client.AzureOpenAI'):
            client = get_model_client()
            assert isinstance(client, AzureModelClient)

    def test_get_model_client_not_set(self, monkeypatch):
        """Test error when MODEL_PROVIDER is not set."""
        monkeypatch.delenv("MODEL_PROVIDER", raising=False)

        with pytest.raises(ValueError, match="MODEL_PROVIDER environment variable not set"):
            get_model_client()

    def test_get_model_client_empty_string(self, monkeypatch):
        """Test error when MODEL_PROVIDER is empty string."""
        monkeypatch.setenv("MODEL_PROVIDER", "")

        with pytest.raises(ValueError, match="MODEL_PROVIDER environment variable not set"):
            get_model_client()

    def test_get_model_client_invalid_provider(self, monkeypatch):
        """Test error with invalid provider name."""
        monkeypatch.setenv("MODEL_PROVIDER", "openai")

        with pytest.raises(ValueError, match="Invalid MODEL_PROVIDER.*Must be 'azure' or 'bedrock'"):
            get_model_client()

    def test_get_model_client_whitespace_handling(self, monkeypatch):
        """Test that whitespace is handled correctly."""
        monkeypatch.setenv("MODEL_PROVIDER", "  azure  ")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")

        with patch('model_client.azure_client.AzureOpenAI'):
            client = get_model_client()
            assert isinstance(client, AzureModelClient)

    def test_get_model_info_azure(self, monkeypatch):
        """Test getting model info for Azure."""
        monkeypatch.setenv("MODEL_PROVIDER", "azure")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4-turbo")

        with patch('model_client.azure_client.AzureOpenAI'):
            info = get_model_info()
            assert info["provider"] == "azure"
            assert info["model_name"] == "gpt-4-turbo"

    def test_get_model_info_bedrock(self, monkeypatch):
        """Test getting model info for Bedrock."""
        monkeypatch.setenv("MODEL_PROVIDER", "bedrock")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key-id")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")

        with patch('boto3.client'):
            info = get_model_info()
            assert info["provider"] == "bedrock"
            assert info["model_name"] == "anthropic.claude-3-sonnet"

    def test_get_model_info_error_handling(self, monkeypatch):
        """Test that get_model_info handles errors gracefully."""
        monkeypatch.delenv("MODEL_PROVIDER", raising=False)

        info = get_model_info()
        assert info["provider"] is None
        assert info["model_name"] is None
        assert "error" in info

    def test_get_model_info_initialization_error(self, monkeypatch):
        """Test get_model_info when client initialization fails."""
        monkeypatch.setenv("MODEL_PROVIDER", "azure")
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        info = get_model_info()
        assert info["provider"] is None
        assert info["model_name"] is None
        assert "error" in info
        assert "AZURE_OPENAI_API_KEY" in info["error"]

    def test_factory_creates_new_instance_each_call(self, monkeypatch):
        """Test that factory creates new instance on each call."""
        monkeypatch.setenv("MODEL_PROVIDER", "azure")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")

        with patch('model_client.azure_client.AzureOpenAI'):
            client1 = get_model_client()
            client2 = get_model_client()
            # Should be different instances
            assert client1 is not client2

    def test_get_model_client_provider_validation_message(self, monkeypatch):
        """Test that error message includes valid options."""
        monkeypatch.setenv("MODEL_PROVIDER", "invalid")

        with pytest.raises(ValueError) as exc_info:
            get_model_client()

        error_message = str(exc_info.value)
        assert "azure" in error_message.lower()
        assert "bedrock" in error_message.lower()

    def test_azure_client_initialization_with_all_env_vars(self, monkeypatch):
        """Test Azure client with all environment variables set."""
        monkeypatch.setenv("MODEL_PROVIDER", "azure")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-123")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://custom.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-05-01")
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "custom-gpt-4")

        with patch('model_client.azure_client.AzureOpenAI') as mock_azure:
            client = get_model_client()
            assert isinstance(client, AzureModelClient)
            mock_azure.assert_called_once_with(
                api_key="test-key-123",
                api_version="2024-05-01",
                azure_endpoint="https://custom.openai.azure.com"
            )

    def test_bedrock_client_initialization_with_all_env_vars(self, monkeypatch):
        """Test Bedrock client with all environment variables set."""
        monkeypatch.setenv("MODEL_PROVIDER", "bedrock")
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-opus")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key-id-123")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key-123")

        with patch('boto3.client') as mock_boto:
            client = get_model_client()
            assert isinstance(client, BedrockModelClient)
            mock_boto.assert_called_once()
            call_args = mock_boto.call_args
            assert call_args.kwargs['region_name'] == 'eu-west-1'
            assert call_args.kwargs['aws_access_key_id'] == 'test-key-id-123'
            assert call_args.kwargs['aws_secret_access_key'] == 'test-secret-key-123'
