"""Base model client interface for action item extraction."""

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


class ModelAPIError(Exception):
    """Raised when model API call fails."""
    pass


class InvalidResponseError(Exception):
    """Raised when model returns invalid response."""
    pass


@dataclass
class ActionItem:
    """Represents an extracted action item."""
    description: str
    owner: Optional[str] = None
    due_date: Optional[str] = None  # ISO date format YYYY-MM-DD
    confidence: Optional[float] = None  # 0.0 to 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "description": self.description,
            "owner": self.owner,
            "due_date": self.due_date,
            "confidence": self.confidence
        }


class BaseModelClient(ABC):
    """Abstract base class for AI model clients."""

    @abstractmethod
    async def extract_action_items(self, notes: str) -> List[ActionItem]:
        """Extract action items from meeting notes.

        Args:
            notes: Raw meeting notes text

        Returns:
            List of ActionItem objects

        Raises:
            ModelAPIError: If API call fails
            InvalidResponseError: If response doesn't match expected schema
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name/identifier."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name (azure, bedrock, etc)."""
        pass
