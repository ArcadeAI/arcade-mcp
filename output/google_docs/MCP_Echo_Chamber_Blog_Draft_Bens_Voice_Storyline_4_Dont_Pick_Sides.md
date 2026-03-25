---
title: "MCP Echo Chamber Blog Draft — Ben's Voice (Storyline 4: Don't Pick Sides)"
id: 1Zfr3XCXysuh0oPDBQ_5Fj-2GxEAZdCcK5r99SMns55M
modified_at: 2026-03-13T20:15:58.506Z
public_url: https://docs.google.com/document/d/1Zfr3XCXysuh0oPDBQ_5Fj-2GxEAZdCcK5r99SMns55M/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->

Stop Picking Sides in the Protocol War. Build the Infrastructure Both Sides Need.

There's a pattern I've watched play out three times in my career.

A new paradigm emerges. Developers adopt it fast. The ecosystem produces a wave of low-quality implementations that disappoint everyone who tries them. A credible voice — usually someone at a company people respect — publicly announces they're abandoning the paradigm and going back to something simpler. The internet declares the paradigm dead. Enterprises, already cautious, freeze. Meanwhile, the companies that understood the paradigm correctly were never the problem — they were building infrastructure.

This week, that credible voice was Denis Yarats, CTO of Perplexity, announcing they're moving away from MCP in favor of APIs and CLIs.

I understand why he made that call. I'd likely make the same one in his position. But I think the conclusion most people are drawing from it is wrong in a way that will cost them.

---

What Yarats Is Actually Saying

His complaints are specific: MCP bloats the context window, and MCP's auth model creates friction across service boundaries. Both are real problems. Neither is an argument against the concept of a standardized agent-tool interface.

They're arguments against the current quality of the MCP ecosystem.

A security firm called Knostic scanned nearly 2,000 publicly exposed MCP servers last year. Every single verified instance responded without authentication. No auth. Full tool exposure. Open to the internet. Equixly analyzed popular MCP implementations and found 43% contained command injection flaws.

This is the ecosystem Yarats evaluated and rejected. He's right to reject it. But "the community-built implementations are terrible" is a different statement than "the protocol is wrong."



The CLI Hot Takes Are Doing Our Marketing For Us

Here's what I find genuinely funny about this moment.

Every post on X and LinkedIn declaring "MCP is dead, just use CLIs" is making the case for what we're building at Arcade. Not despite the argument — because of it.

The CLI crowd is right about the interface. Developers want to type a command. They don't want to configure MCP servers. They don't want to manage persistent connections. They want ergonomics. Fine. That's a completely reasonable position.

But they're not asking the question that comes next: what executes the command? When that CLI call hits an enterprise system — Salesforce, Workday, a financial database, a healthcare record system — something has to handle authorization. Something has to scope permissions. Something has to log the action for your auditors. Something has to enforce policy before the tool executes.

The CLI is the front door. The control plane is the building.

One of our engineers, Evan Tahler, built an open-source tool called mcpx — "curl for MCP" — that makes this concrete. You type a command. mcpx routes it. The Arcade Gateway handles OAuth, scopes permissions, enforces policy, and logs the audit trail. The developer never thinks about any of that. They just typed a command.

Check it out: https://github.com/evantahler/mcpx

That's not a CLI replacing MCP. That's a CLI sitting on top of MCP, running through a control plane that makes it enterprise-ready. Both things coexist. Neither one won.

I've Watched This Movie Three Times

At JBoss, we were the runtime that made Java EE accessible. People argued about J2EE vs. Spring vs. lightweight containers. We built infrastructure that ran under all of them.

At MongoDB, people argued about SQL vs. NoSQL. We built a database that enterprises could actually operate, govern, and audit — not just prototype with.

At Okta, people argued about enterprise SSO vs. developer-friendly auth. We built an identity platform that did both, because the enterprise and the developer were the same customer at different stages.

The pattern: the protocol debate is always a proxy for a real infrastructure gap. The companies that win aren't the ones who pick the right side of the debate. They're the ones who build the layer that makes the debate irrelevant.

That's what we're doing at Arcade. Not picking MCP. Not picking CLIs. Not picking APIs. Building the runtime that works regardless of which interface the developer prefers — and that satisfies the requirements the enterprise actually has.

---

The Requirements That Don't Change

I'll be direct about what those requirements are, because I don't think the protocol debate crowd has spent much time with them.

Any organization under SOC-2, ISO-27001, HIPAA, or FedRAMP needs to answer three questions before an agent touches a production system:

Who authorized this action, on behalf of whom, and at what scope? That's not "we have an API key." That's delegated user authorization — the intersection of what the agent is permitted to do and what the specific human it's acting for is permitted to do. Just-in-time. Least privilege. Revocable.

What actually happened, and can you prove it? Not "our API logs captured the traffic." A full audit trail that your compliance team can export to a SIEM, that maps every tool call to an authorization event, that a regulator can read.

Is this tool production-grade or a community experiment? Most MCP servers aren't. Ours are. 7,500+ tools optimized for LLM use — not thin API wrappers that force the model to infer intent from raw parameter schemas, but tools that understand "update the intro paragraph" and translate it to the exact document segment ID the API requires.

These requirements don't care whether the developer used a CLI, an API, or an MCP client. They exist at the execution layer, not the interface layer.

The Bet

Gartner says more than 40% of agentic AI projects will be scrapped by 2027. The failure mode is always the same: demo works, production doesn't. The demo runs in single-player mode on someone's laptop. Production involves real users, real systems, real compliance reviews, and real security teams who ask uncomfortable questions.

We're not building for the demo. We're building for production.

The protocol war will resolve itself, the way these debates always do — not because one side wins, but because the right infrastructure makes the question moot. The developer gets the CLI they want. The enterprise gets the governance it requires. The control plane is what makes both possible simultaneously.

That's Arcade. Come find us when the demo is ready to become production.

Ben Sabrin has built developer platforms and enterprise infrastructure at JBoss, MongoDB, and Okta. He is currently the CRO at Arcade (arcade.dev), the only runtime for MCP.
