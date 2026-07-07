"""Tests for model client abstraction."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from temporal.src.model_client.base import ActionItem, ModelAPIError, InvalidResponseError
from temporal.src.model_client.factory import get_model_client, get_model_info
from temporal.src.model_client.azure_client import AzureModelClient


class TestActionItem:
    """Test ActionItem dataclass."""

    def test_action_item_creation(self):
        item = ActionItem(
            description="Test task",
            owner="John",
            due_date="2026-07-15",
            confidence=0.95
        )
        assert item.description == "Test task"
        assert item.owner == "John"
        assert item.due_date == "2026-07-15"
        assert item.confidence == 0.95

    def test_action_item_optional_fields(self):
        item = ActionItem(description="Test task")
        assert item.description == "Test task"
        assert item.owner is None
        assert item.due_date is None
        assert item.confidence is None

    def test_action_item_to_dict(self):
        item = ActionItem(
            description="Test task",
            owner="Jane",
            confidence=0.88
        )
        result = item.to_dict()
        assert result == {
            "description": "Test task",
            "owner": "Jane",
            "due_date": None,
            "confidence": 0.88
        }


class TestModelFactory:
    """Test model client factory."""

    def test_factory_requires_provider(self):
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="MODEL_PROVIDER"):
                get_model_client()

    def test_factory_rejects_invalid_provider(self):
        with patch.dict('os.environ', {'MODEL_PROVIDER': 'invalid'}):
            with pytest.raises(ValueError, match="Invalid MODEL_PROVIDER"):
                get_model_client()

    @patch('temporal.src.model_client.azure_client.AzureOpenAI')
    def test_factory_creates_azure_client(self, mock_azure):
        with patch.dict('os.environ', {
            'MODEL_PROVIDER': 'azure',
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-4'
        }):
            client = get_model_client()
            assert isinstance(client, AzureModelClient)
            assert client.get_provider_name() == 'azure'

    @patch('temporal.src.model_client.azure_client.AzureOpenAI')
    def test_get_model_info_success(self, mock_azure):
        with patch.dict('os.environ', {
            'MODEL_PROVIDER': 'azure',
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-4'
        }):
            info = get_model_info()
            assert info['provider'] == 'azure'
            assert info['model_name'] == 'gpt-4'

    def test_get_model_info_failure(self):
        with patch.dict('os.environ', {}, clear=True):
            info = get_model_info()
            assert info['provider'] is None
            assert 'error' in info


class TestAzureClient:
    """Test Azure OpenAI client."""

    @patch('temporal.src.model_client.azure_client.AzureOpenAI')
    async def test_extract_action_items_success(self, mock_azure_class):
        # Setup mock
        mock_client = Mock()
        mock_azure_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='''{
                "action_items": [
                    {
                        "description": "Follow up with Sarah",
                        "owner": "John",
                        "due_date": "2026-07-15",
                        "confidence": 0.95
                    },
                    {
                        "description": "Review design doc"
                    }
                ]
            }'''))
        ]
        mock_client.chat.completions.create = Mock(return_value=mock_response)

        with patch.dict('os.environ', {
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-4'
        }):
            client = AzureModelClient()
            items = await client.extract_action_items("Test meeting notes")

            assert len(items) == 2
            assert items[0].description == "Follow up with Sarah"
            assert items[0].owner == "John"
            assert items[0].due_date == "2026-07-15"
            assert items[1].description == "Review design doc"
            assert items[1].owner is None

    @patch('temporal.src.model_client.azure_client.AzureOpenAI')
    async def test_extract_action_items_invalid_json(self, mock_azure_class):
        mock_client = Mock()
        mock_azure_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='Invalid JSON'))]
        mock_client.chat.completions.create = Mock(return_value=mock_response)

        with patch.dict('os.environ', {
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        }):
            client = AzureModelClient()

            with pytest.raises(InvalidResponseError):
                await client.extract_action_items("Test notes")

    @patch('temporal.src.model_client.azure_client.AzureOpenAI')
    async def test_extract_action_items_missing_array(self, mock_azure_class):
        mock_client = Mock()
        mock_azure_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='{"other_key": "value"}'))
        ]
        mock_client.chat.completions.create = Mock(return_value=mock_response)

        with patch.dict('os.environ', {
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        }):
            client = AzureModelClient()

            with pytest.raises(InvalidResponseError, match="action_items"):
                await client.extract_action_items("Test notes")

    @patch('temporal.src.model_client.azure_client.AzureOpenAI')
    async def test_extract_action_items_api_error(self, mock_azure_class):
        mock_client = Mock()
        mock_azure_class.return_value = mock_client

        mock_client.chat.completions.create = Mock(
            side_effect=Exception("API Error")
        )

        with patch.dict('os.environ', {
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        }):
            client = AzureModelClient()

            with pytest.raises(ModelAPIError):
                await client.extract_action_items("Test notes")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
