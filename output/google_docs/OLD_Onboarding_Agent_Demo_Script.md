---
title: "OLD: Onboarding Agent Demo Script"
id: 1JwvBZgQdNTLSu34FxMavzz4gTUJYpN68ofk3moWrvFE
modified_at: 2026-03-17T22:55:05.795Z
public_url: https://docs.google.com/document/d/1JwvBZgQdNTLSu34FxMavzz4gTUJYpN68ofk3moWrvFE/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->

# Onboarding Agent Demo Script
## Document Set Overview
The onboarding documents are spread across two systems: Google Drive (company-wide and sales docs managed by People Ops, Finance, and Sales Ops) and Confluence (engineering and stale legacy docs that were never migrated). The agent must search both sources to assemble a complete picture.
### Document Locations
<table><tr><td><b>Doc</b></td><td><b>Title</b></td><td><b>Location</b></td><td><b>Scope</b></td></tr><tr><td>1</td><td>General Onboarding Checklist</td><td>Google Drive</td><td>Company-wide, current (Feb 2026)</td></tr><tr><td>2</td><td>IT Systems & Access Guide</td><td>Google Drive</td><td>Company-wide, current (Jan 2026)</td></tr><tr><td>3</td><td>Office & Facilities Guide</td><td>Google Drive</td><td>Company-wide, current (Mar 2026)</td></tr><tr><td>4</td><td>Travel & Expense Policy</td><td>Google Drive</td><td>Company-wide, current (Mar 2026)</td></tr><tr><td>5</td><td>Engineering Team Onboarding</td><td>Confluence</td><td>Eng-specific, current (Feb 2026)</td></tr><tr><td>6</td><td>Engineering Security & Compliance</td><td>Confluence</td><td>Eng-specific, current (Jan 2026)</td></tr><tr><td>7</td><td>IT Setup Guide</td><td>Confluence</td><td><b>STALE (Jun 2024)</b> -- conflicts with Doc 2</td></tr><tr><td>8</td><td>Travel & Expense Policy</td><td>Confluence</td><td><b>STALE (Sep 2024)</b> -- conflicts with Doc 4</td></tr><tr><td>9</td><td>Slack Norms & Communication Guidelines</td><td>Google Drive</td><td>Company-wide, current (Jan 2026)</td></tr><tr><td>10</td><td>Benefits & Perks Overview</td><td>Google Drive</td><td>Company-wide, current (Feb 2026)</td></tr><tr><td>11</td><td>Sales Team Onboarding</td><td>Google Drive</td><td>Sales-specific, current (Feb 2026)</td></tr><tr><td>12</td><td>Sales Expense & Client Entertainment Policy</td><td>Google Drive</td><td>Sales-specific, current (Jan 2026)</td></tr><tr><td>13</td><td>Sales Onboarding Guide</td><td>Confluence</td><td>Sales-specific, <b>STALE (May 2024)</b> -- conflicts with Doc 11</td></tr></table>### Documents the agent SHOULD use for an engineering hire
<table><tr><td><b>Doc</b></td><td><b>Title</b></td><td><b>Location</b></td></tr><tr><td>1</td><td>General Onboarding Checklist</td><td>Google Drive</td></tr><tr><td>2</td><td>IT Systems & Access Guide</td><td>Google Drive</td></tr><tr><td>3</td><td>Office & Facilities Guide</td><td>Google Drive</td></tr><tr><td>4</td><td>Travel & Expense Policy</td><td>Google Drive</td></tr><tr><td>5</td><td>Engineering Team Onboarding</td><td>Confluence</td></tr><tr><td>6</td><td>Engineering Security & Compliance</td><td>Confluence</td></tr><tr><td>9</td><td>Slack Norms & Communication Guidelines</td><td>Google Drive</td></tr><tr><td>10</td><td>Benefits & Perks Overview</td><td>Google Drive</td></tr></table>### Documents the agent SHOULD skip
<table><tr><td><b>Doc</b></td><td><b>Title</b></td><td><b>Location</b></td><td><b>Why</b></td></tr><tr><td>7</td><td>IT Setup Guide</td><td>Confluence</td><td><b>STALE</b> -- conflicts with Doc 2 (Google Drive)</td></tr><tr><td>8</td><td>Travel & Expense Policy</td><td>Confluence</td><td><b>STALE</b> -- conflicts with Doc 4 (Google Drive)</td></tr><tr><td>11</td><td>Sales Team Onboarding</td><td>Google Drive</td><td>Wrong team</td></tr><tr><td>12</td><td>Sales Expense & Client Entertainment Policy</td><td>Google Drive</td><td>Wrong team</td></tr><tr><td>13</td><td>Sales Onboarding Guide</td><td>Confluence</td><td>Wrong team + <b>STALE</b></td></tr></table>### Why This Split Matters for the Demo
The stale docs live in Confluence alongside the current engineering docs. The agent can't just trust one source -- it has to cross-reference across systems. For example:

- Doc 7 (stale IT guide, Confluence) says "use LastPass" while Doc 2 (current IT guide, Google Drive) says "use 1Password"
- Doc 8 (stale travel policy, Confluence) says "use Concur" while Doc 4 (current travel policy, Google Drive) says "use Navan"

If the agent only searches Confluence, it will find stale info. If it only searches Google Drive, it will miss the engineering-specific docs. It must search both and resolve conflicts by recency.
### Intentional Conflicts the Agent Must Resolve
**Stale IT doc (Doc 7, Confluence) vs. current IT doc (Doc 2, Google Drive):**

<table><tr><td><b>Topic</b></td><td><b>Doc 7 (STALE, Confluence)</b></td><td><b>Doc 2 (CURRENT, Google Drive)</b></td></tr><tr><td>Project management</td><td>Asana</td><td>Jira</td></tr><tr><td>Password manager</td><td>LastPass</td><td>1Password</td></tr><tr><td>HR/Payroll system</td><td>Gusto</td><td>BambooHR</td></tr><tr><td>Endpoint security</td><td>Symantec</td><td>CrowdStrike</td></tr><tr><td>MFA policy</td><td>SMS allowed</td><td>SMS prohibited</td></tr><tr><td>Laptop specs</td><td>M2, 32GB/8GB RAM</td><td>M4, 16GB/16GB RAM</td></tr><tr><td>Min password length</td><td>12 characters</td><td>16 characters</td></tr><tr><td>IT help channel</td><td>Email only</td><td>#it-help on Slack</td></tr></table>
**Stale travel doc (Doc 8, Confluence) vs. current travel doc (Doc 4, Google Drive):**

<table><tr><td><b>Topic</b></td><td><b>Doc 8 (STALE, Confluence)</b></td><td><b>Doc 4 (CURRENT, Google Drive)</b></td></tr><tr><td>Booking platform</td><td>Concur</td><td>Navan</td></tr><tr><td>Corporate card</td><td>Amex</td><td>Ramp</td></tr><tr><td>Hotel limit</td><td>$200/night flat</td><td>$250 + high-cost city exceptions</td></tr><tr><td>Meal per diem</td><td>$60/day</td><td>$75/day</td></tr><tr><td>Alcohol</td><td>Not reimbursable</td><td>$25/person/day cap</td></tr><tr><td>Receipt deadline</td><td>10 business days</td><td>5 business days</td></tr><tr><td>Approval threshold</td><td>$250</td><td>$500</td></tr></table>
**Stale sales doc (Doc 13, Confluence) vs. current sales doc (Doc 11, Google Drive):**

<table><tr><td><b>Topic</b></td><td><b>Doc 13 (STALE, Confluence)</b></td><td><b>Doc 11 (CURRENT, Google Drive)</b></td></tr><tr><td>CRM</td><td>HubSpot</td><td>Salesforce</td></tr><tr><td>Sequencing tool</td><td>SalesLoft</td><td>Outreach</td></tr><tr><td>Content/enablement</td><td>Seismic</td><td>Highspot</td></tr><tr><td>Expense tool</td><td>Concur</td><td>Ramp</td></tr><tr><td>Client meal cap</td><td>$100/person</td><td>$150/person</td></tr></table>
**Sales docs (Docs 11, 12, Google Drive) vs. company-wide docs (Doc 4, Google Drive):**

<table><tr><td><b>Topic</b></td><td><b>Doc 4 (Company-wide)</b></td><td><b>Doc 12 (Sales-specific)</b></td></tr><tr><td>Client meal limit</td><td>$150/person (Dir. approval)</td><td>$150/person (no approval under 5 people)</td></tr><tr><td>Team dinner limit</td><td>$40/person</td><td>Not referenced (uses client meal rules)</td></tr><tr><td>Gift policy</td><td>Not mentioned</td><td>$100/person, max 2/account/quarter</td></tr><tr><td>Entertainment hosting</td><td>Not mentioned</td><td>Up to $2,000/event with VP + Finance approval</td></tr></table>
The agent should NOT surface the sales expense limits to an engineering hire. An engineer's meal and entertainment rules come from Doc 4 only.


## Demo Prompts
The demo onboards a fictional new hire. Use the following details:

- **Name**: Glean Killer
- **Role**: Software Engineer
- **Team**: Engineering
- **Manager**: Nate
- **Email**: <EMPLOYEE_EMAIL_PLACEHOLDER>
- **Start date**: Monday, March 23, 2026
- **Location**: San Francisco (in-office)
- **Previous company**: Stripe
- **Fun fact**: Once built a mechanical keyboard from scratch
### Prompt 1: Slack Welcome Message
Glean Killer is starting as a Software Engineer on the Engineering team on March 23. Their manager is Nate. They were previously at Stripe and once built a mechanical keyboard from scratch.

Based on our onboarding docs and Slack norms, post a welcome message for Glean in the #general Slack channel.

**What the agent should do:**

- Search Google Drive and find the Slack Norms doc (Doc 9), which specifies #new-hires for introductions, and the General Onboarding Checklist (Doc 1)
- Post a welcome message in #general with Glean's details, following the spirit of the intro template from Doc 9 (name, role, team, location, fun fact) but adapted as a third-person announcement since this is from the company, not from Glean
- Should NOT post in #new-hires (that's for Glean to do themselves on Day 1)
### Prompt 2: Welcome Email
Draft and send a welcome email to Glean Killer (<EMPLOYEE_EMAIL_PLACEHOLDER>) for their first day as a Software Engineer. Include the key things they need to do on Day 1 and engineering-specific setup steps. Keep it concise. Don't include Slack setup info since we've already added them. Send it from Nate.

**What the agent should do:**

- Search BOTH Google Drive (Docs 1, 2, 3) and Confluence (Docs 5, 6) to build the email
- Skip Slack-related steps (already handled)
- Skip sales docs (Docs 11, 12, 13) entirely
- Use CURRENT tool names (Jira not Asana, 1Password not LastPass, BambooHR not Gusto, Ramp not Amex, Navan not Concur) -- proving it resolved the stale doc conflicts across systems
- Use CURRENT laptop specs (M4, 16GB RAM) not the stale specs from Confluence
- Use CURRENT MFA policy (no SMS) not the stale policy from Confluence
- Keep it concise: logistics, accounts, HR essentials, eng setup commands, and links to key docs
- Send via Gmail to <EMPLOYEE_EMAIL_PLACEHOLDER>
### Prompt 3: Share Relevant Documents
Share the onboarding documents that are relevant and up-to-date for Glean Killer (<EMPLOYEE_EMAIL_PLACEHOLDER>), a new Software Engineer. Only share current docs -- skip anything outdated or not applicable to their role.

**What the agent should do:**

- Search BOTH Google Drive and Confluence to identify all 13 docs
- Filter to the 8 that are both current AND relevant to an engineer
- Exclude Doc 7 (stale IT, Confluence), Doc 8 (stale travel, Confluence), Doc 11 (sales, Google Drive), Doc 12 (sales expense, Google Drive), Doc 13 (stale sales, Confluence)
- Share the 8 relevant docs with Glean via email or direct sharing to <EMPLOYEE_EMAIL_PLACEHOLDER>

**Correct set to share:**

<table><tr><td><b>Doc</b></td><td><b>Title</b></td><td><b>Source</b></td></tr><tr><td>1</td><td>General Onboarding Checklist</td><td>Google Drive</td></tr><tr><td>2</td><td>IT Systems & Access Guide</td><td>Google Drive</td></tr><tr><td>3</td><td>Office & Facilities Guide</td><td>Google Drive</td></tr><tr><td>4</td><td>Travel & Expense Policy</td><td>Google Drive</td></tr><tr><td>5</td><td>Engineering Team Onboarding</td><td>Confluence</td></tr><tr><td>6</td><td>Engineering Security & Compliance</td><td>Confluence</td></tr><tr><td>9</td><td>Slack Norms & Communication Guidelines</td><td>Google Drive</td></tr><tr><td>10</td><td>Benefits & Perks Overview</td><td>Google Drive</td></tr></table>

## Success Criteria
The demo is successful if the agent:

1. **Searches both systems** -- pulls from Google Drive AND Confluence, not just one
1. **Resolves stale conflicts across systems** -- never references Asana, LastPass, Gusto, Concur, Amex, Symantec, SalesLoft, HubSpot, or Seismic (all from stale Confluence docs)
1. **Filters by team** -- never surfaces sales-specific tools (Salesforce, Gong, Outreach, Clari, Highspot) or sales expense policies to the engineer
1. **Posts the Slack welcome** in #general with Glean's details
1. **Sends a concise email** with correct, current information from both sources and eng-specific setup
1. **Shares exactly 8 docs** from both Google Drive (6 docs) and Confluence (2 docs) -- the current, relevant subset

