"""Unit tests for configuration management."""
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from config import Settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.temporal_address == "temporal:7233"
        assert settings.temporal_namespace == "default"
        assert settings.temporal_task_queue == "main"
        assert settings.supabase_url == "http://host.docker.internal:54321"
        assert settings.supabase_service_role_key == "dev-service-role-key"

    def test_settings_from_environment(self, monkeypatch):
        """Test loading settings from environment variables."""
        monkeypatch.setenv("TEMPORAL_ADDRESS", "localhost:7233")
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "production")
        monkeypatch.setenv("TEMPORAL_TASK_QUEUE", "prod-queue")
        monkeypatch.setenv("SUPABASE_URL", "https://prod.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "prod-key-123")

        settings = Settings()
        assert settings.temporal_address == "localhost:7233"
        assert settings.temporal_namespace == "production"
        assert settings.temporal_task_queue == "prod-queue"
        assert settings.supabase_url == "https://prod.supabase.co"
        assert settings.supabase_service_role_key == "prod-key-123"

    def test_case_insensitive_env_vars(self, monkeypatch):
        """Test that environment variables are case insensitive."""
        monkeypatch.setenv("temporal_address", "test:7233")
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "test-ns")

        settings = Settings()
        assert settings.temporal_address == "test:7233"
        assert settings.temporal_namespace == "test-ns"

    def test_temporal_address_validation(self, monkeypatch):
        """Test temporal address setting."""
        monkeypatch.setenv("TEMPORAL_ADDRESS", "custom-host:9999")
        settings = Settings()
        assert settings.temporal_address == "custom-host:9999"

    def test_temporal_namespace_validation(self, monkeypatch):
        """Test temporal namespace setting."""
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "custom-namespace")
        settings = Settings()
        assert settings.temporal_namespace == "custom-namespace"

    def test_temporal_task_queue_validation(self, monkeypatch):
        """Test temporal task queue setting."""
        monkeypatch.setenv("TEMPORAL_TASK_QUEUE", "custom-queue")
        settings = Settings()
        assert settings.temporal_task_queue == "custom-queue"

    def test_supabase_url_http(self, monkeypatch):
        """Test supabase URL with http."""
        monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
        settings = Settings()
        assert settings.supabase_url == "http://localhost:54321"

    def test_supabase_url_https(self, monkeypatch):
        """Test supabase URL with https."""
        monkeypatch.setenv("SUPABASE_URL", "https://secure.supabase.co")
        settings = Settings()
        assert settings.supabase_url == "https://secure.supabase.co"

    def test_supabase_service_role_key(self, monkeypatch):
        """Test supabase service role key."""
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "super-secret-key")
        settings = Settings()
        assert settings.supabase_service_role_key == "super-secret-key"

    def test_empty_env_vars_use_defaults(self, monkeypatch):
        """Test that empty environment variables fall back to defaults."""
        monkeypatch.delenv("TEMPORAL_ADDRESS", raising=False)
        monkeypatch.delenv("TEMPORAL_NAMESPACE", raising=False)
        monkeypatch.delenv("TEMPORAL_TASK_QUEUE", raising=False)

        settings = Settings()
        assert settings.temporal_address == "temporal:7233"
        assert settings.temporal_namespace == "default"
        assert settings.temporal_task_queue == "main"

    def test_partial_env_override(self, monkeypatch):
        """Test overriding only some environment variables."""
        monkeypatch.setenv("TEMPORAL_ADDRESS", "custom:7233")
        # Leave others as defaults

        settings = Settings()
        assert settings.temporal_address == "custom:7233"
        assert settings.temporal_namespace == "default"
        assert settings.temporal_task_queue == "main"

    def test_settings_are_immutable_after_creation(self, monkeypatch):
        """Test that settings values are fixed at creation."""
        monkeypatch.setenv("TEMPORAL_ADDRESS", "initial:7233")
        settings = Settings()
        assert settings.temporal_address == "initial:7233"

        # Changing env var after creation shouldn't affect existing instance
        monkeypatch.setenv("TEMPORAL_ADDRESS", "changed:7233")
        assert settings.temporal_address == "initial:7233"

    def test_docker_compose_defaults(self):
        """Test defaults are suitable for docker-compose."""
        settings = Settings()
        # Default temporal address should work in docker-compose
        assert "temporal" in settings.temporal_address
        # Default supabase URL should work with docker host
        assert "host.docker.internal" in settings.supabase_url or "localhost" in settings.supabase_url

    def test_production_like_config(self, monkeypatch):
        """Test production-like configuration."""
        monkeypatch.setenv("TEMPORAL_ADDRESS", "temporal.production.com:7233")
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "production")
        monkeypatch.setenv("TEMPORAL_TASK_QUEUE", "production-queue")
        monkeypatch.setenv("SUPABASE_URL", "https://production.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "production-secret-key")

        settings = Settings()
        assert settings.temporal_address == "temporal.production.com:7233"
        assert settings.temporal_namespace == "production"
        assert settings.temporal_task_queue == "production-queue"
        assert settings.supabase_url == "https://production.supabase.co"
        assert settings.supabase_service_role_key == "production-secret-key"

    def test_localhost_config(self, monkeypatch):
        """Test localhost development configuration."""
        monkeypatch.setenv("TEMPORAL_ADDRESS", "localhost:7233")
        monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")

        settings = Settings()
        assert settings.temporal_address == "localhost:7233"
        assert settings.supabase_url == "http://localhost:54321"

    def test_settings_field_types(self):
        """Test that settings fields are correct types."""
        settings = Settings()
        assert isinstance(settings.temporal_address, str)
        assert isinstance(settings.temporal_namespace, str)
        assert isinstance(settings.temporal_task_queue, str)
        assert isinstance(settings.supabase_url, str)
        assert isinstance(settings.supabase_service_role_key, str)

    def test_settings_not_empty(self):
        """Test that default settings are not empty strings."""
        settings = Settings()
        assert len(settings.temporal_address) > 0
        assert len(settings.temporal_namespace) > 0
        assert len(settings.temporal_task_queue) > 0
        assert len(settings.supabase_url) > 0
        assert len(settings.supabase_service_role_key) > 0

    def test_multiple_settings_instances_independent(self, monkeypatch):
        """Test that multiple Settings instances can have different values."""
        monkeypatch.setenv("TEMPORAL_ADDRESS", "first:7233")
        settings1 = Settings()

        monkeypatch.setenv("TEMPORAL_ADDRESS", "second:7233")
        settings2 = Settings()

        # First instance should keep its original value
        assert settings1.temporal_address == "first:7233"
        # Second instance should have new value
        assert settings2.temporal_address == "second:7233"
