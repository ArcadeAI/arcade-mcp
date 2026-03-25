---
title: "Engineering Team Onboarding"
id: 720899
modified_at: 2026-03-18T23:11:35.542Z
public_url: https://arcade-hackathon.atlassian.net/wiki/spaces/Company/pages/720899/Engineering+Team+Onboarding
---

**Last updated: February 2026** **Owner: VP Engineering** **Status: CURRENT**

**Public URL:** [https://arcade-hackathon.atlassian.net/wiki/x/AwAL](https://arcade-hackathon.atlassian.net/wiki/x/AwAL)
## Welcome to Acme Engineering

This document supplements the General Onboarding Checklist with engineering-specific setup, tools, and norms. Complete the general checklist first, then work through this doc.
## Welcome Email Additions

When drafting the welcome email for an engineering hire, append the following section after HR and before KEY DOCS:

**ENGINEERING SETUP**
- 

Run the bootstrap: `git clone git@github.com:acme-corp/eng-setup.git && cd eng-setup && ./bootstrap.sh`
- 

Clone core repos: acme-api, acme-web, acme-infra, acme-docs
- 

Verify local dev: `cd acme-api && make dev-up`
- 

Add your @acmecorp.com email to GitHub and request org access in #eng-onboarding.

Also append to KEY DOCS:
- 

Engineering Onboarding Guide
- 

Engineering Security & Compliance

## Dev Environment Setup

1. 

Install Homebrew, then run the bootstrap script from the eng-setup repo:
wide760
```
   git clone git@github.com:acme-corp/eng-setup.git
   cd eng-setup && ./bootstrap.sh
```

This installs: Docker Desktop, Node.js (via nvm), Python 3.12 (via pyenv), Go 1.22, Terraform, and the AWS CLI.
1. 

Configure your GitHub account:
  - 

Ensure your @acmecorp.com email is added to your GitHub account.
  - 

Enable MFA (hardware key preferred, Okta Verify acceptable).
  - 

Request org access from your manager or in #eng-onboarding on Slack.

2. 

Clone the core repos:
  - 

`acme-api` (backend services)
  - 

`acme-web` (frontend)
  - 

`acme-infra` (Terraform modules)
  - 

`acme-docs` (internal engineering docs)

3. 

Verify you can run the local dev environment:
wide760
```
   cd acme-api && make dev-up
```

This starts all services locally via Docker Compose. See the README for troubleshooting.
## AWS Access

- 

AWS access is federated via Okta. You will see an "AWS" tile on your Okta dashboard.
- 

You will be assigned to IAM roles based on your team. If you need elevated access (e.g., production), submit an access request in #eng-infra with your manager's approval.
- 

Never create long-lived AWS access keys. Use `aws sso login` for CLI access.

## Datadog

- 

Datadog is our observability platform for logs, metrics, traces, and alerts.
- 

Your Okta account will grant read access by default. Write access (creating monitors, dashboards) requires team lead approval.
- 

Familiarize yourself with the team's primary dashboard: search "Team Overview" in Datadog.

## PagerDuty

- 

All engineers join the on-call rotation after their first 30 days.
- 

Your manager will add you to the appropriate PagerDuty schedule.
- 

Install the PagerDuty app on your phone and confirm push notifications work.
- 

Escalation policy: if you cannot respond within 15 minutes, the alert escalates to the secondary on-call, then to the team lead.

## CI/CD

- 

We use CircleCI for continuous integration and deployment.
- 

All PRs must pass CI before merge. Do not force-merge failing builds without a tech lead's approval.
- 

Deployments to staging are automatic on merge to `main`. Production deployments are triggered via ChatOps in #eng-deploys.

## Code Review Norms

- 

All code changes require at least 1 approving review before merge.
- 

PRs should be small and focused. If a PR exceeds 400 lines, consider splitting it.
- 

Reviewers should respond within 1 business day. If blocked, escalate in your team's Slack channel.
- 

Use conventional commit messages (see the style guide in acme-docs).

## Engineering Slack Channels

- 

#engineering: General eng discussion.
- 

#eng-onboarding: Ask setup questions here. No question is too basic.
- 

#eng-deploys: Deployment notifications and ChatOps.
- 

#eng-infra: AWS, Terraform, and infrastructure questions.
- 

#eng-incidents: Active incident coordination. Do not use for non-incidents.

## First Two Weeks

- 

Week 1: Complete dev setup, pair with your onboarding buddy on a "starter task" (a small, well-scoped issue labeled `good-first-issue` in Jira).
- 

Week 2: Pick up your first real ticket from the sprint backlog. Attend your first sprint planning and retro.
- 

End of Week 2: 1:1 with your manager to discuss initial impressions and any blockers.
