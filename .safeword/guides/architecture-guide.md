# Architecture & Design Documentation Guide

**See:** `@.safeword/guides/llm-writing-guide.md` for LLM-consumable documentation principles.

---

## Survey & Reconcile (Before You Propose)

The order is load-bearing (full version in `@.safeword/SAFEWORD.md` → Clarify):

1. **Frame** the hard constraints — data model, non-negotiable framework idioms, prior decisions.
2. **Design the ideal** with `/figure-it-out`, as if the codebase didn't exist. This is your yardstick.
3. **Survey** the existing patterns in the area — _now_, not before. Surveying first anchors the design to the status quo.
4. **Reconcile** — conform by default; record the call when your ideal diverges.

### Survey: what to look for

- **Sibling implementations** — grep the layer/feature for code that solves the same shape of problem. How is it structured?
- **Prior decisions** — search `ARCHITECTURE.md` and tickets for an existing ruling on this pattern.
- **Tests near the code** — they encode the conventions you'd be expected to match.
- **Call-site count** — how many places use the existing pattern? Write the number down; it is the cost of deviating.

### Reconcile: conform by default

Default to the existing pattern. Per Google's code-review standard, conform "as long as that doesn't worsen the overall code health of the system" — deviate only when your ideal is a _real_ improvement, not your taste.

**Ideal and existing agree → no decision, no record.** When they diverge, record the call (below). You can't silently conform your ideal away (that is how mediocre patterns calcify), and you can't silently deviate (that is how a codebase splits in two).

### The reconcile record

Required only when the ideal diverges from what exists:

| Field                       | Notes                                                                                                           |
| --------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Direction**               | Conform, or deviate                                                                                             |
| **Reason**                  | The load-bearing why                                                                                            |
| **Health defect** (deviate) | A _named_ failure of the existing pattern the ideal fixes. "Cleaner" is not a defect.                           |
| **Inconsistency cost**      | The call-site count you're splitting (from the survey)                                                          |
| **Pre-mortem**              | One line: "assume deviating was wrong — what broke?" Prospective hindsight surfaces costs you're discounting.   |
| **Uplevel ticket**          | The tracked follow-up to migrate the rest. Track it; don't migrate every call site now (avoid the rabbit-hole). |

**Depth scales with reversibility:**

- **Reversible + local** → the record is a few lines in the ticket.
- **Irreversible or cross-cutting** (data model, public API) → promote to a full Architecture Doc decision (What / Why / Trade-off / Alternatives, below) and get a second opinion that tries to _refute_ the deviation before committing.

---

## Document Type Decision Tree (Follow in Order)

Answer **IN ORDER**. Stop at the first "Yes":

1. **Technology or library choice?** → **Architecture Doc**
2. **New data model or schema change?** → **Architecture Doc**
3. **Project-wide pattern or convention?** → **Architecture Doc**
4. **Implementing a specific feature?** → **Design Doc**

**Tie-breaker:** If a feature requires a new tech/schema choice, document the tech/schema in Architecture Doc first, then reference it in Design Doc.

| Term                 | Definition                                                                 |
| -------------------- | -------------------------------------------------------------------------- |
| Technology choice    | Selecting a library, framework, database, or tool                          |
| Schema change        | Adding/modifying entities, tables, relationships, or data types            |
| Project-wide pattern | Convention that applies to 2+ features or multiple developers              |
| Major decision       | Affects 2+ components, costs >$100/month, or cannot be easily reversed     |
| Living document      | Updated in place (not immutable); changes tracked via version/status       |
| ADR                  | Architecture Decision Record—legacy pattern of separate files per decision |

---

## Quick Decision Matrix

| Scenario                        | Doc Type                        | Rationale                          |
| ------------------------------- | ------------------------------- | ---------------------------------- |
| Choosing between technologies   | Architecture                    | Tech choice affects whole project  |
| Data model design               | Architecture                    | Schema is project-wide             |
| Implementing a new feature      | Design                          | Feature-scoped implementation      |
| Recording a trade-off           | Architecture                    | Trade-offs inform future decisions |
| Project-wide principles         | Architecture                    | Principles apply everywhere        |
| Component breakdown for feature | Design                          | Implementation detail              |
| Feature needs new schema        | Architecture first, then Design | Schema in Arch, feature in Design  |

---

## Architecture Document

**Use when**: Project-wide decisions, data models, system design

**Characteristics**:

- One per project/package (in monorepos)
- Living document (updated in place—not immutable ADRs)
- Documents WHY behind all major decisions
- Includes version, status, table of contents

**Location**: Project root (`ARCHITECTURE.md`)

**Edge cases:**

- Schema change for one feature → Architecture Doc (schema is project-wide)
- Library for one feature → Architecture Doc if precedent-setting; Design Doc if one-off
- Performance optimization → Architecture Doc if changes patterns; Design Doc if feature-specific

### Required Sections

- **Header**: Version, Last Updated, Status (Production/Design/Proposed/Deprecated)
- **Table of Contents**: Section links
- **Overview**: Technology choices, data model philosophy, high-level architecture
- **Data Model / Schema**: Tables, types, relationships
- **Key Decisions**: What, Why, Trade-off, Alternatives Considered
- **Best Practices**: Domain-specific patterns
- **Migration Strategy**: How to evolve architecture

---

## Best Practices

### 1. One Architecture Doc Per Project/Package

**✅ GOOD:**

```plaintext
project/
├── ARCHITECTURE.md
└── docs/design/
    ├── feature-a.md
    └── feature-b.md
```

**❌ BAD:** `docs/adr/001-use-typescript.md, 002-adopt-monorepo.md...` (50+ files = fragmented context)

### 2. Living Document (Not Immutable)

Update in place with version/status tracking:

```markdown
### Decision: State Management

**Status**: Active (Updated 2025-01-20)
**What**: Migrated from localStorage to IndexedDB
**Why**: Hit 5MB limit, needed unlimited storage
**Migration**: Completed 2025-01-20, users auto-migrated on load
```

**Edge cases:**

- Decision reversed → Update original with "Superseded" status
- Major shift → Bump version (v1 → v2), add migration section
- Affects multiple subsystems → Update main Architecture Doc, not separate files

### 3. Document WHY, Not Just WHAT

**✅ GOOD:**

```markdown
### Principle: Separation of Concerns

**What**: Static data → immutable storage; Mutable state → persistent storage
**Why**: Static data saves NKB per instance; updates affect all instances instantly
**Trade-off**: More complex loading (fetch static + query persistent)
**Alternatives Considered**: All localStorage (rejected: 5MB limit); All IndexedDB (rejected: overkill for config)
```

**❌ BAD:** `Database: PostgreSQL, State: Zustand, UI: React` (no rationale)

**Required fields:**

| Field        | Required        | Description                                 |
| ------------ | --------------- | ------------------------------------------- |
| What         | Always          | The decision (1-2 sentences)                |
| Why          | Always          | Rationale with specifics (numbers, metrics) |
| Trade-off    | Always          | What we gave up or accepted                 |
| Alternatives | Major decisions | Other options and why rejected              |
| Migration    | If breaking     | How to evolve from previous state           |

**Edge cases:**

- Obvious choice → Still document; future devs may question
- Inherited decision → Document as "Inherited: [reason]"
- Temporary decision → Mark "Temporary" with planned review date

### 4. Include Code References

**✅ GOOD:**

```markdown
**Implementation**: See `src/stores/gameStore.ts:12-45`
**Usage example**: See `src/components/GamePanel.tsx`
```

**❌ BAD:** "We use Zustand for state management" (no reference to actual code)

- Key patterns → file + line range
- Simple utilities → file path only (no line numbers)
- Frequently changing code → file path only (line numbers go stale)

### 5. Version and Track Status

| Status     | Meaning                            |
| ---------- | ---------------------------------- |
| Design     | Initial draft, not yet implemented |
| Production | Live in production                 |
| Proposed   | Planned extension to production    |
| Deprecated | Being phased out                   |

**Version bumps:** Major schema changes → v1 → v2; New sections → v1.0 → v1.1; Clarifications → no bump

---

## TDD Workflow Integration

**Workflow Order**:

1. User Stories → What we're building
2. Test Definitions → How we'll verify
3. Design Doc → How we'll build it
4. Check Architecture Doc → New tech/schema needed?
5. Implement (RED → GREEN → REFACTOR)
6. Update Architecture Doc if needed

### When to Update Architecture Doc

| Trigger                                     | Example                          |
| ------------------------------------------- | -------------------------------- |
| New data model concept                      | New "Subscription" entity        |
| Technology choice                           | "Chose Resend for email"         |
| New pattern/convention                      | "All forms use react-hook-form"  |
| Architectural insight during implementation | "IndexedDB needed for offline"   |
| Performance bottleneck requiring change     | "Migrated to Redis for sessions" |

### When NOT to Update

| Scenario                        | Where Instead            |
| ------------------------------- | ------------------------ |
| Single feature implementation   | Design Doc               |
| Bug fix                         | Code comments if complex |
| Refactor without pattern change | PR description           |

**Edge case:** Bug fix reveals architectural flaw → Document flaw and fix in Architecture Doc.

---

## Common Mistakes

### Architecture Doc Anti-Patterns

| Anti-Pattern             | Fix                                 |
| ------------------------ | ----------------------------------- |
| ADR sprawl (001, 002...) | One comprehensive `ARCHITECTURE.md` |
| No decision rationale    | Add What/Why/Trade-off              |
| Missing version/status   | Add header with Version and Status  |
| Implementation details   | Move to Design Doc or code          |

**❌ BAD:** `GET /api/users → Returns users from PostgreSQL` (implementation detail)

**✅ GOOD:** `API Design: RESTful routes with input validation at boundary` (principle)

---

## Re-evaluation Path (When Unclear)

Answer **IN ORDER**:

1. **Affects 2+ features?** → Architecture Doc (stop)
2. **Technology/data model choice?** → Architecture Doc (stop)
3. **Future developers need this for whole project?** → Architecture Doc
4. **Only for this feature?** → Design Doc

**Tie-breaker:** When still unclear, default to Design Doc. Easier to promote later than to split.

### Worked Example: Adding User Notifications

**Scenario:** Add email notifications when users complete a purchase.

1. **Affects 2+ features?** No, only checkout → Continue
2. **Tech choice?** Yes, need to choose email service (SendGrid vs SES) → **Architecture Doc**

**Result:**

- `ARCHITECTURE.md` → "Email Service: SendGrid (Why: deliverability, cost, SDK quality)"
- `planning/design/checkout-notifications.md` → Feature implementation referencing email decision

---

## File Organization

```plaintext
project/
├── ARCHITECTURE.md                    # Single comprehensive doc
├── <namespace-root>/tickets/
│   └── {id}-{slug}/
│       ├── ticket.md
│       ├── test-definitions.md
│       └── design.md                  # Feature-specific design docs
└── src/
```

---

## Layers & Boundaries

**Purpose:** Define architectural layers and enforce dependency rules to prevent circular dependencies, god modules, and leaky abstractions.

### Layer Definitions

| Layer  | Directory     | Responsibility                 |
| ------ | ------------- | ------------------------------ |
| app    | `src/app/`    | UI, routing, composition       |
| domain | `src/domain/` | Business rules, pure logic     |
| infra  | `src/infra/`  | IO, APIs, DB, external SDKs    |
| shared | `src/shared/` | Utilities usable by all layers |

### Allowed Dependencies

| From   | To     | Allowed | Rationale                                         |
| ------ | ------ | ------- | ------------------------------------------------- |
| app    | domain | ✅      | UI composes business logic                        |
| app    | infra  | ✅      | UI triggers side effects                          |
| app    | shared | ✅      | Utilities available everywhere                    |
| domain | app    | ❌      | Domain must be framework-agnostic                 |
| domain | infra  | ❌      | Domain contains pure logic only                   |
| domain | shared | ✅      | Utilities available everywhere                    |
| infra  | domain | ✅      | Adapters may use domain types                     |
| infra  | app    | ❌      | Infra should not depend on UI                     |
| infra  | shared | ✅      | Utilities available everywhere                    |
| shared | \*     | ❌      | Shared has no dependencies (except external libs) |

**Note:** This template allows direct app→infra. Alternative: force app→domain→infra for stricter separation (hexagonal/ports-adapters pattern).

### Edge Cases

| Scenario                             | Solution                                                                  |
| ------------------------------------ | ------------------------------------------------------------------------- |
| Project doesn't fit 3-layer model    | Document actual layers, same boundary rules apply                         |
| Feature module needs another feature | Import via public API (`index.ts`) only                                   |
| Shared utilities                     | Create `shared/` layer, all layers may import                             |
| Brownfield adoption                  | Start with warnings-only mode, fix violations incrementally, then enforce |
| Monorepo with multiple apps          | Each app has own layers; shared packages are explicit dependencies        |

### Enforcement with eslint-plugin-boundaries

**Setup:**

1. Install: `bun add -D eslint-plugin-boundaries`

2. Add to `eslint.config.mjs`:

```javascript
import boundaries from 'eslint-plugin-boundaries';

export default defineConfig([
  // ... other configs ...
  {
    name: 'boundaries-config',
    files: ['**/*.{js,ts,tsx}'],
    plugins: { boundaries },
    settings: {
      'boundaries/include': ['src/**/*'],
      'boundaries/elements': [
        { type: 'app', pattern: 'src/app/**/*' },
        { type: 'domain', pattern: 'src/domain/**/*' },
        { type: 'infra', pattern: 'src/infra/**/*' },
        { type: 'shared', pattern: 'src/shared/**/*' },
      ],
    },
    rules: {
      'boundaries/element-types': [
        'error',
        {
          default: 'disallow',
          rules: [
            { from: 'app', allow: ['domain', 'infra', 'shared'] },
            { from: 'domain', allow: ['shared'] },
            { from: 'infra', allow: ['domain', 'shared'] },
            { from: 'shared', allow: [] },
          ],
        },
      ],
      'boundaries/no-unknown-files': 'error',
    },
  },
]);
```

3. Define layers in `ARCHITECTURE.md` (see template)

4. Errors appear in IDE + CI automatically

**Common Issues:**

| Issue                            | Fix                                                                      |
| -------------------------------- | ------------------------------------------------------------------------ |
| "Unknown file" errors            | Ensure all source files are in defined layers                            |
| False positives on tests         | Exclude test files: `'boundaries/include': ['src/**/*', '!**/*.test.*']` |
| External library imports flagged | External deps are allowed by default; check `boundaries/ignore` setting  |

---

## Data Architecture

**Escalate to `data-architecture-guide.md` when ANY apply:**

- Adding a second data store (database, cache, queue)
- Complex schema (5+ entities OR cross-feature relationships)
- Designing ETL, sync, or data pipeline flows
- Data compliance requirements (GDPR, HIPAA, audit trails)
- Performance-critical queries needing optimization strategy
- Multi-service data ownership questions

**The guide covers:** Data quality principles, governance policies, flow documentation, performance targets.

**Skip for:** Single-store CRUD, simple schema additions, feature-scoped entities.

---

## Quality Checklist

**Architecture Doc:**

- [ ] Sequential decision tree or clear structure
- [ ] All decisions have What/Why/Trade-off
- [ ] Version and Status in header
- [ ] Code references for key patterns
- [ ] No implementation details

---

## Key Takeaways

- One Architecture Doc per project—not scattered ADRs
- Every decision needs: What / Why / Trade-off / Alternatives
- Update when adding: technology, schema, or project-wide pattern
- Living document—update in place with version/status tracking
