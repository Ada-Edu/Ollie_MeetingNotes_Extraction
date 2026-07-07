"""Quick test to verify Bedrock connection."""

import asyncio
import os
import sys
from pathlib import Path

# Add temporal src to path
sys.path.insert(0, str(Path(__file__).parent / "temporal" / "src"))

from model_client.factory import get_model_client


async def test_bedrock():
    """Test Bedrock client initialization and simple call."""

    print("=" * 60)
    print("Testing AWS Bedrock Connection")
    print("=" * 60)

    # Load environment
    from dotenv import load_dotenv
    load_dotenv()

    provider = os.getenv("MODEL_PROVIDER")
    print(f"\n✓ MODEL_PROVIDER: {provider}")

    region = os.getenv("AWS_REGION")
    print(f"✓ AWS_REGION: {region}")

    api_key = os.getenv("BEDROCK_API_KEY")
    if api_key:
        print(f"✓ BEDROCK_API_KEY: {api_key[:20]}...")

    model_id = os.getenv("BEDROCK_MODEL_ID")
    print(f"✓ BEDROCK_MODEL_ID: {model_id}")

    print("\n" + "-" * 60)
    print("Initializing Model Client...")
    print("-" * 60)

    try:
        client = get_model_client()
        print(f"✓ Client created: {client.__class__.__name__}")
        print(f"✓ Provider: {client.get_provider_name()}")
        print(f"✓ Model: {client.get_model_name()}")

        print("\n" + "-" * 60)
        print("Testing Extraction...")
        print("-" * 60)

        test_notes = """
        Team meeting notes - July 7, 2026

        Attendees: Sarah, John, Mike

        Discussion points:
        - Q4 budget review is coming up
        - Need to finalize the architectural design

        Action items:
        1. John to follow up with Sarah on Q4 budget by July 15
        2. Mike to review the architectural design doc by next week
        3. Schedule a follow-up meeting for next Monday
        """

        print(f"Test notes: {len(test_notes)} characters")
        print("\nCalling model API...")

        action_items = await client.extract_action_items(test_notes)

        print(f"\n✓ SUCCESS! Extracted {len(action_items)} action items:")
        print("=" * 60)

        for i, item in enumerate(action_items, 1):
            print(f"\n{i}. {item.description}")
            print(f"   Owner: {item.owner or 'Unassigned'}")
            print(f"   Due Date: {item.due_date or 'No due date'}")
            if item.confidence:
                print(f"   Confidence: {item.confidence:.0%}")

        print("\n" + "=" * 60)
        print("✅ Bedrock connection test PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_bedrock())
