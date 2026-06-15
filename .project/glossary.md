# Glossary

<!--
Project-wide domain vocabulary. Every spec, JTBD, and scenario in this
project should use terms consistently with this file. Safeword validates
the file's structure during `safeword check`; the `bdd` intake flow reads
it so domain terms stay consistent across tickets.

FORMAT

Each term is a `##` block with:

- A term name in the header (e.g., `## Tool`)
- A `**Definition:**` line (required) — one or more lines; wrapped text
  is joined into a single definition.

Optional fields (parsed if present, never required):

- `**Used in:**` — which domains/services use this term.
- `**Example:**` — a usage example.
- `**Do not confuse with:**` — related terms with distinct meanings.
- `**Aliases:**` — comma-separated synonyms (e.g., `**Aliases:** Function, Capability`).

Unknown `**Field:**` lines are tolerated (forward-compat). An alias must
not collide with a declared term name (lookup would be ambiguous).

To retire a term, delete its block.

EXAMPLE (uncomment, customize, then delete this comment)

## Tool

**Definition:** A single callable capability exposed by the platform — for
example, `GitHub.CreateIssue`. Each tool has a typed input schema and
returns a structured result.

**Used in:** Engine (routing), MCP servers (registration), all specs that
describe tool invocation.

**Example:** `When the agent calls the "GitHub.CreateIssue" tool`

**Do not confuse with:** Toolkit — a tool is a single operation; a toolkit
is the collection of related tools for one service.

**Aliases:** Capability
-->
