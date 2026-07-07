"""Factory for creating model clients based on configuration."""

import os
import logging
from .base import BaseModelClient
from .azure_client import AzureModelClient
from .bedrock_client import BedrockModelClient

logger = logging.getLogger(__name__)


def get_model_client() -> BaseModelClient:
    """Get the appropriate model client based on MODEL_PROVIDER env var.

    Returns:
        BaseModelClient instance

    Raises:
        ValueError: If MODEL_PROVIDER is not set or invalid
    """
    provider = os.getenv("MODEL_PROVIDER", "").lower()

    if not provider:
        raise ValueError(
            "MODEL_PROVIDER environment variable not set. "
            "Must be 'azure' or 'bedrock'. "
            "Please configure your model provider."
        )

    logger.info(f"Initializing model client for provider: {provider}")

    if provider == "azure":
        return AzureModelClient()
    elif provider == "bedrock":
        return BedrockModelClient()
    else:
        raise ValueError(
            f"Invalid MODEL_PROVIDER: '{provider}'. "
            f"Must be 'azure' or 'bedrock'. "
            f"Current value: {provider}"
        )


def get_model_info() -> dict:
    """Get current model provider information.

    Returns:
        Dict with provider and model name
    """
    try:
        client = get_model_client()
        return {
            "provider": client.get_provider_name(),
            "model_name": client.get_model_name()
        }
    except Exception as e:
        logger.error(f"Failed to get model info: {str(e)}")
        return {
            "provider": None,
            "model_name": None,
            "error": str(e)
        }
