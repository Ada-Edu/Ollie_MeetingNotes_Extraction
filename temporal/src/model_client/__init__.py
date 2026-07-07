"""Model client abstraction for AI-powered action item extraction."""

from .base import BaseModelClient, ActionItem, ModelAPIError, InvalidResponseError
from .factory import get_model_client

__all__ = [
    "BaseModelClient",
    "ActionItem",
    "ModelAPIError",
    "InvalidResponseError",
    "get_model_client",
]
