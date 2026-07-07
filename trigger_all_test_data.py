"""
Trigger extraction workflows for all test data in the database.

This script finds all meeting notes without extraction runs and
triggers workflows for them via the API.
"""

import os
import asyncio
import aiohttp
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
supabase_url = os.getenv("VITE_SUPABASE_URL", "http://localhost:54321")
supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY")
api_url = "http://localhost:8000"

if not supabase_key:
    print("ERROR: VITE_SUPABASE_ANON_KEY not found in .env")
    exit(1)

supabase = create_client(supabase_url, supabase_key)


async def trigger_extraction(session, meeting_note):
    """Trigger extraction workflow for a single meeting note."""

    meeting_id = meeting_note["id"]
    notes_text = meeting_note["notes_text"]

    print(f"\n[{meeting_id}] Triggering extraction...")
    print(f"  Length: {len(notes_text)} chars")

    # Create extraction_run record
    try:
        extraction_result = supabase.table("extraction_runs").insert({
            "meeting_notes_id": meeting_id,
            "workflow_id": f"extract-{meeting_id}",
            "status": "processing"
        }).execute()

        if not extraction_result.data:
            print(f"  ✗ Failed to create extraction_run record")
            return False

        extraction_run_id = extraction_result.data[0]["id"]
        print(f"  ✓ Created extraction_run: {extraction_run_id}")

    except Exception as e:
        print(f"  ✗ Database error: {str(e)}")
        return False

    # Trigger workflow via API
    try:
        payload = {
            "workflow_name": "ExtractMeetingActionItemsWorkflow",
            "workflow_id": f"extract-{meeting_id}",
            "args": {
                "meeting_notes_id": meeting_id,
                "notes_text": notes_text
            },
            "task_queue": "main"
        }

        async with session.post(
            f"{api_url}/trigger-workflow",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"  ✓ Workflow triggered: {result.get('workflow_id')}")
                return True
            else:
                error_text = await response.text()
                print(f"  ✗ API error ({response.status}): {error_text[:100]}")

                # Update extraction_run to failed
                supabase.table("extraction_runs").update({
                    "status": "failed",
                    "error_message": f"API error: {error_text[:200]}"
                }).eq("id", extraction_run_id).execute()

                return False

    except asyncio.TimeoutError:
        print(f"  ✗ Timeout connecting to API")
        supabase.table("extraction_runs").update({
            "status": "failed",
            "error_message": "Timeout connecting to workflow API"
        }).eq("id", extraction_run_id).execute()
        return False

    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        supabase.table("extraction_runs").update({
            "status": "failed",
            "error_message": str(e)
        }).eq("id", extraction_run_id).execute()
        return False


async def main():
    """Find all meeting notes and trigger extractions."""

    print("=" * 60)
    print("Triggering Extraction for All Test Data")
    print("=" * 60)

    # Get all meeting notes
    try:
        result = supabase.table("meeting_notes") \
            .select("id, notes_text") \
            .order("created_at", desc=True) \
            .execute()

        meeting_notes = result.data
        print(f"\n✓ Found {len(meeting_notes)} meeting notes in database")

    except Exception as e:
        print(f"✗ Error fetching meeting notes: {e}")
        return

    if not meeting_notes:
        print("\nNo meeting notes found. Run load_test_data.py first.")
        return

    # Filter out those that already have extraction runs
    notes_without_extraction = []

    for note in meeting_notes:
        existing = supabase.table("extraction_runs") \
            .select("id") \
            .eq("meeting_notes_id", note["id"]) \
            .execute()

        if not existing.data:
            notes_without_extraction.append(note)

    print(f"✓ Found {len(notes_without_extraction)} notes without extraction")

    if not notes_without_extraction:
        print("\nAll meeting notes already have extraction runs.")
        print("Check Supabase Studio to see results: http://localhost:54323")
        return

    # Trigger extractions
    print(f"\nTriggering {len(notes_without_extraction)} extractions...")
    print("This may take a few minutes...")

    success_count = 0
    failed_count = 0

    async with aiohttp.ClientSession() as session:
        for note in notes_without_extraction:
            success = await trigger_extraction(session, note)
            if success:
                success_count += 1
            else:
                failed_count += 1

            # Add small delay between requests
            await asyncio.sleep(1)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✓ Successfully triggered: {success_count}")
    print(f"✗ Failed: {failed_count}")
    print(f"Total: {len(notes_without_extraction)}")

    if success_count > 0:
        print("\n⏳ Workflows are processing...")
        print("   Each extraction takes 5-10 seconds")
        print(f"   Total time: ~{len(notes_without_extraction) * 7} seconds")
        print("\nMonitor progress:")
        print("  • Temporal UI: http://localhost:8080")
        print("  • Supabase: http://localhost:54323")
        print("  • Frontend: http://localhost:3000/meeting-notes")


if __name__ == "__main__":
    asyncio.run(main())
