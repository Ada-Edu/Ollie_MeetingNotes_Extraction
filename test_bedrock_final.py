"""Final Bedrock connection test with correct credentials."""

import asyncio
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_bedrock():
    """Test Bedrock with correct model ID."""

    print("=" * 70)
    print("TESTING AWS BEDROCK CONNECTION")
    print("=" * 70)

    # Configuration
    region = os.getenv("AWS_REGION", "af-south-1")
    api_key = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-6")

    print(f"\n[OK] Region: {region}")
    print(f"[OK] Model ID: {model_id}")
    if api_key:
        print(f"[OK] Bearer Token: {api_key[:30]}...")
    else:
        print("[ERROR] AWS_BEARER_TOKEN_BEDROCK not found!")
        return

    # Construct endpoint
    endpoint = f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke"
    print(f"[OK] Endpoint: {endpoint}")

    # Test prompt - extract action items
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

IMPORTANT: Do NOT hallucinate. If owner is unclear, use null. If due date is unclear, use null.

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

    print("\n" + "-" * 70)
    print("CALLING BEDROCK API...")
    print("-" * 70)

    # Request body
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

            response = await client.post(
                endpoint,
                json=request_body,
                headers=headers
            )

            print(f"\n[OK] Response Status: {response.status_code}")

            if response.status_code != 200:
                print(f"[ERROR] API Error ({response.status_code}):")
                print(response.text)
                print(f"\n[ERROR] Headers: {dict(response.headers)}")
                return

            response_data = response.json()
            print(f"[OK] Response received!")

            # Extract content
            if "content" in response_data:
                content_blocks = response_data.get("content", [])
                if content_blocks and len(content_blocks) > 0:
                    content = content_blocks[0].get("text", "")
                    print(f"\n[OK] Model Response:")
                    print("-" * 70)
                    print(content)
                    print("-" * 70)

                    # Parse JSON
                    try:
                        json_start = content.find("{")
                        json_end = content.rfind("}") + 1
                        if json_start != -1 and json_end > 0:
                            json_str = content[json_start:json_end]
                            data = json.loads(json_str)

                            action_items = data.get("action_items", [])
                            print(f"\n[SUCCESS] Extracted {len(action_items)} action items:")
                            print("=" * 70)

                            for i, item in enumerate(action_items, 1):
                                print(f"\n{i}. {item.get('description')}")
                                print(f"   Owner: {item.get('owner') or 'Unassigned'}")
                                print(f"   Due Date: {item.get('due_date') or 'No due date'}")
                                confidence = item.get('confidence')
                                if confidence:
                                    print(f"   Confidence: {int(confidence * 100)}%")

                            print("\n" + "=" * 70)
                            print("[SUCCESS] BEDROCK CONNECTION TEST PASSED!")
                            print("=" * 70)
                            print("\n[NEXT STEP] Ready to run full workflow!")
                            print("  1. Start Docker containers: make up")
                            print("  2. Start Temporal worker: make worker")
                            print("  3. Start frontend: cd frontend && npm run dev")
                            print("  4. Open browser: http://localhost:5173")
                            return True

                        else:
                            print("[ERROR] No JSON found in response")
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] JSON parsing error: {e}")
                        print(f"Content: {content[:500]}")
            else:
                print("[ERROR] Unexpected response format")
                print(json.dumps(response_data, indent=2))

    except httpx.TimeoutException:
        print("[ERROR] Request timed out (60 seconds)")
    except Exception as e:
        print(f"[ERROR] Exception: {str(e)}")
        import traceback
        traceback.print_exc()

    return False


if __name__ == "__main__":
    success = asyncio.run(test_bedrock())
    if success:
        print("\n[OK] Configuration validated! Ready to proceed.")
    else:
        print("\n[ERROR] Test failed. Check configuration.")
