---
title: "Engineering Security & Compliance Requirements"
id: 720906
modified_at: 2026-03-18T23:11:00.022Z
public_url: https://arcade-hackathon.atlassian.net/wiki/spaces/Company/pages/720906/Engineering+Security+Compliance+Requirements
---

**Last updated: January 2026** **Owner: Security Engineering** **Status: CURRENT**

**Public URL: **[https://arcade-hackathon.atlassian.net/wiki/x/CgAL](https://arcade-hackathon.atlassian.net/wiki/x/CgAL)
## Overview

All engineers must comply with the following security practices. These are not optional. Violations may result in access revocation and disciplinary action.
## Code & Repository Security

- 

Never commit secrets, API keys, tokens, or credentials to source control. Use 1Password for credential storage and inject secrets via environment variables or our Vault (HashiCorp) integration.
- 

All repos must have branch protection enabled on `main`: require PR reviews, require passing CI, and disable force pushes.
- 

Dependabot alerts must be triaged within 5 business days. Critical/high severity vulnerabilities must be patched within 48 hours.

## Data Handling

- 

**PII**: Personally identifiable information must never appear in logs, error messages, or non-production databases. Use tokenization or masking for any PII in test environments.
- 

**Production Data**: Never copy production data to local machines. If you need production-like data for testing, use the anonymized dataset (see #eng-infra for access).
- 

**Encryption**: All data at rest must use AES-256 encryption. All data in transit must use TLS 1.2+.

## Access & Authentication

- 

SSO via Okta is mandatory for all internal tools. Do not create standalone accounts.
- 

MFA is required on Okta, GitHub, AWS, and Datadog. Hardware keys (YubiKey) are preferred. Okta Verify is acceptable. SMS-based MFA is prohibited.
- 

Access follows least privilege. Request only the access you need. Managers review access quarterly.

## Incident Response

- 

If you discover a security vulnerability or suspect a breach, immediately report it in #eng-incidents and page the Security on-call via PagerDuty.
- 

Do not attempt to investigate or remediate a potential breach on your own. Preserve evidence and escalate.
- 

All security incidents trigger a post-incident review within 5 business days.

## Compliance Training

- 

Complete the annual SOC 2 awareness training in BambooHR within your first 10 business days.
- 

If you handle payment data, complete PCI-DSS training within 5 business days.

## Approved Tools

- 

Do not use unapproved SaaS tools, browser extensions, or AI coding assistants without Security team review. Submit a request in #security-review.
- 

Approved AI tools: GitHub Copilot (org-managed license only). Unapproved: any tool that sends code to external APIs without org-level controls.
