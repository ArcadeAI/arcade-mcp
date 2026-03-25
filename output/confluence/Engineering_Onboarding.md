---
title: "Engineering Onboarding"
id: 1376257
modified_at: 2026-03-18T22:51:33.191Z
public_url: https://arcade-hackathon.atlassian.net/wiki/spaces/Company/pages/1376257/Engineering+Onboarding
---

**Last updated: March 2024** **Owner: VP Engineering Status: STALE**
## Welcome to Acme Engineering

This doc covers everything you need to get set up as a new engineer. Complete the general company onboarding first, then work through this guide.
## Dev Environment Setup

1. 

Install Homebrew, then manually install the following:
  - 

Docker Desktop
  - 

Node.js 18 LTS (via nvm)
  - 

Python 3.10 (via pyenv)
  - 

Go 1.20
  - 

Terraform
  - 

AWS CLI v2

2. 

Configure your GitHub account:
  - 

Add your @acmecorp.com email to GitHub.
  - 

Enable MFA (Google Authenticator or SMS).
  - 

Request org access by emailing your manager.

3. 

Clone the core repos:
  - 

`acme-monorepo` (all backend and frontend code)
  - 

`acme-infra` (Terraform modules)

4. 

Verify you can run the local dev environment:
wide760
```
   cd acme-monorepo && docker-compose up
```

## AWS Access

- 

AWS access is managed via IAM users. Your manager will create your IAM account and send you your access key and secret key via 1Password.
- 

Store your keys in `~/.aws/credentials`. Do not commit them to source control.

## Monitoring

- 

**New Relic**: Our observability platform for logs, metrics, and APM. Your Okta account will grant access. Familiarize yourself with the "Production Overview" dashboard.
- 

Datadog access is available for infrastructure metrics only. Most engineers won't need it.

## On-Call

- 

All engineers join the on-call rotation after their first 60 days.
- 

We use OpsGenie for alerting and on-call scheduling. Install the OpsGenie app on your phone.
- 

Escalation policy: if you cannot respond within 30 minutes, the alert escalates to the secondary on-call.

## CI/CD

- 

We use Jenkins for continuous integration and deployment.
- 

All PRs must pass CI before merge.
- 

Deployments to staging are triggered manually via the Jenkins dashboard. Production deployments require a deploy ticket approved by your tech lead in Jira.

## Code Review Norms

- 

All code changes require at least 2 approving reviews before merge.
- 

There is no hard line limit on PRs, but keep them reasonable.
- 

Reviewers should respond within 2 business days.
- 

Commit message format is flexible -- just keep them descriptive.

## Engineering Slack Channels

- 

#engineering: General eng discussion.
- 

#deploys: Deployment notifications.
- 

#infra: AWS and infrastructure questions.
- 

#incidents: Active incident coordination.

## First Two Weeks

- 

Week 1: Complete dev setup, shadow a senior engineer for 2 days, review the architecture docs in Confluence.
- 

Week 2: Pick up a small bug fix from the backlog. Attend sprint planning.
- 

End of Week 2: Present a brief summary of what you learned to the team in the Friday eng standup.
