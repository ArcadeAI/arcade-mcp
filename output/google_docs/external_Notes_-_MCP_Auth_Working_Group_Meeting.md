---
title: "[external] Notes - MCP Auth: Working Group Meeting"
id: 1urCZnGC3rxMMQ2WmRX8r3oOhZ2NLQEcsT5fnGAzzqSI
modified_at: 2026-03-11T21:00:47.608Z
public_url: https://docs.google.com/document/d/1urCZnGC3rxMMQ2WmRX8r3oOhZ2NLQEcsT5fnGAzzqSI/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->

## 
### Attendees
- Tag yourselves
- 
- 
- 
- Pamela Dingle
- 
- 

### Agenda
- Working group readouts
  - Tool Scopes
    - (not here)
  - Fine-grained Authz
    - Broken down into scenarios, and start to prioritize what’s  impactful
    - Next meeting is next week to zero in on a SEP
      - Solutions still in the air (RAR on the table)
  - Mixup Protection
    - SEP for iss parameter on OAuth callback.
    - Waiting on IETF next week, would like it to be accepted to OAuth 2.1
    - Resource URL proposals are floating around, wanted to see how that settles at IETF
      - Some deconflicting / reconciliation to happen next week.
  - Profiles
    - DPoP (SEP 1932), WIF (SEP 1933)
    -  The immediate next steps are to:
      - Develop a conformance test.
      - Create a reference implementation
- SEP pipeline
  - Accepted:
    - (wils) SEP-2207 - OIDC-flavored refresh token guidance
  - Draft:
    - SEP-2352: Clarify authorization server binding and migration
    - SEP-2351: Explicitly specify RFC 8414 well-known URI suffix for MCP
    - SEP-2350: Clarify client-side scope accumulation in step-up authorization
    - SEP-837: Update authorization spec to clarify client type requirements
    - (docs): Update documentation for MCP security best practices

### Group Agenda Items
- [pam]Standards work in AAIF vs. here
  - People may be going to AAIF meetings thinking it’s standards writing, that should actually come to auth-ig
- [max] Multi-agent systems and token downscoping
  - https://datatracker.ietf.org/doc/draft-song-oauth-ai-agent-collaborate-authz/
  - https://datatracker.ietf.org/doc/html/draft-li-oauth-delegated-authorization-01
  - 
- [tristan] Tool annotation extension guidance, overlap / relationship with things like RAR
  - [tristan] I misread the expression types in the latest RAR proposal, as a way of talking about schema validation it's useful. 
- .
- .

## 
## Attendees
- **_Tag yourselves_**
- 
- Atul Tulshibagwale
- Kryspin Ziemski
- 
- Martin Besozzi
- Stephen Halter
- Pieter Kasselman
- Victor Lu
- Ervis Shqiponja - 
- 
- 
- Emily Lauber 
- 
- Aaron Parecki
## Top of mind
- Extension - mapping MCP tool parameters to AuthZen. There’s an issue in ext-auth.
  - Example for experimental: https://github.com/modelcontextprotocol/experimental-ext-interceptors 
  - Some of the extensions here are not client-to-server items. CC/OAuth/Client-To-Server pieces that are critical.
  - If we identify something that has no client impact - do we need to even standardize it over MCP in any capacity?
  - Most base OAuth specs are client-to-server, but there are a lot of things added that do not really touch clients.
- **Proposed topic:** Discussion on how to add or describe AS behavior in the MCP spec. Will impact the Mix Up Protection WG work. Inspired by this comment https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2207#issuecomment-3857978027 
  - AS behavior to send the issuer claim. What is the guidance?
  - RT SEP - mostly in OAuth 2.1, we just need some additional pieces lined up for MCP.
  - Slow-walk SHOULD to MUST with spec releases for issuer
- **Proposed (mini) topic: **Should we recommend AGAINST custom header auth for MCP servers?
- From Ervis: Is there any standard approach on how the MCP Client can obtain two tokens from two different Authorization Servers? The main use case I am looking for is where the MCP Servers are behind a MCP GW. The MCP GW needs to validate one token against one Authorization Server, and the server itself (usually 3-rd party) needs to validate against some other Authorization Server.
  - We may not get to this, but could look at some docs if there are any. 
- Placeholder
- Placeholder
- Placeholder
- 
##  | 

### Attendees
- Tag yourselves
- …
- 
- 
- 
- 
- 
- 
- @Emily Lauber
- 
- 
- 
- Yaron Zehavi
- Pieter Kasselman
- 
- Stephen Halter
- Jens Ernstberger
### FYI’s
- New Auth Working groups kicking off
  - Recap working group vs. interest group
  - Groups
    - Tool scopes (led by: Sam Morrow)
    - Fine-grained auth (led by: Nate Barbettini)
    - Mixup protection (led by: Emily Lauber)
    - Continuing:
      - Profiles (w/ DPoP, workload identity federation)
  - Question:
    - Separate discord channels?
- 
### Group Agenda Items
-  [ Max ] Mixup protection (make iss required) in OAuth 2.1 
  - OAuth 2.1 discussion in this latest email thread: https://mailarchive.ietf.org/arch/msg/oauth/po5z5bC07eaYvxJf2i8a8sXo9AY/ 
  - Consider adding more voices in support of iss required on the thread above
  - Will be discussed further in the Mix Up Protection WG and next steps defined there 
-  [ Yaron ] RAR Metadata discovery and WWW-Authenticate signaling
  - [Max] Is this https://datatracker.ietf.org/doc/draft-lombardo-oauth-step-up-authz-challenge-proto/ ? Or something related?
  - [ Aaron ] related: https://datatracker.ietf.org/doc/draft-zehavi-oauth-rar-metadata/ 
  - [Max] How does the client know what values to put into the schema? Outside of trivial cases. Edit: Oh I see it is returned in authorization_details
  - One previous related mailing list thread: https://mailarchive.ietf.org/arch/msg/oauth/s0aGBOp178lTQpMa4VewOOMlync/ 
-  [Pieter] Updates to the DPoP and Workload Identity Federation SEPs were published:
    - SEP-1932: DPoP Profile for MCP (https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1932) 
    - SEP-1933: Workload Identity Federation (https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1933)
-  [ your name ] your topic
-  [ your name ] your topic
-  [ your name ] your topic


Action items
-  Create discord channels
-  Scoot this meeting to monthly
-  to try to figure out discord role for calendar editing!
- @emily  Chime in on iss being required. Potential action item for Mix Up Protection WG to have a formalized response to OAuth thread 
- @Nate make sure Yaron is included in fine grained auth WG / Discord
- organize vote on new ext-auth additions 
- post notes as discussion (will do when back ) 

## 
## 
Notes:
- Attendees
  - Tag yourselves
  - 
  -  
  - 
  - Brian Campbell
  - Matt Cooper
  - Emily Lauber
  - Aaron Parecki
  - Darin McAdams
  - Kryspin Ziemski
  - 
  - 
    - Discord invite: https://discord.com/invite/6CSzBmMkjX 
  - Darin McAdams (darin@defakto.security)
  -  **😺**
  - 
  - Tyler Leonhardt
  - 
- FYI’s
  - [Max] We rolled out `iss` query param support last week - very easy to do from the IDP side as an implementor. Everybody should do this ;)
  - [paulc] claude.ai supports CIMD now
- Group agenda items
  -  [Darin/Pieter] Next steps for DPoP and Workload Identify Federation (draft specs)
    - DPoP: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1932
    - Workload Identity Federation: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1933
    - [Brian] I still struggle with requirements around content digest with DPoP - not sure if the juice is worth the squeeze (notetaker’s note - paraphrasing aggressively)
    - [Pieter] The PR is written confirming to the new format. We have a separate document with a lot more detail. How should we combine those?
    - [Darin] SEP process has existed but we had prior art here. SEP process has also changed to be a pull request. It has been very confusing.
    - Are we expecting this to live in ext-auth or MCP? SEP currently exists in MCP spec
    - Not sure if following all the paperwork is useful or helpful if it is all the same people reviewing throughout
    - Any specific outcomes on process? Or sort out details later.
    - **Decision: Sort out details later. Fine for SEP to live in core spec but to land in ext-auth later.**
  -  [Emily] Issuer validation followup
    - Re: https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1721 
    - Is this mandatory yet? Nope. We are considering adding it as mandatory within the MCP spec. One of the working groups will be taking a look at mix-up attacks in 2026
    - There is wide agreement on the value of this work
  -  [John] Did we end up with a group thinking about “tool scopes”? (from last meeting’s agenda)https://meet.google.com/usc-ccdw-oig
    - Den leading. Will find first working group meeting time in January
    - WG channel not spun up yet
    - We have anti-tool scope people and pro-tool-scope people and we need to get them in the same room
  -  Get more clarity on Identity Assertion Auth Grant from the client’s perspective. What should clients do to light this up?
    - [Tyler] I wanted to go implement this on the client side but wasn’t really sure what the requirements were for it. Want to learn a little more about this from a client implementer perspective.
    - If you’re signed in, you can discover MCP servers based on your signed in account
    - [Aaron] VSCode is unique because folks don’t usually sign in to it and you need to figure that out.
    - [Aaron] Working on a spec to solve that particular discovery question. Karl posted the spec to IETF yesterday. We (Okta) are likely building an endpoint to do that in the future as well.
    - We can create a different story for the MCP discovery context (e.g. using directories or registries or something else) separate from the SaaS context
    - Need a mechanism to determine auth for each server in the registry
    - [Aaron] Let’s take this to a smaller working group and explore it further
    - Karl also posted the spec to the Discord, take a look there!
    - [Paul] We need 3 parties for this to work - IDP, Client, and AS. Do we have all 3?
      - [Brian] Ping can kind of be made to support both the IDP and AS side with a little bit of fidgeting. Better support is coming.
      - [Max] Auth0 has beta support. Stytch is working on developing support soon as well.
      - [Wils] Okta had announced several ISV partners at their conference this year - unclear what is live today
      - [John] Asana is considering it as an AS
    - [Paul] There is a draft for the Python SDK. Also if anyone is passionate about writing a conformance test that would be very helpful
    - 
	

## 
## 
Notes:
- Attendees
  - 
  - 
  - 
  - 
  - 
  - 
  - Darin McAdams 
  - 
  - victorjunlu@gmail.com
  - EmilyLauber@microsoft.com
  - 
- FYI’s
  - Spec release shipped! 🎉 [best link for sharing?]
    - https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/ 
    - https://aaronparecki.com/2025/11/25/1/mcp-authorization-spec-update
    - https://den.dev/blog/mcp-november-authorization-spec/ 
  - Transport “onsite” next week, expect decisions on transport things after that, mostly don’t think it will affect authz.
- Group agenda items 
  -  [pcarleton] Working group spin-up
    -  "proof of possession" (or "mitm prevention?"): covering DPoP vs. http request signing, and other mixup /mitm scenarios, like resource parameter on callback [Darin: Can give an update. In plan for auth-profile-wg]
      - Mixup prevention
      - Resource parameter in oauth callback - 
      - https://datatracker.ietf.org/doc/draft-mcguinness-oauth-resource-token-resp/
    -  "tool scopes": pre-declaring required scopes, and also supporting mid-tool call scope  challenges
      - [max] How much of this is in support of Apps usecases?
      - [John Baldo]  have to drop but interested in this
      - [Nate B.] Definitely interested in this also
      - [Simon R] me too
      - [Max] Me too - call it scope hints instead and I’ll be happy
      - https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1488 
    -  (more open-ended on this one): token exchange / consent-fatigue reduction: how do we get separately scoped / revokable access per "agent"/conversation w/o it being awful? how do we make "2nd hop" setups less tedious?
      - [Nate B.] Interested in collab'ing on this as well
      - [Simon R] Also mes
      - [Aaron P] +1
      - [Wils D.] +2
  -  [pcarleton] Working group spin-down
    - Registration
    - Devx
    - profiles 
  -  [pcarleton] CIMD + OAuth mixup prevention (iss parameter, diff URL per AS)
    - https://datatracker.ietf.org/doc/rfc9207/
      - https://www.ietf.org/archive/id/draft-ietf-oauth-v2-1-13.html#name-mix-up-defense-via-issuer-i ← referenced here in oauth 2.1
      - https://www.rfc-editor.org/rfc/rfc9700.html#section-4.4.2.1
    - In OAuth 2.1 - security considerations around OAuth mix up attacks. Prevention mechanisms:
      - Different redirect URLs per AS / issuer. E.g. don’t accidentally send zoom’s auth code to google
      - Check iss query param in redirect URL
        - Anticipate substantial challenge with rolling this out
    - We don’t mention this at all in MCP spec today. 
    - Interop with CIMD
      - You _could_ generate a unique CIMD doc for each issuer, but that isn’t a great practice. Easy for people to start misusing it
      - Also means we have many different client IDs for the same client, which could make interesting things down the line harder to pull off (e.g. tracking client usage across many different ASs)
    - Maybe we should put this in security best practice and conformance testing
  -  [Aaron] JWT Authorization Grant for non-enterprise use cases
    - Enterprise managed authorization profile extension has two parts
      - Client exchanges ID token for JWT auth grant
      - Client exchanges JWT auth grant for access token
      - Everything is under the same IDP, very clean well defined trust boundaries
    - At IETF - we discussed having _something else_ issue the ID JAG. Why does it have to be an enterprise IDP? Couldn’t it be ____
      - It _could_ be anything however we can’t just point to the RFC and say “do it” because the RFC doesn’t define trust relationships 
      - Useful to pull on this thread a little bit more. Smithery implemented something like this - they create JWT, they send it to the client to take to the API. Trust relationship between Smithery and API since Smithery is running the platform. But Smithery is _not_ an enterprise managed IDP
      - Enough people with enough usecases that it is actually worth pursuing 
      - “If my MCP server is in front of some other API, how do I get a token for the downstream API?” -> possibly also solved by this
        - MCP Server itself can generate its own JAG (??) and use to access downstream API, or could exchange its own access token for a JAG for another access token
    - Does this change anything about the MCP client <-> Server flow or is it a pattern?
      - Might reduce use of elicitation
      - Might also be explicitly out of scope
      - Better user experience than URL elicitation (says Wils! He’s allowed to) since consent can sometimes be pre-established. For non-enterprise usecase we need to explain and explore more here
    - Does this simplify client registration story? Do we still need client IDs if we have JAGs?
      - Yes, use CIMD
  -  [Darin] Cut an official release for ext-auth to coincide with core release?
  -  [Max] Applicability of MCP OAuth profile outside of MCP?
## 

Notes:
- FYI’s
  - Conformance testing
    - [paul] If you have thoughts please find me in the discord channel
  - URL elicitation
    - [dd] we should label as experimental as well to align it with tasks
    - [nate] Will experimental label hinder adoption?
    - [dd] Not worried from a client support standpoint - but the notifications / tasks / setup needs to converge, not diverge
    - [paul] Should have it on lists for sdks to implement, and should be in conformance tests. Just need to switch from notifications to tasks in the future & let folks know that is coming
    - [nate] so long as vscode is cool I'm cool 😛
    - [simon] elicitation support is pretty bad today, I'm worried that experimental label will not help at all here - also there is a mismatch with tasks because of how it resolves
    - [dd] will be officially supported sdk feature with a lot of high demand behind it
    - elicitation support today is p bad - only IDEs support it now (Cursor, VSCode). Claude, etc. doesn't support it today
    - [max] URL elicitation comes up waaay more often in convos compared to classic elicitation
    - [dd] plan is to start making the process a lot more controlled in the new year, avoid breaking changes going forward. Not going to be "slower" but will be "more controlled" compared to current state
      - More experimental / extension features coming down the pipe next year - expect the label to be a common thing
    - [nate] Could we label just the notification mechanism as experimental, or do we need to label the whole elicitation subfeature as experimental?
      - [paul] Just the notification mechanism
      - [nate] yeah that makes sense - we only need to swap out the notification mechanism once tasks are solidified
    - 
- Group agenda items
  - 
  - 
  - 
  -  resource params - normalised?
    - [simon] should we be normalizing when we compare resource URLs?
    - [paul] summary of current threads: 
      - trailing slash vs not issue (JS sticks one on where it shouldn't) 
      - Whether to match on a base URL for MCP
      - URL encoding (is there a security hole floating around around normalization?)
    - [paul] For conformance test - give you some definitely invalid ones and some definitely valid ones
    - [tobin] - what is happening in the transport group and are we going to use different URLs going forward? e.g. /mcp or /sse ? Is the transport group doing anything there that we should think about?
      - [simon] one proposal to make each thing a unique URL so you can resume them, not sure if it will play out
    - [paul] Need to do prefix matching on the path, already some ambiguity on resource identifiers for PRM. If you have multitenant, maybe your resource is just your tenant
    - [dd] you're looking for the server you're connecting to, which is the full path
    - [paul] it's fine if it is super specific, you just need a super specific PRM. then the logic is more complicated on the AS for what Resource Parameter it wants to accept
      - [dd] that's outside of our domain right now, AS can do whatever it wants
      - Path itself is not set in stone - doesn't need to be /mcp
      - [max] Lots of MCP servers don't use /mcp today btw
    - [paul] Similar to scopes metadata in DCR response - we are no longer enforcing that in the client library side of things. Maybe convo is slightly different, we want clients to not send a token for 
      - https://datatracker.ietf.org/doc/draft-mcguinness-oauth-resource-token-resp/
  -  test suite w/ mcp-jam
    - [tobin] It would be fun to merge some of the conformance testing work with the inspector v2 
    - mcp-jam also has a really nice auth debugging flow
    - we should merge all this together
      - https://www.mcpjam.com/blog/oauth-debugger
  -  CIMD caching?
    - [tobin] Now that we have CIMD, how does caching work?
    - [max/den] follow Cache Control Headers, pick a value that makes sense as a default
      - In test, maybe don't cache at all
      - In prod, we (stytch) are doing like 15 minutes, do what makes sense for you 
## 
## Nov 5, 2025
Attendees: tag yourself please  
Notes:
- FYIs
  - Clarification: Don’t fallback to root for AS metadata discovery
    - https://modelcontextprotocol.io/specification/draft/basic/authorization#authorization-server-metadata-discovery 
      - Path:
        - OAuth 2.0 Authorization Server Metadata with path insertion: https://auth.example.com/.well-known/oauth-authorization-server/tenant1
        - OpenID Connect Discovery 1.0 with path insertion: https://auth.example.com/.well-known/openid-configuration/tenant1
        - OpenID Connect Discovery 1.0 path appending: https://auth.example.com/tenant1/.well-known/openid-configuration
      - No Path (but don’t fallback to this if your issuer has a path):
        - OAuth 2.0 Authorization Server Metadata: https://auth.example.com/.well-known/oauth-authorization-server
        - OpenID Connect Discovery 1.0: https://auth.example.com/.well-known/openid-configuration
- Group agenda items
  -  Conformance testing
    - https://github.com/modelcontextprotocol/conformance 
  - Go/no-go for progress tracking in URL Elicitation SEP
    -  will follow up on investigating a new notification type, or simply removing progress from the SEP before release
  - 
  - 
  - 
  - 


##  | 
Attendees: tag yourself please 
 

Notes
- FYI’s:
  - CIMD metadata accepted into core spec and implemented in VS Code
  - 
- Group Agenda Items
  -  MCP Client initiated user registration (thread)
  -  CIMD guidelines
  -  HTTP Signatures (Auth) - determine path forward
  - 
  - 
  - 

Action items
- [Community] Den will call for reviews on CIMD tutorial docs. Keep an eye out and give feedback.
- [Paul] Aged SEPs, in particular HTTP Auth proposal; close out?

**Notes**
- On MCP client-initiated user registration, this _feels _like the Enterprise profile that was discussed earlier.
  - There are major privacy implications here about the fact that this would be “silent” without consent.
  - Without consent flows, this is not something that we can really get through, but then we’re really just implementing OAuth.
  - You can accomplish all of this today, using existing MCP + OAuth, this is really just a convenience wrapper
  - Account creation over API is a big problem - TOS and Consent / Bot Accounts, etc. are quite annoying
  - Cannot be a widely open API - probably want direct relations between the account creator and the backend service. If we get to that point, do we even need a standard for this bespoke thing?
  - No -nos:
    - Form to collect password and then sign up in the background using a JS scripted headless browser
    - POST in the background for signup
- CIMD guidelines
  - We need a guide for CIMD that has implications for client implementers and server implementers as well as practical examples 
- 
## 
##  | 
Attendees:           

Notes
- FYI’s:
  - X-auth repository for authorization extensions
- Group Agenda Items
  -  Scopes follow up re: DCR field
  - CIMD vote coming up
  -  securitySchemes / SEP-1488 thoughts
  - 
  - 
  - 
  - 
  - 
  - 

Action items
- 



##  | 
Attendees:          

Notes
- Notes from last time: https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1457
- FYI’s
  - Spec release date aiming for November (blog here)
  - New #extensions channel in Discord for tying together a few threads
  - Upcoming changes
    - WWW-Authenticate clarification (landed)
      - https://github.com/modelcontextprotocol/modelcontextprotocol/pull/971  
    - Default Scopes (835) (coming soon)
  - IAG was accepted as IETF working group draft document
  - CIMD call for adoption has just started (2 weeks from Monday will be when call ends)
    - IETF lifecycle: 
      - Someone writes a document
      - Convince a working group that it’s worth solving as a working group
      - If goes well, changes to “adopted working group draft”
- Group agenda items
  -  Authorization Guide
  -  Client Type Requirements SEP
  -  conformance tests
    - Olivier’s prototype
    - Negative tests for not doing certain things
      - Resource parameter as an example
    - Difference between certification vs. helping you build
      - Amount of debugging information shown
      - Helping you build is more work to make it useful vs. just binary output
    - Initial tests:
      - Go through SDK’s and find the discrepancies today, and start from that
        - 
      - C# vs. typescript:
        - Serialization, trailing slash thing localhost:3000 vs. localhost:3000/
      - Fastmcp for auth is different. Confused deputy example
    - Java example
  -  software statements approach for desktop apps (time permitting)
    - https://discord.com/channels/1358869848138059966/1419726663977009334 
  -  [add yours here] 
  - 

Action items
- 



##  | 
Attendees:                   

Notes
- [x] [reminder]: Start transcription – notes will be posted as a github issue after the meeting.
- Welcome new folks! 
  - [async intros here]
  - [your name] what you’re up to / what you want to get out of this
  - [Simon Russell] we’re building an agent identity platform at Prefactor, MCP auth is the first part of that; we’ll be tracking the changes to MCP pretty closely so here to see what’s going on/help out where I can
  - [kele (Damian Bowater)] Working on Identity and Access Control at Google, recently a lot of it around AI Agents. Strong focus on making things secure without developers having to do much. :) 
  - [Aaron Parecki] working on OAuth at Okta, and co-author of OAuth 2.1
  - .
  - [Paul] working on MCP at Anthropic, focused on auth and security. Hoping to get some good momentum with this group towards some of the common pain points we’re seeing.
  - [Wils Dawson] building Arcade.dev. Looking forward to making MCP more secure and usable for devs
  - [Geoff Goodman] Collaborating with colleagues at OKTA / Auth0 on figuring out MCP Auth. Generally interested in the challenges in this space. Looking to forward efforts that facilitate downstream auth.
  - [Andreas] DevOps engineer at QuantStack mostly working on System and OAuth integration involving JupyerHub.
  - [Rene Leveille] Working on identity technologies at 1Password. Joining to see how auth and credentials can be secure with AI agents.
  - [Ricky Padilla] Working on auth tech at 1Password, also joining to see how auth and credentials can be secure with AI agents.
  - [Yann Jouanin] working on m2m and delegation pattern for auth in Entreprise WG
  - [Tyler Leonhardt] VS Code dev. Owner of MCP auth experience in vscode.
  - [Den Delimarsky] Core Maintainer @ MCP, CoreAI @ Microsoft
  - [Nate Barbettini] Building Arcade.dev, previously at Okta. Strongly interested in promoting security best practices for MCP.
- Latest update on SEP’s
  - Quick recap of MCP spec principles: Simple, Minimal, Concrete
  - Client_credentials approved
  - Enterprise idp deferred
  - (links to other in-review, and drafts below)
- Splitting out into smaller Working groups
  - Too many attendees to have a super productive conversation in this big group, so I suggest we do smaller working groups that meet separately.
  - Evolving client registration 
    - (CIMD, software_statement, http req signing)
    - Chair: volunteer
    - Members: Aaron Parecki, Tyler Leonhardt
    - Interested party: Simon Russell, Den, Andreas Trawöger, , Darin McAdams, , , 
  - Making auth development easier
    -  (examples/how-tos, reference impl, testing suite)
    - Chair: Den (volunteering?)
    - Members: Andreas Trawöger, , 
    - Interested party: , Yann Jouanin Paul, Tyler Leonhardt, 
  - Formalizing auth profiles
    - (high security, enterprise, non-interactive)
    - Chair: Darin McAdams
    - Members: Aaron Parecki, , 
    - Interested party: ( (depends on the scope)), Den, Andreas Trawöger, , , 
  - Fine-grained authorization Fancy Scopes
    - (primitive authz, tool authz)
    - Chair:  (back )
    - Members
    - Interested party: Simon Russell, , Darin McAdams, Andreas Trawöger, , Tyler Leonhardt, 
    - Discussion
      - What is this
        - List of tools allowed to evoke
        - What parameters are they allowed to invoke
      - [kele's interpretation] **Except** what the MCP client needs to understand (e.g. what kind of OAuth scopes are necessary to invoke a tool)
      - Idea: Don’t get into FGA: openFGA, Cedar, Zanzibar. Tools for modeling resources  
      - Is there enough demand? Maybe too early for a WG.
      - SEP-850 – move to a guideline,  many ways to do authz, here’s how you could do it.
- SEP discussions (current auth drafts, auth in-review, auth accepted), keep to 5 minutes each  (if too many, we’ll vote and talk about the most voted). 
  - [kele] Updated . Still a bit rough, but more fleshed out. 
  - [Wils] URL Elicitation 
    - What’s the way to get this moved forward? 
    - 
  - https://github.com/modelcontextprotocol/modelcontextprotocol/pull/835 
  - [Simon Russell] Websockets https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1288
  - [paul] http req signing
- Other topics
  -  [Yann Jouanin] Should RFC 7192 be used in the Client_credentials/JWT auth context to help in key/secret rotation
  -  [darin] how to close old/unsponsored seps 
  -  [your name] your topic
  -  [your name] your topic
  - 

Action items
- Group chairs: schedule follow-ups on specific areas.
- to start a thread on reviewing old SEP’s and closing


## 
##  | 
Attendees:        
Attached files:  

Notes
- Recommendations on In-Review Auth SEP’s
  - Current list of in-review SEP’s (only auth one is WWW-Authenticate)
    - SEP-990: Enable enterprise IdP policy controls during MCP OAuth flows
      - How to mark as optional / profile specific
      - (also comes up with DCR endpoint, pre-registration, “high security profile”)
    - SEP-985: Align OAuth 2.0 Protected Resource Metadata with RFC 9728
      - Paul sponsoring, will present.
      - Meta-level: it’s fine for MCP to ratchet up things i.e. be more specific.
      - MUST -> MAY
        -  vs. SHOULD 
        - Arg for SHOULD: can’t do incremental auth
          - SHOULD means SDK’s will probably do it, MAY means most people won’t do it. 
        - Clients MUST (check for header, then fallback), servers SHOULD
    - Elicitation URLs?
      - https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1036
      - Demo on progress 
      - [duke] Agentic auth: elicitation for URLs
        - Providing another resource for the server
        - What about for the 1st party getting that?
          - WWW-Authenticate is one way to that, to request for more scopes
          - ^ this is only for the “1st leg MCP connection”
          - 
  - Current list of all SEP’s related to Auth (drafts)
    - Client Credentials flow
      - https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1046
      - Prefer asymmetric methods whenever possible
        - Prototype implementation?
        - Cognito – not yet
          - What about okta/auth0? Both support client authentication JWT’s
            -  (7523) – JWT represents a user’s authz (enterprise profile)
            - Other thing is “client authorization” as a JWT.
      - Strong demand, and implementation PR’s for it
      - In this situation, there is no user context. This is essentially creating a “service account” MCP client.
        - Key to emphasize, this is representing itself, not on behalf of a user.
- [kele] 
  - What is blocked / what can we not do now based on this?
    - isReadonly – risk-based decision about what to do
      - Not a reliable signal
    - User.profile scope is not built in.
      - Know ahead of time via the tool annotation whether the command will work
    - A few things to tease apart:
      - Client knowing ahead of time what it can call
        - Why not just filter them if they can’t do
      - Using scopes as the way they enforce things 
      - Servers that act as registries:
        - General tools available – make a plan, to get all the scopes to succeed.
    - How is this different from advertising scopes in resource metadata?
      - E.g. default scopes on resource
      - Resource might have multiple tools
    - Will clients go through finely scoped tokens?
      - Go through “view files” … and then will have to go through a 2nd flow?
      - **TODO(kele): Clarify the downscoping question. Do we expect MCP clients to get multiple tokens?**
- [darinm] Client registration debate: Pivot fast to Client URL instead of DCR?
  - https://github.com/modelcontextprotocol/modelcontextprotocol/issues/991 
- [paulc] Auth “profiles” to allow clients / servers to more clearly opt in to auth features
- [paulc] Threat model
- 




Action items
- 

## 
##  | 
Attendees:      

Agenda
- (first) Start transcription
- Intro’s / level setting on how we want to use this time
  - What’s blocking folks
  - Go through backlog of items
  - Scopes: associating tools with scopes
    - Properties of the tools (e.g. IoT devices)
- **Bigger topics**
  - Evolving DCR (see below) 
  - OIDC support more generally (see below)
- **Specific Proposals**
  - Enterprise Auth Profile (PR)
  - Default scopes / scopes_default (PR)
  - WWW-Authenticate MUST -> SHOULD (PR)
    - Notes: don’t flip the order for sure, also share implications on step-up auth.
- If time / areas to continue exploring:
  - Relax authentication requirements: e.g. non-OAuth Bearer Tokens / API Keys
  - "primitive auth" / "tool auth" / fine-grained auth
  - combination / delegation / obo identities for user+service account/agent workflows.


### Evolving DCR

In MCP auth, the user often provides an MCP Server URL to a generic MCP client (e.g. VSCode, Cursor, Claude Code). This makes traditional pre-registration of an OAuth client difficult because it requires coordination between Server developers and Client developers to have happened prior to the user entering the URL.

- Client developers don’t want to be responsible for pre-registering with 100’s of MCP servers and distributing client IDs and secrets
- User’s don’t want to go through a lengthy registration process individually, for each MCP server
- Server developers want to protect their users from phishing

“Open” DCR solves this situation, but adds additional risks around phishing, and operational burdens for Server developers.

The ideal situation is that you as the MCP server provider (or an enterprise user of your provider) can decide to allow an MCP client, and then it Just Works™, as in the user doesn't need to copy paste anything, and the client developer doesn’t need to change anything.

The paths to that world are:
1. (not great): Redirect URL allowlisting w/ DCR
1. (okay): DCR w/ software_statement
1. (better, but a bigger change): Client ID metadata  (i.e. client ID is a URL to metadata).

What those flows allow is the server to still gate what clients it accepts, but when it decides to trust one, it doesn't need to distribute new information to the client out-of-band, since the client is providing a trusted assertion that it is who it says it is (via the metadata URL or software statement).

**What path forward do we want to take for client registration?**
Recommendation: (2) & (3) i.e. encourage software_statements, and add optional support for client ID metadata.
### OIDC Support more generally
**Background**
We’ve added some support related to OIDC, but have not come out explicitly saying it’s a supported method of authorization.  To fully support it, we’d need to add more parameters to authorization URLs in SDK’s.

Support items accepted or in the queue
- ✅OIDC metadata support (PR)
- (pending) application_type support
- PR’s up for things like consent and nonce


Discussion Questions:
- What are reasons to add it vs. leave it out?
- Should we support sending id_token in the bearer field instead of access_token?
### Meeting notes
- **Aaron:** to move things forward on https://datatracker.ietf.org/doc/draft-parecki-oauth-client-id-metadata-document/, it'd be best to join IETF meetings and join the discussions.
### Action items

- 

As for topics...  we have a handful of small to large spec things pending that would be good to smash through (some of this can be async, but sync as a backstop):
OIDC metadata endpoints, in addition to OAuth authorization server
Enterprise Auth profile
scopes_default
application_type clarification

There's also a few more nebulous topics to discuss:
- Allow non-oauth in MCP 

