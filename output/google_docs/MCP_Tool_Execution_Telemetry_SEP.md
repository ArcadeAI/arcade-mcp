---
title: "MCP Tool Execution Telemetry SEP"
id: 1_pQtzy0ISOGx78SoGTPKDGFkGikBPYnbkcWPyeuEj5I
modified_at: 2026-03-17T17:16:37.370Z
public_url: https://docs.google.com/document/d/1_pQtzy0ISOGx78SoGTPKDGFkGikBPYnbkcWPyeuEj5I/edit?usp=drivesdk
---

# OpenTelemetry Span Passback in MCP

<!-- Tab ID: t.7lyjwszbwtax -->

# MCP Server Execution Telemetry
# 

SEP: XXXX
Title: MCP Server Execution Telemetry
Authors: 
Sponsor: [TBD]
Type: Standards Track
Status: Draft
Created: 
Requires: SEP-414
PR: WIP




# 
# Abstract
This SEP defines a standard MCP capability that allows servers to return OpenTelemetry spans to clients in responses to service side operations. This covers tools/call and resources/read , the two MCP operations that involve opaque server side processing most relevant to cross-organization observability. Clients can then ingest these spans into their own observability backend, providing end-to-end distributed tracing across organizational boundaries without requiring a shared collector.
This SEP defines a delivery mechanism for a client visible trace slice, a server-selected subset of trace data that the server determines is appropriate to disclose to the requesting client. It complements SEP-414 by enabling the response-side return of execution spans. Together, these SEPs enable distributed trace stitching across organizational boundaries without requiring shared collectors or federated observability infrastructure.
Servers advertise the _serverExecutionTelemetry_ capability during initialization. Clients request span data via __meta.otel_ in _tools/call_ and _resources/read_ requests, and servers return spans under the same __meta.otel_ key in responses.

# Motivation
MCP enables agents to call tools hosted by MCP servers operated by different organizations. SEP-414 enables propagation of _traceparent_ into MCP servers. However, there is currently no standardized mechanism for servers to return execution telemetry to clients.
In cross-organization MCP scenarios, this creates a one-way observability gap:

- Tool execution appears as a black box: the client sees a single mcp.call_tool span,  everything the server does (auth checks, API calls, cache operations etc..) is invisible.
- Resource reads are equally opaque: resources/read can involve expensive server-side I/O, ACL checks, remote API lookups, and format conversion. When a resource read is denied or slow, the client has no visibility into why.
- Guardrail or runtime control decisions are not observable: when a server blocks a tool call due to policy denial or auth failure, the client has no structured visibility into which processing stage failed or why.
- Server-side latency breakdown cannot be stitched into client traces: clients cannot debug server-side bottlenecks or accurately attribute latency across the call boundary.
****
In traditional OpenTelemetry deployments, services export spans to shared or federated collectors. This model does not apply to many cross-organization MCP deployments:

- Server operators typically do not expose collector access to external clients.
- Clients and servers may use different telemetry backends with no federation.
- Server-side spans may contain sensitive infrastructure details unsuitable for external exposure.

This observability gap is particularly relevant for:
- Enterprise agents calling vendor-operated MCP servers which has become the de facto integration pattern.
- Multi-tenant MCP platforms serving customers with independent observability systems
- Compliance sensitive deployments requiring structured visibility into tool execution and control decisions

This SEP defines an explicit, opt-in mechanism for returning a minimal trace slice directly in MCP responses, without requiring shared infrastructure. Together with SEP-414, it enables a full-circle telemetry story for MCP.

# Specification

## Protocol Key
The capability is advertised as _serverExecutionTelemetry_ in the server's capabilities object. Request and response telemetry data is keyed under __meta.otel_ in tool-call messages.

1. Server Capability Advertisement
In the _initialize_ response, an MCP server that supports span passback MUST advertise:

<table><tr><td>{<br> "capabilities": {<br>   "serverExecutionTelemetry": {<br>     "version": "2026-03-01",<br>     "signals": {<br>       "traces": { "supported": true }<br>     }<br>   }<br> }<br>}</td></tr></table>








<table><tr><td><b>Field</b><b></b></td><td><b>Type</b><b></b></td><td><b>Description</b><b></b></td></tr><tr><td>version</td><td>string</td><td>Schema version (date based)</td></tr><tr><td>signals.traces.supported</td><td>boolean</td><td>Whether span passback is available (metrics may be supported too in future)</td></tr></table>
1. Client Request
Clients MAY explicitly request span passback via _meta.otel of a _tools/call_ request:

<table><tr><td>{<br> "_meta": {<br>   "traceparent": "00-abcdef1234567890abcdef1234567890-1234567890abcdef-01",<br>   "otel": {<br>     "traces": {<br>       "request": true,<br>       "detailed": false<br>     }<br>   }<br> }<br>}</td></tr></table>
<table><tr><td><b>Field</b></td><td><b>Type</b></td><td><b>Description</b></td></tr><tr><td>otel.traces.request</td><td>boolean</td><td><i>true</i> to opt into receiving spans in the response</td></tr><tr><td>otel.traces.detailed</td><td>boolean</td><td><i>false</i> = root + direct children only<i>true</i> = full span tree</td></tr></table>

The _traceparent_ field ([W3C Trace Context](https://www.w3.org/TR/trace-context/)) is passed alongside but outside the _otel_ key. Trace context propagation via _traceparent_ in MCP requests follows the mechanism defined in SEP-414.

**resources/read example**

The same __meta.otel_ mechanism applies to resource reads. The client includes telemetry options in the request, and the server returns spans alongside the resource contents.

<table><tr><td>{<br> "method": "resources/read",<br> "params": {<br>   "uri": "file:///data/report.csv",<br>   "_meta": {<br>     "traceparent": "00-abcdef1234567890abcdef1234567890-fedcba0987654321-01",<br>     "otel": {<br>       "traces": {<br>         "request": true,<br>         "detailed": false<br>       }<br>     }<br>   }<br> }<br>}</td></tr></table>1. Server Response
Servers return spans under _meta.otel in the JSON-RPC response.

**tools/call response example**


<table><tr><td>{<br> "_meta": {<br>   "otel": {<br>     "traces": {<br>       "resourceSpans": [<br>         {<br>           "resource": {<br>             "attributes": [<br>               { "key": "service.name", "value": { "stringValue": "mcp-weather-server" } }<br>             ]<br>           },<br>           "scopeSpans": [<br>             {<br>               "scope": { "name": "mcp-span-passback" },<br>               "spans": [ ... ]<br>             }<br>           ]<br>         }<br>       ]<br>     }<br>   }<br> }<br>}</td></tr></table>****
<table><tr><td><b>Field</b></td><td><b>Type</b></td><td><b>Description</b></td></tr><tr><td>traces.resourceSpans</td><td>array</td><td>Verbatim [OTLP JSON](https://opentelemetry.io/docs/specs/otlp/) <i>resourceSpans</i>, can POST directly to <i>/v1/traces</i></td></tr></table>****

**resources/read example**

<table><tr><td>{<br> "result": {<br>   "contents": [<br>     {<br>       "uri": "file:///data/report.csv",<br>       "mimeType": "text/csv",<br>       "text": "id,name,value\n1,alpha,100\n..."<br>     }<br>   ],<br>   "_meta": {<br>     "otel": {<br>       "traces": {<br>         "resourceSpans": [<br>           {<br>             "resource": {<br>               "attributes": [<br>                 { "key": "service.name", "value": { "stringValue": "mcp-data-server" } }<br>               ]<br>             },<br>             "scopeSpans": [<br>               {<br>                 "scope": { "name": "mcp-span-passback" },<br>                 "spans": [<br>                   {<br>                     "name": "resources/read file:///data/report.csv",<br>                     "spanId": "aaaa000000000001",<br>                     "traceId": "abcdef1234567890abcdef1234567890",<br>                     "parentSpanId": "fedcba0987654321",<br>                     "kind": 2,<br>                     "startTimeUnixNano": "1710000000000000000",<br>                     "endTimeUnixNano": "1710000000050000000",<br>                     "status": { "code": 1 }<br>                   }<br>                 ]<br>               }<br>             ]<br>           }<br>         ]<br>       }<br>     }<br>   }<br> }<br>}</td></tr></table>
****
1. Client Ingestion
The client reconstructs the OTLP envelope:
<table><tr><td>{ "resourceSpans": <traces.resourceSpans from response> }</td></tr></table>and POSTs it to its own OTLP collector at _/v1/traces_.

1. Span Ownership Model
This SEP establishes the following ownership model for spans in a passback exchange:
- The MCP client creates a span for the tool call and passes its context via traceparent to the server.
- The MCP server creates a SERVER span parented to that client span.
- The server returns the SERVER span (and optional child spans) via _meta.otel.
- The client ingests these spans without modifying them.

This ensures a single CLIENT → SERVER relationship in the distributed trace, no duplicate or phantom spans are introduced.

**Scope note: **This specification addresses single-hop telemetry passback between an MCP client and its directly connected MCP server. Multi-hop chain propagation, where an MCP server acts as a client to another MCP server is anticipated but deferred to a future SEP. To preserve trace continuity in multi-hop scenarios, servers that call external MCP tools SHOULD forward
_ _meta.traceparent_ even if they do not support telemetry passback themselves.

**Before this SEP:**
****

****
****
****
****
****
****
****
****
****
****
**After this SEP:**



1. Public Span Model - Best Practices
The server determines which spans to return. The following best practices guide server implementers in constructing a useful public span set:

1. Always include a root span. The response SHOULD contain a root SERVER span representing the tool call, parented to the client's _traceparent_. This gives the client a single entry point to anchor the returned spans in its trace.
1. Include key processing phases as child spans. Servers SHOULD surface spans for major execution stages such as authentication, policy evaluation, and tool handler invocation as direct children of the root span. These provide a top-level breakdown of where time was spent and what decisions were made, without requiring the client to understand internal implementation details.
1. Avoid exposing sensitive information. Span names and attributes SHOULD use generic labels rather than exposing internal service names, credentials, policy definitions, or business payloads. Servers SHOULD sanitize spans before returning them.
1. All returned spans MUST share the same _traceId_ as the client's _traceparent_, ensuring they can be stitched into the client's distributed trace.
1. Error and denial behavior. When the tool is not executed (due to policy denial, authentication failure, or other pre-execution checks), servers MAY still return spans for the processing stages that did execute. Servers MAY include __meta_ span data in JSON-RPC error responses. Span status MAY be set independently of JSON-RPC error semantics.


# Rationale
## Design Principles
1. Opt-in at every layer: Server advertises support, client explicitly requests spans per call. This ensures neither party is forced into telemetry exchange.
1. Standard OTLP format: Returned spans use verbatim OTLP JSON (_resourceSpans_), directly POSTable to any _/v1/traces_ endpoint. No custom serialization or proprietary format is introduced.
## Alternatives Considered: Extensions Track

An alternative approach would use the _experimental_ capability namespace with a namespaced key such as _io.modelcontextprotocol/otel_, allowing iteration without core spec changes and lowering the initial adoption bar.

This was rejected because observability is not a niche feature. Cross-organization deployments, which is the primary MCP growth vector, all need it. Keeping telemetry passback experimental would signal lack of commitment and discourage adoption by server implementers who need confidence that the capability will remain stable.

## Why Not HTTP Server-Timing (https://www.w3.org/TR/server-timing)

Mechanisms such as HTTP _Server-Timing_ provide trace identifiers but do not provide span data. They still require access to the server's telemetry backend to retrieve actual spans, which is precisely the access that cross-organization MCP deployments lack. This SEP returns span data directly in the response, eliminating the need for shared backend access.
## Why Verbatim OTLP JSON

Using the exact OTLP JSON wire format means clients can POST the payload directly to any standards-compliant collector without transformation. This maximizes compatibility with the OpenTelemetry ecosystem and avoids inventing a new serialization format that would require custom parsing on both sides.

## Relationship to SEP-414

SEP-414 handles the request side of distributed tracing in MCP whereas this SEP handles the response side. Together, SEP-414 and this SEP enable complete bidirectional distributed tracing across MCP without requiring shared collectors or shared observability infrastructure. i.e., SEP-414 gives the server the client's trace context and this SEP gives the client the server's execution telemetry.

# Related Work

- SEP-414: W3C Trace Context propagation from MCP clients to servers (request-side context propagation)
- OTel MCP Semantic Conventions: ([PR #2083](https://github.com/open-telemetry/semantic-conventions/pull/2083)). Defines mcp.* and gen_ai.* attributes used on MCP spans
# Backward Compatibility

This SEP introduces no backward incompatibilities. It adds a new capability that existing MCP clients and servers already ignore if unrecognized.
- Servers that do not support telemetry passback simply omit _serverExecutionTelemetry_ from their capabilities. Clients detect this and never send passback requests.
- Clients that do not support telemetry passback never include _otel_ in request __meta_. Servers see no passback request and behave normally.
- This is a new capability addition, not a change to existing messages.

# Reference Implementation
**NOTE: **This should be replaced by Arcade <> Galileo reference implementation

- Server: FastMCP-based MCP server that generates a minimal public trace slice and returns it via _meta.otel per this SEP
- Client: MCP Python SDK client that reads _meta.otel from tool call responses and exports returned spans to its own OTLP collector
- Agent: LangChain ReAct agent that invokes MCP tools via a custom tool wrapper, demonstrating before/after span passback across success and auth-denied scenarios
- Agent, client, and server operate across organizational boundaries with independent telemetry backends. i.e., no shared collector required
- Demonstration with standard OTLP collector (Jaeger)

# Security Implications
Telemetry passback crosses organizational trust boundaries.

MCP Servers:
- MUST NOT expose secrets, credentials

MCP Clients:
- MUST validate trace lineage (with the parent trace ID)
- SHOULD treat returned spans as untrusted external telemetry.

# 
# 
# 
# 
# 
****
****
****
****
****
****
**Demo ****[INTERNAL ONLY, WILL NOT BE PART OF SEP]******
****
**Without SEP**
****
****
****
****
****
****
****
****
****
****
****
****
****
**With SEP**
****
****
****
**With SEP and critical tool call details**
****
****
****
**With Full Span Tree**
****
****
****
****
****
****
**With minimal high-level span tree**
****
****
****
