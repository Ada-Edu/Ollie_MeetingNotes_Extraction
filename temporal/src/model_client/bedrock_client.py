"""AWS Bedrock client implementation."""

import os
import json
import logging
from typing import List
import boto3
from .base import BaseModelClient, ActionItem, ModelAPIError, InvalidResponseError
from .prompts import build_extraction_prompt

logger = logging.getLogger(__name__)


class BedrockModelClient(BaseModelClient):
    """AWS Bedrock implementation of model client."""

    def __init__(self):
        """Initialize AWS Bedrock client."""
        region = os.getenv("AWS_REGION", "us-east-1")
        api_key = os.getenv("AWS_BEARER_TOKEN_BEDROCK") or os.getenv("BEDROCK_API_KEY")

        # Check if using API key authentication
        if api_key:
            # Bedrock API key authentication
            # API key format suggests this might be for a proxy/adapter service
            logger.info("Using Bedrock API key authentication")

            # Parse the API key to extract credentials if needed
            # The key format suggests it might contain embedded credentials
            import base64
            try:
                decoded = base64.b64decode(api_key).decode('utf-8')
                # Expected format might be: "BedrockAPIKey-{id}-at-{timestamp}:{actual_key}"
                if ':' in decoded:
                    parts = decoded.split(':', 1)
                    # Use as custom authentication
                    logger.info(f"Decoded API key format: {parts[0][:30]}...")
            except Exception as e:
                logger.warning(f"Could not decode API key: {e}, using as-is")

            # For now, store the API key for custom requests
            self.api_key = api_key
            self.use_api_key = True
            self.client = None  # Will use custom HTTP client if needed
        else:
            # Standard AWS IAM authentication
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

            if aws_access_key and aws_secret_key:
                self.client = boto3.client(
                    "bedrock-runtime",
                    region_name=region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
            else:
                # Use default credentials chain
                self.client = boto3.client(
                    "bedrock-runtime",
                    region_name=region
                )

            self.use_api_key = False

        self.region = region
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
        logger.info(f"Initialized Bedrock client with model: {self.model_id}, region: {region}")

    async def extract_action_items(self, notes: str) -> List[ActionItem]:
        """Extract action items using AWS Bedrock.

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

            logger.info(f"Calling AWS Bedrock API (model: {self.model_id})")

            # Use API key authentication if available
            if self.use_api_key:
                import httpx

                # Construct Bedrock endpoint
                endpoint = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{self.model_id}/invoke"

                # Format request based on model
                if "anthropic" in self.model_id.lower():
                    # Anthropic Claude format for Bedrock
                    request_body = {
                        "anthropic_version": "bedrock-2023-05-31",
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.3
                    }
                else:
                    # Generic format
                    request_body = {
                        "inputText": prompt,
                        "textGenerationConfig": {
                            "maxTokenCount": 2000,
                            "temperature": 0.3
                        }
                    }

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        endpoint,
                        json=request_body,
                        headers=headers,
                        timeout=30.0
                    )

                    if response.status_code != 200:
                        raise ModelAPIError(f"Bedrock API returned {response.status_code}: {response.text}")

                    response_body = response.json()

            else:
                # Standard boto3 SDK approach
                # Format request based on model
                if "anthropic" in self.model_id.lower():
                    # Anthropic Claude format
                    request_body = json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.3
                    })
                else:
                    # Generic format
                    request_body = json.dumps({
                        "inputText": prompt,
                        "textGenerationConfig": {
                            "maxTokenCount": 2000,
                            "temperature": 0.3
                        }
                    })

                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=request_body
                )

                response_body = json.loads(response["body"].read())

            # Extract text based on model and response format
            if "anthropic" in self.model_id.lower():
                # Check for new Messages API format first
                if "content" in response_body:
                    # New format: {"content": [{"type": "text", "text": "..."}]}
                    content_blocks = response_body.get("content", [])
                    if content_blocks and len(content_blocks) > 0:
                        content = content_blocks[0].get("text", "")
                    else:
                        content = ""
                else:
                    # Old format: {"completion": "..."}
                    content = response_body.get("completion", "")
            else:
                content = response_body.get("results", [{}])[0].get("outputText", "")

            logger.info(f"Received response from Bedrock (length: {len(content)})")

            # Parse JSON from response
            try:
                # Try to extract JSON from response
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start == -1 or json_end == 0:
                    raise InvalidResponseError("No JSON found in model response")

                json_str = content[json_start:json_end]
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from model: {content[:200]}")
                raise InvalidResponseError(f"Model returned invalid JSON: {str(e)}")

            # Validate structure
            if "action_items" not in data:
                logger.error(f"Missing 'action_items' key in response")
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
            logger.error(f"Bedrock API error: {str(e)}")
            raise ModelAPIError(f"Bedrock API call failed: {str(e)}")

    def get_model_name(self) -> str:
        """Return the Bedrock model ID."""
        return self.model_id

    def get_provider_name(self) -> str:
        """Return provider name."""
        return "bedrock"
