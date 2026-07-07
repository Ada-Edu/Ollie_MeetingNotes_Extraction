"""Unit tests for Supabase client."""
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import Mock, AsyncMock, patch
from supabase_client import SupabaseClient, get_supabase_client


class TestSupabaseClient:
    """Tests for SupabaseClient."""

    @pytest.fixture
    def mock_settings(self, monkeypatch):
        """Mock settings for testing."""
        monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")

    @pytest.fixture
    def client(self, mock_settings):
        """Create client instance."""
        return SupabaseClient()

    def test_initialization(self, client):
        """Test client initialization."""
        assert client.base_url == "http://localhost:54321"
        assert client.rest_url == "http://localhost:54321/rest/v1"
        assert "apikey" in client.headers
        assert "Authorization" in client.headers
        assert client.headers["Content-Type"] == "application/json"

    def test_headers_configuration(self, client):
        """Test that headers are properly configured."""
        assert client.headers["apikey"] == "test-service-key"
        assert client.headers["Authorization"] == "Bearer test-service-key"
        assert client.headers["Prefer"] == "return=representation"

    @pytest.mark.asyncio
    async def test_request_get(self, client):
        """Test GET request."""
        mock_response = [{"id": "1", "name": "Test Entity"}]

        with patch('httpx.AsyncClient') as mock_client:
            mock_request = AsyncMock(return_value=Mock(
                status_code=200,
                json=Mock(return_value=mock_response)
            ))
            mock_client.return_value.__aenter__.return_value.request = mock_request

            result = await client._request("GET", "entities")

            assert result == mock_response
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args.kwargs['method'] == 'GET'
            assert 'entities' in call_args.kwargs['url']

    @pytest.mark.asyncio
    async def test_request_post(self, client):
        """Test POST request."""
        mock_data = {"name": "New Entity", "type": "test"}
        mock_response = {"id": "123", **mock_data}

        with patch('httpx.AsyncClient') as mock_client:
            mock_request = AsyncMock(return_value=Mock(
                status_code=200,
                json=Mock(return_value=mock_response)
            ))
            mock_client.return_value.__aenter__.return_value.request = mock_request

            result = await client._request("POST", "entities", data=mock_data)

            assert result == mock_response
            call_args = mock_request.call_args
            assert call_args.kwargs['json'] == mock_data

    @pytest.mark.asyncio
    async def test_request_with_params(self, client):
        """Test request with query parameters."""
        params = {"id": "eq.123", "limit": "10"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_request = AsyncMock(return_value=Mock(
                status_code=200,
                json=Mock(return_value=[])
            ))
            mock_client.return_value.__aenter__.return_value.request = mock_request

            await client._request("GET", "entities", params=params)

            call_args = mock_request.call_args
            assert call_args.kwargs['params'] == params

    @pytest.mark.asyncio
    async def test_request_http_error(self, client):
        """Test request with HTTP error."""
        import httpx

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock(status_code=404, text="Not Found")
            mock_request = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "404 Not Found",
                    request=Mock(),
                    response=mock_response
                )
            )
            mock_client.return_value.__aenter__.return_value.request = mock_request

            with pytest.raises(httpx.HTTPStatusError):
                await client._request("GET", "entities")

    @pytest.mark.asyncio
    async def test_request_timeout(self, client):
        """Test request timeout handling."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_request = AsyncMock(side_effect=Exception("Timeout"))
            mock_client.return_value.__aenter__.return_value.request = mock_request

            with pytest.raises(Exception, match="Timeout"):
                await client._request("GET", "entities")

    @pytest.mark.asyncio
    async def test_create_entity(self, client):
        """Test creating an entity."""
        mock_response = {"id": "entity-123", "entity_type": "test_type"}

        with patch.object(client, '_request', AsyncMock(return_value=mock_response)):
            result = await client.create_entity("test_type", "source-123")

            assert result == mock_response
            client._request.assert_called_once_with(
                "POST",
                "entities",
                data={
                    "entity_type": "test_type",
                    "source_record_id": "source-123"
                }
            )

    @pytest.mark.asyncio
    async def test_create_entity_from_list_response(self, client):
        """Test creating entity when API returns list."""
        mock_response = [{"id": "entity-123", "entity_type": "test_type"}]

        with patch.object(client, '_request', AsyncMock(return_value=mock_response)):
            result = await client.create_entity("test_type")

            assert result == mock_response[0]

    @pytest.mark.asyncio
    async def test_get_entity(self, client):
        """Test getting an entity."""
        mock_response = [{"id": "entity-123", "entity_type": "test_type"}]

        with patch.object(client, '_request', AsyncMock(return_value=mock_response)):
            result = await client.get_entity("entity-123")

            assert result == mock_response[0]
            client._request.assert_called_once_with(
                "GET",
                "entities",
                params={"id": "eq.entity-123"}
            )

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self, client):
        """Test getting entity that doesn't exist."""
        with patch.object(client, '_request', AsyncMock(return_value=[])):
            result = await client.get_entity("nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_create_entity_version(self, client):
        """Test creating an entity version."""
        mock_response = {
            "id": "version-123",
            "entity_id": "entity-123",
            "version_number": 1,
            "data": {"key": "value"},
            "is_current": True
        }

        with patch.object(client, '_request', AsyncMock(return_value=mock_response)):
            result = await client.create_entity_version(
                "entity-123",
                1,
                {"key": "value"}
            )

            assert result == mock_response
            call_args = client._request.call_args
            assert call_args[0] == ("POST", "entity_versions")
            assert call_args[1]['data']['entity_id'] == "entity-123"
            assert call_args[1]['data']['version_number'] == 1
            assert call_args[1]['data']['is_current'] is True

    @pytest.mark.asyncio
    async def test_get_current_entity_version(self, client):
        """Test getting current entity version."""
        mock_response = [{
            "id": "version-123",
            "entity_id": "entity-123",
            "is_current": True
        }]

        with patch.object(client, '_request', AsyncMock(return_value=mock_response)):
            result = await client.get_current_entity_version("entity-123")

            assert result == mock_response[0]
            client._request.assert_called_once_with(
                "GET",
                "entity_versions",
                params={
                    "entity_id": "eq.entity-123",
                    "is_current": "eq.true"
                }
            )

    @pytest.mark.asyncio
    async def test_create_relationship(self, client):
        """Test creating a relationship."""
        mock_response = {
            "id": "rel-123",
            "relationship_type": "parent_of",
            "parent_id": "parent-123",
            "child_id": "child-123",
            "is_current": True
        }

        with patch.object(client, '_request', AsyncMock(return_value=mock_response)):
            result = await client.create_relationship(
                "parent_of",
                "parent-123",
                "child-123",
                {"note": "test"}
            )

            assert result == mock_response
            call_args = client._request.call_args
            assert call_args[1]['data']['relationship_type'] == "parent_of"
            assert call_args[1]['data']['metadata'] == {"note": "test"}

    @pytest.mark.asyncio
    async def test_create_fact_type(self, client):
        """Test creating a fact type."""
        mock_response = {
            "id": "fact-type-123",
            "key": "revenue",
            "label": "Revenue",
            "unit": "USD"
        }

        with patch.object(client, '_request', AsyncMock(return_value=mock_response)):
            result = await client.create_fact_type(
                "revenue",
                "Revenue",
                "Total revenue",
                "USD"
            )

            assert result == mock_response

    @pytest.mark.asyncio
    async def test_get_fact_type_by_key(self, client):
        """Test getting fact type by key."""
        mock_response = [{
            "id": "fact-type-123",
            "key": "revenue"
        }]

        with patch.object(client, '_request', AsyncMock(return_value=mock_response)):
            result = await client.get_fact_type_by_key("revenue")

            assert result == mock_response[0]
            client._request.assert_called_once_with(
                "GET",
                "fact_types",
                params={"key": "eq.revenue"}
            )

    @pytest.mark.asyncio
    async def test_upsert_entity_fact(self, client):
        """Test upserting an entity fact."""
        mock_response = {
            "id": "fact-123",
            "entity_id": "entity-123",
            "fact_type_id": "fact-type-123",
            "value": 100.0
        }

        with patch('httpx.AsyncClient') as mock_httpx:
            mock_post = AsyncMock(return_value=Mock(
                status_code=200,
                json=Mock(return_value=mock_response)
            ))
            mock_httpx.return_value.__aenter__.return_value.post = mock_post

            result = await client.upsert_entity_fact(
                "entity-123",
                "fact-type-123",
                100.0
            )

            assert result == mock_response

    @pytest.mark.asyncio
    async def test_insert_time_series_point(self, client):
        """Test inserting time series data point."""
        mock_response = {
            "id": "ts-123",
            "entity_id": "entity-123",
            "fact_type_id": "fact-type-123",
            "observed_at": "2026-07-07T10:00:00Z",
            "data_payload": {"value": 100}
        }

        with patch.object(client, '_request', AsyncMock(return_value=mock_response)):
            result = await client.insert_time_series_point(
                "entity-123",
                "fact-type-123",
                "2026-07-07T10:00:00Z",
                {"value": 100}
            )

            assert result == mock_response


class TestGetSupabaseClient:
    """Tests for get_supabase_client singleton."""

    def test_returns_singleton(self, monkeypatch):
        """Test that get_supabase_client returns same instance."""
        monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")

        # Reset global client
        import supabase_client
        supabase_client._supabase_client = None

        client1 = get_supabase_client()
        client2 = get_supabase_client()

        assert client1 is client2

    def test_creates_client_on_first_call(self, monkeypatch):
        """Test that client is created on first call."""
        monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")

        # Reset global client
        import supabase_client
        supabase_client._supabase_client = None

        client = get_supabase_client()
        assert client is not None
        assert isinstance(client, SupabaseClient)
