# Personas

<!--
Project-wide persona definitions. Every spec, JTBD, and scenario in this
project references personas from this file by name or short code.
Safeword validates these references during intake — unknown personas
surface as questions, not silent failures.

FORMAT

Each persona is a `##` block with:

- A name in the header (e.g., `## Platform Operator`)
- A `**Role:**` one-sentence description (required)
- An optional `**Context:**` block (technical level, environment, constraints)

SHORT CODES

Codes auto-derive when you save the file:

- Multi-word names → first letter of each word, uppercased
  ("Platform Operator" → PO; "Site Reliability Engineer" → SRE)
- Single-word names → first 2 characters, uppercased
  ("Auditor" → AU)
- Collisions get a numeric suffix ("PO", "PO2", "PO3")
- Override by authoring the code explicitly: `## Platform Operator (PLATOPS)`

Codes must match `^[A-Z][A-Z0-9]{1,5}$` (2–6 chars, uppercase letter first).

To retire a persona, delete the block. References to retired codes surface
as unknown automatically.

EXAMPLE (uncomment, customize, then delete this comment)

## Platform Operator

**Role:** Infrastructure owner — registers servers, configures rate limits, manages projects.

**Context:** Has Dashboard admin access; may have direct infrastructure access. Reads logs, sets configuration, manages service accounts.

## End User

**Role:** Signs in to use the product.
-->
