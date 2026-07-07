"""
Load test meeting notes into the database.

This script extracts all examples from TEST_DATA.md and inserts them
into the meeting_notes table in Supabase.
"""

import os
import re
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client with service role key (has full permissions)
supabase_url = os.getenv("VITE_SUPABASE_URL", "http://localhost:54321")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_key:
    print("ERROR: SUPABASE_SERVICE_ROLE_KEY not found in .env")
    print("This script needs service role key to insert data.")
    exit(1)

supabase = create_client(supabase_url, supabase_key)

# Test examples to load
TEST_EXAMPLES = [
    {
        "title": "Example 1: Complete Data",
        "notes": """Sprint Planning Meeting - July 7, 2026
Attendees: Sarah (PM), John (Dev), Mike (Architect), Lisa (QA)

Sprint Goal: Complete user authentication and payment features

Discussion:
- Reviewed last sprint's velocity
- Prioritized user stories for this sprint
- Identified technical risks

Action Items:
1. John to implement OAuth integration by July 12
2. Sarah to schedule stakeholder demo for July 15 at 2pm
3. Mike to complete architecture review by July 10
4. Lisa to create test plan for payment flow by July 14
5. John to fix critical bug in login flow by end of day July 8"""
    },
    {
        "title": "Example 2: Missing Owners",
        "notes": """Product Roadmap Meeting - July 7, 2026

Discussed Q3 priorities and resource allocation.

Key Decisions:
- Focus on mobile experience
- Delay API v3 until Q4
- Prioritize performance improvements

Action Items:
1. Update the product roadmap document by next Friday
2. Review competitor analysis and share findings with the team
3. Schedule follow-up meeting with engineering team
4. Research customer feedback on mobile app
5. Prepare budget proposal for Q3 initiatives"""
    },
    {
        "title": "Example 3: Vague Dates",
        "notes": """Team Sync - July 7, 2026
Attendees: John, Sarah, Mike

Quick check-in on project status.

Action Items:
1. John to follow up with the design team soon
2. Sarah to review the documentation when she has time
3. Mike to update the API specs eventually
4. Someone needs to fix the broken test suite ASAP
5. Look into the performance issues at some point"""
    },
    {
        "title": "Example 4: Client Meeting",
        "notes": """Client Kickoff Meeting - Acme Corp
Date: July 7, 2026
Attendees: Sarah (Our PM), John (Tech Lead), Bob (Client CTO), Alice (Client PM)

Project: E-commerce Platform Redesign
Budget: $150K
Timeline: 12 weeks

Discussion Points:
- Client wants mobile-first design
- Integration with existing inventory system required
- Need weekly progress reports
- Security audit required before launch

Action Items:
1. Sarah to send project proposal and SOW to Bob by July 10
2. John to schedule technical discovery session with Alice by July 12
3. Our design team to create initial mockups by July 18
4. Sarah to set up weekly status meeting (every Monday at 10am)
5. John to review Acme's API documentation by July 14
6. Bob to provide access to staging environment by July 9"""
    },
    {
        "title": "Example 5: Engineering Standup",
        "notes": """Daily Standup - Engineering Team
Date: July 7, 2026 - 9:00 AM

Sarah:
- Yesterday: Finished user profile page
- Today: Working on settings page
- Blockers: None
- Action: Push settings page code by end of day

John:
- Yesterday: Debugging payment integration
- Today: Continue payment work
- Blockers: Waiting for API keys from finance
- Action: Follow up with finance team about API keys today

Mike:
- Yesterday: Architecture review
- Today: Database optimization
- Blockers: Need production metrics
- Action: Request production dashboard access by noon

Lisa:
- Yesterday: Wrote test cases
- Today: Running regression tests
- Blockers: Test environment is slow
- Action: File ticket for test environment performance issue"""
    },
    {
        "title": "Example 6: No Action Items",
        "notes": """Team Retrospective - Sprint 23
Date: July 7, 2026

What Went Well:
- Great collaboration between frontend and backend teams
- Deployment process was smooth
- Good code review quality

What Could Be Better:
- More time for testing next sprint
- Better communication with product team
- Documentation needs improvement

Insights:
- Team velocity is stable
- Technical debt is manageable
- Morale is good

No specific action items identified - will continue current processes."""
    },
    {
        "title": "Example 7: Mixed Quality",
        "notes": """quick notes from leadership mtg - july 7

discussed:
* Q3 okrs
* hiring plans
* budget stuff

things to do:
- someone needs to update the hiring doc (maybe sarah?)
- john mentioned he'll look at the budget thing by next week or so
- review slides before board meeting (not sure who)
- mike has to finish that report eventually
- schedule 1:1s with new team members (sarah + john)

other stuff:
revenue is up, team morale good, office space renewal coming up

random: pizza party on friday"""
    },
    {
        "title": "Example 8: Technical Planning",
        "notes": """Architecture Review Meeting - Microservices Migration
Date: July 7, 2026
Attendees: Mike (Architect), John (Backend Lead), Sarah (DevOps)

Current State:
- Monolithic application with 500K lines of code
- Performance bottlenecks in order processing
- Scaling issues during peak traffic

Proposed Solution:
- Break into 5 microservices (User, Order, Payment, Inventory, Notification)
- Use Kubernetes for orchestration
- Implement API gateway pattern

Technical Decisions Made:
1. Use gRPC for inter-service communication
2. PostgreSQL for transactional services
3. Redis for caching layer
4. Kafka for event streaming

Action Items:
1. Mike to create detailed migration plan by July 14
2. John to set up proof-of-concept for User service by July 20
3. Sarah to provision Kubernetes cluster in staging by July 12
4. Mike to document service boundaries and API contracts by July 18
5. John to evaluate gRPC libraries and create comparison doc by July 15
6. Sarah to set up monitoring stack (Prometheus + Grafana) by July 19
7. Team to conduct risk assessment workshop on July 21"""
    },
    {
        "title": "Example 9: Sales Meeting",
        "notes": """Q3 Business Review - Sales & Marketing
Date: July 7, 2026
Present: Tom (Sales Dir), Emma (Marketing), Lisa (Finance), Bob (CEO)

Q2 Results:
- Revenue: $2.3M (15% above target)
- New customers: 47
- Churn rate: 3.2%
- Marketing ROI: 340%

Q3 Targets:
- Revenue goal: $2.8M
- New customer target: 60
- Launch 2 new products
- Expand to European market

Strategic Initiatives:
1. Partner with industry influencers
2. Attend 3 major conferences
3. Launch referral program
4. Improve onboarding process

Action Items:
1. Tom to negotiate partnership agreements by July 31
2. Emma to book conference booth for TechCon by July 10
3. Lisa to finalize Q3 budget allocation by July 12
4. Emma to launch referral program campaign by July 25
5. Tom to hire 2 additional sales reps by August 1
6. Bob to approve European expansion budget by July 15"""
    },
    {
        "title": "Example 10: Crisis Response",
        "notes": """INCIDENT POST-MORTEM - Payment Service Outage
Date: July 7, 2026
Severity: P1 - Critical
Duration: 2 hours 15 minutes (3:00 AM - 5:15 AM)

Incident Summary:
Payment service crashed due to memory leak in new deployment.
Impact: $50K in lost transactions, 1,200 affected customers.

Root Cause:
- Database connection pool not properly configured
- Memory leak in payment processing logic
- Insufficient monitoring alerts

Immediate Actions Taken:
- Rolled back to previous version at 4:00 AM
- Manually processed queued transactions
- Notified affected customers

URGENT Action Items:
1. John to fix memory leak in payment service by end of day July 7
2. Sarah to implement database connection pooling properly by July 8
3. Mike to set up memory usage alerts in monitoring by July 8
4. Lisa to add integration tests for payment flow by July 9
5. Tom to send apology emails to affected customers by July 7 EOD
6. Sarah to schedule incident review with full team by July 8
7. Mike to document proper deployment checklist by July 10
8. John to conduct knowledge transfer session on payment architecture by July 12"""
    },
    {
        "title": "Example 11: Quick Decision",
        "notes": """Quick Sync - Feature Flag Decision
July 7, 2026

Decision: Use feature flags for gradual rollout of new search.

Actions:
1. John implements feature flag by tomorrow
2. Sarah tests in staging
3. Mike monitors metrics after launch"""
    },
    {
        "title": "Example 12: Executive Meeting",
        "notes": """Executive Leadership Meeting - Strategic Planning
Date: July 7, 2026
Attendees: Bob (CEO), Alice (CTO), Tom (VP Sales), Emma (VP Marketing)

Topics Discussed:
- Q2 financial results: Revenue $5.2M, up 23% YoY
- Product roadmap for Q3/Q4
- Scaling challenges and infrastructure needs
- Series B fundraising timeline
- Team growth and hiring plans

Key Decisions:
- Move to Kubernetes within 6 months
- Begin Series B fundraising process
- Hire 2 enterprise sales reps
- Launch new content marketing campaign

Action Items Identified:
1. Mike to finalize Q3 product roadmap by July 14
2. Lisa to prepare Series B fundraising materials by July 20
3. Tom to close the Acme Corp deal by July 15
4. Alice to get Kubernetes migration quotes by July 18
5. Emma to launch new content campaign by July 25
6. Lisa to update financial projections by July 12
7. Alice to complete security audit remediation by July 30
8. Tom to hire 2 enterprise sales reps by August 1"""
    }
]


def load_test_data():
    """Load all test examples into the database."""

    print("=" * 60)
    print("Loading Test Data into Database")
    print("=" * 60)

    loaded_count = 0

    for i, example in enumerate(TEST_EXAMPLES, 1):
        title = example["title"]
        notes = example["notes"]

        print(f"\n[{i}/{len(TEST_EXAMPLES)}] {title}")
        print(f"  Length: {len(notes)} characters")

        try:
            # Insert into meeting_notes table
            result = supabase.table("meeting_notes").insert({
                "notes_text": notes,
                "user_id": None  # No user for test data
            }).execute()

            if result.data:
                meeting_note_id = result.data[0]["id"]
                print(f"  [OK] Inserted: ID {meeting_note_id}")
                loaded_count += 1
            else:
                print(f"  [FAIL] Failed: No data returned")

        except Exception as e:
            print(f"  [ERROR] Error: {str(e)}")

    print("\n" + "=" * 60)
    print(f"[SUCCESS] Successfully loaded {loaded_count}/{len(TEST_EXAMPLES)} examples")
    print("=" * 60)

    print("\nYou can now:")
    print("  1. View them in Supabase Studio: http://localhost:54323")
    print("  2. Manually trigger extraction from the UI")
    print("  3. Or run trigger_all_test_data.py to extract all at once")


if __name__ == "__main__":
    load_test_data()
