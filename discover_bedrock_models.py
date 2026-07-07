"""Discover available Bedrock models and inference profiles."""

import asyncio
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()


async def list_models():
    """Try to list available models."""

    region = os.getenv("AWS_REGION", "af-south-1")
    api_key = os.getenv("AWS_BEARER_TOKEN_BEDROCK")

    print("=" * 70)
    print("DISCOVERING BEDROCK MODELS")
    print("=" * 70)
    print(f"\n[OK] Region: {region}")

    if not api_key:
        print("[ERROR] AWS_BEARER_TOKEN_BEDROCK not set")
        return

    # Try different API endpoints to discover models
    endpoints_to_try = [
        f"https://bedrock.{region}.amazonaws.com/foundation-models",
        f"https://bedrock-runtime.{region}.amazonaws.com/models",
        f"https://bedrock.{region}.amazonaws.com/models",
        f"https://bedrock.{region}.amazonaws.com/inference-profiles",
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint in endpoints_to_try:
            print(f"\n[TRYING] {endpoint}")
            try:
                response = await client.get(endpoint, headers=headers)
                print(f"  Status: {response.status_code}")

                if response.status_code == 200:
                    print(f"  [SUCCESS] Found models!")
                    data = response.json()
                    print(json.dumps(data, indent=2)[:2000])
                elif response.status_code == 404:
                    print(f"  [NOT FOUND] Endpoint doesn't exist")
                else:
                    print(f"  [ERROR] {response.text[:200]}")
            except Exception as e:
                print(f"  [ERROR] {str(e)[:100]}")

    print("\n" + "-" * 70)
    print("TRYING COMMON INFERENCE PROFILE FORMATS")
    print("-" * 70)

    # Common inference profile formats based on AWS docs
    model_formats = [
        # Cross-region profiles
        "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        "eu.anthropic.claude-3-5-sonnet-20240620-v1:0",

        # Region-specific profiles
        "af-south-1.anthropic.claude-3-5-sonnet-20240620-v1:0",
        "us-east-1.anthropic.claude-3-5-sonnet-20240620-v1:0",

        # Direct model IDs (older format)
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-v2:1",
    ]

    print(f"\nTesting {len(model_formats)} model ID formats...")

    test_payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 10
    }

    for model_id in model_formats:
        endpoint = f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke"

        try:
            response = await client.post(
                endpoint,
                json=test_payload,
                headers={**headers, "Content-Type": "application/json"},
                timeout=10.0
            )

            if response.status_code == 200:
                print(f"\n[SUCCESS] {model_id}")
                print(f"  ✓ This model works!")
                return model_id
            elif response.status_code == 400:
                error_msg = response.json().get("message", "")
                if "inference profile" in error_msg.lower():
                    print(f"\n[INFO] {model_id}")
                    print(f"  → Needs inference profile")
                elif "invalid" in error_msg.lower():
                    print(f"[SKIP] {model_id} - Not available")
            else:
                print(f"[ERROR] {model_id} - Status {response.status_code}")

        except httpx.TimeoutException:
            print(f"[TIMEOUT] {model_id}")
        except Exception as e:
            pass  # Silent fail for discovery

    print("\n" + "=" * 70)
    print("[RESULT] No working model found automatically")
    print("=" * 70)
    print("\n[NEXT STEPS]:")
    print("1. Check AWS Bedrock Console for available models in af-south-1")
    print("2. Contact your AWS admin for the correct model ID or inference profile")
    print("3. Try: aws bedrock list-foundation-models --region af-south-1")
    print("4. Or: aws bedrock list-inference-profiles --region af-south-1")


if __name__ == "__main__":
    asyncio.run(list_models())
