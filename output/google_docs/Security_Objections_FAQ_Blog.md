---
title: "Security Objections FAQ Blog"
id: 1PkcWrzbXZXBz5Gp8NDV-J-3rgVbvkaZDLtmRsN_0vPw
modified_at: 2026-03-11T00:38:38.405Z
public_url: https://docs.google.com/document/d/1PkcWrzbXZXBz5Gp8NDV-J-3rgVbvkaZDLtmRsN_0vPw/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->

# Securing AI Agents in the Enterprise: Your Questions Answered
As AI agents move from proof-of-concept to production, security teams are asking tough questions about how to maintain control without stifling innovation. We've been having these conversations with Fortune 500 companies for months now, and certain questions come up consistently. Here's what enterprise security teams want to know about deploying AI agents safely.
## Where does your runtime actually run?
This is always the first question, and for good reason. No matter how compelling a third-party service is, convincing a large enterprise to route their core identity and authorization flows through someone else's cloud is nearly impossible.

We learned this lesson the hard way in previous roles. That's why Arcade was designed from day one to be self-deployable. We provide Helm charts that let you run everything in your own VPC. While we maintain a public cloud service for smaller companies and evaluations, our enterprise customers run on-premises. From day one, the architecture has always been built for enterprises that need full control over where their data lives.
## How do you handle all those authentication tokens?
When security teams hear that we're storing tokens for every combination of agent, user, and downstream service, their immediate reaction is concern. If you have three agents serving 1,000 users across five applications, that's 15,000 tokens to manage. The security implications seem enormous.

The key insight is that we're not an identity provider. We don't store raw user identities or try to replace your existing IDP infrastructure. Whether you're running Entra, Google Workspace, Ping, or Okta, we integrate with what you already have. Think of us as the agent's broker, managing the OAuth tokens and their entire lifecycle including refreshes and mismatch resolution.

We cache these tokens to avoid unnecessary latency, but the authorization policies themselves live in your systems. We're primarily a policy enforcement layer, not a policy management layer. We've been in the identity space long enough to know that policy silos create drift and headaches. Our preferred pattern is to do live checks against your centralized authorization system rather than trying to replicate your policies in our database.
## Can we externalize secrets management completely?
Right now, we act as a secure token vaultwallet for the secrets that agents need at runtime. This isn't meant to replace infrastructure secret storesyour central secret store like HashiCorp Vault. Instead, it's designed specifically for agents and agentic use cases.to take the burden off developers and minimize what agents can access.

The critical security principle here is that agents never actually see the secrets. When an agent wants to perform an action like updating a database record, it calls a tool. That tool has access to the necessary credentials in our vault, and we inject them at the last possible moment. The agent doesn't know the secret exists and has no way to access it directly. This means it can't hallucinate its way (or be tricked) into leaking credentials.

Currently, secrets would need to sync from your central store to our cache. Making them completely external with direct pass-through is on the roadmap, but it's a function of prioritization rather than architectural limitation.
## How do you handle fine-grained authorization policies?
This gets to the heart of what makes agent authorization different from traditional application security. It's not just about whether a user can access a service. It's about the specific actions an agent attempts on behalf of that user.

For example, you might want a policy that prevents an agent from sending emails to more than 5,000 recipients, or blocks certain sequences of tool calls that indicate something has gone wrong. Arcade seesWe see all the parameters flowing into tool requests, which means you can write policies against that data.

In early access, we provide a powerful hook system. Right before a tool executes, we can call out to whatever authorization system you use. One bank we work with has us checking their SailPoint instance through an intermediate translation layer. WeThey get a yes or no back, and we proceed or block accordingly.

Over time, we'll build first-party integrations for common systems. But we'll also expose an agent-specific policy layer for rules that don't fit neatly into traditional entitlement systems. Things like contextual access management based on conversation history or tool call sequences. We're still learning what this should look like as we see more production deployments.
## What about session management and security controls?
This is where our architecture with a custom-built gateway becomes important. We're not using off-the-shelf proxy technology. We built our own gateway in Go because we needed extreme performance, high availability, and the ability to run multiple gateways per project, each with its own tool collections and authorization rules.
Because we servecontrol the gateway layer, we can hook into your existing security posture and policy systems at every enforcement point. Before hitting a tool, we can check not just our token store but also call out to your entitlement system, validate device posture with something like CrowdStrike, or perform any other check you need.

We've also built out-of-band communication capabilities that aren't limited by current protocol constraints. This enables things like MFA for high-risk actions and backward compatibility with agents running older versions of MCP.

OurThe goal is to be extensible and meet developers where they are,minimize our opinions while making it easy for themdevelopers to get security right. Most people building agents are machine learning engineers, not identity specialists. We want to handle the complexity so they can focus on making agents useful rather than making them secure.
## Built by people who understand what enterprises need
Our team sits at a unique intersection of deep expertise in security, distributed systems, and AI. We've spent years building identity and authorization systems at scale, and we did the hard work to create a runtime that meets the intense requirements enterprises have for security and governance. If you're thinking about how to move AI agents into production safely, we'd love to chat about what we've learned.

