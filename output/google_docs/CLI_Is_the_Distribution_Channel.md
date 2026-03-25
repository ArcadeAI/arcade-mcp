---
title: "CLI Is the Distribution Channel"
id: 1GEaCy_HLCj_bvhO0FO57aUA5DQGwjUUqM3_qITxdOY0
modified_at: 2026-03-13T01:24:08.684Z
public_url: https://docs.google.com/document/d/1GEaCy_HLCj_bvhO0FO57aUA5DQGwjUUqM3_qITxdOY0/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->

**STRICTLY ARCADE INTERNAL**

<table><tr><td><b>CLI Is Not the Competition.</b><b>CLI Is the Distribution Channel.</b><i>The fastest path to ecosystem integration. Ship it.</i></td></tr></table>
<table><tr><td><b>TL;DR</b>The internet is debating CLI vs. MCP like they’re competitors. They’re not. CLI is an interface. MCP is the infrastructure underneath. Every developer running Claude Code, Cursor, Windsurf, or any coding agent is a potential Arcade customer <b>if we give them a CLI that runs through our Gateway.</b> Evan’s MCP CLI project proves it works. Nothing changes architecturally. The Gateway still runs. Auth still works. Governance is still enforced. We just made the front door wider. This is the fastest path to ecosystem integration we have.</td></tr></table>
## The Insight: CLI Is a Layer, Not a Lane
The current discourse frames CLI, API, and MCP as competing protocols. Pick one. This framing is wrong, and it’s costing us a massive GTM opportunity.
**Here’s the reality: CLI is just an interface.** It’s the convenience layer. The thing the developer types into. It’s not a protocol. It’s not an architecture. It’s a front door. And behind that front door, something still has to execute the tool call, manage the auth, scope the permissions, and log the action.
**That “something” is the runtime. That’s us.**
Why is the market so excited about CLI? Because developers don’t want to write MCP server code. They don’t want to configure custom MCP servers every time they need a new tool. They want to type a command and have it work. CLI abstracts away the MCP plumbing and that’s exactly why it’s an opportunity for us, not a threat.
You don’t bring Snowflake to your laptop. You don’t run Salesforce locally. You execute against those systems through an interface _and something in the middle handles auth, execution, and governance._ CLI doesn’t eliminate that middle layer. It needs it.
<table><tr><td><b>THE STACK (nothing changes)</b>Developer types a command↓<b>CLI  (the new interface — Evan’s MCP CLI project)</b>↓<b>Arcade Gateway  (auth, scoping, policy enforcement)</b>↓<b>Arcade Runtime  (tool execution, governance, audit)</b>↓7,500+ tools</td></tr></table>
## The Opportunity: Fastest Path to Ecosystem Integration
**_what’s the easiest way to expand and simplify this for clients?_**
**This is the answer.** Every developer using a coding agent today lives in the CLI. Claude Code, Cursor, Windsurf, Cline, Aider, Continue. These are CLI-first environments. The developers in them aren’t browsing MCP registries. They’re typing commands. If our tools are one CLI command away, we’re in their workflow. If they’re not, we’re in a docs page they’ll bookmark and forget.
**There’s already market validation.** An independent MCP CLI client built by a developer at IBM has pulled over 1000 GitHub stars. That’s organic demand for exactly this pattern. Developers want CLI access to MCP tools. Someone else is building it in the open. We should be the ones delivering it — with auth, governance, and the world’s largest tool catalog behind it.
### Why this is a big deal:
<table><tr><td><b>Without MCP CLI</b></td><td><b>With MCP CLI (via Arcade Gateway)</b></td></tr><tr><td>Every agent client needs a custom connector</td><td>One CLI, any agent, any tool</td></tr><tr><td>We fight upstream to get into each platform</td><td>Developers pull us into their workflow</td></tr><tr><td>Onboarding requires Gateway config + MCP client setup</td><td>npm install + one command</td></tr><tr><td>Enterprise pilot takes weeks of integration</td><td>First tool call in minutes, governance from day one</td></tr><tr><td>We compete in the MCP-vs-API debate</td><td>We transcend the debate — CLI runs on MCP, through our Gateway</td></tr></table>
## Proof of Concept: Evan’s MCP CLI Project
**This isn’t theoretical. Evan already built it.** The MCP CLI project demonstrates that a developer can interact with Arcade’s tool catalog through a standard command-line interface, with the Gateway handling all auth and execution underneath. The plumbing works. The question isn’t “can we build this?” It’s “how fast can we productize it?”

## The Narrative Judo: Turn the Debate Into Our Distribution
Right now, every hot take on X and LinkedIn about “MCP is dead, just use CLIs” is unintentionally making our case. They’re arguing for the interface layer. We own the execution layer. The louder the CLI crowd gets, the more developers will want CLI access to tools **and they’ll need a runtime to make those tools work securely at scale.**
_The positioning writes itself: “You want CLI? Great. Here’s CLI. It connects to the world’s largest catalog of agent-optimized tools, through a Gateway that handles auth, scoping, and audit for you. You get the interface you love with the infrastructure your CISO requires.”_
**We don’t pick a side in the protocol war. We become the runtime that all sides need.**
## Open Questions
<table><tr><td><b>Question</b></td><td><b>Context</b></td></tr><tr><td><b>Repo home</b></td><td>Do we keep this in Evan’s repo and iterate there, or move it into the Arcade org repo? Evan’s repo is fast and low-friction. Arcade repo signals product commitment and makes it easier to integrate into CI/CD, docs, and release processes. Recommendation: start in Evan’s repo for speed, migrate to Arcade repo when we’re ready to announce.</td></tr><tr><td><b>Competitive positioning</b></td><td>An independent MCP CLI client (built by an IBM developer) already has 2,000+ GitHub stars. That’s organic demand we should be capturing. How do we position Arcade’s CLI against this? Our edge: auth, governance, 7,500+ production-grade tools, and enterprise readiness. The open-source client proves the demand. We deliver the production version.</td></tr><tr><td><b>Launch plan</b></td><td></td></tr></table>
## The Ask
1. **Prioritize Evan’s MCP CLI project for productization.** The prototype exists. Let’s scope V1 and ship it.
1. **Decide on repo ownership.** Evan’s repo for speed now, Arcade repo for launch. We need a call on timing.
1. **Lock in a launch plan.** Blog post, social, docs, Getting Started. The narrative is ready. We need a date and owners.

<table><tr><td><b>THE BOTTOM LINE</b>Someone else is already building an MCP CLI in the open and getting thousands of stars for it. The demand is real. We have the Gateway, the auth layer, the governance, and 7,500+ tools. Evan proved the integration works. We just need to ship it, name it, and launch it. This is the fastest path to ecosystem integration we’ve ever had.<b>The protocol debate is the distraction. Distribution is the game.</b><b></b><b>Dominate coding agent users via CLI, Dominate Agentic Apps via MCP</b></td></tr></table>
