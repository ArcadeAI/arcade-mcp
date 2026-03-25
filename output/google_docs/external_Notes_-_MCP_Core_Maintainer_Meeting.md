---
title: "[external] Notes - MCP Core: Maintainer Meeting"
id: 1annqJ2m4jNFOx6vU0FMnDSr6V3c5uN4TCT_uuZcZFh8
modified_at: 2026-03-18T18:00:58.133Z
public_url: https://docs.google.com/document/d/1annqJ2m4jNFOx6vU0FMnDSr6V3c5uN4TCT_uuZcZFh8/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->


##  | 
Attendees:         

Notes

**Facilitator Proposed Order based on Priority of Discussion/Protocol Priorities:**
1. Agenda for Maintainers/Core Maintainers in person Meetup in NY
  - Maintainers Agenda
  - Core Maintainers Agenda (8-10AM - AAIF, CM dinner?)

1. Release milestones:
  1.  - **Release Candidate**
    1. List of SEPs that are making it into the spec is given.
    1. Changes can still be done to SEPs.
    1. SDK developers can start implementing and battle-testing the proposals.
    1. Client implementers receive a heads-up about the changes.
  1.  - **Stable**
    1. Spec released.
    1. Tier 1 SDKs have full support for SEPs.
  1. SEPs
    1. Scrub during the onsite.

1. Review SEPS/Proposals by MCP Roadmap Priority Area Topics 
  1. Transport Evolution & Scalability Topics
    1. [kvg] Pluggable Transports PR – how to get prioritized? 
    1. [] MRTR Design decision related to MRTR SEP-2322
  1. Agent Communication - No Topics
  1. Governance Maturation - No Topics
    1. SEP-2149: MCP Group Governance and Charter Template by dsp-ant · Pull Request #2149 · modelcontextprotocol/modelcontextprotocol
  1. Enterprise Readiness:
    1. Security vulnerability disclosure program for SDKs
      1. We moved to GHSA, and need shared guidance on how we handle scenarios where a vulnerability in one SDK can be applicable to other SDKs.
    1. [**Den**] Surgical auth SEPs (async voting is fine - want to raise awareness):
      1. **SEP-2352**: Clarify authorization server binding and migration
      1. **SEP-2351**: Explicitly specify RFC 8414 well-known URI suffix for MCP
      1. **SEP-2350**: Clarify client-side scope accumulation in step-up authorization
      1. **SEP-837**: Update authorization spec to clarify client type requirements

1. Other SEPs to Review:
  1. **SEP-2164**: Standardize resource not found error code (-32602) by pja-ant · Pull Request #2164 · modelcontextprotocol/modelcontextprotocol - Peter
  1. **SEP-2093**: Resource Contents Metadata and Capabilities by pja-ant · Pull Request #2093 · modelcontextprotocol/modelcontextprotocol - Peter
  1. **SEP-2293** Add Support for Completions Metadata by evalstate : Add Support for Completions Metadata - Sponsors: @evalstate


**All Proposed Agenda Topics**
SEPS to Review
- **SEP-2164**: Standardize resource not found error code (-32602) by pja-ant · Pull Request #2164 · modelcontextprotocol/modelcontextprotocol - Peter
- **SEP-2093**: Resource Contents Metadata and Capabilities by pja-ant · Pull Request #2093 · modelcontextprotocol/modelcontextprotocol - Peter
- **SEP-2293** Add Support for Completions Metadata by evalstate : Add Support for Completions Metadata - Sponsors: @kentcdodds & @evalstate
- SEP-2149 https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2149: WG / IG Charter Template
- [**Den**] Surgical auth SEPs (async voting is fine - want to raise awareness):
  - **SEP-2352**: Clarify authorization server binding and migration
  - **SEP-2351**: Explicitly specify RFC 8414 well-known URI suffix for MCP
  - **SEP-2350**: Clarify client-side scope accumulation in step-up authorization
  - **SEP-837**: Update authorization spec to clarify client type requirements

Discussions : 
- Agenda for Maintainers/Core Maintainers in person Meetup in NY
  - Maintainers Agenda
  - Core Maintainers Agenda
- Release milestones:
  -  - **Release Candidate**
    - List of SEPs that are making it into the spec is gaveled.
    - Changes can still be done to SEPs.
    - SDK developers can start implementing and battle-testing the proposals.
    - Client implementers receive a heads-up about the changes.
  -  - **Stable**
    - Spec released.
    - Tier 1 SDKs have full support for SEPs.
  - SEPs
- [kvg] Pluggable Transports PR – how to get prioritized? 
- [] MRTR Design decision related to MRTR SEP-2322
- Security vulnerability disclosure program for SDKs
  - We moved to GHSA, and need shared guidance on how we handle scenarios where a vulnerability in one SDK can be applicable to other SKUs.

Action items
- Data on client/host support in terms of capabilities - **Caitie** and **Den **to coordinate on client outreach.
  - **Shaun** to help with the Hugging Face dataset for sharing client data from the dataset.



##  | 
Attendees:            

Notes
- [paulc, wils]: SEP-2207 refresh token clarification
- [dsp]: 2026 Roadmap
- [den]: June spec release milestones
  - Den will start a doc on release milestones, other CMs will fill in some areas. Will review the next CM meeting. 
- [] Updates on SEP-2243 HTTP Standardization
  - This was voted to “Accept w/ Changes”. Do we need to revisit the changes? 
  - Write up of solutions for “any field in the request”. Would love feedback from CM.
- [/ ]: SEP-2322: Multi Round-Trip Requests
- 

Action items
- 



##  | 
Attendees:           
Attached files:  

Agenda
1. Maintainer/Core Maintainer meetup @ NYC (March 31st - April 1st)
  1. First two days, rest is conference - giving you time to attend/speak.
  1. Decision - first day, Maintainers; second day (Workshop) - Core Maintainers.  working with LF to get space, but if we don’t get anything, will have alternatives around Block, Microsoft, Google.
1. Review and finalize priorities: 
  1. Q: refining existing functionality likely better than new functionality?
  1. Everyone on the hook to do top 3-5 at the bottom of the document, make it very specific
1. Official MCP auth extensions
  1. Need client support examples - this is the most important thing. There needs to be a clear path to extension adoption across a wide variety of clients.
  1. Are some extensions less relevant to bulk of the clients? E.g., enterprise might be building machine-to-machine connections that require special things.
    1. Even if they come back with internal clients, that’s enough proof.
  1. We need better documentation and an obvious way to adopt extensions → Den
1. REVIEWS:
  1. [Caitie Sponsoring from Transport WG] SEP-2260 Require Server requests to be associated with a Client request. by evalstate · Pull Request #2260 · modelcontextprotocol/modelcontextprotocol - initial step to moving the protocol to be stateless.
    1. Ready to vote
  1. [Kurtis Sponsoring from Transport WG] SEP-2243 HTTP Standardization by mikekistler · Pull Request #2243 · modelcontextprotocol/modelcontextprotocol
    1. We should see if there is a way to standardize the custom header approach
    1. We should double-click on the encoding approach
    1. Come back next week with those improvements for vote
1. Quick update on governance & values 
1. Quick update on infra
Notes
- 

Action items
- 



##  | 
Attendees:           
Attached files:  

Notes
- REVIEWS
- Primitive Grouping: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2084
- Agent Hints Tool: https://github.com/modelchttps://github.com/modelcontextprotocol/modelcontextprotocol/pull/2084ontextprotocol/modelcontextprotocol/pull/1938
- Document OpenTelemetry Trace Context Propagation Convention: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/414
- MCP Vision / Values Exploration


Action items
- 



##  | 
Attendees:  Nick Cooper, Che Liu
Facilitator: 
## Agenda
- Short note from 
- Introducing the new Core Maintainers
  - Caitie McCaffrey
  - Kurtis Van Gent
- MCP Apps release & ratification of the extension SEP as official extension
- Triaging existing SEPs - lots of issues that are not yet converted to proper SEPs (PRs)
  - Delegate to WGs for explicit filtering at first
  - Too much work for core maintainers - automation for sponsor-less SEPs
  - 60days/90 days for SEP closure
- Automatic Core Maintainer facilitator rotation
- Repository health (VISR)
- Swift-sdk update
- Transports
  - Need to block off some time for extra review
  - We will need to do a joint thing w/Tasks to see what the overlap is
- SEP review cadence - board + top-of-mind:
  - https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2085
  - https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1724 
- Skills vs. MCP - needs better explaining
  - Potentially need a blog post on this to explain
  - Caitie to help take a pass on the blog post
##  | 
Attendees:        
Attached files:  

Notes
- Rotation:
  - We need to build that discord bot
    - Den is building that. So the next iteration will have this.
- MCP Governance:
  - Changes to Core Maintainer group.
    - Clearly define expectations.
    - Sourcing new Core Maintainers
    - How to improve the interactions between core maintainers & working group leads
    -  to be invited to join core maintainers.
    - to be invited to join core maintainers.
  - Sarah’s Suggestions:
    - Contribution Ladder
    - Governance improvements
    - She will engage with the governance-wg
  - Mapping of Core Maintainer to WG
- Swift SDK maintenance.
  - https://discord.com/channels/1358869848138059966/1399987383562141826/1458146953069068328
- SEP Priorities:
  - Extensions
  - Server Cards
  - MCP Apps
  - SDK Tiering
- License Changes
  - Apache 2.0 as the new default
    - https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/1995
  - Maybe relicsing.
Action items
- Document expectations of core maintainers
- David to reach out to 
- David to reach out to 
- David to make a proposal for core maintainer and work with working groups. This overlaps with work from Sarah Notovny.
- to run the next meeting or the bot will decide.



##  | 
Attendees:        
Attached files:  

Notes
- [dsp]
  - Retrospective
  - Core Maintainer rotation:
    - Responsibilities
      - Preparing the meeting
      - Preparing notes to share with the public
      - Write a github action that runs weekly that pings via discord with a person.
  - Core Maintainer dispersity to working groups:
    - We need core maintainers to sponsor people in a working group.
      - Agents-wg
      - Auth-wg
      - Transport-wg
  - Public priority list:
    - Roadmap update

Action items
- 



##  | 
Attendees:        
Notes
- [david]
  - **Core Maintainer Meeting Length **I think we need to move Core Maintainer meetings to 90 minutes, with an async hold to pre-read. Realistically we are not getting enough discussions in and don't come prepared enough. I would love to experiment with 90 minutes sessions from now on for the core maintainer meeting, but the optional SEP reading stays.
- [den]
  - Quick-follows for the spec **this week** (these are pre-requisites for spec finalization based on feedback). There are two items currently on deck.
    - CIMD clarification https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1839 
    - SSE downgrade clarification https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1844 
    - SSE polling - had some feedback as well. Agents WG is where most of the conversation is.
  - Sign-off on general direction of the blog post (see PR). I am working on adding photos and some quotes from notable industry folks that have adopted MCP. **No major items here - just need folks to be aware of the framing and content.**
  - Check-in on SDK progress.
  - Small spec process adjustments/clarification (experimental flags, RC expectations) - we need to document those while we're going through the process and feel the pain first-hand
- [paul]
  - SF in December: do we want any EOY core maintainer things independent of the transport working group?
- [david] SEP process
  - 7-0, no sep voting. We are doing that.
- [david] community health proposals
- AI Card https://github.com/Agent-Card/ai-card
  - We want something MCP specific, but stay in touch
  - We want a discriminator identifying that it’s an mcp server card
  - Discovery and Schema are two different things
    - Discovery should be the same
    - Schema can be different
  - 

(Tasks feedback)
taskHint
https://modelcontextprotocol.io/specification/draft/basic/utilities/tasks#tool-level-negotiation 
- should we make it server MUST error on non-task requests if taskHint: always? 
- should we make client MUST invoke tool as task?
- What’s the intended behavior if taskHint: always and server doesn’t error?

input_required
https://modelcontextprotocol.io/specification/draft/basic/utilities/tasks#input-required-status 
- SHOULD pre-emptively call tasks/result -> so basically once there’s input_required at least once, it becomes blocking again?
  - Should we add language that server SHOULD cancel the stream instead via SEP-1699 to close the connection for client to return back to polling?
- Rapid back and forth transitions


Action items
- Nick A to follow-up with Luca on the Task clarifications
- URL mode elicitations - flag as experimental, clarify client behavior
- David - draft blog post on protocol being “slowed down/stable” (framing different, this is just the idea). Aim for **December**. Focus on ergonomics



##  | 
Attendees:        
Attached files:  

Agenda

- **ℹ️ NOTE**: Primary purpose of this call should be **locking down the list of SEPs** for 2025-11-25 release. They are included below for review.
  - The SEPs were included in the milestone document but have not been reviewed/accepted. We need to make that call today.
- Determine DRIs for SDK work.

Notes
- 

Action items
- ⚠️ Check out 1372 and see if this is something that we want to include in the upcoming spec release.
### SEP Review
<table><tr><td><b>SEP ID</b></td><td><b>Title</b></td><td><b>Sponsor</b></td><td><b>Presenter</b></td><td><b>Modality</b></td><td><b>To be discussed in meeting</b></td><td><b>Votes</b></td></tr><tr><td>1577</td><td>Sampling With Tools</td><td></td><td>pending availability to present</td><td></td><td></td><td></td></tr><tr><td>1649</td><td>MCP Server Cards: HTTP Server Discovery via .well-known</td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>1699</td><td>Support SSE polling via server-side disconnect</td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>1724</td><td>Extensions</td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>1533</td><td>Metadata in Resource Read Response</td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>1730<br>(PR adding to docs)</td><td>SDKs Tiering System</td><td></td><td></td><td></td><td></td><td></td></tr></table>
## 
##  | 
Attendees:        
Attached files:  

Notes
- Reverse DNS for labeling everywhere.
- Spec Release Timeline
  - Extra meetings before 11/11 to review SEP backlog
- AI-Card

Action items
- 

### SEP Review
<table><tr><td><b>SEP ID</b></td><td><b>Title</b></td><td><b>Sponsor</b></td><td><b>Presenter</b></td><td><b>Modality</b></td><td><b>To be discussed in meeting</b></td><td><b>Votes</b></td></tr><tr><td>1442, revised (one-pager)</td><td>Make MCP Stateless (by default) (revised to exclude new sessions RPCs)</td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>1686</td><td>Tasks</td><td></td><td>Luca Chang</td><td></td><td></td><td>Accepted</td></tr></table>



##  | 
Attendees:        
Attached files: 
Notes
- 

Action items
- 
### SEP Review
<table><tr><td><b>SEP ID</b></td><td><b>Title</b></td><td><b>Sponsor</b></td><td><b>Presenter</b></td><td><b>Modality</b></td><td><b>To be discussed in meeting</b></td><td><b>Votes</b></td></tr><tr><td>SEP-1686</td><td>Tasks</td><td></td><td>Luca</td><td></td><td></td><td></td></tr></table>



##  | 
Attendees:         
Attached files:  

Notes
### SEP Review
<table><tr><td><b>SEP ID</b></td><td><b>Title</b></td><td><b>Sponsor</b></td><td><b>Presenter</b></td><td><b>Modality</b></td><td><b>To be discussed in meeting</b></td><td><b>Votes</b></td></tr><tr><td>SEP-991</td><td>Enable URL-based Client Registration using OAuth Client ID Metadata Documents</td><td>Paul Carleton</td><td>Paul Carleton, Aaron PareckiSlides</td><td></td><td></td><td>7 Accepted1 Accpeted with changes (Accepted), Concerns around securing desktop</td></tr><tr><td>SEP-1330</td><td>Elicitation Enum Schema Improvements and Standards Compliance</td><td>Cliff Hall</td><td>Cliff Hall, Tapan Chugh</td><td></td><td></td><td>4 Accepted<b>4 Accepted with Changes, </b>tie break: accepted with changes.</td></tr><tr><td>SEP-1391</td><td>Long-Running Operations</td><td>Nick Aldridge</td><td><i>(</i><b><i>Non-voting</i></b><i>)<br>Directional discussion</i></td><td></td><td></td><td></td></tr><tr><td>SEP-1306</td><td>Binary Mode Elicitation for File Uploads</td><td>Den Delimarsky</td><td><i>Den</i><i>(</i><b><i>Non-voting</i></b><i>)</i><i>Directional discussion</i></td><td></td><td></td><td></td></tr><tr><td>SEP--1303</td><td>Input Validation Errors as Tool Execution Errors</td><td>Adam Jones</td><td></td><td></td><td></td><td>Async</td></tr><tr><td>SEP-1533</td><td>Metadata in Resource Read Response</td><td>David Soria Parra</td><td>Peter Alexander</td><td></td><td></td><td>Async</td></tr></table>
### Action Items
- Action items



##  | 
Attendees:        
Attached files:  

Notes
- Follow ups from previous reviews
  - JSON Schema
  - Version management
- SEP Review

NickC Notes [Async]
- SEP1422 ✅ I don’t personally align with the motivation for the Stateless design, however I do approve of it. It decouples fairly core concepts in a way that is meaningful and I think affords future development. It also finally resolves session lifetime in a meaningful way.
- SEP986 🟨I do like the idea of having a format for tool names. I think in general we need to be better on field limitations across the board, and having this as recommendation (not requirement) is good. I would however prefer a longer limit than 64 characters, and also think case sensitivity is a bit odd and best avoided.
NickA Notes [Pre-Read]
- SEP1422 🟨: I like the idea of statelessness. This is something that I feel is critical to do for the prolonged success of MCP and in working on SEP1391 for async we have run into a lot of nuances related to statefulness. However, I am concerned that we are now mixing transport-layer and data-layer notions of sessions. I was not clear if the new session management RPC methods can be decoupled from this and whether we can instead just take a change to describe how stateless servers/clients can avoid initialization.
- SEP986 🟨: I would like a clearer motivation for this change given it is a big breaking change. Other than just reducing ambiguity, are there practical issues that clients are running into that are resulting in this. For example, many models limit tool names to <=64 chars so I would think that would be one motivation. Do we have insights from client implementors over here?
### SEP Review

<table><tr><td><b>SEP ID</b></td><td><b>Title</b></td><td><b>Sponsor</b></td><td><b>Presenter</b></td><td><b>Author</b></td><td><b>Modality</b></td><td><b>Issue Link</b></td><td><b>To be discussed in meeting</b></td><td><b>Votes</b></td></tr><tr><td>SEP-1442</td><td>Make MCP Stateless (by default)SlidesOpen Preview</td><td></td><td></td><td>Shaun Smith, , Mark Roth, Harvey Touch</td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1442</td><td></td><td></td></tr><tr><td>SEP-986</td><td>Specify Format for Tool Names</td><td></td><td>Kent Dodds</td><td>Kent Dodds</td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/986</td><td></td><td>AcceptedYes: 5No: 1Absent: 2</td></tr></table>
Action items

- Paulc notes on sep-1442
  - Definitely in favor of:
    - Removing mandatory handshake
  - Discussion questions:
    - Why have sessions be client controlled? Typical web behavior is set-cookie on the server.  That seems more familiar, and the server seems in a better place to determine if a session is needed to support a tool.
    - Client capabilities request (for server->client streaming): why does this need to change? Seems like we could leave this as is with the current “GET on the mcp endpoint” – if the client sends the GET, it has the capability
    - Minor
      - Why have HTTP and STDIO differ? (discussion in the issue on this)
        - Seems better to use _meta all the time and optionally duplicate in HTTP headers (or required?) – then SDK’s can have more stuff be transport agnostic.
      - Discovery – would like this to line up with the few notions of server identity floating around (registry, mcp.json, etc.).  Not a strong opinion on what the schema is, just that we use the same one in all the places.



##  | 
Attendees:        
Attached files:
Notes
- : I would like to spend more time talking about working groups and the setup for them, to ensure we can scale ourselves. In addition I want to talk about async votes.
  -  Additional optional meeting for asynchronous voting 
  -  Work on more powerful working groups 
- : What’s needed for spec release. Timing for spec release?
  - November 25th

**Action items**
****
### SEP Review (will cap to 4 in ascending order)

<table><tr><td><b>SEP ID</b></td><td><b>Title</b></td><td><b>Sponsor</b></td><td><b>Presenter</b></td><td><b>Author</b></td><td><b>Modality</b></td><td><b>Issue Link</b></td><td><b>To be discussed in meeting</b></td><td><b></b></td></tr><tr><td>SEP-1309</td><td>Specification Version Management</td><td></td><td></td><td></td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1309</td><td></td><td></td></tr><tr><td>SEP-1302</td><td>Formalize Working Groups and Interest Groups in MCP Governance</td><td></td><td></td><td>Tadas</td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1302</td><td></td><td></td></tr><tr><td>SEP-834</td><td>Support full JSON Schema 2020-12</td><td>Ola</td><td>John</td><td></td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/834</td><td></td><td></td></tr><tr><td>SEP-835</td><td>Update authorization spec with default scopes definition</td><td></td><td></td><td></td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/pull/835</td><td></td><td></td></tr></table>

##  | 
Attendees:        
Attached files:  

Notes
- 

Action items
- 



##  | 
Attendees:        
Attached files:  

## Agenda
### SEP Review (will cap to 4 in ascending order)
- Async:
  - Thread per SEP
    - Sponsor comes in, gives an overview
    - Wait 1-2 days for concerns
    - Start vote for 3 days

<table><tr><td><b>SEP ID</b></td><td><b>Title</b></td><td><b>Sponsor</b></td><td><b>Presenter</b></td><td><b>Author</b></td><td><b>Modality</b></td><td><b>Issue Link</b></td><td><b>To be discussed in meeting</b><b></b></td><td><b></b></td></tr><tr><td>SEP-975</td><td>Transport-agnostic resumable requests</td><td>Jonathan Hefner</td><td>Jonathan Hefner</td><td>Jonathan Hefner</td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/975</td><td></td><td>Declined</td></tr><tr><td>SEP-973</td><td>Expose additional metadata for Implementations, Resources, Tools and Prompts</td><td>David Soria Parra</td><td>David Soria Parra</td><td>jesselumarie</td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/973</td><td></td><td>Accepted with changes</td></tr><tr><td>SEP-985</td><td>Align OAuth 2.0 Protected Resource Metadata with RFC 9728</td><td>Paul Carleton</td><td>Paul Carleton</td><td>sunishsheth2009</td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/985</td><td></td><td></td></tr><tr><td>SEP-990</td><td>Enable enterprise IdP policy controls during MCP OAuth flows</td><td>Aaron Parecki</td><td>aaron.parecki@okta.com</td><td>aaron.parecki@okta.com</td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/990</td><td></td><td>Deferred</td></tr><tr><td>SEP-1024</td><td>MCP Client Security Requirements for Local Server Installation</td><td>Den Delimarsky</td><td>den.delimarsky@microsoft.com</td><td>den.delimarsky@microsoft.com</td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1024</td><td></td><td></td></tr><tr><td>SEP-1034</td><td>Support default values for all primitive types in elicitation schemas (TO BE CONFIRMED)</td><td>Shaun Smith</td><td>Shaun Smith</td><td>Shaun Smith</td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1034</td><td></td><td></td></tr><tr><td>SEP-1046</td><td>Support OAuth client credentials flow in authorization</td><td>Darin McAdams</td><td>darinm@amazon.com</td><td>darinm@amazon.com</td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1046</td><td></td><td></td></tr><tr><td>SEP-1300</td><td>Tool Filtering with Groups and Tags</td><td>Cliff Hall</td><td>Cliff Hall</td><td>Cliff Hall</td><td></td><td>https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1300</td><td></td><td></td></tr></table>
### Other Agenda
- Financial Working Group
- Retrospective:
  - Working Group: What defines a working group? Who should be part of MAINTAINERS.md?
  - SEP Process
- Focus:
  - Async Tasks
  - Server discovery

Notes
- 

Action items
- 



##  | 
Attendees:         

## Agenda
- Poll: In Person Meeting
  - New York: Alex is offering at Block, and OpenAI can also.
    - dsp can’t do: 18th August - 25th August, 3rd August
  - London: October 2, 2025
  - In general share when people are in SF
- Going through open SEPs
  - 
  - Decision:
    - All SEPs are numbered by issue id: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1045 
- MCP Core Design Principles : 
- Discord proposal
- SDK problems
  - SEP for SDK requirements.
- Blog
- Going through Roadmap
- Async pre-read of SEPs before:
  - Next time: I send out an email with SEPs, agenda 24h in advance.
## Notes
_Prior meeting’s notes:_ 

## Questions

## Action Items
- Clarify SEP numbering: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1045 

##  | 
Attendees:        

Agenda
- [dsp] How do we want to spend the time
- [dsp] Governance
  - Working Groups
  - Discord
  - Review Timelines
  - SEP Process
- [dsp] Next Specification Release
  - Time based is great.
  - We might be a release candidate.
- [dsp] Top Priorities for MCP
  - Semantic Versioning -> Can this be a SEP?
  - Map between which SDK supports which spec.

Notes
- https://github.com/modelcontextprotocol/modelcontextprotocol/pull/931

Questions:
- MCP’s design philosophy: What are they? What are the design philosophies
  - Also, what are the boundaries of MCP - what goes into MCP and what not
  - Should we come up first with a charter around these?
- What is our process for handling an issue where the core maintainers have different opinions?
- For SEPs, what are the specific acceptance criteria?
  - [paul] what’s the first SEP we want to run through the process?
- Communicating with public
  - What specific information from core maintainer meetings should be made public?
  - Should we publish regular status updates to the community?
- What's the review timeline for SEPs once they have sponsors?

Action items
- SEP-002: Design Philosophy (Lean into the lightweight process)
- Nick A: SEP for Semantic Versioning
- Den: Evolution of discord proposal
- Paul: Spec compliance checker proposal
- Everyone: Review SEP-001 and accept/request review.
- Find someone from the NYC folks to find us space for an in-person meeting in NYC


