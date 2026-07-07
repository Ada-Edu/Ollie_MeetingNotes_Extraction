"""Azure OpenAI client implementation."""

import os
import json
import logging
from typing import List
from openai import AzureOpenAI
from .base import BaseModelClient, ActionItem, ModelAPIError, InvalidResponseError
from .prompts import build_extraction_prompt

logger = logging.getLogger(__name__)


class AzureModelClient(BaseModelClient):
    """Azure OpenAI implementation of model client."""

    def __init__(self):
        """Initialize Azure OpenAI client."""
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable not set")
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")

        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )

        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        logger.info(f"Initialized Azure OpenAI client with deployment: {self.deployment}")

    async def extract_action_items(self, notes: str) -> List[ActionItem]:
        """Extract action items using Azure OpenAI.

        Args:
            notes: Meeting notes text

        Returns:
            List of ActionItem objects

        Raises:
            ModelAPIError: If API call fails
            InvalidResponseError: If response is invalid
        """
        try:
            prompt = build_extraction_prompt(notes)

            logger.info(f"Calling Azure OpenAI API (deployment: {self.deployment})")

            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Low temperature for consistency
                max_tokens=2000,
                response_format={"type": "json_object"}  # Force JSON output
            )

            content = response.choices[0].message.content
            logger.info(f"Received response from Azure OpenAI (length: {len(content)})")

            # Parse JSON response
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from model: {content[:200]}")
                raise InvalidResponseError(f"Model returned invalid JSON: {str(e)}")

            # Validate structure
            if "action_items" not in data:
                logger.error(f"Missing 'action_items' key in response: {data}")
                raise InvalidResponseError("Model response missing 'action_items' array")

            if not isinstance(data["action_items"], list):
                raise InvalidResponseError("'action_items' must be an array")

            # Convert to ActionItem objects
            action_items = []
            for item in data["action_items"]:
                if not isinstance(item, dict):
                    logger.warning(f"Skipping non-dict item: {item}")
                    continue

                if "description" not in item:
                    logger.warning(f"Skipping item without description: {item}")
                    continue

                action_items.append(ActionItem(
                    description=item["description"],
                    owner=item.get("owner"),
                    due_date=item.get("due_date"),
                    confidence=item.get("confidence")
                ))

            logger.info(f"Extracted {len(action_items)} action items")
            return action_items

        except InvalidResponseError:
            raise
        except Exception as e:
            logger.error(f"Azure OpenAI API error: {str(e)}")
            raise ModelAPIError(f"Azure OpenAI API call failed: {str(e)}")

    def get_model_name(self) -> str:
        """Return the Azure deployment name."""
        return self.deployment

    def get_provider_name(self) -> str:
        """Return provider name."""
        return "azure"
