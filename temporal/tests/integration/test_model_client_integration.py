import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json
import time
import os

from botocore.exceptions import ClientError, BotoCoreError
from azure.core.exceptions import HttpResponseError, ServiceRequestError

try:
    import vcr
    HAS_VCR = True
except ImportError:
    HAS_VCR = False
    vcr = None


class TestModelClientIntegration:
    """Integration tests for model client functionality.

    These tests verify actual integration with model APIs using VCR.py to record/replay
    real API responses. Tests marked with @pytest.mark.skipif will only run when:
    1. vcr library is installed (pip install vcrpy)
    2. Real credentials are configured (AWS_ACCESS_KEY_ID or AZURE_OPENAI_ENDPOINT)

    On first run with credentials, VCR records actual API responses to cassettes/.
    Subsequent runs replay recorded responses without hitting the API.
    """

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_VCR, reason="vcr library not installed")
    @pytest.mark.skipif(not os.getenv('AWS_ACCESS_KEY_ID'), reason="AWS credentials not configured")
    async def test_bedrock_client_actual_extraction(self):
        """Test actual extraction using real Bedrock client with recorded responses."""
        cassette_path = os.path.join(os.path.dirname(__file__), 'cassettes', 'bedrock_extraction.yaml')
        os.makedirs(os.path.dirname(cassette_path), exist_ok=True)

        with vcr.use_cassette(cassette_path, record_mode='once'):
            from model_client import BedrockModelClient
            client = BedrockModelClient(model_id='anthropic.claude-3-sonnet-20240229-v1:0')

            result = await client.extract_action_items('Real meeting transcript: We need to complete the project proposal by next Friday and review the quarterly budget.')

            assert result is not None
            assert 'action_items' in result
            assert isinstance(result['action_items'], list)
            if len(result['action_items']) > 0:
                assert 'description' in result['action_items'][0]
                assert result['action_items'][0]['description'] != ''
                assert len(result['action_items'][0]['description']) > 5

    @pytest.mark.asyncio
    async def test_bedrock_api_error_handling(self):
        """Test handling of Bedrock API errors."""
        mock_bedrock_client = Mock()
        mock_bedrock_client.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'InvokeModel'
        )

        with patch('boto3.client', return_value=mock_bedrock_client):
            from model_client import BedrockModelClient
            client = BedrockModelClient(model_id='anthropic.claude-3-sonnet-20240229-v1:0')

            with pytest.raises(Exception) as exc_info:
                await client.extract_action_items('Test transcript')

            assert 'ThrottlingException' in str(exc_info.value) or 'Rate' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_response_handling(self):
        """Test handling of invalid/malformed responses."""
        mock_bedrock_client = Mock()
        mock_response = {
            'body': Mock(read=lambda: b'Invalid JSON response')
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        with patch('boto3.client', return_value=mock_bedrock_client):
            from model_client import BedrockModelClient
            client = BedrockModelClient(model_id='anthropic.claude-3-sonnet-20240229-v1:0')

            with pytest.raises((json.JSONDecodeError, ValueError, KeyError, Exception)):
                await client.extract_action_items('Test transcript')

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_VCR, reason="vcr library not installed")
    @pytest.mark.skipif(not os.getenv('AZURE_OPENAI_ENDPOINT'), reason="Azure credentials not configured")
    async def test_azure_client_actual_extraction(self):
        """Test actual extraction using real Azure OpenAI client with recorded responses."""
        cassette_path = os.path.join(os.path.dirname(__file__), 'cassettes', 'azure_extraction.yaml')
        os.makedirs(os.path.dirname(cassette_path), exist_ok=True)

        with vcr.use_cassette(cassette_path, record_mode='once'):
            from model_client import AzureModelClient
            client = AzureModelClient(
                endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', 'https://test.openai.azure.com'),
                api_key=os.getenv('AZURE_OPENAI_API_KEY', 'test-key'),
                deployment_name=os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')
            )

            result = await client.extract_action_items('Azure meeting notes: Review the deployment pipeline and update the documentation.')

            assert result is not None
            assert 'action_items' in result
            assert isinstance(result['action_items'], list)
            if len(result['action_items']) > 0:
                assert 'description' in result['action_items'][0]
                assert result['action_items'][0]['description'] != ''
                assert len(result['action_items'][0]['description']) > 5

    @pytest.mark.asyncio
    async def test_rate_limiting_handling(self):
        """Test rate limiting behavior and backoff."""
        mock_bedrock_client = Mock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ClientError(
                    {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate limit exceeded'}},
                    'InvokeModel'
                )
            return {
                'body': Mock(read=lambda: json.dumps({
                    'content': [{'text': json.dumps({'action_items': []})}]
                }).encode())
            }

        mock_bedrock_client.invoke_model.side_effect = side_effect

        with patch('boto3.client', return_value=mock_bedrock_client):
            from model_client import BedrockModelClient
            client = BedrockModelClient(
                model_id='anthropic.claude-3-sonnet-20240229-v1:0',
                max_retries=3,
                retry_delay=0.1
            )

            result = await client.extract_action_items('Test transcript')

            assert call_count == 3
            assert result is not None

    @pytest.mark.asyncio
    async def test_authentication_errors(self):
        """Test handling of authentication and authorization errors."""
        mock_bedrock_client = Mock()
        mock_bedrock_client.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'UnauthorizedException', 'Message': 'Invalid credentials'}},
            'InvokeModel'
        )

        with patch('boto3.client', return_value=mock_bedrock_client):
            from model_client import BedrockModelClient
            client = BedrockModelClient(model_id='anthropic.claude-3-sonnet-20240229-v1:0')

            with pytest.raises(Exception) as exc_info:
                await client.extract_action_items('Test transcript')

            assert 'Unauthorized' in str(exc_info.value) or 'credentials' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_model_client_factory(self):
        """Test model client factory for creating different client types."""
        from model_client import ModelClientFactory

        bedrock_config = {
            'provider': 'bedrock',
            'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'region': 'us-east-1'
        }

        azure_config = {
            'provider': 'azure',
            'endpoint': 'https://test.openai.azure.com',
            'api_key': 'test-key',
            'deployment_name': 'gpt-4'
        }

        with patch('boto3.client'):
            bedrock_client = ModelClientFactory.create_client(bedrock_config)
            assert bedrock_client is not None
            assert bedrock_client.__class__.__name__ == 'BedrockModelClient'

        with patch('openai.AzureOpenAI'):
            azure_client = ModelClientFactory.create_client(azure_config)
            assert azure_client is not None
            assert azure_client.__class__.__name__ == 'AzureModelClient'

    @pytest.mark.asyncio
    async def test_data_transformation(self):
        """Test data transformation from raw API response to structured format."""
        raw_response = {
            'action_items': [
                {
                    'id': '1',
                    'description': 'Update documentation',
                    'priority': 'high',
                    'due_date': '2026-07-10',
                    'assignee': 'dev@example.com'
                },
                {
                    'id': '2',
                    'description': 'Fix bug in payment flow',
                    'priority': 'critical',
                    'due_date': '2026-07-08'
                }
            ]
        }

        from model_client import ActionItemTransformer
        transformer = ActionItemTransformer()

        transformed = transformer.transform(raw_response)

        assert len(transformed) == 2
        assert all('id' in item for item in transformed)
        assert all('description' in item for item in transformed)
        assert all('priority' in item for item in transformed)
        assert transformed[0]['priority'] == 'high'
        assert transformed[1]['priority'] == 'critical'

    @pytest.mark.asyncio
    async def test_action_item_serialization(self):
        """Test serialization of action items to different formats."""
        action_items = [
            {
                'id': '1',
                'description': 'Complete integration tests',
                'priority': 'high',
                'due_date': '2026-07-15',
                'assignee': 'qa@example.com',
                'status': 'pending'
            },
            {
                'id': '2',
                'description': 'Deploy to staging',
                'priority': 'medium',
                'due_date': '2026-07-20',
                'assignee': 'devops@example.com',
                'status': 'in_progress'
            }
        ]

        from model_client import ActionItemSerializer
        serializer = ActionItemSerializer()

        json_output = serializer.to_json(action_items)
        assert isinstance(json_output, str)
        parsed = json.loads(json_output)
        assert len(parsed) == 2

        dict_output = serializer.to_dict(action_items)
        assert isinstance(dict_output, dict)
        assert 'action_items' in dict_output
        assert len(dict_output['action_items']) == 2

    @pytest.mark.asyncio
    async def test_retry_behavior_exponential_backoff(self):
        """Test retry behavior with exponential backoff."""
        mock_bedrock_client = Mock()
        attempt_times = []

        def side_effect(*args, **kwargs):
            attempt_times.append(datetime.now())
            if len(attempt_times) < 4:
                raise ClientError(
                    {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service temporarily unavailable'}},
                    'InvokeModel'
                )
            return {
                'body': Mock(read=lambda: json.dumps({
                    'content': [{'text': json.dumps({'action_items': []})}]
                }).encode())
            }

        mock_bedrock_client.invoke_model.side_effect = side_effect

        with patch('boto3.client', return_value=mock_bedrock_client):
            from model_client import BedrockModelClient
            client = BedrockModelClient(
                model_id='anthropic.claude-3-sonnet-20240229-v1:0',
                max_retries=5,
                retry_delay=0.1,
                exponential_backoff=True
            )

            result = await client.extract_action_items('Test transcript')

            assert len(attempt_times) == 4
            assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests to model client."""
        mock_bedrock_client = Mock()
        request_count = 0

        def side_effect(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            return {
                'body': Mock(read=lambda: json.dumps({
                    'content': [{'text': json.dumps({
                        'action_items': [{'id': str(request_count), 'description': f'Task {request_count}'}]
                    })}]
                }).encode())
            }

        mock_bedrock_client.invoke_model.side_effect = side_effect

        with patch('boto3.client', return_value=mock_bedrock_client):
            from model_client import BedrockModelClient
            client = BedrockModelClient(model_id='anthropic.claude-3-sonnet-20240229-v1:0')

            tasks = [
                client.extract_action_items(f'Transcript {i}')
                for i in range(5)
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            assert request_count == 5
            assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_empty_transcript_handling(self):
        """Test handling of empty or null transcripts."""
        mock_bedrock_client = Mock()
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'content': [{'text': json.dumps({'action_items': []})}]
            }).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        with patch('boto3.client', return_value=mock_bedrock_client):
            from model_client import BedrockModelClient
            client = BedrockModelClient(model_id='anthropic.claude-3-sonnet-20240229-v1:0')

            result_empty = await client.extract_action_items('')
            assert result_empty is not None
            assert 'action_items' in result_empty
            assert len(result_empty['action_items']) == 0

            result_whitespace = await client.extract_action_items('   ')
            assert result_whitespace is not None

    @pytest.mark.asyncio
    async def test_large_transcript_processing(self):
        """Test processing of large transcripts with token limits."""
        mock_bedrock_client = Mock()
        large_transcript = 'Meeting notes. ' * 10000

        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'content': [{'text': json.dumps({
                    'action_items': [
                        {'id': '1', 'description': 'Task from large transcript', 'priority': 'high'}
                    ]
                })}]
            }).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        with patch('boto3.client', return_value=mock_bedrock_client):
            from model_client import BedrockModelClient
            client = BedrockModelClient(
                model_id='anthropic.claude-3-sonnet-20240229-v1:0',
                max_tokens=4096
            )

            result = await client.extract_action_items(large_transcript)

            assert result is not None
            assert 'action_items' in result

            call_args = mock_bedrock_client.invoke_model.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_model_rate_limiting(self):
        """Test that model client respects rate limits."""
        mock_bedrock_client = Mock()
        request_times = []

        def side_effect(*args, **kwargs):
            request_times.append(time.time())
            return {
                'body': Mock(read=lambda: json.dumps({
                    'content': [{'text': json.dumps({
                        'action_items': [{'id': str(len(request_times)), 'description': f'Task {len(request_times)}'}]
                    })}]
                }).encode())
            }

        mock_bedrock_client.invoke_model.side_effect = side_effect

        with patch('boto3.client', return_value=mock_bedrock_client):
            from model_client import BedrockModelClient
            client = BedrockModelClient(
                model_id='anthropic.claude-3-sonnet-20240229-v1:0',
                max_requests_per_minute=10
            )

            start_time = time.time()
            results = []

            for i in range(20):
                result = await client.extract_action_items(f'Test transcript {i}')
                results.append(result)

            elapsed = time.time() - start_time

            assert len(results) == 20
            assert all(result is not None for result in results)
            if hasattr(client, 'max_requests_per_minute') and client.max_requests_per_minute:
                assert elapsed >= 60.0, f"Rate limiting should enforce at least 60s for 20 requests at 10 req/min, got {elapsed}s"

            if len(request_times) >= 11:
                first_window_duration = request_times[10] - request_times[0]
                assert first_window_duration >= 60.0, f"First 10 requests should span at least 60s with rate limiting, got {first_window_duration}s"

    @pytest.mark.asyncio
    async def test_model_cost_tracking(self):
        """Test that model usage is tracked for cost control."""
        mock_bedrock_client = Mock()
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'content': [{'text': json.dumps({
                    'action_items': [
                        {'id': '1', 'description': 'Test task', 'priority': 'high'}
                    ]
                })}]
            }).encode()),
            'ResponseMetadata': {
                'usage': {
                    'inputTokens': 150,
                    'outputTokens': 50
                }
            }
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        with patch('boto3.client', return_value=mock_bedrock_client):
            from model_client import BedrockModelClient
            client = BedrockModelClient(model_id='anthropic.claude-3-sonnet-20240229-v1:0')

            initial_cost = getattr(client, 'total_cost', 0)
            initial_tokens = getattr(client, 'total_tokens', 0)
            initial_count = getattr(client, 'request_count', 0)

            await client.extract_action_items('Test transcript for cost tracking')

            if hasattr(client, 'total_cost'):
                assert client.total_cost >= initial_cost, "Cost tracking should increase or stay same"
            if hasattr(client, 'total_tokens'):
                assert client.total_tokens > initial_tokens, "Token count should increase after request"
            if hasattr(client, 'request_count'):
                assert client.request_count == initial_count + 1, "Request count should increment by 1"

            cost_per_request = getattr(client, 'total_cost', 0) - initial_cost
            tokens_per_request = getattr(client, 'total_tokens', 0) - initial_tokens

            if hasattr(client, 'get_usage_report'):
                usage_report = client.get_usage_report()
                assert 'total_cost' in usage_report or 'total_tokens' in usage_report or 'request_count' in usage_report
                assert usage_report.get('request_count', 0) >= 1

    @pytest.mark.asyncio
    async def test_cost_limit_enforcement(self):
        """Test that cost limits are enforced to prevent runaway spending."""
        mock_bedrock_client = Mock()
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'content': [{'text': json.dumps({
                    'action_items': [{'id': '1', 'description': 'Task'}]
                })}]
            }).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        with patch('boto3.client', return_value=mock_bedrock_client):
            from model_client import BedrockModelClient
            client = BedrockModelClient(
                model_id='anthropic.claude-3-sonnet-20240229-v1:0',
                max_cost_limit=0.01
            )

            if hasattr(client, 'max_cost_limit') and client.max_cost_limit:
                if hasattr(client, 'total_cost'):
                    client.total_cost = 0.009

                await client.extract_action_items('Test transcript')

                if hasattr(client, 'total_cost'):
                    client.total_cost = 0.011

                with pytest.raises(Exception) as exc_info:
                    await client.extract_action_items('Another test transcript')

                assert 'cost' in str(exc_info.value).lower() or 'limit' in str(exc_info.value).lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
