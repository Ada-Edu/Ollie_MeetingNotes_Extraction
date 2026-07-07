"""Test multiple model IDs to find which ones work."""

import asyncio
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()


# List of model IDs to try
MODEL_IDS_TO_TEST = [
    # Claude 3.5 variants
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "claude-3-5-sonnet",

    # Claude 3 variants
    "anthropic.claude-3-opus-20240229-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "claude-3-opus",
    "claude-3-sonnet",
    "claude-3-haiku",

    # Claude 2 variants
    "anthropic.claude-v2:1",
    "anthropic.claude-v2",
    "claude-v2",
    "claude-v2:1",

    # Simple formats
    "claude-3.5-sonnet",
    "claude-3-sonnet",
    "claude-2",
]


async def test_model_id(model_id: str, region: str, api_key: str) -> dict:
    """Test a single model ID."""

    endpoint = f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke"

    # Simple test prompt
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {
                "role": "user",
                "content": "Say 'Hello' in JSON format: {\"message\": \"Hello\"}"
            }
        ],
        "max_tokens": 100,
        "temperature": 0.1
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                endpoint,
                json=request_body,
                headers=headers
            )

            return {
                "model_id": model_id,
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.text[:200] if response.status_code != 200 else "SUCCESS",
                "error_type": response.headers.get("x-amzn-errortype", "N/A")
            }

    except httpx.TimeoutException:
        return {
            "model_id": model_id,
            "status_code": 0,
            "success": False,
            "response": "TIMEOUT",
            "error_type": "Timeout"
        }
    except Exception as e:
        return {
            "model_id": model_id,
            "status_code": 0,
            "success": False,
            "response": str(e)[:200],
            "error_type": "Exception"
        }


async def main():
    """Test all model IDs."""

    print("=" * 70)
    print("TESTING ALL MODEL IDs")
    print("=" * 70)

    region = os.getenv("AWS_REGION", "af-south-1")
    api_key = os.getenv("BEDROCK_API_KEY")

    if not api_key:
        print("[ERROR] BEDROCK_API_KEY not found in .env")
        return

    print(f"\n[OK] Region: {region}")
    print(f"[OK] API Key: {api_key[:30]}...")
    print(f"[OK] Testing {len(MODEL_IDS_TO_TEST)} model IDs...")
    print("\n" + "-" * 70)

    results = []

    for i, model_id in enumerate(MODEL_IDS_TO_TEST, 1):
        print(f"\n[{i}/{len(MODEL_IDS_TO_TEST)}] Testing: {model_id}")
        result = await test_model_id(model_id, region, api_key)
        results.append(result)

        if result["success"]:
            print(f"  [SUCCESS] Status: {result['status_code']}")
            print(f"  [SUCCESS] THIS MODEL WORKS!")
        else:
            status = result['status_code']
            error_type = result['error_type']
            print(f"  [FAIL] Status: {status} | Error: {error_type}")
            if status == 400:
                print(f"  [FAIL] Response: {result['response']}")

        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    if successful:
        print(f"\n[SUCCESS] Working models ({len(successful)}):")
        for r in successful:
            print(f"  - {r['model_id']}")
        print("\n[ACTION] Update your .env with one of these:")
        print(f"  BEDROCK_MODEL_ID={successful[0]['model_id']}")
    else:
        print(f"\n[FAIL] No working models found ({len(failed)} failed)")
        print("\nCommon errors:")
        error_types = {}
        for r in failed:
            et = r['error_type']
            error_types[et] = error_types.get(et, 0) + 1

        for error_type, count in error_types.items():
            print(f"  - {error_type}: {count} times")

        print("\n[NEXT STEPS]:")
        print("  1. Check HOW_TO_FIND_BEDROCK_INFO.md")
        print("  2. Verify the endpoint URL is correct")
        print("  3. Check if this is a custom Bedrock proxy")
        print("  4. Contact your platform team for documentation")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
