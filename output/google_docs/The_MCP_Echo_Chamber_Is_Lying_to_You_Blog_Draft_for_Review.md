---
title: "The MCP Echo Chamber Is Lying to You — Blog Draft for Review"
id: 15ik4UxUkIjiZGKaPY7OfhvxMwzO_fA9UGzeHnFCln-M
modified_at: 2026-03-12T23:54:16.479Z
public_url: https://docs.google.com/document/d/15ik4UxUkIjiZGKaPY7OfhvxMwzO_fA9UGzeHnFCln-M/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->

# The MCP Echo Chamber Is Lying to You

The debate raging across X, LinkedIn, and developer forums about MCP vs. APIs vs. CLIs is missing the point entirely. Here's what's actually happening — and why most of the people talking loudest about it have never shipped an agent into production.

---

When Perplexity CTO Denis Yarats announced at Ask 2026 that his company is abandoning MCP internally in favor of traditional APIs and CLIs, the internet lit up. Product leaders nodded sagely. Developers posted takes. The "MCP is dead" crowd felt vindicated.

I've watched this exact movie before. When REST displaced SOAP. When containers displaced VMs. When microservices displaced monoliths. Every time, the discourse was dominated by people arguing about the protocol. Every time, the people actually running production infrastructure were dealing with a completely different set of problems.

Let me offer a contrarian view — and then tell you what actually matters.

---

THE PERPLEXITY SIGNAL IS REAL, BUT IT'S BEING MISREAD

Yarats cited two practical objections: high context window consumption and clunky authentication. These are legitimate engineering complaints. MCP tool definitions consume tokens — every schema, parameter, and response format eats into working memory. At production scale, across long multi-tool conversations, that overhead compounds fast.

But here's what nobody in the echo chamber is saying: the problem isn't MCP. The problem is that most MCP servers are garbage.

Knostic researchers scanned nearly 2,000 publicly exposed MCP servers and found that every single verified instance responded to unauthenticated requests — zero auth, full tool exposure, open to anyone on the internet. Equixly's analysis of popular MCP implementations found that 43% contained command injection flaws. The MCP specification itself, in its original form, didn't even require authentication as a baseline.

Developers looked at this landscape of poorly built, bloated, insecure MCP servers — and rationally concluded that raw APIs were more reliable. That's not an indictment of the protocol. That's an indictment of the ecosystem that rushed to ship before anyone thought about quality, security, or production readiness.

Garry Tan built a CLI. Yarats is moving to APIs. These are reasonable responses to a broken ecosystem — not evidence that standardized agent-tool interfaces are a dead end.

---

THE DEBATE IS HAPPENING IN SINGLE-PLAYER MODE

Here's the uncomfortable truth: the vast majority of people participating in this conversation are operating in a context that has almost nothing to do with enterprise software.

They're running Claude Desktop on a MacBook. They're connecting to their local file system, their personal GitHub, their own Notion workspace. They're building clever automations for themselves, in a sandboxed environment, with no users other than themselves, interfacing with no systems that require access governance.

That's a fine use case. It's not enterprise software.

The moment you introduce multi-user environments, multi-tenant data, enterprise systems of record, and human beings other than the developer into the picture — the entire problem set transforms. You're no longer asking "which protocol is more ergonomic?" You're asking:

- Who authorized this agent to act on behalf of this user?
- What is the exact scope of that authorization, and who can revoke it?
- Which systems can this agent touch, and which are off-limits for this user's role?
- How do I prove to my auditors what the agent did, when, and why?

None of these questions appear in the MCP vs. API debate. Because the people having that debate have never had to answer them.

---

THE COMPLIANCE QUESTION NOBODY IS ASKING

Let me be direct: I genuinely struggle to understand how any organization operating under SOC-2, ISO-27001, HIPAA, or FedRAMP signs off on the current paradigm.

These frameworks don't just require that your systems are secure in theory. They require demonstrable controls, audit trails, least-privilege access, and evidence that you know — at a granular level — who accessed what, when, and under what authorization.

Now consider what's being proposed in the "just use APIs" camp: agents dynamically constructing calls to enterprise APIs, potentially synthesizing novel sequences of actions against production systems, with credentials managed however the individual developer thought to manage them, and audit trails that exist only insofar as your API logs capture the traffic.

In what compliance regime does that clear review? In what security architecture does that represent acceptable risk?

The answer isn't "move to APIs." The answer isn't "move back to MCPs." The answer is that you never had a governance layer in the first place — and switching protocols doesn't create one.

---

WHAT ACTUALLY MATTERS: THE CONTROL PLANE IS NOT OPTIONAL

I've spent my career at the intersection of developer platforms and enterprise infrastructure — JBoss, MongoDB, Okta. The pattern is always the same. A new paradigm emerges, developers adopt it rapidly, and the technology becomes genuinely useful. Then it hits the enterprise wall: security review, compliance requirements, multi-user complexity, audit mandates. The projects that survive that wall are the ones that built a control plane. The ones that don't, stall in pilot purgatory indefinitely.

Gartner projects that more than 40% of agentic AI projects will be scrapped by 2027. The failure mode is consistent: the prototype works beautifully in single-player mode, then shatters when it hits real production requirements. This is not a new story. The tool changes. The pattern doesn't.

The companies shipping agents into production — not demos, not pilots, production systems — have solved three things simultaneously:

Authorization at runtime. Not a shared API key in a .env file. Delegated user authorization that is scoped to exactly what this agent, on behalf of this user, is permitted to do at this moment. Just-in-time, least-privilege, revocable.

Reliable execution. Tools that are actually optimized for LLM use — not thin API wrappers that expose raw parameters and force the model to infer intent. Tools that translate "update the intro paragraph" into the exact document segment ID and text operation required, without burdening the context window with unnecessary schema.

Governance. A centralized control plane where every tool — whether it's in your vendor's catalog or one your team built — is registered, versioned, scoped, and auditable. Pre- and post-call enforcement. Full audit trails exportable to your SIEM. The kind of evidence trail your compliance team can actually work with.

These three requirements aren't sequential. They're simultaneous. You can't have reliable execution without knowing who authorized the action. You can't have governance without knowing what was authorized. Get one wrong and the whole thing fails in production.

---

THE REAL LESSON FROM PERPLEXITY

Yarats' move away from MCP is a data point about the current quality of the MCP ecosystem, not a verdict on standardized agent-tool interfaces as a category. The same complaints — context bloat, auth friction, unreliable execution — are what every serious enterprise team hits when they try to assemble production agents from community tooling.

The response isn't to abandon the concept of a standardized interface. The response is to raise the bar dramatically on what "production-ready" means for agent tooling: agent-optimized tool definitions that don't bloat context, auth that's actually built in rather than bolted on, and a control plane that enforces policy at every invocation regardless of the underlying protocol.

That's the bet we've made at Arcade. Not on MCP specifically. On the principle that as agents scale — more agents, more tools, more users, more systems — the need for a runtime that handles authorization, reliable execution, and governance simultaneously becomes non-negotiable. The protocol is an implementation detail. The control plane is the product.

---

A NOTE ON WHAT "ENTERPRISE READY" ACTUALLY REQUIRES

For every organization serious about deploying agents beyond the laptop:

The question is not "MCP or API?" The question is: do you have a control plane?

One that enforces delegated user authorization at the moment of action. One that applies least privilege at the intersection of what the agent is permitted to do and what the user is permitted to do. One that maintains a full audit trail that satisfies your compliance requirements. One that lets your security team see, govern, and revoke access without shutting down your agents entirely.

If you don't have that control plane, the protocol choice is irrelevant. You're not production-ready. You're just choosing which path leads you to the same compliance review rejection.

The companies that win the agentic AI transition aren't going to be the ones who picked the right protocol in 2026. They're going to be the ones who solved auth and governance before they needed them.

---

The author has built enterprise software platforms at JBoss, MongoDB, and Okta, and is currently focused on the agent infrastructure layer at Arcade (arcade.dev) — the only runtime for MCP.
