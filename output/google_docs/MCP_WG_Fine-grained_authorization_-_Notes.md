---
title: "MCP WG: Fine-grained authorization - Notes"
id: 1jwxDAeu3kQXBOuVRIlyVPOVBswj5SY1icBuwfq6rOrI
modified_at: 2026-03-18T11:02:57.815Z
public_url: https://docs.google.com/document/d/1jwxDAeu3kQXBOuVRIlyVPOVBswj5SY1icBuwfq6rOrI/edit?usp=drivesdk
---

# Overview

<!-- Tab ID: t.0 -->

# Background
Today, MCP uses OAuth 2.1 for client-server authorization, but many practical deployments run into two related problems:
- **Authorization granularity:** OAuth scopes are often too coarse to express real-world access needs (e.g. resource-scoped access, argument-dependent permissions). Overloading scopes to be more fine-grained (e.g. one scope per document ID) is not the right solution.
- **Consent fatigue:** Increasing scope volume leads to repeated user prompts and a frustrating user experience. Human users will either "allow everything" by default, or avoid using the server, both of which are bad.

## Authorization spectrum
We can think of MCP authorization as a spectrum:

Public servers — OAuth 2.1 (mcp scope) — OAuth 2.1 (many coarse scopes) — ???
Many MCP server implementations can happily exist on the left or middle of the spectrum. This working group is interested in the far right side: systems that have authorization requirements too complex for OAuth scopes.

## Charter
This working group will explore how MCP can support fine-grained authorization semantics without requiring repeated interactive consent, and produce concrete recommendations for the protocol and SDKs.

The goal is first to:
- Identify real MCP use cases that require finer-grained permissions
- Establish a shared vocabulary and mental model for authorization granularity in MCP
- _Then and only then_, recommend protocol patterns or new mechanisms that are implementable by server SDKs and understandable by end users


## Constraints
1. MCP is most often implemented as a discrete layer on top of an existing, well-defined system. We cannot **assume or enforce** a particular style of authorization in the underlying system. It could be RBAC, ABAC, Zanzibar, or COBOL on a mainframe… 
1. As a communications protocol, the only thing we can control is the **communication** between the MCP client and MCP server: requests, resources, decisions, context or state.
1. We cannot assume that MCP clients have any specialized knowledge _a priori_ of the servers they connect to. For example, a general-purpose MCP client must not be expected to include special handling of any servers or tools _outside_ of the primitives and mechanisms described in the protocol.
  1. Notably, MCP clients also do not have any specialized knowledge of what tools are available, but are able to become specialized by way of tool descriptions. This is consistent with the view above - specialization _by way of messages passed from the server_ is valid.
1. The output of this working group should be **additive**. In other words, we don't want to create a new "MUST" requirement in the spec that requires all MCP clients and MCP servers to be re-engineered. Incremental adoption is important for the ecosystem.

# Real-world examples
**GitHub** has a rich, established authorization model that does not map well to coarse-grained scopes.
- As an end user, I want to give my agent access to only public repos, to manage discussions
- As an end user, I want to give my agent access to a specific set of repositories, to track secret scanning alerts


**Google Drive** and **Dropbox** both have fine-grained permissions models for document access and sharing. In their APIs, they have both decided to avoid modeling document access as scopes, and instead require developers to host a "file picker" JS widget on an interactive page. The outcome of picking resources to be visible in the API integration is invisible to the OAuth layer - in other words, the access token does not change.
- As an end-user, I want to give my agent read-only access to a single file.
- As an end-user, I want to give my agent write access to a folder.
- As an end-user, I want to revoke access to files or folders, so my agent no longer can see them.

**Gmail** has powerful messaging capabilities that do not map well to coarse-grained scopes. A single scope such as _mail.send_ gives an application the ability to send email to anyone, at any time, with no meaningful limits.
- As an end-user, I want to block my agent from emailing certain people or groups
- As an end-user, I want to allow my agent to send emails only to people in my contacts.

**Google Calendar** allows full control over events once write access is granted, but scopes cannot express common personal boundaries.
- As an end-user, I want to let my agent create meetings only during my working hours.
- As an end-user, I want my agent to avoid double-booking or modifying existing events.

**Autodesk**
I can provide some context based on what we’re doing at **Autodesk**. An example is a cloud MCP server that exposes tools for managing design files/documents, Bill of Materials (BOM; hierarchical/DAG-like), and projects/folders.

In practice we see multiple layers of authorization checks:

1. OAuth: A client making a tool call over HTTP (MCP protocol) must present a valid bearer access token. This is enforced at an API gateway before the request even reaches the MCP server.
1. Entitlements / plan limits: Even if the tool is visible, the call may be rejected if the user (subject of the access token) does not have the appropriate entitlement (license/subscription) and/or is over a usage limit.
1. Data access (resource-level) checks: If #2 is allowed, then the MCP server still needs to call upstream services to read/update data. Those services further enforce different access policies (RBAC/ABAC) via an internal access control service.

From this, I can think of few candidate fine-grained Authz use cases:

- Tool-category allowlisting (capability control) - As an end user, I want to allow my agent to use BOM read/query tools but NOT admin/data-management tools (e.g., create projects, add users).

- Entitlement / quota-gated tool usage -As an end user, I want my agent to be allowed to call certain tools only if I have the right entitlement, and only up to N calls/day.

- Constrained BOM Reads - As a user, I want to allow an agent to read BOM component summaries for one specific design (by model name or root component ID), but not let it enumerate across the hub (think top folder) or traverse arbitrarily deep.

- Destructive project actions require explicit approval (per-action / step-up) - As a user, I want to allow an agent to create a project, but not archive/delete projects unless I explicitly confirm that specific action.

- Membership admin with constrained roles - As a project admin, I want to let an agent invite people to a project, but only with low-privilege roles (e.g., Viewer/Reader), and not allow role removals.

- Folder operations restricted to a project/path - As a user, I want to allow an agent to organize folders inside one project—but I do not want it to bulk change roles or remove groups.



# Open questions
- Can we develop a vocabulary for:
  - Permissions imposed by the underlying service (I don't have access to a private repo in Github; I don't have access to a file in Google Drive)
  - Permissions I want to impose on the agent; "narrowing" (I have access to a private repo in Github, but I do not want my agent to have access to it)
- When does the MCP client need to know about authorization context, vs. when is try-fail-retry acceptable?
- Can we separate authorization interactions that require HITL or a web interaction (e.g. a browser based consent flow and/or URL elicitation) from authorization interactions that _could_ be automatic?
- Can we find public examples of OAuth flows authorizing a single request (e.g. authorizing creation of a single transaction once) as opposed to authorization of access to a single resource?

- Can we find public examples of OAuth flows authorizing a user-controlled numeric variable of some kind - e.g. authorizing access to 10% of quota, or a fixed dollar amount, or a fixed amount of credits?

# Decision log

<!-- Tab ID: t.h1mb8wiokqdm -->

# FGA Working Group decision log
This document tracks decisions made (or converged on) by the FGA Working Group across meetings and working sessions. Each entry includes the decision, its status, the rationale, and where it originated.

**Status key:**

- **Ratified** — Agreed by the WG in a meeting
- **Working position** — Converged on in working sessions; discussed in WG but not yet formally ratified
- **Proposed** — Raised and directionally agreed; awaiting deeper WG discussion


## Scope & Philosophy
### D1: MCP should define authorization _communication_, not policy or mechanism
The WG is not trying to redefine how authorization works inside systems (we're not writing a "Zanzibar paper v2"). MCP should define how MCP servers communicate authorization requirements to MCP clients and how MCP clients resolve them — not what those requirements mean or how they are enforced by the server.

- **Status:** Ratified
- **Source:** Week 1 meeting
- **Rationale:** MCP does not control the underlying system's authorization model (RBAC, ABAC, Zanzibar, custom, etc). MCP controls the protocol layer between MCP client and MCP server. MCP's concern is the _communication_ of authorization decisions over the wire, not the server-side mechanisms that produce them.
### D2: Full policy representation is not a goal
The WG's primary concern is: how does an MCP client ask for permission (if necessary), how does an MCP server say no, and how does an MCP client recover — either interactively or non-interactively. We may also choose to define how MCP servers communicate authorization requirements or hints about the authorization model, but MCP must _not_ attempt to represent the full policy of the underlying system in the wire protocol.

- **Status:** Ratified
- **Source:** Week 1 meeting
- **Rationale:** This focuses the WG on the protocol gap that actually exists. The systems behind MCP servers already have authorization models; what's missing is a structured way to communicate denials and recovery paths over the MCP wire. We are not trying to build a "universal representation model" to represent all possible authorization models used by the systems behind MCP servers.
### D3: Any FGA mechanisms must be optional, additive, and backwards-compatible
An MCP server may express no FGA at all. An MCP client may ignore FGA entirely. The benefit to supporting any mechanism proposed here is better UX for the end-user.

- **Status:** Ratified
- **Source:** Week 1 meeting
- **Rationale:** MCP serves a wide spectrum from simple public MCP servers to complex enterprise systems. FGA mechanisms must layer on without breaking existing deployments.
### D4: MCP is its own protocol; it should pick and choose from prior art, not adopt it wholesale
MCP is a new protocol layer and a new abstraction. It should be informed by OAuth, OpenID Connect, and other prior art, but it is not bound to adopt any of them in their entirety. The WG should pick and choose what MCP needs from existing patterns and avoid importing unsolved problems from other ecosystems.

- **Status:** Working position
- **Source:** Week 3 meeting
- **Rationale:** MCP's existing choice of OAuth 2.1 already reflects this selective approach. "MCP-ifying" existing systems _will_ require them to adapt to MCP's conventions in some way. The alternative — trying to accommodate every possible OAuth flow, for example — imports unnecessary complexity.
### D5: The reactive model (try-then-negotiate) is the correct foundation; authorization preflight rejected
Authorization is negotiated at call time via structured denials, not predicted in advance via tool metadata. Lightweight predictive _hints_ could be a compatible optimization on top. Specifically, runtime preflight checks _for authorization_ — where the MCP client signals intent to access a resource before actually doing it, to learn whether it's allowed — were considered and rejected.

- **Status:** Working position of both FGA and Tool Scopes WGs
- **Source:** Week 2 meeting; discussion with Tool Scopes WG
- **Rationale:** Authorization is inherently dynamic (permissions change, tokens expire, resources move). Complex authorization models can't be expressed as scope lists. The MCP server must always enforce at call time anyway. The try/fail/negotiate pattern is consistent with HTTP, OAuth, and the existing MCP spec. Authorization preflight specifically fails because of TOCTOU races (the answer can change between the check and the call), it doubles round trips for the common success case, many MCP servers can't answer it (e.g., a GitHub MCP server can't tell you if a resource will 404 without trying), and it risks becoming mandatory once it exists. Declarative metadata (planning hints) could provide most of the value of preflight without these downsides.

Note: The proposed tools/resolve for _behavioral_ annotation refinement (e.g., "is this operation destructive?") is a separate, deterministic question that the Tool Scopes WG owns — the rejection of preflight applies specifically to using preflight to check _authorization state_.
## Transport & Wire Format
### D6: Design for transport-agnosticism first, HTTP bindings second
FGA mechanisms should not necessarily assume HTTP semantics. In this WG, we should design mechanisms that are transport-agnostic first, and then describe how they are bound to the HTTP transport. FGA mechanisms should be expressible at the JSON-RPC level for transports and response patterns where HTTP headers are unavailable.

- **Status:** Proposed (discussed in Week 3 meeting, directionally agreed)
- **Source:** Week 3 meeting
- **Rationale:** HTTP is often our primary focus, but both STDIO and HTTP are first-class transports. There will be other transports as extensions in the future. We should aim to describe mechanisms that solve the stated problems first, then map them to a transport.
## Building Blocks
### D7: Structured Denials as a building block is the first priority
When a tool call or resource read fails due to authorization, the MCP server returns a structured denial with a machine-readable reason and zero or more typed remediation hints. Don't (yet?) include RAR, CIBA, additional or one-time tokens - build the foundation first.

- **Status:** Ratified
- **Source:** Week 2 meeting, refined in weeks 2–3
- **Rationale:** Without structured denials, the MCP client receives a generic error and has no path to recovery. This is the foundation — all other building blocks have limited value without it.


# Interaction matrix

<!-- Tab ID: t.59fvzhwwy0q2 -->

# Interaction axes + matrix
This document identifies **three independent axes** that characterize an authorization interaction in MCP. One describes the **remediation process** (who or what resolves the denial?) and two describe the **remediation outcome** (what changes as a result?). Together they form a lens for classifying scenarios, identifying protocol gaps, and deciding what the WG needs to design.
## 0. Notes
**Blocking vs. non-blocking**: All scenarios in this document assume that the authorization decision is **blocking** (non-optional): A request cannot proceed without a positive authorization decision.

**Timing of remediation**: The timing of remediation can matter to the client: knowing whether to poll and retry, or defer work until later. This is not captured here, because the goal of the matrix is to capture the _nature_ of the remediation, not the timing of it. I think timing is important to represent, but on top of this foundation.


## 1. Process axis
This describes how the denial gets resolved at the highest level: does a human need to intervene, or can the client resolve it autonomously?
### Interactivity
<table><tr><td><b>Value</b></td><td><b>What it means</b></td><td><b>Example scenarios</b></td></tr><tr><td><b>Human required</b></td><td>A human must perform some action — click a link, approve a request, select a resource in a picker, enter credentials. The client's UX layer must surface the remediation to a person.</td><td>Google Picker, Dropbox Chooser, bank consent screen, Notion page sharing dialog, "ask your admin for access"</td></tr><tr><td><b>Machine-resolvable</b></td><td>The client (or agent) may resolve the denial programmatically with no human involvement.</td><td>Pre-configured policy grant, token exchange, machine-resolvable challenge</td></tr></table>

## 2. Outcome axes
These describe what the result of remediation looks like: what changed and how long it lasts.
### Resolution Mechanism
**Is the change that permits the action ****_only_**** on the server, or does the client also need to change its credentials?**

This axis determines _which part of the client architecture_ participates in remediation.

<table><tr><td><b>Value</b></td><td><b>What it means</b></td><td><b>Client outcome</b></td></tr><tr><td><b>Server-side state change only</b></td><td>Something changes on the server or an external service that now permits the action. The client's credentials are unchanged.</td><td>Client retries with the <b>same token</b>. Only the UX layer is involved (presenting URLs, showing messages) - if at all. The auth stack is uninvolved.</td></tr><tr><td><b>Client credential change</b></td><td>The client needs different or additional OAuth credentials — broader scopes, a one-time token, specific authorization_details.</td><td>Client retries with a <b>different token</b>. The auth stack must do real work (new OAuth flow, token exchange, manage token lifecycle, etc).</td></tr></table>### Grant Duration
**Is the resulting access one-shot or time-limited, or does it persist until explicitly revoked?**

This axis determines how the client and server should handle the lifecycle of the permission.

<table><tr><td><b>Value</b></td><td><b>What it means</b></td></tr><tr><td><b>Ephemeral</b> (single-use or time-limited)</td><td>The resulting access is one-shot, single-use, or has a short TTL. After it's consumed or expires, the client is back to its previous authorization state.</td></tr><tr><td><b>Durable</b> (persistent)</td><td>The resulting access persists until explicitly revoked. The authorization state has permanently changed.</td></tr></table>### Outcome matrix
<table><tr><td><b></b></td><td><b>Ephemeral</b></td><td><b>Durable</b></td></tr><tr><td><b>Server-side</b></td><td>Single-operation approval. Server requests confirmation for a specific bank payment.</td><td>Google Picker (user selects a file, app gains persistent access). Notion page sharing. Admin grants access. GitHub org admin approves a fine-grained PAT.</td></tr><tr><td><b>Client credential</b></td><td>TrueLayer resource token: a single-use, per-payment token separate from the baseline access token. PSD2 payment authorization.</td><td>Current MCP WWW-Authenticate scope challenge: client re-authorizes with broader scopes and gets a new token that replaces the old one.</td></tr></table>
## 2a. A nuance on client credential change
The "client credential change" row is not uniform. It actually has a sub-distinction that the week 3 meeting circled around:

<table><tr><td><b>Variant</b></td><td><b>Description</b></td><td><b>Client complexity</b></td><td><b>Example</b></td></tr><tr><td><b>Replaced token</b></td><td>A new token supersedes the old one. Client manages one token slot; the value changes.</td><td>Low</td><td>WWW-Authenticate scope challenge today</td></tr><tr><td><b>Additional token</b></td><td>Client holds <i>both</i> the original token and a new one-time token: two concurrent tokens for the same connection.</td><td>High</td><td>TrueLayer resource token, PSD2 payment authorization</td></tr></table>
One of the things the WG must decide is whether to recommend that MCP require clients to handle multiple tokens (the "additional token" variant). The full matrix below helps put this decision into context: which scenarios are blocked on it?


## 5. Full interaction matrix
The three axes produce 2×2×2 = 8 cells. This collapses the earlier sync/async splits into single rows focused on authorization mechanics rather than client wait strategy.

<table><tr><td><b>#</b></td><td><b>Interactivity</b></td><td><b>Resolution</b></td><td><b>Duration</b></td><td><b>Example Scenarios</b></td><td><b>Proposed Mechanism</b></td></tr><tr><td>A1</td><td>Human</td><td>Server-side</td><td>Durable</td><td>Google Picker; Dropbox Chooser; Notion page sharing; "ask your admin for access"; GitHub org admin PAT approval</td><td>Structured denial, url or message</td></tr><tr><td>A2</td><td>Human</td><td>Server-side</td><td>Ephemeral</td><td>Destructive operation consent; bank payment consent (server records per-payment approval)</td><td>TBD</td></tr><tr><td>A3</td><td>Human</td><td>Client cred</td><td>Durable</td><td>WWW-Authenticate scope challenge</td><td>✅ Already exists</td></tr><tr><td>A4</td><td>Human</td><td>Client cred</td><td>Ephemeral</td><td>PSD2 payment authorization; one-time token after human approval</td><td>TBD</td></tr><tr><td>A5</td><td>Machine</td><td>Server-side</td><td>Durable</td><td>Pre-configured policy grant; out-of-band approval grants durable access</td><td>Structured denial or CIBA?</td></tr><tr><td>A6</td><td>Machine</td><td>Server-side</td><td>Ephemeral</td><td>Server-side cooldown expires; out-of-band approval for a specific operation creates a time-limited grant</td><td>TBD / CIBA?</td></tr><tr><td>A7</td><td>Machine</td><td>Client cred</td><td>Durable</td><td>Token exchange for elevated scopes; out-of-band approval yields elevated token</td><td>TBD / CIBA?</td></tr><tr><td>A8</td><td>Machine</td><td>Client cred</td><td>Ephemeral</td><td>Token exchange for a one-time token; out-of-band approval yields one-time token</td><td>TBD / CIBA?</td></tr></table>
Most real-world systems today are in the **human + server-side** columns. The proposed Structured Denials concept covers the human + server-side well. The **ephemeral** column and the **machine-resolvable** rows are where the protocol has gaps.


# Building blocks

<!-- Tab ID: t.mscn75ixc2yt -->

## Nate's thoughts on initial building blocks
These four building blocks are ordered roughly by priority and dependency. Building Block 1 is the foundation — without structured denials, the others have limited value. Building Blocks 2–4 are independent of each other and could be designed in parallel.
None of these building blocks require the protocol to understand or model authorization policies. They provide mechanism, not semantics. The server remains the authority on what access means; the protocol provides structured ways to communicate about it.

### Structured Denials with Typed Remediation
When a tool call or resource read fails due to authorization, the server MAY return a machine-readable denial with a list of one or more typed remediation hints. Each hint indicates:
- A **type** – starting with **URL** and **message** (extensible in the future - JAG? RAR?)****
- Whether the remediation is **synchronous or asynchronous**
The client can use this information to decide how to present the failure and recovery options to the user or agent.
**Concrete example — Google Drive:** An MCP server wrapping Google Drive receives a tools/call: read_file for a file the user hasn't picked yet. Today, this returns a generic error. With structured denials, the server returns a denial with a URL remediation hint pointing to the Google Picker, marked as synchronous. The client presents the Picker link to the human. When the human finishes selecting files, the ElicitationCompletedNotification fires and the client retries.
A second remediation hint of type message could say "Or ask the file owner to share it with you" (asynchronous), giving the client and user a choice.

### Authorization Characteristics as Tool Metadata
Tool definitions MAY optionally declare an interactionRequiredHint (always, sometimes, never) indicating whether human interaction is needed for authorization. This is static metadata communicated at tool list time, not a runtime check. It gives clients — especially agentic clients — a signal for planning: "should I even attempt this without a human present?"
**Concrete example — TrueLayer (Open Banking):** A TrueLayer MCP server's create_payment tool declares interactionRequiredHint: "always". Every payment requires the user to authorize it through their bank's consent screen — there is no way to skip this. An autonomous agent building a multi-step plan sees this hint and knows it must pause and involve the human before executing any payment step. Without the hint, the agent would discover this only after creating the payment and receiving an authorization_required denial, wasting a round trip and potentially confusing its planning.

**Example 2 – Do I have the scopes I need for this tool call?** Client and agent developers are unhappy with the UX of calling a tool and not knowing whether it will require a WWW-Authenticate scope challenge or a URL elicitation challenge before it can run. A server that knows a particular client **does** have the necessary scopes for a given tool can return interactionRequiredHint: never for that tool's metadata.

### "Configure Authorization" Affordance
The server MAY advertise a "configure access" URL where the user can manage the access boundary for this server. This is a pointer, not a mechanism — the configuration UI, the policy model, and the enforcement are entirely owned by the service.
**Concrete example — GitHub:** A GitHub MCP server advertises a configure-access URL pointing to the GitHub App installation settings page. When a user wants to constrain their agent to only operate on certain repositories, the client can surface this link: "You can configure which repositories can be accessed by this client." The user clicks through to GitHub's UI, adjusts the repository selection or permissions, and the server's access boundary changes accordingly — without MCP needing to understand anything about GitHub's permission model.

### Resource Discovery Model
The server MAY advertise its resource discovery model for MCP resources along two dimensions: (a) how complete its resource enumeration is (all, bounded, or none), and (b) optionally, a text description of the shape of its access boundary. Both are hints — neither is required, and the client must always be prepared for the server to say nothing.
**Concrete example — Notion:** A Notion MCP server advertises resourceEnumerationHint: "bounded" — it can list pages, but only those the user has explicitly shared with the integration. The client knows that resources/list will not return **all** of the user's Notion pages, only the currently-accessible subset. If the user asks "what else is in my Notion workspace?", the client understands that interactive discovery (asking the user to share more pages in Notion's UI) is needed to expand the set — it won't find more pages by paginating resources/list. 



# Meeting notes 2025-01-28

<!-- Tab ID: t.4que45gs6yez -->

**Do we need to define how permissions/authorization are modeled?**No: We are not trying to write "Zanzibar paper v2". How authorization is modeled in a system is not our concern.
We are primarily concerned with the mechanism of: how does a client ask for permission (if necessary), and most importantly how does a server **say no**. And how does a client recover, either interactively or non-interactively.
Can the client proactively prevent the server from saying no?
What does resource discovery look like?
How much do we really need to care about representing the permissions themselves (ideally not much)? 
What is a non-interactive way to make authorization decisions in an enterprise IDP context? This speaks to two axes in general in MCP: is a human in the loop? is an enterprise IDP in the loop?

Action items:
- Nate: Check in on tool scopes WG and catch up with Sam @ Github
- 


# Meeting notes 2025-02-11

<!-- Tab ID: t.mn3tkhk5zrn8 -->

## Meeting notes
- Discuss "Building blocks" ideas along these axes: **interactive vs. non-interactive**

**Structured Denials with Typed Remediation**
Discussion:
- Could the existing signal of 401/WWW-Authenticate be reused to get someone into a web flow? (reuse the authorization flow to "bootstrap" someone into whatever URL I need them to go to)
- Consider the AuthZen sec 5.5.1 (decision object) - includes context about what the client can do
- How "dumb" will MCP clients actually be? Can they actually take any action besides sending the human to a URL?
  - Hypothetically the LLM could remediate some things, if the server allowed it
- What is the purpose of authorization?
  - Not just about user consent; it is about whether the an action should complete in the current context 


Max: Useful to think about how much each party actually needs to know:
- Specification: does not need to understand anything about the authorization model; protocol is generic
- MCP server: full knowledge of the "underlying" authorization model
- Client: This is the interesting spot! How much of the authorization model needs to be communicated to the client?
  - Atul: Client needs to know how the server will make the authorization decision – but how much does it need to know?

Simon: Calling out again that there is huge overlap between what we're discussing here and what's being discussed in the Tool Scopes WG. Need to discuss together!

# Meeting notes 2025-03-04

<!-- Tab ID: t.v3jdd5t96b74 -->

### Meeting notes 2025-03-04

Important WG scoping question: **Are we designing FGA mechanisms that assume HTTP semantics, or must they work over any MCP transport?** This is a consequential decision that the WG has not yet explicitly resolved. It affects everything downstream — the wire format for denials, how scope challenges work, and whether existing HTTP-native patterns (WWW-Authenticate) are sufficient.
- It is nice to say that we can be transport-agnostic, but many of the things we are discussing here are very tied to OAuth semantics (which are HTTP transports)
- Max: Two levels of what we define here in the WG
  - First level: what messages must be passed back and forth? (transport-agnostic)
  - Second level: how do the messages (fundamental building blocks) get mapped to a transport?
- Local server development is rough
  - Can’t convert a local STDIO server to a HTTP server easily because of dynamic port allocation making it hard to register localhost HTTP servers in desktop applications
  - Dynamic port allocation also works poorly with local servers packaged in Docker, since the port needs to be exposed in Docker as well
  - Only OAuth client callbacks handle dynamic ports well - everything else in the system does not
-  


Analyzing Monmohan's RAR proposal surfaced a fundamental architectural distinction that we should agree on as shared vocabulary. When a denial occurs, "how to resolve it" has two fundamentally different answers depending on what needs to change: **server-side state or client-side state (client credentials).** Notably, most of what we've discussed here so far is about server-side opaque state, and also notably the current scope challenge mechanism in MCP (WWW-Authenticate) is about the latter.
- Max disagrees with the naming: we will always be changing server state. A better distinction is between **short-lived access** and **long-lived access**. 
- Max: Can we (for example) model short-lived or long-lived access as a claim in the RAR payload, so that we can move the complexity to the AS/RS
  - Put the expiry on the permission/grant, not on the access token itself
  - Instead of making clients manage multiple access tokens (which OAuth has been having a hard time doing) - profile the RAR payload for MCP and for our usecases and always return a long-lived access token


**Review and discuss Monmohan's proposal** - specifically with an eye towards layering (what mechanisms could we ship today, what should be spun out as a separate mini-proposal)

# Appendix: Research on well known services

<!-- Tab ID: t.lrq4sp7x6fcz -->

# **Existing Systems (Fine-Grained Authorization in the Wild)**
This document surveys real-world systems that use OAuth for coarse-grained authorization but also implement fine-grained, resource-level access control through mechanisms that go beyond OAuth. The goal is to identify common patterns, pain points, and requirements that MCP's FGA mechanism will need to accommodate.

## **1. Evaluation Framework**
For each system we survey, we analyze it along several axes. These axes are chosen to surface the properties that matter most for MCP protocol design.
### **Axis 1: OAuth Scope Granularity**
How coarse or fine are the system's OAuth scopes?
<table><tr><td><b>Level</b></td><td><b>Description</b></td><td><b>Example</b></td></tr><tr><td>Coarse</td><td>A single scope grants access to an entire product surface</td><td>drive — full access to all files</td></tr><tr><td>Medium</td><td>Scopes are broken down by operation type but not by resource</td><td>drive.readonly — read all files, but can't write</td></tr><tr><td>Narrow</td><td>Scopes limit access to a subset of resources, but the subset is determined by a separate mechanism</td><td>drive.file — only files the app created or the user explicitly selected</td></tr></table>
In most real-world systems, even the narrowest OAuth scopes do not specify _which_ resources. The "which" is determined outside OAuth.
### **Axis 2: Resource Selection Mechanism**
How does the user (or system) decide _which_ specific resources the application can access?
<table><tr><td><b>Mechanism</b></td><td><b>Description</b></td><td><b>Relationship to OAuth</b></td></tr><tr><td>Implicit (scope-based)</td><td>The OAuth scope itself determines the resource set (e.g. "all repositories")</td><td>Inside OAuth</td></tr><tr><td>Consent-embedded selection</td><td>The OAuth consent screen itself includes a resource picker — the user selects specific resources as part of granting consent (e.g. Notion lets the user choose which pages to share during the OAuth flow)</td><td>Piggybacked on OAuth</td></tr><tr><td>Proprietary UI widget</td><td>A vendor-specific UI (picker, dialog) lets the user select resources after OAuth consent</td><td>Outside OAuth</td></tr><tr><td>Sharing/invitation model</td><td>Access is granted when another user shares a resource (e.g. sharing a doc)</td><td>Outside OAuth</td></tr><tr><td>API-based grant</td><td>The app calls an API to request access to a specific resource</td><td>Outside OAuth</td></tr><tr><td>Admin policy</td><td>An administrator pre-configures which resources the app can access</td><td>Outside OAuth</td></tr></table>### **Axis 3: Failure Signaling**
When an API call is denied due to insufficient fine-grained permissions, how does the system communicate that to the client?
We care about:
- HTTP status code — Is it 403? 404? Something else?
- Structured error body — Is there a machine-readable reason code?
- Remediation hint — Does the error tell the client _how_ to get access?
- Ambiguity — Can the client distinguish "you don't have permission" from "this resource doesn't exist"?
### **Axis 4: Access Remediation**
After a denial, what options does the client have to obtain access?
<table><tr><td><b>Approach</b></td><td><b>Description</b></td><td><b>Interactive?</b></td></tr><tr><td>Re-launch resource picker</td><td>App reopens a vendor-specific UI for the user to select resources</td><td>Yes (human required)</td></tr><tr><td>Request access</td><td>App or user sends an access request to the resource owner</td><td>Yes (human required, async)</td></tr><tr><td>Escalate OAuth scope</td><td>App triggers a new OAuth consent flow with broader scopes</td><td>Yes (human required)</td></tr><tr><td>Step-up authentication</td><td>App re-authenticates with a stronger factor</td><td>Yes (human required)</td></tr><tr><td>No remediation</td><td>Client cannot self-service; must contact an admin out-of-band</td><td>No path forward</td></tr></table>### **Axis 5: Resource Discovery**
Can the client learn what resources are available (or accessible) without already knowing their identifiers?
<table><tr><td><b>Level</b></td><td><b>Description</b></td></tr><tr><td>Full discovery</td><td>Client can list/search all resources visible to the user</td></tr><tr><td>Scoped discovery</td><td>Client can list only resources it already has access to</td></tr><tr><td>No discovery</td><td>Client must know resource identifiers in advance</td></tr></table>### **Axis 6: Temporal Scoping**
Can access be limited in duration, and at what granularity?
<table><tr><td><b>Level</b></td><td><b>Description</b></td></tr><tr><td>Token-level</td><td>Access lasts until the OAuth token (or refresh token) expires</td></tr><tr><td>Session-level</td><td>Access is scoped to a session and revoked when it ends</td></tr><tr><td>Grant-level</td><td>Individual resource grants can have their own expiration</td></tr><tr><td>Per-request</td><td>Each request is independently authorized (no persistent grant)</td></tr></table>### **Axis 7: Interaction Model Assumptions**
What does the system assume about who is driving the client?
<table><tr><td><b>Assumption</b></td><td><b>Implication</b></td></tr><tr><td>Human at the keyboard</td><td>Picker UIs, consent screens, and interactive flows are viable</td></tr><tr><td>Attended automation</td><td>An agent acts on behalf of a human who can be prompted when needed</td></tr><tr><td>Unattended automation</td><td>A service account or daemon with no human in the loop; all access must be pre-configured</td></tr></table>
## **2. Case Study: Google Drive**
Google Drive is a compelling first case study because it embodies many of the tensions MCP FGA needs to address: broad OAuth scopes coexisting with fine-grained per-file permissions, a proprietary resource selection mechanism (the Picker), and an access model that fundamentally assumes a human is present.
### **2.1 System Overview**
Google Drive's authorization has two layers:
- OAuth 2.0 scopes determine the _category_ of access (read-only, read-write, per-file, metadata-only).
- Per-file permissions (owner, editor, commenter, viewer) and Picker-based selection determine _which files_ the app can access.
These two layers are largely independent. An app with the drive scope can access any file the authenticated user can access. An app with the drive.file scope can only access files it created or that the user explicitly selected via the Google Picker.
### **2.2 OAuth Scopes**
<table><tr><td><b>Scope</b></td><td><b>Sensitivity</b></td><td><b>Description</b></td></tr><tr><td>drive.file</td><td>Non-sensitive</td><td>Files created by the app, or selected by the user via Picker</td></tr><tr><td>drive.metadata.readonly</td><td>Restricted</td><td>View metadata for all files</td></tr><tr><td>drive.readonly</td><td>Restricted</td><td>View and download all files</td></tr><tr><td>drive</td><td>Restricted</td><td>Full read-write access to all files</td></tr></table>Google classifies drive.file as non-sensitive specifically because it does not grant blanket access — the user retains control over which files are exposed, one at a time. The restricted scopes grant access to _all_ of a user's files and require additional review from Google during app verification.
Key observation: The narrow scope (drive.file) is essentially a capability _container_ — it says "the app may access _some_ files" but the scope itself does not say which ones. The "which" is a completely separate mechanism.
### **2.3 The Google Picker: Resource Selection Outside OAuth**
The Google Picker API is a JavaScript widget that renders a file browser inside the app's web page. The user navigates their Drive, selects one or more files, and the Picker returns the file IDs to the app.
How it works:
- The app obtains an OAuth access token with the drive.file scope.
- The app renders the Picker widget, passing it the access token.
- The user browses and selects files within the Picker UI (which is rendered by Google, not the app).
- The Picker returns the selected file IDs to the app via a JavaScript callback.
- The app can now use those file IDs with the Drive API. Google's backend has recorded that these files were "picked" for this app.
Critical properties:
- The access token does not change after the Picker interaction. The token still says drive.file; Google's backend tracks the per-file grants separately.
- The Picker is completely proprietary. There is no OAuth standard for "let the user select which resources to expose."
- The Picker requires a web browser and a human user. There is no API equivalent — an unattended service cannot invoke the Picker.
- File access granted via the Picker appears to be indefinite — it persists beyond the session and across token refreshes, until the user explicitly revokes it or the app's access is removed.
### **2.4 Analysis Against the Framework**
<table><tr><td><b>Axis</b></td><td><b>Google Drive</b></td></tr><tr><td>OAuth Scope Granularity</td><td>Ranges from coarse (drive) to narrow (drive.file), but even the narrow scope does not identify specific resources</td></tr><tr><td>Resource Selection</td><td>Proprietary UI widget (Google Picker). Completely outside OAuth.</td></tr><tr><td>Failure Signaling</td><td>HTTP 404 for resources the user can't access (same as GitHub — avoids confirming existence). HTTP 403 for permission-related errors where the resource is known to exist (e.g., wrong scope). JSON error body with reason and message fields, but no remediation URL or machine-readable "how to fix" hint.</td></tr><tr><td>Access Remediation</td><td>Re-launch the Picker (interactive, human required). Or escalate to a broader scope (new OAuth consent). No programmatic remediation.</td></tr><tr><td>Resource Discovery</td><td>With drive or drive.readonly: full discovery (list/search all files). With drive.file: scoped discovery only (can only see files already granted).</td></tr><tr><td>Temporal Scoping</td><td>Token-level for OAuth. Picker grants are indefinite (persist across sessions). No per-resource temporal scoping.</td></tr><tr><td>Interaction Model</td><td>Assumes a human at the keyboard. The Picker is a visual, interactive widget. No path for unattended automation under drive.file. Service accounts use domain-wide delegation (admin policy) instead.</td></tr></table>### **2.5 Implications for MCP**
#### **2.5.1 Structured Denials with Remediation**
Today, an MCP server can return an error to the client, but the client has no structured way to know _why_ it failed or _how to fix it_. "The human should open the Picker" is not expressible in MCP today.
Requirement: The protocol needs structured denial responses with a machine-readable reason, a typed remediation path (e.g., "navigate to URL", "request broader scope"), and whether remediation requires a human.
#### **2.5.2 Resource Selection as a First-Class Concept**
URL elicitation in MCP today _could_ direct the user to a Picker, but the client wouldn't know the semantics — it can't distinguish "select resources" from "complete a payment." There is also no callback to signal "selection is complete, retry now."
Requirement: Resource selection flows should be semantically distinct from generic URL elicitation, with retry signaling after completion.
#### **2.5.3 Discovery Model**
Under drive.file, the client can't list available files — it can only see files already granted. The only way to discover new files is the Picker, which is interactive. Under drive, discovery is trivial but grants far more access than desired.
Requirement: The server should be able to advertise its discovery model — whether the client can enumerate resources, whether enumeration requires broader permissions, and whether interactive discovery is available.
#### **2.5.4 Interaction Model Spectrum**
The Picker requires a human. An agent client cannot operate it, but needs structured metadata to ask its human operator to intervene. Pre-configured access (admin policy, service accounts) is the alternative for non-interactive clients.
Requirement: The server should signal which interaction model each remediation path requires: fully interactive, attended automation (agent escalates to human), or fully non-interactive (pre-configured access only).

## **3. Case Study: GitHub**
GitHub is an instructive counterpoint to Google Drive. Where Google Drive uses OAuth scopes as a meaningful gate and supplements them with a proprietary Picker, GitHub's recommended authorization model — fine-grained personal access tokens — puts resource selection entirely at token creation time, and the real authorization is an entirely server-side permission model that the token holder cannot inspect. GitHub is also notable because a production MCP server already exists, giving us a concrete example of how (and where) the FGA gap manifests in practice.
_Note: GitHub also has a legacy "classic" OAuth model with extremely coarse scopes (e.g., __repo__ = full access to all repos). This model is effectively deprecated; we focus on fine-grained PATs as the recommended pattern._
### **3.1 System Overview**
GitHub's authorization has three layers, each increasingly fine-grained:
- Token permissions and repository selection determine the _ceiling_ of what the token can do — which repos, and what operations.
- GitHub's server-side permission model (repository collaborator status, organization membership, team roles, repository visibility) determines the _actual_ access for a given user.
- Context-specific rules (branch protection, required reviews, CODEOWNERS, SAML/SSO enforcement) further constrain what actions are allowed even when the user has nominal access.
The critical insight: layers 2 and 3 are completely invisible to the token holder. A fine-grained PAT configured with "Contents: read-write" on a repo looks identical whether the underlying user is a repo admin or has been removed as a collaborator since the token was created.
### **3.2 Fine-Grained Personal Access Tokens**
Fine-grained PATs are GitHub's recommended authorization model. They combine resource selection and permission scoping into a single token configuration step:
- Repository selection: At token creation time (in GitHub's web UI), the user selects _specific repositories_ (or "all repositories") the token can access.
- Granular permissions: 50+ permissions (e.g., "Issues: read", "Pull requests: write", "Contents: read") each set to "no access", "read", or "read and write".
- Org admin approval: Organizations can require administrator approval before a fine-grained PAT can access org resources. This is an async approval workflow — the token is created but non-functional until an admin approves it.
- Mandatory expiration: Fine-grained PATs must have an expiration date (max 1 year).
This is a form of resource selection at token creation time — the user narrows the token's access to specific repos and specific operations before the token is ever used. Notably, this happens entirely in GitHub's web UI, not through any OAuth protocol mechanism. The token itself is opaque — the holder cannot inspect it to determine which repos or permissions it covers.
### **3.3 Server-Side Permission Model**
Even with a perfectly configured fine-grained PAT, every API request is checked against GitHub's server-side authorization:
- Repository visibility: Public repos are accessible to anyone; private repos require collaborator access or org membership.
- Collaborator roles: Owner, Admin, Write, Triage, Read — each with different operation permissions.
- Organization membership: Org members may have default access to org repos, or access may require explicit grants.
- Team-based access: Teams can be granted access to specific repos with specific roles.
- SAML/SSO enforcement: Orgs using SAML can require that tokens be explicitly authorized for SSO.
- Branch protection / rulesets: Even a user with "write" access may be blocked from pushing to main without a PR.
None of this is expressed in or visible through the token. The token says "Contents: read-write on repos X, Y, Z"; the server decides whether the specific operation on the specific resource is actually allowed given the user's current relationship to that resource.
### **3.4 Failure Signaling: The 404 Problem**
Like Google Drive, GitHub returns 404 Not Found rather than 403 Forbidden for private resources the caller can't access — a deliberate security choice to avoid confirming resource existence. This appears to be an industry-standard practice for systems with private resources.
Where GitHub differs from Google Drive is in how 403 is used:
- 404 Not Found: Private repositories, files, or other resources the token cannot access. Indistinguishable from genuinely non-existent resources.
- 403 Forbidden: Rate limiting, SAML/SSO enforcement failures, operations blocked by policy (e.g., branch protection preventing a direct push). These are cases where the resource is _known_ to the caller but the specific operation is blocked.
- There is no remediation hint in either response. The client cannot determine what, if anything, it could do to gain access.
### **3.5 The GitHub MCP Server in Practice**
The GitHub MCP server is one of the most widely used MCP servers today (~27K GitHub stars). Examining how it handles authorization reveals the current state of the FGA gap.
Authentication options:
- Remote server: Uses OAuth 2.1 with PKCE, implementing RFC 9728 (Protected Resource Metadata). Returns HTTP 401 with a WWW-Authenticate header pointing to the authorization server.
- Local server: Uses fine-grained PATs passed as environment variables.
Authorization approach:
- Beyond basic authentication, the server simply passes through GitHub API responses. If the GitHub API returns 404 for a private repo the token can't access, the MCP server surfaces that as a tool error.
- There is no FGA-aware negotiation. The server cannot tell the client "you don't have access to this repo, but you could request access" or "your token doesn't include this repo — you'd need to create a new token" or "this repo requires SSO authorization for your token."
Toolset-level gating: The server has a separate mechanism for controlling which _tools_ are available (not which _resources_):
- --read-only mode removes all write tools.
- --toolsets flag enables/disables categories of tools (repos, issues, pull_requests, etc.).
- --lockdown-mode filters out content from untrusted users in public repos.
- Dynamic tool discovery lets the host list and enable toolsets on demand.
This is _tool-level_ authorization, not _resource-level_ authorization. The server can say "you can't use the create_pull_request tool at all" but it cannot say "you can use create_pull_request on repo A but not repo B."
### **3.6 Analysis Against the Framework**
<table><tr><td><b>Axis</b></td><td><b>GitHub</b></td></tr><tr><td>OAuth Scope Granularity</td><td>N/A in the traditional sense. Fine-grained PATs replace OAuth scopes with per-repo, per-permission configuration. The "scope" is the set of (repo, permission) pairs selected at token creation.</td></tr><tr><td>Resource Selection</td><td>At token creation time — user selects specific repos in GitHub's web UI. This is a one-time, pre-session decision. Changing the resource set requires creating a new token.</td></tr><tr><td>Failure Signaling</td><td>Deliberately ambiguous. 404 for inaccessible private resources (not 403). No remediation hints. No machine-readable "why" or "how to fix."</td></tr><tr><td>Access Remediation</td><td>Create a new token with the needed repo (human, out-of-band). Request access from repo owner (async, human). Ask org admin to approve fine-grained PAT (async, human). Authorize token for SSO (interactive, human). No programmatic remediation path.</td></tr><tr><td>Resource Discovery</td><td>Full discovery <i>within</i> the token's access: can list/search all repos the token can see. But cannot discover repos that exist but are inaccessible (they return 404).</td></tr><tr><td>Temporal Scoping</td><td>Fine-grained PATs have mandatory expiration (max 1 year). No per-resource temporal scoping.</td></tr><tr><td>Interaction Model</td><td>Primarily attended automation: a human creates and configures the token, then automation (or an agent) uses it. Can also support unattended automation if the token is pre-provisioned.</td></tr></table>### **3.7 Implications for MCP**
#### **3.7.1 Ambiguous Denial**
GitHub returns 404 for inaccessible private resources, making it impossible to distinguish "doesn't exist" from "not authorized." The MCP server likely cannot resolve this ambiguity.
Requirement: The protocol must accommodate ambiguous/opaque denial — allowing the server to say "access denied, reason unknown or undisclosed." The client should not assume every 404 is a permanent, non-remediable failure.
#### **3.7.2 Opaque Authorization Models**
A fine-grained PAT configured with "Contents: read-write" is only a _ceiling_, not a _grant_. Whether an operation succeeds depends on server-side checks (collaborator status, org policies, branch protection, SSO) that are invisible to the token holder.
Requirement: The protocol should not assume token configuration maps to actual access. FGA must work when the server's authorization model is completely opaque to the client.
#### **3.7.3 Out-of-Band and Async Remediation**
Expanding a PAT's access requires creating a new token in GitHub's web UI. Org admin approval may add hours or days of delay. These are out-of-band, asynchronous processes.
Requirement: The protocol should support out-of-band administrative remediation as a structured type — distinct from "navigate to this URL now." The client needs to know this isn't resolvable immediately.
#### **3.7.4 Resource-Level Constraints Alongside Tools**
The GitHub MCP server controls which _tools_ are available but cannot express which _resources_ each tool can operate on. The client only learns about resource-level restrictions when a call fails.
Requirement: Servers should be able to optionally advertise resource-level constraints alongside tool availability — e.g., "this tool operates on repositories; here are the ones you can access."

## **4. Case Study: Dropbox**
Dropbox introduces a model where resource selection is completely decoupled from the app's OAuth session. The Dropbox Chooser — a proprietary UI widget — operates using the end-user's own Dropbox web session, not the app's access token. Dropbox also introduces ephemeral, per-resource access (direct links that expire after 4 hours).
### **4.1 System Overview**
Dropbox's authorization has two largely independent tracks:
- OAuth 2.0 with scoped permissions governs API access. Scopes are organized by API area and action (e.g., files.content.read, files.content.write, sharing.read). Content access level — App Folder (only the app's own folder within /apps) or Full Dropbox (all user files) — is set at app registration time and cannot be changed at runtime.
- Pre-built components (Chooser, Saver, Embedder) provide file selection and interaction without requiring the app's OAuth token at all. These components rely on the user's own authenticated Dropbox web session.
These two tracks can operate independently. An app can use the Chooser to let a user select files without the app having any OAuth API access to Dropbox. Conversely, an app with Full Dropbox OAuth access has no need for the Chooser — it can enumerate and access files directly via the API.
### **4.2 OAuth Scopes and Content Access**
Dropbox's OAuth scopes are organized by API surface area:
<table><tr><td><b>Area</b></td><td><b>Example Scopes</b></td><td><b>Description</b></td></tr><tr><td>Account</td><td>account_info.read</td><td>Read account name, email, etc.</td></tr><tr><td>Files</td><td>files.content.read, files.content.write, files.metadata.read</td><td>Read/write file contents, read metadata</td></tr><tr><td>Sharing</td><td>sharing.read, sharing.write</td><td>Access shared folders and links</td></tr><tr><td>Team (Business API)</td><td>team_info.read, members.read, team_data.member</td><td>Team-level administration</td></tr></table>Layered on top of scopes is a content access level selected at app creation:
- App Folder: The app can only access files within its own dedicated folder (/Apps/<app-name>/). Suitable for apps that manage only their own content.
- Full Dropbox: The app can access all files in the user's Dropbox, subject to the scopes granted.
This content access level is an app-level architectural constraint — it is baked into the app registration and cannot be escalated at runtime. An App Folder app that discovers it needs broader access must be re-registered as a Full Dropbox app.
Key observation: Content access level functions as a hard ceiling set by the developer at registration time, not by the user at authorization time. The access boundary is invisible to the OAuth flow itself.
### **4.3 The Chooser: Sessionless Resource Selection**
The Dropbox Chooser is a JavaScript component (with deprecated Android and iOS equivalents) that lets users select files from their Dropbox within the context of a third-party app.
How it works:
- The app embeds Dropbox's JavaScript SDK (dropins.js) with its app key.
- The app triggers the Chooser — either via a styled button (Dropbox.createChooseButton(options)) or directly from code (Dropbox.choose(options)). The Chooser must be triggered from a user gesture (click/tap) or the browser will block the pop-up.
- A pop-up window opens showing the user's Dropbox. The user is authenticated via their own Dropbox web session — no app OAuth token is involved.
- The user browses and selects files. The app can constrain selection via options: file extensions, size limits, single vs. multi-select, files vs. folders.
- The Chooser returns file metadata to the app via a JavaScript success callback.
Critical properties:
- No OAuth token involved. The Chooser uses the end-user's own Dropbox web session. The app does not need — and the Chooser does not use — any OAuth access token. This means an app can let users select Dropbox files without having any API access to Dropbox at all.
- Returns links, not API access. The Chooser returns URLs to the files, not grants that allow subsequent API calls. The app receives a link it can use to download or preview the file, but this does not grant the app's OAuth token permission to access that file via the Dropbox API.
- Two link types with very different lifetimes:
  - Preview links point to a human-readable preview page. They are persistent (do not expire), but the user can revoke them. They are for sharing, not programmatic access.
  - Direct links point to the raw file content and support CORS for client-side JavaScript access. They expire after 4 hours. They are meant for immediate download.
- The Chooser is interactive-only. It opens a pop-up window and requires a human to browse and select files. There is no programmatic equivalent.
- The Chooser is sessionless from the app's perspective. The app doesn't know or control the user's Dropbox session. If the user is not signed into Dropbox, they'll be prompted to sign in within the pop-up.
### **4.4 The Dual-Track Model**
Dropbox has two largely parallel access models:
<table><tr><td><b>Track</b></td><td><b>Mechanism</b></td><td><b>What It Grants</b></td><td><b>Requires OAuth Token?</b></td></tr><tr><td>API track</td><td>OAuth 2.0 scopes + content access level</td><td>API access to files (read, write, list, search)</td><td>Yes</td></tr><tr><td>Component track</td><td>Chooser / Saver / Embedder</td><td>Links to specific files selected by the user</td><td>No (uses user's web session)</td></tr></table>An app may use either or both. Resource selection and API authorization are entirely independent systems.
### **4.5 Temporal Scoping: Ephemeral Per-Resource Access**
Dropbox has multiple temporal scoping levels:
<table><tr><td><b>Access Type</b></td><td><b>Lifetime</b></td></tr><tr><td>OAuth access token</td><td>Short-lived (hours); refresh tokens available for offline access</td></tr><tr><td>Chooser preview link</td><td>Persistent until user revokes</td></tr><tr><td>Chooser direct link</td><td>4 hours</td></tr><tr><td>API-accessed files (Full Dropbox)</td><td>As long as OAuth token/refresh token is valid</td></tr><tr><td>API-accessed files (App Folder)</td><td>As long as OAuth token/refresh token is valid</td></tr></table>The 4-hour expiration on direct links is notable: it is a per-resource temporal scope that is shorter than the session. If an MCP client receives a direct link from the Chooser and stores it, the link will silently stop working after 4 hours. The Chooser documentation explicitly warns: "make sure to download the contents of the file immediately after the file is chosen."
### **4.6 Analysis Against the Framework**
<table><tr><td><b>Axis</b></td><td><b>Dropbox</b></td></tr><tr><td>OAuth Scope Granularity</td><td>Medium. Scopes are broken down by API area and action (e.g., files.content.read). Content access level (App Folder vs. Full Dropbox) adds an additional constraint, but is set at app registration, not at authorization time.</td></tr><tr><td>Resource Selection</td><td>Proprietary UI widget (Chooser), completely outside OAuth. Uniquely, the Chooser does not use the app's OAuth token — it operates on the user's own Dropbox session. Returns links, not API access grants.</td></tr><tr><td>Failure Signaling</td><td>HTTP 409 Conflict for path-related errors (Dropbox's convention for operations that fail due to path issues — e.g., file not found, no permission). Structured JSON error bodies with machine-readable error tags. HTTP 403 for OAuth scope violations. No remediation hints.</td></tr><tr><td>Access Remediation</td><td>Re-invoke the Chooser (interactive, human required). Or use the API track with appropriate scopes (requires OAuth setup). Cannot escalate from App Folder to Full Dropbox at runtime — requires re-registration.</td></tr><tr><td>Resource Discovery</td><td>With Full Dropbox + files.content.read: full discovery (list/search). With App Folder: scoped to the app's folder. Via the Chooser: interactive discovery through the user's full Dropbox (independent of the app's API access).</td></tr><tr><td>Temporal Scoping</td><td>Multiple levels: token-level (OAuth), per-resource ephemeral (direct links expire in 4 hours), per-resource persistent (preview links until revoked).</td></tr><tr><td>Interaction Model</td><td>Chooser assumes a human at the keyboard (pop-up dialog). API track can support unattended automation if configured with Full Dropbox access and refresh tokens.</td></tr></table>### **4.7 Implications for MCP**
#### **4.7.1 Access Types: Capabilities vs. Artifacts**
The Chooser returns URLs — not API permission grants. The link works without any token and can be used to download content, but it does not grant the app's OAuth token access to the file via the API. This is a fundamentally different access model from systems where selection grants ongoing API access.
Requirement: The protocol should distinguish capability-based access (ongoing API operations on a resource) from artifact-based access (a time-limited link or content blob). Resource selection does not always result in persistent, programmatic access.
#### **4.7.2 Ephemeral Resource Grants**
Direct links expire after 4 hours with no warning. An MCP client that stores a link will encounter silent failures. There is no structured way to communicate "this access will expire" or "this access has expired, re-invoke the Chooser."
Requirement: The protocol should support ephemeral grants with explicit expiration metadata — whether access is ephemeral or persistent, when it expires, and how to renew it.
#### **4.7.3 Hard Architectural Constraints**
App Folder vs. Full Dropbox is set at app registration and cannot be changed at runtime. There is no remediation path within the session.
Requirement: The server should be able to signal non-remediable architectural constraints — access boundaries that are permanent and inherent to the app's registration.
#### **4.7.4 Parallel Discovery Models**
The Chooser provides interactive discovery of the user's entire Dropbox, even when the app's API access is limited to the App Folder. The user can see and select files the app cannot access programmatically.
Requirement: The protocol should accommodate systems where interactive discovery is broader than programmatic discovery.

## **5. Case Study: Notion**
Notion introduces resource selection embedded directly in the OAuth consent flow. When a user authorizes a public Notion integration, the OAuth consent screen itself includes a page picker — the user selects which pages and databases to share as part of granting consent. It is resource selection _inside_ the OAuth handshake.
Notion also provides a contrasting model for internal (single-workspace) integrations, where resource selection is a fully manual, per-page process that happens outside any OAuth flow entirely.
### **5.1 System Overview**
Notion has two integration types with fundamentally different authorization models:
- Internal integrations are tied to a single workspace. They use a static API token (not OAuth). Access to pages is granted manually: a user navigates to a Notion page, opens the "Add connections" menu, and explicitly shares the page with the integration. No OAuth flow, no consent screen, no resource picker — just direct, per-page, user-initiated sharing.
- Public integrations use OAuth 2.0. The consent flow includes a built-in page picker where the user selects which workspace pages the integration can access. The integration receives an access token scoped to those pages.
Both models share a core principle: the integration can only access pages explicitly shared with it. There is no "full workspace access" scope. Even after authorization, an integration cannot see pages it hasn't been granted access to.
### **5.2 Public Integration OAuth Flow**
The public integration auth flow is standard OAuth 2.0 with one significant addition — resource selection is part of the consent screen:
- The app redirects the user to Notion's authorization URL.
- Notion displays a consent screen showing the integration's capabilities (read content, update content, insert content, etc.).
- The user clicks "Select pages" and a page picker opens — rendered by Notion, not the app.
- The user selects specific pages and databases. Selecting a parent page automatically grants access to all child pages (hierarchical inheritance).
- The user clicks "Allow access" and is redirected to the app's redirect URI with an authorization code.
- The app exchanges the code for an access token.
Critical properties:
- Resource selection is part of the OAuth flow, not a separate step. The user selects pages during consent, and if they don't complete the flow, the integration gets no access at all.
- The page picker only shows pages where the user has full access. A user cannot share a page they only have read access to.
- Access is per-user. Each workspace member who wants to use a public integration must individually go through the auth flow. One user's authorization does not extend to other members.
- Capabilities are fixed at integration creation time. The developer declares what the integration can do (read, update, insert content; read, insert comments) when creating the integration. These are not OAuth scopes the user selects — they are developer-declared and presented to the user as information, not choices.
- No "all pages" option exists. There is no equivalent of Google Drive's drive scope or Dropbox's "Full Dropbox." The integration always accesses only explicitly selected pages.
### **5.3 Internal Integrations: Manual Page Sharing**
For internal integrations, resource selection is entirely manual and out-of-band:
- A workspace admin creates the integration and receives a static API token.
- To grant the integration access to a page, a user navigates to that page in Notion, opens the ••• menu, scrolls to "Add connections," and selects the integration.
- The integration can now access that page (and its children) via the API.
This is a sharing/invitation model — the same conceptual pattern as sharing a Google Doc with someone, but applied to an API integration rather than a human user. There is no OAuth flow, no picker, and no way for the integration to request access programmatically.
### **5.4 Template-Based Access Bootstrapping**
Public integrations can optionally provide a Notion template. During the auth flow, the user is offered a choice: duplicate the template into their workspace, or select existing pages. If the user duplicates the template:
- A new page is created in their workspace (a copy of the template).
- The integration is automatically granted access to that new page.
- The token response includes a duplicated_template_id so the integration knows which page was created.
This is a "create-and-grant" pattern — the integration bootstraps its own resource to work with, sidestepping the chicken-and-egg problem of needing to know which pages exist before selecting them. It is the only pattern in our survey where the authorization flow _creates_ a resource rather than selecting an existing one.
### **5.5 Analysis Against the Framework**
<table><tr><td><b>Axis</b></td><td><b>Notion</b></td></tr><tr><td>OAuth Scope Granularity</td><td>Not applicable in the traditional sense. Capabilities (read, update, insert) are fixed at integration creation. There are no user-selectable scopes. The "scope" is the set of pages selected during consent.</td></tr><tr><td>Resource Selection</td><td>Consent-embedded selection (public integrations) — the OAuth consent screen includes a page picker. Manual sharing (internal integrations) — users add the integration to pages one at a time.</td></tr><tr><td>Failure Signaling</td><td>API returns errors when the integration accesses pages it hasn't been shared with. No structured remediation hints — the fix is always "share the page with the integration."</td></tr><tr><td>Access Remediation</td><td>For public integrations: user can update page access in Notion's settings at any time (not via re-running OAuth). For internal integrations: user manually adds the integration to more pages. No programmatic remediation.</td></tr><tr><td>Resource Discovery</td><td>Scoped discovery only — the integration can search and list only pages that have been explicitly shared with it. No way to discover pages that exist but haven't been shared.</td></tr><tr><td>Temporal Scoping</td><td>Token-level. Access tokens are short-lived with refresh tokens for ongoing access. Page-level grants persist until the user removes the connection.</td></tr><tr><td>Interaction Model</td><td>Public integrations: human in the loop during initial consent (page picker), then automation. Internal integrations: human-driven per-page sharing, then automation. Neither supports fully unattended resource selection.</td></tr></table>### **5.6 Implications for MCP**
#### **5.6.1 Consent-Embedded Resource Selection**
Notion's OAuth consent screen _is_ the resource picker — there is no separate step for the MCP client to manage. However, access is frozen at consent time. Expanding access later requires the user to manually add pages in Notion's settings — re-running OAuth won't re-show the picker.
Requirement: The protocol should accommodate systems where expanding access requires out-of-band user action in the vendor's UI — distinct from re-running OAuth and distinct from a standalone picker.
#### **5.6.2 Hierarchical Resource Grants**
Selecting a parent page grants access to all child pages. The accessible set can grow without re-authorization as the user adds children under already-shared parents.
Requirement: The protocol should express that access grants may be hierarchical — access to a resource may implicitly include subordinate resources, and the set may grow dynamically.
#### **5.6.3 The Create-and-Grant Pattern**
Notion's template duplication creates a new resource and grants access in a single step, sidestepping the discovery problem entirely.
Requirement: The protocol should accommodate flows where the authorization process creates resources, not just selects existing ones.
#### **5.6.4 No Full-Access Scope**
Notion has no "access everything" scope. The integration always operates on an explicit allowlist of pages, with no broad scope to escalate to.
Requirement: The protocol must work for systems where there is no broad-access fallback — the only escalation is "ask the user to share more resources."

## **6. Case Study: TrueLayer (Open Banking)**
TrueLayer's Payments API represents a fundamentally different model from the previous case studies: authorization of a single action (a payment) with specific parameters (amount, beneficiary), where the "resource" is created by the app and then authorized by the user before it takes effect.
This case study directly addresses two open questions from the overview:
Can we find public examples of OAuth flows authorizing a single request (e.g. authorizing creation of a single transaction once) as opposed to authorization of access to a single resource?
Can we find public examples of OAuth flows authorizing a user-controlled numeric variable of some kind — e.g. authorizing access to 10% of quota, or a fixed dollar amount, or a fixed amount of credits?
TrueLayer answers both. It follows UK/EU Open Banking standards, where regulatory requirements mandate explicit per-transaction consent.
### **6.1 System Overview**
TrueLayer's Payments API (v3) uses a two-phase authorization model:
- Server-to-server OAuth 2.0 with client_credentials grant and a payments scope. This token gives the app the ability to _create_ payment resources — but creating a payment does not execute it.
- Per-payment user authorization via bank consent screens. Each payment is created in an authorization_required state. The user must explicitly authorize that specific payment (amount, beneficiary) through their bank's consent UI before it executes.
The critical insight: the OAuth token grants the ability to propose actions, not to execute them. Execution requires per-instance human authorization that is bound to the specific parameters of the request.
### **6.2 The Two-Token Model**
TrueLayer uses two distinct tokens with very different semantics:
<table><tr><td><b>Token</b></td><td><b>How Obtained</b></td><td><b>What It Grants</b></td><td><b>Lifetime</b></td></tr><tr><td>Access token</td><td>OAuth 2.0 client_credentials with payments scope</td><td>Ability to create payment resources via the API</td><td>~1 hour</td></tr><tr><td>Resource token</td><td>Returned in the response when a payment is created</td><td>Authorization context for one specific payment; used to initiate the user consent flow</td><td>Short-lived, single-use</td></tr></table>The access token is a standard OAuth bearer token — it authenticates the app. The resource token is something different: it is a per-resource artifact that binds the authorization flow to a specific payment instance. The app cannot reuse a resource token for a different payment, and the resource token alone does not authorize anything — it is an input to the user consent flow.
### **6.3 The Payment Lifecycle**
The flow proceeds as follows:
- App authenticates — POST /connect/token with client_credentials grant and payments scope. Returns a standard access token.
- App creates a payment — POST /v3/payments with the access token. The request body specifies the amount, currency, beneficiary, and payment method. The API returns the payment resource with status: "authorization_required" and a resource_token.
- App initiates user authorization — POST /v3/payments/{id}/authorization-flow using the resource token. This kicks off the bank consent flow.
- User authorizes at their bank — The user is redirected to their bank's consent UI, where they see the exact payment details (amount, recipient) and explicitly approve. This authorization is at the bank level, not at TrueLayer's level.
- Payment executes — Once the user authorizes, the payment moves through Open Banking rails. The app monitors the payment status via polling or webhooks.
Critical properties:
- authorization_required is the normal state, not an error. Every payment goes through this state. It is the expected, designed-for flow — not a failure case that requires remediation.
- Authorization is bound to specific parameters. The user authorizes _this_ payment of _this_ amount to _this_ beneficiary. The authorization cannot be generalized or reused.
- The resource is created before it is authorized. The payment exists as an API resource in a pending state. The app creates it; the user authorizes it. This is the inverse of every other case study, where the resource exists first and the app requests access.
- Each payment requires its own authorization. There is no persistent grant. Authorizing payment A does not authorize payment B, even for the same amount to the same beneficiary.
- Authorization is regulatory, not discretionary. Open Banking regulations require per-transaction consent. This isn't a design choice the platform could change.
### **6.4 Analysis Against the Framework**
<table><tr><td><b>Axis</b></td><td><b>TrueLayer</b></td></tr><tr><td>OAuth Scope Granularity</td><td>Coarse. The payments scope grants the ability to create payment resources, but does not authorize any specific payment. The scope is essentially "this app is a payments app."</td></tr><tr><td>Resource Selection</td><td>Not applicable in the traditional sense. The app <i>creates</i> the resource (the payment), then the user authorizes it. There is no selection from existing resources.</td></tr><tr><td>Failure Signaling</td><td>authorization_required is an explicit, structured status on the payment resource — not an HTTP error code. It is the expected state, with a clear programmatic path forward (initiate authorization flow).</td></tr><tr><td>Access Remediation</td><td>User authorization flow (redirect to bank consent screen). This is the primary flow, not an exception case. If the user declines, the payment fails — there is no alternative remediation path.</td></tr><tr><td>Resource Discovery</td><td>Not applicable. The app creates payment resources; it does not discover or browse existing ones.</td></tr><tr><td>Temporal Scoping</td><td>Per-request. Each payment is independently authorized. The resource token is short-lived and single-use. There is no persistent grant that carries across payments.</td></tr><tr><td>Interaction Model</td><td>Requires human at the keyboard for each payment authorization. The bank consent screen is interactive and cannot be automated. The server-to-server OAuth token can be obtained non-interactively, but execution always requires a human.</td></tr></table>### **6.5 Implications for MCP**
#### **6.5.1 Authorization of Actions, Not Resources**
TrueLayer reframes authorization from "can this app access this resource?" to "can this app execute this action with these parameters?" In MCP, this maps to tool calls where specific arguments require per-invocation user consent.
Requirement: The protocol should support per-invocation authorization — calling a tool with specific arguments may require its own independent user authorization, bound to the arguments (not just the tool). This is distinct from tool-level and resource-level authorization.
#### **6.5.2 "Authorization Required" as a Normal State**
TrueLayer's authorization_required is the _designed, expected_ outcome of creating a payment — not a failure case. Every payment goes through this state.
Requirement: The protocol should support a two-phase commit model — the server responds with "action registered, authorization required" as a structured non-error intermediate state with a clear path forward.
#### **6.5.3 Parameter-Bound Consent**
The user authorizes _this specific payment_ of _this specific amount_ to _this specific beneficiary_. Changing any parameter requires new authorization. This directly answers the overview's question about authorizing numeric variables.
Requirement: Authorization may be bound to specific parameter values — not just to a tool or resource. This is a form of intent binding.
#### **6.5.4 No Persistent Grants**
Every payment is independently authorized — fully per-request, no state carried across invocations.
Requirement: The protocol must not assume authorization persists. Some systems grant indefinite access; others require fresh authorization for every action.

## **7. Future Case Studies**
The following systems are strong candidates for analysis using this same framework. Each exhibits different FGA patterns:
<table><tr><td><b>System</b></td><td><b>Why It's Interesting</b></td></tr><tr><td>Slack</td><td>Bot tokens scoped to channels; channel membership as implicit authorization; workspace admin policies</td></tr><tr><td>Microsoft Graph / OneDrive</td><td>Similar file-picker model to Google Drive but within the Microsoft ecosystem; "Files.ReadWrite.Selected" scope</td></tr><tr><td>Stripe</td><td>API keys with restricted permissions; connected accounts; authorization of specific financial operations</td></tr><tr><td>AWS IAM</td><td>Policy-based authorization with resource ARNs; assumed roles; temporary credentials; session policies</td></tr></table>Each of these will add new dimensions to the requirements list and help validate whether the framework captures the relevant distinctions.

## **8. Cross-Cutting Observations**
### **8.1 OAuth Scopes Are Necessary But Not Sufficient**
Every system we've surveyed uses OAuth scopes as a _first gate_, but none relies on scopes alone for resource-level authorization. The actual "which resources" decision happens through a mechanism the OAuth spec doesn't cover. In GitHub's case, the scopes are so coarse they are effectively a formality — repo is almost a binary "can you use the API at all" flag. Dropbox adds an extra layer: the content access level (App Folder vs. Full Dropbox) is an app-level constraint set at registration time, further illustrating that scopes alone don't capture the full access model. Notion goes furthest in decoupling "what can you do" from "where can you do it" — capabilities are fixed by the developer, and the user controls only the page set. TrueLayer takes this to its logical extreme: the payments scope grants the ability to _propose_ actions, but every individual action requires its own authorization.
### **8.2 Resource Selection Is Always Proprietary**
There is no standard protocol for "let the user select which resources to expose to this app." Every vendor invents their own mechanism (Google Picker, Notion's page picker during OAuth consent, GitHub's repo selector in fine-grained PAT creation, GitHub App installation repo selection, Dropbox Chooser). This is a major gap. The mechanisms also vary in _when_ they occur (during OAuth, before OAuth, after OAuth, independently of OAuth) and in what they _grant_ (API access, links, or persistent sharing). Even the concept of "resource selection" is not uniform. TrueLayer doesn't have resource selection at all — the app creates the resource and the user authorizes it, inverting the pattern entirely.
### **8.3 The Token Usually Doesn't Change**
When a user selects resources (via a picker, PAT configuration, or app installation), the OAuth access token typically remains the same. The backend tracks per-resource grants separately. GitHub's fine-grained PATs _do_ bake resource selection into the token, but the token itself is opaque — the client cannot inspect it to learn which repos it covers. Dropbox's Chooser doesn't involve the app's OAuth token at all. Notion's page selection happens during the OAuth flow but the resulting token doesn't encode which pages were selected — the backend tracks that separately. TrueLayer introduces a second token (the resource token) that is per-resource and single-use, but the primary access token remains unchanged. This confirms the instinct from the overview (question 11): MCP access tokens should probably not be mutated as a result of FGA negotiation.
### **8.4 The 404-as-403 Pattern Is Common But Not Universal**
Google Drive, GitHub, and Notion return opaque errors for resources the caller can't access — 404 for non-existent-or-inaccessible resources, or generic errors without remediation hints. Dropbox uses 409 Conflict for path-related errors. These systems share a pattern: the error response does not tell the client how to get access. TrueLayer is a notable exception — authorization_required is an explicit, structured, non-error status with a clear programmatic path forward. MCP's FGA mechanism must handle both the opaque case (client cannot distinguish "doesn't exist" from "not authorized") and the explicit case (server clearly communicates what authorization is needed).
### **8.5 The Interaction Model Is the Hardest Constraint**
The biggest challenge for MCP is not representing permissions — it's handling the spectrum from "human in the browser" to "unattended agent." Most existing resource selection mechanisms assume a human. GitHub's model is more agent-friendly than Google Drive's (fine-grained PATs can be pre-configured for automation), but remediation still requires humans. Dropbox occupies an interesting middle ground: the Chooser is interactive-only, but the API track with Full Dropbox access and refresh tokens can support fully unattended automation — if the app was registered for it. Notion's internal integrations are unique in that granting access is a user action within the product UI itself. TrueLayer adds another dimension: the _server-side_ flow (creating payments) can be fully automated, but _authorization_ requires a human for every single invocation — by regulation, not by design limitation.
### **8.6 Authorization Models Range from Transparent to Opaque**
Google Drive's model is relatively transparent — the client can understand "you have drive.file scope, you need to pick files." GitHub's model is largely opaque — the client cannot predict what it can access without trying. Dropbox sits between the two — the client can know its content access level (App Folder vs. Full Dropbox) and its scopes, but the Chooser's results are transient artifacts whose validity the client cannot verify without trying to use them. Notion is transparent in a different way — the access model is simple (you can access exactly the pages shared with you) but the client has no way to learn _what else exists_ that it could request access to. TrueLayer is fully transparent — the client knows exactly what it needs to do (initiate authorization flow) and the system tells it explicitly when authorization is required. MCP must support all of these patterns. This suggests the protocol should not require servers to describe their authorization model, but should allow them to if they choose.
### **8.7 Access Comes in Different Forms**
Not all "access" is the same. Google Drive and GitHub both grant API access — the ability to make authenticated API calls against a resource. Dropbox's Chooser grants _artifact access_ — a URL that the client can use directly, without further API authentication. TrueLayer grants _execution authorization_ — consent for a specific action with specific parameters to proceed. These different forms of access have different lifetimes, different failure modes, and different remediation paths. MCP should not assume that all resource access follows the API-call-with-token model.
### **8.8 Resource Selection Happens at Every Stage of the Lifecycle**
Across our case studies, resource selection (or authorization) occurs at remarkably different points:
<table><tr><td><b>When</b></td><td><b>System</b></td><td><b>Mechanism</b></td></tr><tr><td>App registration time</td><td>Dropbox</td><td>App Folder vs. Full Dropbox</td></tr><tr><td>Token creation time</td><td>GitHub</td><td>Fine-grained PAT repo selection</td></tr><tr><td>OAuth consent time</td><td>Notion</td><td>Page picker embedded in consent flow</td></tr><tr><td>Post-OAuth, on demand</td><td>Google Drive</td><td>Picker invoked at any time after consent</td></tr><tr><td>Independent of OAuth</td><td>Dropbox</td><td>Chooser uses user's own session</td></tr><tr><td>Ongoing, manual</td><td>Notion (internal)</td><td>User adds connection to pages one at a time</td></tr><tr><td>Per-invocation</td><td>TrueLayer</td><td>Each payment requires its own user authorization</td></tr></table>MCP's FGA mechanism needs to accommodate all of these timing models. Some systems allow the client to trigger resource selection (Google Drive Picker, Dropbox Chooser). Others require user-initiated action in the vendor's own UI (Notion's "add connection"). TrueLayer requires user authorization as part of every tool invocation. The protocol should support signaling _when_ and _how_ resource selection or authorization can happen, not just _whether_ it's needed.
### **8.9 Not All Systems Have a Broad-Access Fallback**
Google Drive, GitHub, and Dropbox all have a spectrum from narrow to broad access — the user or developer can choose to grant more expansive access when needed (drive scope, "all repositories" PATs, Full Dropbox). Notion has no such option. Access is always an explicit allowlist of pages, and there is no "access everything" scope to escalate to. This means the escalation path is fundamentally different: not "request a wider scope" but "ask the user to share more resources one at a time." MCP should not assume that every system has a broad-access tier available as a fallback remediation.
### **8.10 Authorization Is Not Always About Resources**
The first four case studies frame authorization as "which resources can this app access?" — files, repos, pages. TrueLayer reveals that authorization can also be about actions: "can this app execute this specific operation with these specific parameters?" This distinction matters for MCP because tool calls are inherently actions, not resource accesses. Some MCP tools will be resource-oriented ("read this file"), but others will be action-oriented ("send this payment," "post this message," "create this record"). The FGA mechanism should support both models without forcing one into the other's shape.
### **8.11 The Spectrum of Authorization Persistence**
Our case studies span the full spectrum of how long authorization lasts:
<table><tr><td><b>Persistence</b></td><td><b>System</b></td><td><b>Example</b></td></tr><tr><td>Indefinite</td><td>Google Drive</td><td>Picker grants persist until revoked</td></tr><tr><td>Indefinite (user-managed)</td><td>Notion</td><td>Page connections persist until removed</td></tr><tr><td>Token-scoped</td><td>GitHub</td><td>Fine-grained PAT expires (max 1 year)</td></tr><tr><td>Hours</td><td>Dropbox</td><td>Direct links expire after 4 hours</td></tr><tr><td>Single-use</td><td>TrueLayer</td><td>Each payment authorization is consumed once</td></tr></table>MCP's FGA mechanism must accommodate this full range. A protocol that assumes authorization is persistent (like a session) would fail for TrueLayer. A protocol that assumes authorization is always per-request would add unnecessary friction for Google Drive or Notion. The server should be able to signal the persistence model of its authorization grants.

## **9. Consolidated Requirements**
The individual case studies surfaced 27 requirements. Many are variations on the same theme. The following table consolidates them into 12 distinct requirements, grouped by concern.
### **Failure Signaling & Denial**
<table><tr><td><b>#</b></td><td><b>Requirement</b></td><td><b>Surfaced By</b></td></tr><tr><td>R1</td><td>Structured denial responses — machine-readable reason codes, accommodating opacity (server may not distinguish "not found" from "not authorized")</td><td>Google Drive, GitHub, Notion</td></tr><tr><td>R2</td><td>Remediation taxonomy — typed remediation hints (interactive URL, scope escalation, admin action, vendor UI action, non-remediable architectural constraint) indicating whether human-interactive, sync vs. async, and when to retry</td><td>All five systems</td></tr></table>### **Resource Selection & Discovery**
<table><tr><td><b>#</b></td><td><b>Requirement</b></td><td><b>Surfaced By</b></td></tr><tr><td>R3</td><td>Resource selection semantics — distinguish resource-selection flows from generic URL elicitation so the client understands the nature of the interaction</td><td>Google Drive, Dropbox, Notion</td></tr><tr><td>R4</td><td>Discovery model advertisement — server signals whether the client can enumerate resources, whether enumeration requires broader permissions, and whether interactive discovery covers a broader set than programmatic access</td><td>Google Drive, GitHub, Dropbox, Notion</td></tr><tr><td>R5</td><td>Resource-level constraint advertisement — servers can optionally communicate resource-level boundaries alongside tool availability (e.g., "this tool operates on repos; here are the ones you can access")</td><td>GitHub</td></tr></table>### **Access Grants & Temporal Scoping**
<table><tr><td><b>#</b></td><td><b>Requirement</b></td><td><b>Surfaced By</b></td></tr><tr><td>R6</td><td>Temporal scoping spectrum — grants may be indefinite, ephemeral (hours), or single-use, with lifetimes independent of the token. Server communicates persistence model, expiration, and renewal path</td><td>Google Drive, Dropbox, TrueLayer</td></tr><tr><td>R7</td><td>Opaque authorization models — protocol works when the client cannot predict or enumerate access, and when token configuration is a ceiling rather than a grant</td><td>GitHub</td></tr><tr><td>R8</td><td>Access type distinction — distinguish capability-based access (ongoing API operations), artifact-based access (time-limited links/content), and execution authorization (consent for specific parameterized actions)</td><td>Dropbox, TrueLayer</td></tr></table>### **Resource Grant Structure**
<table><tr><td><b>#</b></td><td><b>Requirement</b></td><td><b>Surfaced By</b></td></tr><tr><td>R9</td><td>Hierarchical resource grants — access to a parent may implicitly include children; the accessible set may grow without re-authorization</td><td>Notion</td></tr><tr><td>R10</td><td>Create-and-grant pattern — authorization flows may create new resources, not just select existing ones</td><td>Notion</td></tr></table>### **Action Authorization**
<table><tr><td><b>#</b></td><td><b>Requirement</b></td><td><b>Surfaced By</b></td></tr><tr><td>R11</td><td>Per-invocation authorization with parameter binding — tool calls may require independent user authorization bound to specific argument values (intent binding)</td><td>TrueLayer</td></tr><tr><td>R12</td><td>Two-phase commit model — server responds with "action registered, authorization required" as a structured non-error intermediate state</td><td></td></tr></table>

# [MMS] Proposal: Structured Denial and Remediation

<!-- Tab ID: t.jx6uoap0g6wk -->

# A Proposal for Structured Denials with Typed Remediation
## Problem Definition
See Overview Tab of the document MCP WG: Fine-grained authorization - Notes
## Context-Aware Structured Denials with RAR
The main idea of this proposal is its explicit handling of the AI execution context:

- **Human Presence (Foreground)** versus **Autonomous Execution (Background)**. Standard authorization often assumes a user is actively waiting at a browser, AI agents frequently operate asynchronously.

When an AI Agent (MCP Client) attempts to execute a high-stakes tool without explicit, granular consent, the MCP Server generates a unique Transaction ID (TxID) tied to the exact parameters of that specific tool call (e.g., amount=$5000). It then returns a machine-readable JSON-RPC denial containing this TxID within a typed remediation hint. MCP Server's JSON-RPC challenge provides an array of remediation_hints, the Client evaluates its own OAuth capabilities and its current execution context to select the appropriate path:
- **Asynchronous Remediation (Agent is Autonomous):** If executing in the background without active user interaction, an advanced client selects the urn:ietf:params:oauth:rar hint and may use the CIBA flow. This pushes an out-of-band notification directly to the user, allowing the agent to pause and resume without a browser session.
- **Synchronous Remediation (Human is Present):** If the user is actively engaged in the interface (e.g., a chat window), an advanced client may select the exact same urn:ietf:params:oauth:rar hint but triggers a standard front-channel redirect (/authorize). This renders an immediate consent pop-up in the user's current session.
- **Fallback Remediation (Generic Clients):** If the client lacks support for the RAR extension entirely,  it ignores the RAR payload and selects the URL or message fallback hint. It surfaces the link for the user to click (or the message), relying on a basic try-fail-retry loop to resume the tool call once the user completes the external flow.

It addresses three main requirements for any solution

- **Its Additive:** General-purpose MCP clients lacking support for this remediation type simply treat the response as a standard JSON-RPC tool failure.
- **No Backend Assumptions:** It does not enforce a specific authorization model on the underlying system; it uses RAR along with a client-server communication pattern.
- **Context-Driven UX:** Allows the client to choose the least intrusive consent mechanism (synchronous in-useragent vs. asynchronous push) based on real-time human presence.


##    Execution Flow (The Autonomous Agent Scenario)
**__**
1. **Initialization:** The MCP Client initializes the connection with the MCP Server, passing the baseline Access_Token_1
1. **Tool Call:** The Agent decides to use the execute\_payment tool (tool name is just an example). The MCP Client then sends a JSON-RPC tools/call request to the MCP Server.
1. **JSON-RPC Step-Up Challenge:** The MCP Server inspects the token, realizes it lacks explicit approval for this execution, and returns a JSON-RPC Error containing the RAR payload (The Structured Denial)
  1. In case of SSE streaming the MCP Server returns the structural denial in the payload and closes the stream. The MCP Client and MCP Server are recommended to support resumability for preserving the outcomes of the already executed tasks, when the privilege is granted.
1. **Agent Pause & CIBA Initiation:** The MCP Client intercepts the error, pauses the agent's execution, and makes a REST call to the AS's` backchannel_authentication_endpoint endpoint using the RAR payload
1. **Human Consent:** The human receives a push notification on their device: "Agent XXX wants to execute a $5000 payment. Approve?" The human approves.
1. **Polling & Token Retrieval:** The MCP Client polls the AS token endpoint, receives Access\_Token\_2
1. **Execution Resumption:** The MCP Client then retries the tools/call JSON-RPC request, providing Access\_Token\_2. The MCP Server validates the transaction claim and executes the tool.
**__**
## Payload with Examples
_NOTE:__ JSON payload are just some examples to understand the proposal_
### A. MCP Server Tool Call (Client -> Server)
The agent attempts to call the tool via standard MCP JSON-RPC format.
{
  "jsonrpc": "2.0",
  "id": "req_123",
  "method": "tools/call",
  "params": {
    "name": "execute_payment",
    "arguments": {
      "payee": "Acme Corp",
      "amount": "5000.00",
      "currency": "USD"
    }
  }
}
### B. MCP Server Error/Challenge (Server -> Client)
Instead of an HTTP 401, the MCP Server returns a JSON-RPC error. We leverage the data object within the error to pass the exact OAuth WWW-Authenticate equivalent and the RAR payload.

{
  "jsonrpc": "2.0",
  "id": "req_123",
  "error": {
    "code": -32001, 
    "message": "authorization_required",
    "data": {
      "error_description": "Tool execution requires explicit human approval.",
      "remediation_hints": [
        {
          **"type": "urn:ietf:params:oauth:rar",**
**          "execution_mode_hint": "any",**
          "authorization_details": [
            {
              "type": "urn:mcp:authorization:tool_execution",
              "actions": ["execute_payment"],
              "locations": ["mcp://finance-server"],
              "transaction_info": {
                "tx_id": "tx_999_abc",
                "amount": "XXXX",
             }
            }
          ]
        },
        {
          "type": "URL",
**          "execution_mode_hint": "synchronous",**
          "url":  "https://finance-server.example.com/pending-approvals/tx_999_abc"
        },
        {
          "type": "message",
          **"execution_mode_hint": "asynchronous",**
          "text": "Please log into the Acme Corp portal to approve the pending XXXX payment."
        }
      ]
    }
  }
}

### Design Rationale: Why JSON-RPC Error vs. HTTP 401 WWW-Authenticate?

- **Transport-Agnostic:** I am hoping this same solution can be leveraged to run over multiple transport layers where HTTP headers do not exist OR avoid any complication where Headers may not be returned. 
  - Other issue is that the authorization details may start to push the header size to a limit which may end up getting blocked by Servers
- **JSON-RPC Compliance:** The RAR payload into the _error.data_ object utilizes the exact mechanism JSON-RPC provides for structured error information, so it is protocol standard-compliant.
- **Application-Layer Parsing (Just a guess):** Providing the required_authorization_details directly in the JSON body will likely make it easy for the Agent to pause the agent, and trigger the asynchronous flow . 
### Note on Payload Extensibility and Schema
The exact JSON Schema constraints for the _remediation_hints_ array are TBD. This array would likely be a discriminated union keyed by the _type_ discriminator. That schema will enforce which sibling fields (such as _authorization_details, url, or text)_ are required, allowed, or forbidden for each specific type, as well as the allowed enum values for _execution_mode_hint_. The payload shown in this proposal is to illustrate the concept.


### C. Client Back-Channel Initiation (Client -> AS)
The MCP Client calls the OAuth AS via standard HTTP.

POST /bc-authorize HTTP/1.1
Host: as.example.com

id_token_hint=eyJhbGciOiJSUzI1NiIs...[REDACTED]...
&binding_message=Agent-TX-999
&authorization_details=[{"type":"urn:mcp:authorization:tool_execution","actions":["execute_payment"],"locations":["mcp://finance-server"],"transaction_info":{"tx_id":"tx_999_abc","amount":"5000.00","currency":"USD","payee":"Acme Corp"}}]



**_Note:_**_ For readability, the authorization_details parameter is shown as an unencoded JSON string. I think in reality, because the Content-Type is application/x-www-form-urlencoded, this JSON array will be strictly URL-encoded._

#### **Open Question:** Does this work for Public Clients? How do they authenticate? What are my options here?
#### **Open Question:** Should some scope parameter (e.g., scope=mcp_agent) be included in this request to ensure compatibility with off-the-shelf IdPs, or do we rely entirely on the RAR payload?
**__**
### D. Client Polling & Token Retrieval (Client -> AS)
This is just standard CIBA

The Client polls the token endpoint. Once the user approves the push notification on their device, the AS returns the upgraded token.

POST /token HTTP/1.1Host: as.example.comContent-Type: application/x-www-form-urlencodedAuthorization: Basic Q2xpZW50SUQ6Q2xpZW50U2VjcmV0

grant_type=urn:openid:params:grant-type:ciba&auth_req_id=1c266114-a1be-4252-8ad1-04986c5b9ac1

**Success Response:**

HTTP/1.1 200 OKContent-Type: application/json

{"access_token": "sl.aB2c...[UPGRADED_TOKEN]...xyz","token_type": "Bearer","expires_in": 3600,"id_token": "eyJhbGci...xyz"}
### E. Finally resuming the Tool Call (Client -> Server)
Once the MCP Client has the upgraded token, it retries the exact same JSON-RPC call, utilizing the token strategy defined in Section 5
# Topics to be discussed further 
## Token Management Strategy in Case of Option#1

I was thinking that there are two possible Token types that we can choose from

1. **Option 1: The "Upgraded" Access Token (Incremental Authorization):** This is standard step-up. The Client requests the original baseline scopes _plus_ the new authorization_details. The AS issues a "Superset Token" valid for both standard read tools and the high-stakes execution tool. The Client discards the old token and uses this new one exclusively.
1. **Option 2: The Dedicated SingleUse Token (Strict Isolation):** The Client requests _only_ the authorization_details. The AS issues a highly restricted, short-lived Single-Use Token valid _only_ for the specific execution tool. The Client must now manage two tokens in memory (one for generic calls, one for execution), increasing client complexity but drastically reducing the blast radius. The biggest challenge is this - managing two distinct tokens (one for standard reads, one for high-stakes execution) and knowing _when_ to inject which token forces the general-purpose client to understand server-specific authorization boundaries. This may be a deal breaker.
****

# Authorization Discovery & Resolution Modes [NEW]
We propose to add an established way to describe MCP server’s required authorization as metadata on a tool level. The possible options of describing the metadata could be the protected resource metadata or MCP Server Cards.

The proposal is based on RAR specification. In addition to the _authorization_details_ term, defined by RAR, the proposal introduces an _authorization_details_resolution_modes_ tool metadata field, which defines how the client can resolve the authorization details, and supports the following values:

**_try-fail _**- This is the default mode and sections earlier have gone into a lot of detail about how it can work. 

The client attempts the tool execution.If the request lacks sufficient authorization, the server rejects it and returns the _authorization_details_ model within the structured denial. This is the default fallback mode for all clients.

_Implementation Note for Servers:_ Because the client simply retries the exact same request after obtaining consent, servers can implement try-fail using two different backend strategies -
1. Stateless execution: The server calculates the RAR details, discards them, and relies entirely on the cryptographic proof inside the retried token to authorize the execution.
1. **Stateful reservation (Two-Phase):** For highly dynamic operations (e.g., a financial trade where the price might change during the human approval window), the server can calculate the details, create a "pending" transaction with an expiration time in its database, and return the TxID in the response. When the client retries, the server matches the token's TxID claim to the locked database record to confirm the operation. This is where Tx Token (TBD) comes into picture as well



**_preemptive_** - the tool’s metadata provides _authorization_details_template_. The final _authorization_details_ object can be built by the client from the template, by replacing the placeholders with the values of the request parameters, which are also defined in the tool’s metadata.
When the authorization details are resolved and the Client obtains a fine-grained token, it initiates the operation in any of the other supported modes (try-fail by default).

**_dry-run_** - works similarly to the try-fail mode, but the resource server doesn’t change state. The dry-run mode allows the resource server:
1. Execute the complex validation and business logic without changing the state to confirm resource availability. E.g., validate the amount sufficiency, ensure the accounts exist, etc.)
1. Calculate the dynamic authorization details. E.g., calculate the transaction fee and include it in the authorization detail.
A general access token is sufficient for the dry-run mode. When the authorization details are resolved, and the Client obtains a fine-grained token, it repeats the operation with the same parameters in try-fail mode.


### Example of the tool’s metadata:

```
{
  "tools": [
    {
      "name": "payment_tool",
      "description": "A tool to execute payments to a specified payee with a given amount and currency.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "payee": {
            "type": "string",
            "description": "The recipient of the payment"
          },
          "amount": {
            "type": "number",
            "description": "The amount to be paid"
          },
          "currency": {
            "type": "string",
            "description": "The currency of the payment"
          }
        },
        "required": ["payee", "amount", "currency"]
      },
      "authorization": {
        **"authorization_details_resolution_modes": ["preemptive", "dry-run"],**
        "authorization_details_template": [
          {
            "type": "urn:mcp:authorization:tool_execution",
            "actions": ["execute_payment"],
            "locations": ["mcp://finance-server"],
            "transaction_info": {
              "payee": "{{payee}}",
              "amount": "{{amount}}",
              "currency": "{{currency}}"
            }
          }
        ]
      }
    }
  ]
}

```
The _try-fail_ mode is always supported and used as a fallback mode for clients that don’t support other modes. Therefore, it’s not necessary to mention the try-fail mode in the list of the supported modes.

### Example 1. The client executes payment in preemptive mode.

1. The client reads the tool’s metadata. 
1. If the preemptive mode is supported, the client reads the authorization_details_template field.
1. The client replaces the placeholders in the _authorization_details_ template ({{payee}}, {{amount}}, {{currency}}) with the values of the parameters to be used for calling the tool
1. The client uses the generated authorization_details object for completing the authorization flow with the AS and obtaining a fine-grained token
1. The client calls the tool with the same parameters that were used for generating the authorization_details and with the fine-grained token.


### Example 2. The client executes payment in dry-run mode.

1. The client reads the tool's metadata and identifies that dry-run is supported.
1. The client initiates a tools/call request with the standard parameters but includes a protocol-level directive (e.g., a reserved _meta: { "dry_run": true } flag) to signal the server.
1. The resource server executes the validation and business logic (e.g., calculating dynamic transaction fees) but halts execution before modifying any backend state.
1. The server responds with the standard -32001 JSON-RPC structured denial. The remediation_hints array contains the dynamically calculated authorization_details payload (now including the base amount plus the calculated fee).
1. The client uses this precise RAR payload to complete the authorization flow with the AS and obtains the fine-grained token.
1. The client repeats the tools/call with the exact same parameters and the new token, but omits the dry_run flag to finalize the transaction.

### Example 3. The client executes payment in two-phase mode.


- The client reads the tool's metadata and identifies that two-phase mode is supported.
- The client initiates a tools/call request with the standard parameters 
- The resource server executes the validation and business logic (e.g., calculating dynamic transaction fees) and may temporarily lock the resource (reserves the money).
- The server responds with the authorization_details payload, Tx ID, and Tx TTL.
- The client uses this precise RAR payload to complete the authorization flow with the AS and obtains the fine-grained token.
- The client repeats the tools/call with the same parameters, enriched with the Tx ID, new token, and omits the _"lock": true_ flag to finalize the transaction. The RS uses the Tx ID to match the request to the original request and the locked resource. Having the Tx ID in the request signals to the RS that it’s not a new transaction, but a confirmation for an existing transaction. The RS validates that the parameter values exactly match the original request to guarantee the equality of the confirmation to what was initially requested. The server executes the payment.
- If the confirmation is not sent within the TTL, the RS may take necessary action e.g. release lock on resources.


# [MMS]Proposal II:  Structured Denial

<!-- Tab ID: t.h3kx53jvppl -->

## Scope and Design Constraints from the WG decision logs
- A1 and A2, with a clear extension path to support A4

<table><tr><td><b>#</b></td><td><b>Interactivity</b></td><td><b>Resolution</b></td><td><b>Duration</b></td><td><b>Example Scenarios</b></td><td><b>Proposed Mechanism</b></td></tr><tr><td>A1</td><td>Human</td><td>Server-side</td><td>Durable</td><td>Google Picker; Dropbox Chooser; Notion page sharing; "ask your admin for access"; GitHub org admin PAT approval</td><td>Structured denial, url or message</td></tr><tr><td>A2</td><td>Human</td><td>Server-side</td><td>Ephemeral</td><td>Destructive operation consent; bank payment consent (server records per-payment approval)</td><td>TBD</td></tr><tr><td>A3</td><td>Human</td><td>Client cred</td><td>Durable</td><td>WWW-Authenticate scope challenge</td><td>✅ Already exists</td></tr><tr><td>A4</td><td>Human</td><td>Client cred</td><td>Ephemeral</td><td>PSD2 payment authorization; one-time token after human approval</td><td>TBD</td></tr></table>These are some key decisions that drive current proposal

- D7: Structured Denials as a building block is the first priority 
- D4: MCP is its own protocol; it should pick and choose from prior art, not adopt it wholesale
- D5: The reactive model (try-then-negotiate) is the correct foundation; authorization preflight rejected
- D6: Design for transport-agnosticism first, HTTP bindings second
## Proposal
This proposal defines a transport-agnostic JSON-RPC mechanism for communicating authorization denials and recovery paths between an MCP server and an MCP client.
1. When a tools/call or resources/read request is not currently authorized, an MCP server MAY return a structured authorization denial as a JSON-RPC error response. The denial contains a machine-readable reason and zero or more typed remediation hints.
  1. Initial remediation types are: 1) _url_ and 2) _message._
  1. When multiple remediations are present, they represent alternative recovery paths ie. the client MAY choose any one. Sequential authorization requirements (e.g., admin approval followed by user consent) MUST be expressed as successive denials. The client remediates and retries, and the server returns a new denial for the next required step if needed.
1. This proposal is optional, additive, and backwards-compatible. An MCP server MAY use it. An MCP client MAY ignore it and still surface a normal error
1. This proposal introduces a remediationId — an opaque correlation identifier that MAY appear on any remediation — and a corresponding  notifications/authorization/remediation-complete notification. This keeps the mechanism transport-agnostic at the JSON-RPC layer while allowing a server to proactively inform the client that an out-of-band remediation step has completed and that retry may now be useful. Note:
  1. This is a new structured authorization denial mechanism — this proposal does **NOT** use URLElicitationRequiredError
  1. _remediationId_ and notifications/authorization/remediation-complete are specific to authorization denial remediation. They are not part of the elicitation feature 
### Rationale
- Structured authorization denials and URL elicitation are distinct protocol features with different semantics: elicitation is the client eliciting information from the user on behalf of the server, while authorization remediation is the server directing the user toward a authorization action. Using a dedicated identifier and notification type:
  - Avoids overload between two conceptually different features at low implementation cost ( very similar wire format to elicitation notification)
  - Makes message + remediationId natural since nothing is being "elicited" in a message remediation
### Alternative: Reuse existing elicitation notifications
If the preference is to minimize new notification types, an alternative is to reuse the existing MCP URL-elicitation completion-correlation semantics via elicitationId and notifications/elicitation/complete. Under this approach, a remediationId would instead be an elicitationId, and the server would send notifications/elicitation/complete when remediation completes. This treats an elicitationId established in a structured-denial remediation as a valid origin for that notification, even though no elicitation/create request was issued. This avoids introducing new notifications but mixes two distinct features through a shared namespace.


1. We want to keep an eye on future needs where additional work needs to be done on the client e.g. one time token etc. (A4) such that this proposal has a natural extension path to the same


1.  _WWW-Authenticate_ and the structured denial are complementary, not overlapping. A server SHOULD NOT express a WWW-Authenticate-type challenge as a structured denial.
## 
## Denial Response Example

<table><tr><td>{<br>  "jsonrpc": "2.0",<br>  "id": 17,<br>  "error": {<br>    "code": "<AUTHORIZATION_DENIAL_TBD>",<br>    "message": "The request is not currently authorized.",<br>    "data": {<br>      "reason": "insufficient_authorization",<br>      "retryAuthorization": {<br>        "primaryCredentialAction": "reuse"<br>      },<br>      "remediations": [<br>        {<br>          "type": "url",<br>          "retryTimingHint": "after_completion",<br>          "remediationId": "6f1b0f4a-3d67-4c4d-9c3a-5e8b7f2a91d4",<br>          "url": "https://project.foocon.com/picker?request=abc",<br>          "message": "Select the project you want this server to access."<br>        },<br>        {<br>          "type": "message",<br>          "retryTimingHint": "deferred",<br>          "remediationId": "c2a7e8b1-5f44-4a9d-8e2f-1b6c3d7e92ab"<br>          "message": "Ask the project admin to invite you to the project, then retry."<br>        }<br>      ]<br>    }<br>  }<br>}</td></tr></table>
## 
## Key Fields
Let me talk about some key fields first which may be interesting as all others are quite self-explanatory. 

1. "retryAuthorization": {        "primaryCredentialAction": "reuse"   },
- The idea here was to provide the client with a structured hint about the credential requirements for retrying a denied request. We will start by supporting only one value, “_reuse” -_ it allows the server to indicate that the client may retry using the same MCP credential as the original request. (A1 & A2)
### Extensibility
- But this json _object_ is intentionally designed as an extension point for future work (A4), for cases where retry may require a one-time authorization proof, an additional short-lived presentation, or a different credential. And we wanted to have a transport-agnostic, protocol-level place for expressing retry credential posture before they have a transport binding (e.g. say using RAR etc.)
- This can carry other information like an _authorizationContextID _so a later retry can be linked to the specific denied operation, not just “some future call by this user.” The denial could carry a server-minted authorizationContextId, and the client echoes it on retry in something like _meta.authorizationContextId. (MCP already reserves _params._meta_ for protocol-level metadata)

<table><tr><td><h2>remediationId</h2><b>Rationale:</b> I wanted a way for Server to “help” the client wherever possible for a retry</td></tr></table>- remediationId is an optional opaque correlation identifier for a remediation instance. It MAY appear on any remediation type (url as well as message).

- Essentially
- url + remediationId: user goes somewhere and the server may later notify completion.
- message + remediationId: user follows some out-of-band instruction and the server may later notify when it detects the relevant state change.
- either type without remediationId: valid remediation, but no notification/correlation contract.

- If remediationId is absent:
- the remediation is still valid
- there is no completion-notification contract and retry is manual

- Note that the notification indicates that the remediation step has completed and that retry may now be useful. It does not guarantee that the original denied request will succeed on retry.


<table><tr><td><h2>retryTimingHint</h2></td></tr></table>- _Required_ on every remediation.It tells the client when retrying becomes sensible. It is advisory only. It does not guarantee that the next retry will succeed.**Defined values:**
- _after_completion:_ A retry becomes sensible after this remediation step itself completes. The retry MAY succeed, or it MAY result in a different authorization denial.
- _deferred:_ Completing or displaying this remediation does not make immediate retry useful. The client SHOULD treat retry as a later or manual action.
- A structured authorization denial never grants authorization by itself. After any remediation, the client MAY retry. On every retry, the server MUST perform a fresh authorization check. 
- A retry after after_completion MAY
  - Succeed, 
  - or fail with the same denial 
  - or fail with a different structured authorization denial
<table><tr><td><h2>type</h2></td></tr></table>- url or message (for now)
- url remediations MUST follow the security requirements of MCP URL mode elicitation, including the _Security Considerations_, _Safe URL Handling_, _Identifying the User_, and _Phishing_ requirements in the MCP Elicitation specification.
- A message remediation is just structured guidance. It covers cases like “ask your admin for access,” “ask the page owner to share it,”The client should surface it and give the user a manual resolution path.
- A denial with an empty remediations array is valid and indicates that no interactive or programmatic recovery path is available. The client SHOULD surface the error message to the user as-is.

## A note on Completion notifications
If a remediation includes remediationId, the server MAY later send a completion notification when that remediation step completes:
<table><tr><td>{<br> "jsonrpc": "2.0",<br> "method": "notifications/authorization/remediation-complete",<br> "params": {<br>   "remediationId": "rem_1"<br> }<br>}</td></tr></table>The rules for Servers sending this notification are similar to elicitation notification
- MUST only send it to the client that received the structured denial containing that remediationId.
- MUST include the exact remediationId from the remediation.
- MUST ensure that the completed remediation is bound to the same user and relevant server-side state as the original denial.
- MUST NOT treat completion of the remediation as authorization by itself. On retry, the server MUST perform a fresh authorization check.
Clients:
- MUST ignore notifications referencing unknown or already-completed remediationId values.
- MAY use the notification to update UI or attempt a convenience retry, subject to local UX and safety policy.
- SHOULD still provide manual retry or cancel controls if the notification never arrives.
If a remediation omits remediationId, the remediation is still valid, but there is no completion-notification contract and retry is manual.
## 
## Other fields
- reason - machine-readable classifier for structured authorization denials. The only defined value for now is insufficient_authorization. Future specifications MAY define additional reason values.


### ****
	****


