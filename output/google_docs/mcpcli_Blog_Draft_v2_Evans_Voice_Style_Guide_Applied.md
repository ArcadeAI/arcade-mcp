---
title: "mcpcli Blog Draft v2 — Evan's Voice (Style Guide Applied)"
id: 1fkG3fwxsI2Iv1CdW0Gv6xmithCFC3zjutQse7nCbrXQ
modified_at: 2026-03-13T16:01:16.723Z
public_url: https://docs.google.com/document/d/1fkG3fwxsI2Iv1CdW0Gv6xmithCFC3zjutQse7nCbrXQ/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->

mcpcli: curl for MCP

At work the other day, a developer pinged me frustrated that MCP was "too slow" and "eating the whole context window." I asked to see their setup.

They had configured their agent to load 47 MCP servers at startup. Every tool schema from every server — dumped into the system prompt before the agent had done a single useful thing. We're talking thousands of tokens of JSON, most of it for tools the agent would never call in that session.

That's not an MCP problem. That's a tooling problem. And it's exactly why I built mcpcli.


### No one said REST was dead because curl existed

When curl came out, nobody wrote think pieces declaring REST APIs dead. That would have been absurd. curl is how you talk to REST APIs from a terminal — it's the interface layer, the thing you type. REST is still the architecture underneath. The two things aren't in competition. They compose.

mcpcli is the same idea. I put it right in the README: "curl for MCP."

That framing isn't marketing. It's technically accurate. curl lets you make HTTP calls without writing an HTTP client. mcpcli lets you discover, inspect, and execute MCP tools without maintaining a persistent MCP connection, writing a custom client, or — critically — pre-loading every available tool schema into your agent's context window.

So when I see posts declaring "MCP is dead, just use CLIs"… I'm genuinely confused. CLI is an interface. MCP is what runs underneath the interface. These aren't competing options. One is the front door. The other is the building.


### The context window problem is actually a discovery problem

Here's why MCP keeps getting blamed for something that isn't its fault.

The naive implementation: connect every server at startup, load every tool schema, stuff it all into the system prompt. Your agent now "knows" its tools — at the cost of hundreds or thousands of tokens before it's done a single useful thing. At production scale, across long multi-tool conversations, that overhead compounds fast.

The right approach is progressive discovery. Here's what that looks like in practice:

mcpcli search "post a message to slack"
=> slack/postMessage    (0.94)  Post a message to a channel
=> slack/sendDM         (0.87)  Send a direct message to a user

mcpcli info slack postMessage

mcpcli exec slack postMessage '{"channel": "#general", "text": "hey"}'

Three commands. The agent searched for what it needed, inspected only the schema for that one tool, then executed. The context window never saw the other 7,499 tools available through the Gateway.

That's not a workaround. That's how it should work.

The search command combines keyword and semantic matching — so "post a message to slack" finds the right tool even if the agent isn't sure what it's called. The index is built locally using embeddings, updates incrementally, and doesn't require any API keys. The whole thing is designed to keep tool discovery fast and context-window usage low.


### Two audiences (I want to be honest about both)

I built mcpcli for two audiences, and I think it's worth being direct about this.

The first is MCP developers. If you're building an MCP server, you need a fast way to test it from the terminal without spinning up a full client environment. mcpcli gives you that — connect, list tools, inspect schemas, fire test calls, and debug with verbose HTTP output (-v shows request/response headers and timing, curl-style). It's a dev tool I personally needed and couldn't find, so I built it.

The second audience is AI agents themselves. This is the part that surprised me.

Agents that shell out to mcpcli instead of maintaining persistent MCP connections get a lot for free: better token management (discover on demand, not all upfront), progressive tool discovery (search for what you need, inspect the schema, then execute), and the ability to share a single pool of MCP server connections across multiple agents running on the same machine.

We ship a Claude Code skill and a Cursor rule with the tool. Install with one command:

mcpcli skill install --claude

After that, Claude Code knows to run mcpcli search before assuming it knows what tools are available. The agent discovers what it needs at the moment it needs it. Token usage drops. It actually finds the right tool because it's searching — not guessing from a stale schema loaded at startup.


### What's actually underneath

I want to be transparent about something: when mcpcli runs against the Arcade Gateway, there's considerably more happening than a CLI command.

The Gateway handles OAuth — proper delegated user auth, not a shared API key in a .env file. It scopes permissions at runtime, logs every tool call for audit, and enforces policy before execution reaches the tool. When you run mcpcli with the -v flag and watch the HTTP traffic, you'll see the authorization header and the x-request-id. That request is going through a control plane doing a lot of work you don't have to think about.

That's the point of a good abstraction layer. You type a command. The infrastructure handles the rest.


### The discourse is getting this backwards

The current debate — MCP vs. CLIs vs. APIs — is framed as if you have to pick one. You don't. These things compose.

mcpcli is TypeScript, uses the official @modelcontextprotocol/sdk, implements the full OAuth 2.1 flow for HTTP servers, and has a semantic search index powered by local embeddings so you can find the right tool by describing what you want to do in plain English. It's a CLI. It runs on MCP. Both things are true. Neither one killed the other.

The context window complaints are real. The auth friction complaints are real. But those are ecosystem quality problems, not protocol problems. The answer isn't to abandon standardized agent-tool interfaces — it's to build better tooling around them.

That's what mcpcli is trying to be.

Installs in one command, works with Claude Code, Cursor, and any agent that can shell out. Check it out, try it, break it, send feedback: github.com/evantahler/mcpcli

---

Evan Tahler is Head of Engineering at Arcade (arcade.dev). He has previously built infrastructure at Airbyte, Grouparoo, Voom/Airbus, and TaskRabbit.
