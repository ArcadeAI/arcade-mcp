---
title: "IT Systems & Access Guide"
id: 1x2IQ_Euc69rUhncsa8x1nDCZfk4aXdv_z0hYHa1Xeb8
modified_at: 2026-03-18T23:08:22.747Z
public_url: https://docs.google.com/document/d/1x2IQ_Euc69rUhncsa8x1nDCZfk4aXdv_z0hYHa1Xeb8/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->

# IT Systems & Access Guide
**Last updated: January 2026** **Owner: IT Operations** **Public URL:** https://docs.google.com/document/d/1x2IQ_Euc69rUhncsa8x1nDCZfk4aXdv_z0hYHa1Xeb8/edit?tab=t.0#heading=h.f6as29be02z2  **Status: CURRENT**
## Core Systems
All employees are provisioned with the following tools via Okta SSO. You should not need to create accounts manually for any of these. If you cannot access a tool, file a ticket in #it-help on Slack.
### Communication & Collaboration
- **Google Workspace** (Gmail, Calendar, Drive, Docs, Sheets, Slides): Primary email, docs, and calendar platform.
- **Slack**: Primary real-time communication. All employees should be in #general, #announcements, and their department channel. See the Slack Norms doc for channel naming conventions.
- **Zoom**: Video conferencing. Licensed accounts are provisioned automatically. Use your @acmecorp.com email to sign in via SSO.
### Project Management & Documentation
- **Jira**: Engineering, product, and design use Jira for task tracking. Other teams may use it for cross-functional projects.
- **Confluence**: Internal wiki and documentation. Start with the "New Employee" space.
- **Notion**: Used by Marketing and People Ops for lightweight planning. Access is team-specific.
### Security & Credentials
- **Okta**: SSO portal. Bookmark your Okta dashboard -- it is the front door to everything.
- **1Password**: Shared credential management. Never store passwords in Slack, email, docs, or sticky notes. Your manager will invite you to the appropriate vaults.
- **CrowdStrike Falcon**: Endpoint protection. IT will pre-install this on your laptop. Do not disable it.
### HR & Finance
- **BambooHR**: HR system of record. Pay stubs, PTO requests, benefits enrollment, compliance training, and personal info updates all live here.
- **Ramp**: Corporate card and expense management. Managers will issue you a virtual Ramp card within your first week. See the Travel & Expense Policy for reimbursement rules.
### Engineering-Specific (provisioned by Eng managers)
- GitHub (org: acme-corp)
- AWS (via Okta federated login)
- Datadog
- PagerDuty
- CircleCI
## Password & MFA Policy
- All passwords must be at least 16 characters, generated and stored in 1Password.
- MFA is required on Okta, GitHub, and AWS. Use Okta Verify or a hardware key (YubiKey). SMS-based MFA is not permitted.
- If you lose access to your MFA device, contact IT immediately via #it-help or it-support@acmecorp.com. Do not attempt to reset MFA yourself.
## Laptop Policy
- Engineering: MacBook Pro 14" M4, 16GB RAM, 1TB storage.
- All other teams: MacBook Air 13" M4, 16GB RAM, 512GB storage.
- FileVault disk encryption must be enabled (IT will verify on Day 1).
- Do not install unapproved software. See the Approved Software List in Confluence.
## Getting Help
File a ticket in #it-help on Slack. Include your full name, team, and a description of the issue. SLA is 4 business hours for standard requests, 1 hour for access-blocking issues.

