---
title: "Wil Pong - Arcade.dev Enterprise PM Take Home Assignment"
id: 1t0JZpg21jKXSwBR4rhvpdfKgaLWFyiRybMBMFpNiows
modified_at: 2026-02-26T22:39:56.037Z
public_url: https://docs.google.com/document/d/1t0JZpg21jKXSwBR4rhvpdfKgaLWFyiRybMBMFpNiows/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->

# BossBattle: Building Incident Response Agents With Arcade
**Wil Pong — Enterprise PM Take-Home** 
**February 2026**

GitHub: https://github.com/pong-init/BossBattle
AI-Assisted Development Logs: /vibe-coding/ in repo


## TL;DR
I built an AI incident response agent on Arcade's platform, found the Gateway to be genuinely strong, and spent most of my time wrestling with everything around it — observability, error messages, eval tooling, and tool selection UX. Along the way I contributed an upstream fix to the eval framework (PR #783) and built two working prototypes: an observability stack and a declarative policy engine called Tron. The 90-day roadmap that follows is grounded in that build experience: fix the front door (Month 1), make the Gateway indispensable (Month 2), then sell it to the CISO (Month 3).


## 1. Build Experience: BossBattle
### What I Built
I built **BossBattle**, an AI incident response agent for a fictional Fortune 500 / Global 2000 (F2000) company called PixelCorp. When a production incident fires, BossBattle triages it, pulls context from GitHub, creates a Linear ticket, posts to Slack, and emails the VP of Engineering if it's urgent enough.

I chose incident response deliberately, for a few reasons: it's Arcade's origin story (the team originally pivoted from building an SRE agent), it exercises multiple tool integrations with real auth flows, and it's the kind of cross-service orchestration that enterprise platform teams actually need to solve.

The architecture is a 4-node LangGraph pipeline:

Incident JSON → Triage (LLM) → Context (GitHub) → Ticket (Linear) → Notify (Slack + Gmail)

Each node has explicit severity-based routing: P1/P2 incidents get Slack + email to leadership, and P3/P4 get Slack channel notifications only. The agent processes four seeded incidents ranging from a database failover (P1) to a CSS bug on mobile checkout (P4), each designed to exercise different routing logic and tool combinations.

The whole thing connects to Arcade through a single MCP Gateway endpoint — one URL, ~12 cherry-picked tools, Arcade Headers auth, no more app-by-app OAuth interrupts. More on this below.
### What Worked
**The MCP Gateway is genuinely great.** Creating a gateway, selecting tools from multiple servers, and getting a single endpoint took less than 10 minutes in the dashboard. For a platform that's trying to be the control plane for agent tool use, this is the right abstraction. One URL instead of four separate service connections is a real developer experience win.

**Arcade Headers auth is the right call for programmatic agents.** My original plan assumed I'd be fighting through four separate OAuth interrupts every time the agent ran. Instead, the Gateway with API key + user ID in headers meant the agent just... worked. No interactive auth, no token expiration issues, no 3am wake-up-call problems. The plan's biggest anticipated friction point turned out to be a non-issue because Arcade had already solved it. Credit where it's due.

**The tool catalog has real depth.** Linear support is fully optimized — CreateIssue, UpdateIssue, TransitionIssue all worked out of the box. GitHub and Slack were really comprehensive. When the tools work, the integration path from "I have an agent idea" to "it's calling real APIs" is impressively short.

**Linear connecting on my behalf was genuinely delightful.** I know that sounds small, but the moment where you watch an agent create a real ticket in a real project management tool with the right severity, the right labels, and a description that references the actual suspicious commit from GitHub — that's the magic. That's what you sell.
### What Didn't
**The first impressions were confusing.** I signed up for a fresh Hobby account and landed on a dashboard with pre-populated apps and secrets. I didn’t have any guidance on what was mine versus default, or why there were Arcade-owned assets (like secrets) for tools where I didn’t have an account at all. Since there wasn’t an onboarding flow, or even suggestions on Quickstart guides to follow, I leaned heavily on feeding the docs site directly to my own coding agents to discover how Arcade could help me. 

Because of that, I didn’t discover the MCP Gateway AI Assistant — which is genuinely powerful, with tool suggestions and programmatic creation — until I already scraped my knees on the manual creation flow suggested by Claude. For a platform that's selling "easy auth for agents," the front door doesn't match the promise yet.

**The tool selection UX needs work.** The "shopping cart" experience for adding tools to a Gateway is friction-heavy. I could see the number of tools I had selected, but no way to see _which_ ones, outside of a server level box at the top. Clicking one of these green boxes removed every tool selected for that server, with no undo — I lost my selection multiple times just trying to figure this out. The default assumption seems to be that developers will select an entire server's worth of tools, but that's the equivalent of blanket-selecting all scopes on an OAuth token. This was the single biggest thing that stole my time when setting up the Gateway.

**A platform bug masqueraded as a permissions issue — and nobody could tell.** Arcade's GithubApi_ListPullRequests tool is constructing a malformed URL: it doubles the owner/repo path (github.com/owner/repo/repos/owner/repo/pulls instead of api.github.com/repos/owner/repo/pulls) and hits github.com instead of api.github.com. The result is a 404 on every call, regardless of repo visibility. I spent real time making my repo public because the 404 made me — and my coding agents — assume it was a permissions issue. It wasn't. The URL was just wrong. I only found the root cause by digging into the OTel trace logs, which showed the exact malformed request. This is the strongest possible case for better error remediation: a raw 404 with no context caused a developer to misdiagnose and "fix" a problem that didn't exist.

**Error messages don't help you recover.** When the GitHub tool needed a server URL configured, I got a notification that didn't link to the settings page. Clicking "Edit" opened a modal where I had to find the error at the bottom, which then opened a new tab to a different part of the app. OAuth failures surface raw HTTP errors with no suggested next steps. For a platform selling "easy auth," every error should tell you what to do next.

**Observability was the hardest part of the entire build — and it shouldn't have been.** My plan naively assumed the observability stack would be "a single prompt" to generate. In reality, it was a multi-day debugging saga: traces ≠ metrics (needed a spanmetrics connector), Prometheus's rate() returns NaN for batch workloads, adding Tempo to docker-compose broke Grafana's network config. I shipped a 9-panel Grafana dashboard, but I had to build all of it myself. Arcade sits on the most valuable telemetry data in the agent stack — every tool call, every auth flow — and none of it is observable without developer-side instrumentation.

**The eval framework assumes you're using OpenAI.** I used Gemini 2.5 Flash instead of GPT-4o, and arcade_evals broke because suite.run() hardcodes OpenAI-style tool calling assumptions. This led me to contribute PR #783 to ArcadeAI/arcade-mcp, adding a provider-agnostic InferenceBackend protocol. The fix was ~200 lines with zero breaking changes. It shouldn't have been necessary — an eval framework for a model-agnostic platform should itself be model-agnostic.


## 2. Enterprise Gap Analysis
Everything in §1's "What Didn't" section is a gap — but those are the ones I personally hit. There's a broader set of enterprise gaps that I can infer from the platform's current state, competitive positioning, and what F2000 platform teams typically require.
### Platform Gaps (from building + product observation)
**No native observability.** This is the biggest one. I built an entire OTel → Prometheus → Grafana → Tempo stack to answer a simple question: "why did last night's P1 triage take 45 seconds instead of 12?" Today, the tool execution layer is a black box. The raw ingredients already exist — OpenLLMetry emits traces natively if you configure a MeterProvider. Nobody has connected the dots. Arcade should. Notably, MintMCP (a competing MCP gateway) already ships with real-time monitoring dashboards — this gap is visible to enterprise evaluators.

**The "Two-Tier Tool" problem.** Native Arcade tools (Linear, Slack) appear in traces automatically. Custom tools registered via the Gateway are invisible — no tracing, no eval coverage. Enterprises won't adopt a Gateway where half their tools are observable and the other half are blind spots. Every tool that passes through the Gateway should inherit auth, telemetry, and eval coverage automatically, regardless of who built it.

**No agent identity.** The platform tracks _users_, not _agents_. When PixelCorp is running 47 different agents through the same Gateway, the CISO needs to know which agent called what tool, when, and why. Today there's no way to distinguish BossBattle's tool calls from any other agent running under the same user ID. Cloudflare's MCP Server Portals don't solve this either — they approach from the network layer, not the agent identity layer — but it's only a matter of time before someone does.

**Eval framework locked to one model provider.** Fixed via PR #783, but the underlying issue is architectural. A platform that's model-agnostic should have model-agnostic evaluation infrastructure.
### Inferred Enterprise Gaps
**No admin console or team management.** Who manages the Arcade account? Who can see which Gateways? Who approves tool access? For a F2000 platform team, "everyone shares one account" is a non-starter.

**No SCIM provisioning.** Enterprise IT teams onboard hundreds of developers through automated identity management. Without SCIM, every user is a manual add. This is table stakes for any vendor going through enterprise procurement — Composio and MintMCP will get here eventually too.

**No declarative access policies.** Today, if you want to restrict an agent to only query production repos, or only create tickets in a specific Linear project, or only email internal addresses — there's no mechanism for that. Arcade's Contextual Access framework supports webhooks for custom policy logic, which is architecturally sound but operationally burdensome: every enterprise needs to build and host webhook servers, making their security posture code on a server rather than auditable config in Git. A declarative policy layer (built-in rules + policy-as-code) would cover 80% of use cases with zero code, while webhooks remain the escape hatch for the other 20%.

**No committed-use pricing.** Enterprise procurement needs a contract with predictable costs, not purely usage-based billing. This sounds boring, but it's a literal gate that prevents deals from closing.

**No multi-tenant isolation.** Five teams building agents shouldn't see each other's tools, Gateways, or usage data. Today there's no team-level scoping.


## 3. 90-Day Force-Ranked Roadmap
### Why This Sequencing
The thesis: **Arcade's Gateway is becoming an agent control plane.** It started as auth orchestration, and it's naturally evolving into the single chokepoint where every agent action gets authenticated, observed, and governed.

The sequencing follows the adoption curve:

- **Month 1** makes the control plane easy to adopt (developers need to love it before you can sell to enterprises)
- **Month 2** makes it indispensable (the tools that make teams depend on it, not just appreciate it)
- **Month 3** makes it enterprise-required (the features that get the CISO to sign off)

Each month builds on the last. You can't sell governance (Month 3) if nobody's using the Gateway (Month 1). You can't make the Gateway indispensable (Month 2) if developers bounce during onboarding (Month 1).
### Month 1: Growth & Usability — Fix the Front Door
The problem is simple: the first 10 minutes on Arcade don't match the quality of the underlying platform. The Gateway is great once you find it and figure it out. The "finding it and figuring it out" part is where people drop off.

**Ship a first-run wizard.** Sign-up → working Gateway in under 5 minutes. Pick a template (incident response, customer support, data pipeline), select your tools, authorize once, get a working endpoint. The Gateway AI Assistant already does most of this — it just needs to be the default path instead of a hidden option.

_What it unblocks:_ Time-to-first-value drops from "30 minutes of confusion" to "5 minutes to working agent." This is the top of the funnel. Nothing else matters if developers bounce here.

**Make every error actionable.** Every error in the platform should answer three questions: what went wrong, why, and what to do next. OAuth failures should link to the auth configuration page. Tool errors should suggest alternative tools or configuration changes. "Raw HTTP 400" is never an acceptable error state for a platform selling "easy."

_What it unblocks:_ Reduces support burden, increases self-serve success rate, and stops the most common onboarding failure mode.

**Fix the tool selection UX.** Add a review step before committing tool selections. Add undo. Add search and filtering within servers. Show "created by" metadata on tool servers. Stop making the default action on a selected tool "remove it with no way to get it back."

_What it unblocks:_ Gateway configuration becomes less error-prone, which means fewer misconfigured Gateways, fewer support tickets, and more developers who actually finish setup.

**What you're NOT doing in Month 1:** Enterprise features. No admin console, no SCIM, no governance. This is tempting to prioritize because enterprise deals are big, but you can't sell enterprise if your developer experience bleeds adoption. Fix the foundation first. (I'd love to debate this prioritization with the team — there's a reasonable argument that one lighthouse enterprise customer is worth more than 100 happy hobby-tier devs.)

_What I'd want to validate:_ What does the current onboarding funnel look like? Where do new users drop off? If it's at Gateway creation, the wizard is urgent. If it's at tool selection, the UX fix is urgent. The answer shapes the priority order within this month.
### Month 2: The Gateway IS the Product — Build What Nobody Else Is
Here's the strategic reality: Anthropic owns the MCP spec. Stripe, Salesforce, and Cloudflare are all shipping their own first-party MCP servers. Arcade cannot win a supply-side fight building MCP servers against the companies that own the underlying APIs.

But nobody is building what sits _on top of_ those servers: composition, auth, telemetry, and eval across all of them. That's Arcade's position. The Gateway isn't just a convenience layer — it's the control plane. Cloudflare approaches from the network/security layer up; Arcade approaches from the developer/agent layer down. These are different products for different buyers — for now. The question is whether Arcade can lock in the agent-level identity and governance layer before Cloudflare moves up-stack.

**Ship native OTel export from the Gateway.** Every tool call through the Gateway should emit OTLP traces automatically. No developer-side instrumentation required. I spent hours building an observability stack that the Gateway should provide for free. Arcade sits on the most valuable telemetry data in the agent stack — make it accessible.

_What it unblocks:_ Platform teams can answer "why was last night's agent run slow?" without building their own monitoring infrastructure. This is also a natural upsell path — free tier gets basic metrics, paid tiers get full trace export and dashboards.

_What I'd want to validate:_ How many current users are already wiring up their own observability? If the answer is "almost none," that might mean it's too early. If the answer is "everyone who goes to production," then it's already overdue.

**Solve the Two-Tier Tool problem.** Custom and third-party MCP servers registered with the Gateway must inherit auth, OTel, and eval coverage automatically. Today they get discovery but not treatment. This is a platform integrity issue — if enterprise teams can't observe and govern all their tools equally, the Gateway is a partial solution.

_What it unblocks:_ Enterprises bring their own internal MCP servers. If those servers are second-class citizens in the Gateway, adoption stalls at the platform team level.

**Ship eval governance.** Require evals to pass before tools go to production. Org-wide eval dashboards showing pass rates across teams and agents. CI/CD integration so evals run on every deployment. The eval framework already exists — it just needs the governance wrapper.

_What it unblocks:_ "How do we trust this agent in production?" has an answer. Platform teams get a quality gate that doesn't require manual review of every tool configuration.

**What you're NOT doing in Month 2:** The enterprise admin console. It's coming in Month 3, but shipping it before the Gateway is fully instrumented means you'd be building governance UI for a platform that can't tell you what's happening. Instrument first, govern second.
### Month 3: Ship Tron — The C-Suite Conversation
Months 1 and 2 make Arcade the developer's best friend. Month 3 leverages that position to become the platform the CISO signs off on.

The pitch to enterprise: _"Your developers are already running agents through our Gateway. Now let's make that safe."_

This works because every agent already routes through the Gateway to use tools. Arcade sits at the natural chokepoint. The security product is a _byproduct_ of the developer product, not a separate build.

**Ship Contextual Access Policies.** Declarative rules — YAML, not code — that restrict tool execution by context. "BossBattle can only query repos tagged production." "Gmail.SendEmail is restricted to *@pixelcorp.io recipients." "Linear.CreateIssue requires approval from the on-call lead for P1 incidents."

I built a working prototype of this during the sprint — **Tron**, a policy engine with 26 passing tests and a FastAPI server — to demonstrate what this could look like as a platform primitive. More on that in §4.

_What it unblocks:_ The CISO conversation. Every enterprise security review will ask: "Can you restrict what the agent can do?" Today the answer is no. With Contextual Access, the answer is "yes, declaratively, with an audit trail."

**Ship agent identity.** Move from tracking users to tracking agents. Each agent gets its own identity, its own audit trail, its own policy scope. When PixelCorp's security team asks "which of our 47 agents accessed the HR database last Tuesday?" the platform should have the answer.

_What it unblocks:_ Multi-agent governance. Without agent identity, all agents running under the same user look identical in the audit log. That's a compliance dealbreaker.

**Ship the admin console.** Team management, SCIM provisioning, multi-tenant isolation, usage dashboards. The boring stuff that enterprise IT requires before they'll approve a vendor. This is intentionally last — not because it's unimportant, but because it's most valuable when the platform underneath it is already instrumented (Month 2) and policy-aware (Month 3).

_What it unblocks:_ Enterprise procurement. "Who manages this?" has an answer. "Can we onboard 200 developers through Okta?" has an answer. "Can teams be isolated?" has an answer.

**What you're NOT doing in Month 3:** Building a proprietary LLM layer to the gateway. Stay at the tool and auth layer for now, and let customers handle their own LLM traffic. We can explore the concept of a high-value partnership, like with LiteLLM, to validate whether or not customers are ready for a full agent gateway.

_What I'd want to validate:_ How far along are enterprise pilot conversations? If deals are stalling at "we can't restrict what the agent does," Contextual Access policies might need to move earlier. If deals are stalling at "we can't onboard our team," the admin console might need to come first. The sequencing here is the most debatable part of this roadmap — it depends entirely on what's actually blocking revenue.


## 4. Prototypes & Contributions
I don't love roadmaps that stay abstract. Here's what I built during the sprint to demonstrate what I'm proposing:
### Tron: A Working Contextual Access Policy Engine

**Tron** is a config-driven policy engine: policies defined in YAML, evaluated at request time by a FastAPI server, with 26 passing tests covering tool restrictions, input validation, and output redaction. The key design insight — which emerged during implementation, not planning — is that policies should be written by security teams in config files, not by developers in code.

Here's what an actual policy in Tron looks like today (from the repo's policies.yaml):

access:
  deny_rules:
    - tool: "Gmail.SendEmail"
      condition:
        field: "recipient"
        matches: "*@external.com"
      action: block

pre:
  rules:
    - tool: "Linear.CreateIssue"
      condition:
        field: "project"
        matches: "production-*"
      action: block
      message: "Cannot create issues directly in production projects"

post:
  redactions:
    - tool: "GitHub.*"
      fields: ["author.email", "committer.email"]

This covers the three hook points in Arcade's Contextual Access architecture — access filtering, pre-execution validation, and post-execution redaction — but as declarative config rather than webhook servers. It's a proof of concept for what Arcade could ship as a built-in policy layer: cover 80% of use cases with zero code, keep webhooks as the escape hatch for the other 20%.

The full implementation is in the repo.
### Observability Stack: Grafana + Prometheus + Tempo
A 9-panel Grafana dashboard monitoring BossBattle's tool calls, LLM latency, token usage, and end-to-end triage duration. Built with OpenTelemetry, the spanmetrics connector, and zero custom instrumentation code — OpenLLMetry's LangchainInstrumentor handles all the trace emission natively when a MeterProvider is configured.

The key discovery: the raw ingredients for agent observability already exist in the open-source ecosystem. What's missing is someone connecting them into a seamless developer experience. That someone should be Arcade — the Gateway already sees every tool call. Emitting OTLP traces from that chokepoint is a natural extension, not a new product.

Dashboard panels: tool call latency by tool, success/failure rate, auth flow duration, error rate by tool, LLM token usage, incident triage timeline, cost per incident, request volume, and end-to-end latency distribution.

More screenshots in docs/screenshots/ in the repo.
### Eval Framework Contribution: PR #783
When I swapped from GPT-4o to Gemini 2.5 Flash, arcade_evals broke because suite.run() hardcodes OpenAI-specific assumptions (string tool names, seed=42, strict:true). I contributed a fix upstream: a provider-agnostic InferenceBackend protocol that extracts inference execution behind an interface, so the eval logic stays universal while each provider handles its own quirks.

~200 lines of code. Zero breaking changes to the existing API. PR #783 on ArcadeAI/arcade-mcp.

This is the kind of contribution that scales — it's not just fixing my problem, it's fixing the problem for every developer who wants to use Arcade evals with a non-OpenAI model.


## 5. What's NOT on the Roadmap & Why

**FedRAMP certification.** Takes 12+ months minimum. Not achievable in 90 days, and the market opportunity is large enough without it. Put it on the 12-month roadmap if government is a target segment.

**Competing on MCP server supply.** Anthropic owns the spec. Major vendors are building their own servers. Arcade's SDK for building MCP servers puts the company in a commodity framework fight against players with infinitely more resources. The Gateway — composition, auth, telemetry, governance on top of _any_ server — is the defensible position.

**Consumer / prosumer tier.** Focus on enterprise deal size. The free Hobby tier is a fine top-of-funnel, but product investment should optimize for the F2000 platform team buyer, not the individual developer tinkering on weekends.


## 6. Beyond 90 Days: From Tool Gateway to Agent Gateway
Today, Arcade sees one traffic stream: tool calls. The full enterprise control plane eventually needs to see two: tool calls _and_ LLM traffic (prompts, responses, token costs, PII).

Today:     Agent → LLM → [invisible] → Arcade Gateway → Tool

Tomorrow:  Agent → [Arcade LLM Proxy] → LLM
                         ↕ unified control plane
           Agent → [Arcade Tool Gateway] → Tool

Combined, you'd own both traffic streams — every prompt and every action in a single audit log. Nobody has this today. The CISO who asks "what did the agent say _and_ do?" gets a complete answer.

I don't have enough data to prescribe the build-vs-partner path here — that depends on whether there's organic demand for LLM traffic visibility from current customers, or whether this is still a forward-looking bet. But the strategic direction is clear: the agent control plane that governs both inference and execution is where the enterprise value concentrates. Getting there first matters.


## 7. Appendix
### UX Journal: Selected Entries
These are raw observations from the build process, included for context on where specific friction points informed the roadmap.

**Two different GitHub servers in Gateway setup.** "Featured" vs. not, no "created by" metadata. I wasn't sure which was official. For a tool selection experience that asks developers to trust what they're connecting to, provenance matters.

**Shopping cart removal with no undo.** Selected tools are shown as a count, not a list. Clicking a green checkmark removes the tool immediately with no confirmation and no undo. I re-selected tools multiple times.

**Git Server URL requires hardcoding.** One URL, one repo. Works for a demo, doesn't work for enterprises with hundreds of repos across multiple orgs. If we expect one Gateway per team, that's fine — but the UI doesn't explain the mental model.

**GitHub tool URL construction bug.** GithubApi_ListPullRequests doubles the owner/repo path and hits github.com instead of api.github.com. Every call returns 404 regardless of repo visibility. The error message gave no indication it was a malformed URL — I only found the root cause by reading the OTel trace logs. This is the single best example of why Month 1's error remediation work matters: the raw 404 caused me to waste time changing repo visibility settings for a bug that had nothing to do with permissions.

**Gmail auth looping error.** The sequence of auth → tool call matters more than expected. Not sure if this is a LangChain issue or an Arcade issue, but the error was opaque enough that I spent 30+ minutes debugging a simple agent.

**Gateway AI Assistant discovery.** Found it by accident after manually configuring my first Gateway. It's powerful — describe what you want and it configures everything. Should be the default path, not a hidden alternative.

**Eval framework model assumption.** arcade_evals assumes OpenAI-style tool calling. Using Gemini broke suite.run(). Fixed via PR #783 but the issue revealed a deeper architectural assumption about model-agnosticism that should be addressed at the platform level.
### Methodology & AI Usage
Built with Claude Opus 4.6 (architecture and technical execution) and Gemini 3.1 Pro (product research, initial strategy and code review). All AI-assisted development sessions documented in /vibe-coding/ in the repository, including prompts, outputs, and decision rationale.

To be clear about what's mine vs. what's AI-generated: the architecture decisions, product strategy, gap analysis, and roadmap prioritization are entirely my own judgment. AI accelerated the implementation — writing boilerplate, generating config files, debugging OTel wiring. The development environment used Antigravity (VS Code fork) for planning with Claude Code for execution, which helped with context window management and separation of concerns.

The multi-model approach itself became a data point: when Gemini broke the eval framework that assumed OpenAI, it revealed a real platform gap. The tool you use to build exposes the platform's assumptions about how people build.
### Collaboration Questions for the Arcade Team
Things I'd want to discuss in a review session:

- **Month 1 vs. Month 3 prioritization.** I sequenced developer experience before enterprise features. Is there a lighthouse customer that would justify inverting this? How much of the current pipeline is enterprise vs. developer-led?

- **The "Two-Tier Tool" problem.** How many customers are registering custom MCP servers vs. using the built-in catalog? If it's mostly built-in, this is less urgent. If teams are bringing their own servers, it's a blocker.

- **Native OTel — build depth.** Should Arcade ship basic metric export and let customers bring their own dashboards? Or go deeper with pre-built Grafana templates and anomaly detection? The answer depends on whether observability is a feature or a product.

- **Tron's policy language design.** YAML is my instinct because security teams write config, not code. But HCL (Terraform-style) and OPA (Rego) are both established in the enterprise governance space. What do Arcade's current customers already use?

- **LLM traffic visibility demand.** Is there organic demand from customers who want to see both tool calls and LLM traffic in one place? Or is the "Agent Gateway" vision still ahead of the market?

