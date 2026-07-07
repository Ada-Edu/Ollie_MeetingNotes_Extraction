# Test Meeting Notes Data

Copy and paste these examples into http://localhost:3000/meeting-notes to test different scenarios!

---

## Example 1: Complete Data (All Fields Present)

**Best Case**: Has owners, dates, and clear action items

```
Sprint Planning Meeting - July 7, 2026
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
5. John to fix critical bug in login flow by end of day July 8
```

**Expected**: 5 action items, all with owners and specific dates

---

## Example 2: Missing Owners (Shows "Unassigned")

**Tests**: System doesn't hallucinate owners when unclear

```
Product Roadmap Meeting - July 7, 2026

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
5. Prepare budget proposal for Q3 initiatives
```

**Expected**: 5 action items, all showing "Unassigned" (no hallucination!)

---

## Example 3: Vague Dates (Shows "No due date")

**Tests**: System doesn't guess dates when unclear

```
Team Sync - July 7, 2026
Attendees: John, Sarah, Mike

Quick check-in on project status.

Action Items:
1. John to follow up with the design team soon
2. Sarah to review the documentation when she has time
3. Mike to update the API specs eventually
4. Someone needs to fix the broken test suite ASAP
5. Look into the performance issues at some point
```

**Expected**: Mixed - some owners, but dates show "No due date" (not guessed!)

---

## Example 4: Client Meeting Notes

**Realistic**: Business meeting with external client

```
Client Kickoff Meeting - Acme Corp
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
6. Bob to provide access to staging environment by July 9
```

**Expected**: 6 action items with clear owners and dates

---

## Example 5: Engineering Standup

**Daily**: Short standup format

```
Daily Standup - Engineering Team
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
- Action: File ticket for test environment performance issue
```

**Expected**: 4 action items with owners and rough timeframes

---

## Example 6: No Action Items

**Edge Case**: Meeting with discussion but no tasks

```
Team Retrospective - Sprint 23
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

No specific action items identified - will continue current processes.
```

**Expected**: "No action items found" or empty list

---

## Example 7: Mixed Quality Data

**Real World**: Messy notes with various formats

```
quick notes from leadership mtg - july 7

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

random: pizza party on friday
```

**Expected**: Mixed results - some owners clear, some not; dates vague

---

## Example 8: Technical Planning

**Complex**: Architecture and technical decisions

```
Architecture Review Meeting - Microservices Migration
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
7. Team to conduct risk assessment workshop on July 21
```

**Expected**: 7 action items with clear owners and dates

---

## Example 9: Sales/Business Meeting

**Business Context**: Non-technical meeting

```
Q3 Business Review - Sales & Marketing
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
6. Bob to approve European expansion budget by July 15
```

**Expected**: 6 action items with business context

---

## Example 10: Crisis/Incident Response

**Urgent**: Production incident post-mortem

```
INCIDENT POST-MORTEM - Payment Service Outage
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
8. John to conduct knowledge transfer session on payment architecture by July 12
```

**Expected**: 8 urgent action items with tight deadlines

---

## Example 11: Very Short Meeting

**Minimal**: Quick decision meeting

```
Quick Sync - Feature Flag Decision
July 7, 2026

Decision: Use feature flags for gradual rollout of new search.

Actions:
1. John implements feature flag by tomorrow
2. Sarah tests in staging
3. Mike monitors metrics after launch
```

**Expected**: 3 action items, mix of clarity on dates

---

## Example 12: Long Rambling Notes

**Stress Test**: Large volume of text with scattered action items

```
Executive Leadership Meeting - Strategic Planning Session
Date: July 7, 2026, 9:00 AM - 12:00 PM
Location: Conference Room A

Attendees: Bob (CEO), Alice (CTO), Tom (Sales VP), Emma (Marketing VP), 
Lisa (CFO), Mike (Product VP), 15 other team leads

Opening Remarks by Bob:
Bob opened the meeting discussing the company's vision for the next 5 years.
He emphasized the importance of innovation, customer focus, and team collaboration.
He mentioned that our competitors are moving fast and we need to stay ahead.
Revenue growth has been strong but we need to maintain momentum.

Financial Review by Lisa:
Lisa presented Q2 financial results. Revenue was $5.2M, up 23% YoY.
Operating expenses were $3.8M, within budget. Cash runway is 18 months.
Discussed fundraising options for Series B. Several VCs have expressed interest.
Need to decide on valuation and timing. Board wants updates monthly.

Product Strategy by Mike:
Mike walked through the product roadmap for Q3 and Q4. Focus areas include:
- Mobile app improvements (loading speed, offline mode, better UX)
- Enterprise features (SSO, advanced permissions, audit logs)
- API v3 with better documentation
- Integration marketplace with 50+ partners

There was extensive discussion about whether to build or buy certain features.
Team debated the merits of different approaches for about 30 minutes.
Ultimately decided to build in-house to maintain quality and control.

Sales & Marketing by Tom and Emma:
Tom presented sales pipeline: $8M in opportunities, 60 deals in progress.
Average deal size increasing from $50K to $75K. Sales cycle shortening.
Emma showed marketing metrics: 50K monthly website visitors, 2,000 leads.
Content marketing performing well. Paid ads need optimization.

Technical Infrastructure by Alice:
Alice discussed scaling challenges. Current architecture handling load well
but projections show we'll need to upgrade within 6 months. Proposed moving
to Kubernetes and implementing microservices. Team has concerns about complexity.
Security audit revealed some vulnerabilities that need addressing.

Team Culture Discussion:
Several people raised concerns about work-life balance. Team is growing fast
and processes haven't kept up. Need better onboarding for new hires.
Remote work policy needs clarification. Office space getting cramped.

Random side conversations about lunch options, coffee machine broken,
parking lot full, someone's birthday next week, fantasy football league.

ACTION ITEMS (scattered throughout discussion):

Mike to finalize Q3 product roadmap and share with leadership by July 14.

Lisa needs to prepare Series B fundraising materials by July 20.

Tom to close the Acme Corp deal worth $200K by July 15.

Alice to get quotes for Kubernetes migration from 3 vendors by July 18.

Emma should launch new content marketing campaign by July 25.

Someone mentioned John should fix the login bug (not clear who said this or when).

Mike to schedule product strategy workshop sometime next month.

Lisa to update financial projections for the board meeting by July 12.

Alice to complete security audit remediation by July 30.

Tom to hire 2 enterprise sales reps by August 1.

Emma to redesign the website homepage (no date mentioned).

Bob wants a follow-up meeting in 2 weeks to review progress.

Need to schedule all-hands meeting (who and when unclear).

Closing remarks discussed team dinner, upcoming company retreat,
and appreciation for everyone's hard work.

Meeting adjourned at 12:15 PM (ran over by 15 minutes).
```

**Expected**: ~10-12 action items extracted from the rambling text, mixed quality on owners/dates

---

## How to Use These Examples

### Test Different Scenarios:

1. **Example 1** - Perfect data (everything works)
2. **Example 2** - Missing owners (tests no hallucination)
3. **Example 3** - Vague dates (tests date handling)
4. **Example 6** - No action items (tests empty state)
5. **Example 10** - Urgent items (tests priority understanding)
6. **Example 12** - Long notes (tests extraction from noise)

### Expected Behavior:

✅ **Good AI**: 
- Extracts only actual action items
- Shows "Unassigned" when owner unclear
- Shows "No due date" when date vague
- Handles messy/informal notes

❌ **Bad AI** (we avoided this!):
- Hallucinates owners ("John" when never mentioned)
- Guesses dates ("July 10" when notes say "soon")
- Extracts non-action items as tasks

---

## Quick Copy-Paste Test

**30-Second Test** - Copy this and paste in the UI:

```
Team meeting July 7 2026
John to fix the login bug by Friday
Sarah to review the code when she can
Schedule a meeting with the design team
```

**Expected**:
1. John, Friday date ✅
2. Sarah, no date ✅  
3. Unassigned, no date ✅

---

## Pro Tips

- Start with **Example 1** (works perfectly)
- Try **Example 2** to see "Unassigned" in action
- Test **Example 3** to see "No due date"
- End with **Example 12** to see it handle messy data

**Have fun testing!** 🎉
