---
title: "[Public] MCP Auth Working Group - Tool Scopes"
id: 1HGVxX1PlymQDehNdfi1xfENvvLwMBoa76ubWKD6yKnE
modified_at: 2026-02-17T21:40:00.792Z
public_url: https://docs.google.com/document/d/1HGVxX1PlymQDehNdfi1xfENvvLwMBoa76ubWKD6yKnE/edit?usp=drivesdk
---

# Problem Statement and  Supporting Docs

<!-- Tab ID: t.0 -->

# MCP Auth Working Group - Tool Scopes
MCP Contributor Discord Channel: #auth-wg-tool-scopes
More info on how to join the Discord server here
## Facilitators and Contributors
- John Baldo (Asana)
- Kevin Gao (Descope)
- Ola Hungerford (Nordstrom)
- Nate Barbettini (Arcade.dev)
- Sam Morrow (GitHub)
- Simon Russell (Prefactor)
- thiago (OpenAI)
- Max Gerber (Stych)
- Dineth Marlin Ranasinghe
## Related SEPs and GitHub Issues
- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1881
- https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1862
- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1488
- https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1862
## Problem Statement
**Context**
The MCP specification currently supports OAuth authentication flow and OAuth scope challenges, but these features are implementable without guidance. There is no standardized approach for how to define, manage, and challenge tool scopes in a way that SDK developers can integrate. As a result, current implementations are entirely reliant on individual end developers to build custom solutions.
**Core Problems**
- **No SDK or protocol-level guidance for tool scopes.** There is no place in standard tool definitions to specify required scopes, and no guidance for SDK developers on how to handle scope challenges. Each implementation must solve this independently. There is no source of truth to present to the client.
- **Scopes do not map 1:1 with tools.** A single tool may require different scopes depending on the arguments passed (e.g., Microsoft's MCP server for MS Graph, where one tool supports hundreds of different scope combinations). This makes static scope declarations insufficient.
- **Transport evolution is breaking current workarounds.** The direction of travel for tool responses is toward immediate SSE streams, which makes it impossible to change status codes and headers after tool execution begins. This breaks the ability to send www-authenticate scope challenge responses at the HTTP layer. The transport is also moving toward more stateless patterns, which complicates preflight or session-level checks.
- **Current workarounds are fragile and complex.** GitHub's MCP Server, for example, implements OAuth scope challenges via custom middleware that sits in front of the SDK, requiring double parsing of JSON-RPC payloads. This is not sustainable or scalable.
- **Unclear where the problem lives.** There is not yet consensus on whether this is primarily an SDK implementation problem, a protocol problem, or a client support problem. The C# SDK, for instance, already filters available tools based on scopes in the incoming token and supports scope challenges—suggesting SDK guidance alone may address a significant portion of use cases. This could serve as a reference example.
  - **_2/17 update: _**The group is converging on “primarily an SDK problem first, protocol problem second.” The C# SDK’s existing scope filtering and challenge support was validated again as a useful reference model. The group agreed to create reference implementations starting with the TypeScript SDK, then Python, before pursuing protocol changes.
- **Lack of proper authorization leads to brittle security patterns.** In the absence of scoped/fixed authorization, teams resort to tool allowlisting and blocklisting as a security measure—which is a poor substitute and makes implementations brittle with respect to server updates. A better approach would guarantee that any tool call falling outside authorized scopes will fail predictably.
**Open Questions**
- Should tool calls always succeed, or is it acceptable for them to fail due to insufficient authorization?
  - 2/17 update: Group has converged on “failure is acceptable and expected.” Clients must handle failed tool calls regardless (server could be down, permissions could change, etc.). The focus should be on making failures informative via structured denials and scope challenges, not on preventing them.
- Can preflight/session-level scope checks work given the move toward stateless transports?
  - 2/17 update: Group agrees pre-flight checks are useful as an advisory UX optimization, not as a guarantee. Preferred framing: “pre-flight hints” (Max’s suggestion). Pre-flight is incomplete—you still need error handling on the actual call—but it enables batching authorization requests upfront to reduce consent screen fatigue. The group proposed that the FGA WG should own the pre-flight specification work since the problem is structurally identical for scopes and fine-grained auth (scopes being the simpler case).
- Is an SDK guidance document sufficient, or are spec changes required?
  - 2/17 update: Group decided SDK improvements are the top priority (“mission number one”). The Steering Committee prefers that groups prototype ideas as extensions and prove them out before requesting formal spec inclusion. The group will focus on creating reference implementations in official SDKs—starting with TypeScript/Node—before proposing protocol changes. Spec changes are not off the table but are deferred until real implementations exist and adoption creates demand for them.
- How do we handle progressive authorization (upscoping) within a session?
  - 2/17 update: The existing 401/403 scope challenge mechanism is sufficient for the immediate term. The UX goal is to batch upscope requests via pre-flight hints so users face fewer sequential consent screens. Sam noted that GitHub’s scope challenge rate is low (~sub-1% of tool calls), and that clients which can’t handle scope challenges simply see an error and continue—which is an acceptable degradation.
- What is the appropriate UX for prompting users for authorization—and how do we avoid over-prompting?
  - 2/17 update: Pre-flight hints would allow clients to discover needed scope upgrades before execution and batch them into a single authorization prompt. Simon framed this as particularly valuable in planning scenarios: a client could pre-flight all anticipated tool calls at the start of a workflow and collect authorizations upfront. Sam also raised the possibility of a client capability signal (e.g., “I support interactive scope upgrades” vs. “headless, no interactive auth”) so servers can adjust behavior accordingly.
- What is NOT possible with current implementations? (We need scenarios and a common understanding of constraints.)
  - 2/17 update: Key constraints identified:
  - Some SDKs (e.g., Go) go straight into SSE streams, making mid-tool-call scope challenges technically impossible without architectural changes
  - Protected resource metadata rendering exists in some SDKs but isn’t connected to scope challenge flows
  - No SDK provides a callback mechanism for pre-handler scope checks
  - Developers must work with raw headers and HTTP responses rather than modeled objects
  - GitHub’s workaround (custom middleware with double JSON-RPC parsing) is not sustainable or replicable for most developers
**Why Now**
Now is the right time to solve this problem, especially since we can leverage an extension mechanism rather than requiring core protocol changes.
**Desired Outcome**
A solution that enables MCP server developers and SDK developers to support scope challenges and determine required scopes effectively, with clear guidance for publishing scope requirements to end users and clients. Solutions should consider the end-to-end flow, including UX/DX for both servers and clients.

# Working Group Roadmap

<!-- Tab ID: t.pfs22gza5wro -->

## **Working Group Roadmap**

### **Phase 1 — SDK Improvements (current focus)**
- Improve support for OAuth scope challenges in official SDKs
- Start with TypeScript/Node SDK as reference implementation
- Replicate to Python SDK, then others
- Open issues and contribute code to official SDK repos
- Coordinate with SDK maintainers on architectural constraints (e.g., mid-tool-call challenges)

### **Phase 2 — Protocol Enhancements (future)**
- Scope hint annotations on tool definitions (coordinate with Annotations WG)
- Pre-flight mechanism (coordinate with FGA WG — they own the spec work)
- Client capability signals for authorization support

### **Cross-Group Coordination**
<table><tr><td><b>Group</b></td><td><b>Relevance</b></td></tr><tr><td>Fine-Grained Authorization WG</td><td>Shared pre-flight mechanism, structured denials. Owns the complex version of the same problem.</td></tr><tr><td>Annotations WG</td><td>Pre-flight check infrastructure, client-side annotation filtering.</td></tr><tr><td>Tool Search / Primitive Grouping</td><td>Client-side tool filtering with better server hints may obviate server-side search.</td></tr></table>## 


# 1/22 Meeting Notes

<!-- Tab ID: t.jf7s1y9bgb0e -->

**1/22 Meeting Notes**

Link to corresponding GitHub Discussion (for discoverability): TODO

**Action items for the group before next meeting:**

- Ola or Sam: poll for next meeting
- Ola: Add to public calendar (can copy the last one) and/or find out how to give permission to facilitators to do this
- Ola or Sam: poll for recording/transcribing next meeting(s)?
- Ola: Create a shared document for the group (Done)
- Group: edit and/or add comments (facilitators may be invited as editors, and need to allow public comments) 
- What is the problem we’re solving?
  - Ola drafted based on conversation, needs review from group
- End-to-end scenarios and concrete examples

**Attendees:**

NOTE: We didn’t write down all the attendees who attended but didn’t participate during the meeting (outside of introductions) - will do this next time so we have a more complete record of who was there.  (Also propose we OK recording, since Nate asked for this but hadn’t asked for permission or configured this yet.)

- John Baldo
- Max Gerber
- Ola Hungerford
- Sam Morrow
- David Parks
- Simon Russell
- Ervis Shqiponja

**Agenda and Discussion Topics:**
****
Disclaimer: notes are written on the fly during the meeting and may not be 100% complete or exactly as stated.  Please leave a comment if you feel that anything important has been left out or misrepresented.

Introductions

- Who we are
- Why are we here to talk about this/why is it relevant to each of us?

Working agreements for talking during meetings  - raise hands or just go for it?
- The group decided to go with ‘raising hands’

Discussion Topics

- What is the scope of the group?
- What is the problem we’re solving?
- Do we even agree we should pursue this?
- Previous similar proposals failed - lets make sure we understand why, and why this might be different?
  - Simon Russell: Is this an SDK problem, client support problem, or protocol problem?
    - Related open question: should tool calls always succeed?
  - Max Gerber
    - Metatools and gateways
    - Fine-grained auth WG: 
    - Might not work for everyone, but don’t let perfect be the enemy of good
    - Now is the right time to solve this, especially since we can leverage an extension
- An SDK guidance document might be enough to solve a lot of our problems
- Sam Morrow
  - Tool resolution SEP: related because it allows for adaptation
    - Opt-in
    - Tool that relates to multiple scopes
    - Instead of over-prompting users - only prompt them when you really need to do so
    - Need a source of truth to present the client
    - Transports seem to be moving to a place where we can’t change the headers
- Max Gerber
  - Need to align on the problem before discussing solutions
  - Doesn’t this result in the same amount of authorizations?
    - Sam: yes, solving this would have to be at the Oauth scope level
    - More about when/how the annotations may be interpreted vs scopes
- John Baldo
  - Agreeing on the problem is important but don’t let that put blinders on the end-to-end view
- Simon Russell
  - Plus one to John - need to consider UX and clients as part of proposals/solutions
- Sam Morrow
- John Baldo
  - Following up from previous comment: example of thinking end to end
  - Was interested in CIMD and after thinking through it end to end, realized that it was incompatible with scopes
- Simon Russell
  - Agree that we need scenarios
  - Need a common understanding of what is NOT possible
- Sam Morrow
  - Convo with Tyler L from VSCode - would be nice to use same token but then have the option to upscope
  - Started doing the groundwork, docs, scope challenge middleware - got it working but ran into complexities with how to handle the full implementation
- Simon Russell
  - Went deeper into what is possible and not possible with SSE today
- Sam Morrow
  - Added agreement that while we can drop down to an SSE today, its challenging to implement
- Simon Russell
  - One of the main problems with current implementation could be more about the way the SDKs are implemented rather than a protocol implementation
- Sam Morrow
  - Preflight checks might work for 80% of cases, but it's easy to identify cases where they fall short
- David Parks
  - The problems we’re talking about might be SDK specific since he hasn’t experienced any of these problems with the C# SDK
  - Includes ability to do scope challenges
  - Could serve as a reference example for the guidance we need to improve for SDKs

**Additional Notes from Meeting Chat**
Concrete Examples Discussed:
- David Parks: Microsoft MCP server for enterprise has one tool which supports multiple different scopes dynamically—"More like hundreds… think one tool for all of msgraph." The C# MCP SDK already filters available tools based on scopes present in the incoming token.
- Sam Morrow: GitHub has a fractured app model where you OAuth as either a GitHub App (fine-grained, no upscoping) or OAuth App (classic OAuth scopes, can upscope).
Additional Points from Chat:
- Simon Russell: The tool resolution SEP solves a lot of the issues that upfront docs would solve.
- John Baldo: Tool allowlisting/blocklisting is happening as a security measure, which is a bad security measure and makes things brittle with respect to server updates. Better to have scoped/fixed authorization with a guarantee that any tool call falling outside that authorization will fail.
- David Parks: We need to be careful about pre-flight/session level checks. The transport is moving towards more stateless patterns.
- Sam Morrow: No guidance for SDK developers, and nowhere in standard tool definitions for where to put scopes.
Reference Links Shared:
- Auth WG notes doc (as example): https://docs.google.com/document/d/1urCZnGC3rxMMQ2WmRX8r3oOhZ2NLQEcsT5fnGAzzqSI/edit
- PR #2086 - Implementations required for SEP approval: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2086
- Bluesky client-metadata.json (example of server-specific scope documentation): https://discord.com/api/connections/bluesky/client-metadata.json


# 2/17 Notes from Discord

<!-- Tab ID: t.bxz9xxgvqfn2 -->

# **Preflight Authorization vs. Structured Denials**
(Discord link for original thread: https://discord.com/channels/1358869848138059966/1461088031770677258/1473214686970515536)
## **Summary**
The Fine-Grained Authorization WG has been developing early thinking on structured denials that is directly relevant to our working group’s scope. The core proposal distinguishes between two fundamentally different questions a client might ask before calling a tool, and argues they require different mechanisms.
## **Two Different Questions**
Before calling a tool, a client may need to answer two distinct questions. These questions differ in nature and require different mechanisms:
1. **“What kind of operation is this?”** (e.g., destructive, read-only)
_This is deterministic: _same arguments produce the same answer regardless of who is calling. **Preflight (tools/resolve)** is the right mechanism here because the answer is stable between resolve and call.
1. **“Is the user authorized?”** (depends on token, access grants, policies)
_This is non-deterministic: _the answer can change between any two moments. The recommended pattern is **try-then-recover**: call the tool, and if it fails, the server returns a structured denial with remediation hints (e.g., what scope to request, what URL to visit, what to tell the user).
## **Position on Scope Info in Tool Metadata (SEP-1488)**
There is real value in clients knowing what scopes a tool might need (for consent screens, scope batching, LLM planning). However, because scopes often don’t map 1:1 to tools, scope information should be explicitly advisory rather than treated as security declarations.
**Proposed approach: **
Use a field like scopeHints: ["files:read"], following the existing *Hint naming pattern in the spec. These are planning aids, not security declarations.
## **Suggested Discussion Points**
Based on the above, the working group may want to discuss:
– Alignment on the deterministic vs. non-deterministic distinction for pre-call checks
– Structured denial format and remediation hint schema
– Whether scopeHints is the right naming and framing for advisory scope info (SEP-1488)
– Coordination with the FGA WG on shared patterns


# 2/17 Meeting Notes

<!-- Tab ID: t.kuaaaa53urcf -->

See: https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/2266

Link to original transcript and Gemini notes

Ola: trying out discussions as the main place to post notes.  We can move them here instead if this works better for commenting.
