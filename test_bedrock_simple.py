"""Simplified Bedrock test without full temporal dependencies."""

import asyncio
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_bedrock_api():
    """Test direct Bedrock API call."""

    print("=" * 60)
    print("Testing AWS Bedrock API Connection")
    print("=" * 60)

    # Configuration
    region = os.getenv("AWS_REGION", "af-south-1")
    api_key = os.getenv("BEDROCK_API_KEY")
    model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")

    print(f"\n[OK] AWS_REGION: {region}")
    print(f"[OK] BEDROCK_MODEL_ID: {model_id}")
    if api_key:
        print(f"[OK] BEDROCK_API_KEY: {api_key[:30]}...")
    else:
        print("[ERROR] BEDROCK_API_KEY not found!")
        return

    # Test prompt
    test_prompt = """Extract action items from these meeting notes and return ONLY valid JSON in this exact format:

{
  "action_items": [
    {
      "description": "task description",
      "owner": "person name or null",
      "due_date": "YYYY-MM-DD or null",
      "confidence": 0.95
    }
  ]
}

IMPORTANT: Do NOT hallucinate or guess. If owner is unclear, use null. If due date is unclear, use null.

Meeting notes:
---
Team meeting - July 7, 2026
Attendees: Sarah, John, Mike

Discussion:
- Q4 budget review coming up
- Need to finalize architectural design

Action items:
1. John to follow up with Sarah on Q4 budget by July 15
2. Mike to review the architectural design doc by next week
3. Schedule a follow-up meeting for next Monday
---

Return ONLY the JSON, no other text."""

    # Construct endpoint
    endpoint = f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke"

    print(f"\n[OK] Endpoint: {endpoint}")
    print("\n" + "-" * 60)
    print("Calling Bedrock API...")
    print("-" * 60)

    # Request body for Anthropic Claude on Bedrock
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {
                "role": "user",
                "content": test_prompt
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.3
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"Sending POST request...")
            print(f"Request body: {json.dumps(request_body, indent=2)[:200]}...")

            response = await client.post(
                endpoint,
                json=request_body,
                headers=headers
            )

            print(f"\n✓ Response Status: {response.status_code}")
            print(f"✓ Response Headers: {dict(response.headers)}")

            if response.status_code != 200:
                print(f"\n❌ API Error ({response.status_code}):")
                print(response.text)
                return

            response_data = response.json()
            print(f"\n✓ Response Body:")
            print(json.dumps(response_data, indent=2))

            # Extract content
            if "content" in response_data:
                content_blocks = response_data.get("content", [])
                if content_blocks and len(content_blocks) > 0:
                    content = content_blocks[0].get("text", "")
                    print(f"\n✓ Extracted Text:")
                    print(content)

                    # Try to parse JSON
                    try:
                        json_start = content.find("{")
                        json_end = content.rfind("}") + 1
                        if json_start != -1 and json_end > 0:
                            json_str = content[json_start:json_end]
                            data = json.loads(json_str)

                            print(f"\n✓ Parsed JSON:")
                            print(json.dumps(data, indent=2))

                            action_items = data.get("action_items", [])
                            print(f"\n✅ SUCCESS! Extracted {len(action_items)} action items:")
                            print("=" * 60)

                            for i, item in enumerate(action_items, 1):
                                print(f"\n{i}. {item.get('description')}")
                                print(f"   Owner: {item.get('owner') or 'Unassigned'}")
                                print(f"   Due Date: {item.get('due_date') or 'No due date'}")
                                confidence = item.get('confidence')
                                if confidence:
                                    print(f"   Confidence: {confidence:.0%}")
                        else:
                            print("❌ No JSON found in response")
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON parsing error: {e}")
            else:
                print("❌ Unexpected response format")

            print("\n" + "=" * 60)
            print("✅ Bedrock API test completed!")
            print("=" * 60)

    except httpx.TimeoutException:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_bedrock_api())
