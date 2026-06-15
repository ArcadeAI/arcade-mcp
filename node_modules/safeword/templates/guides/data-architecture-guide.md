# Data Architecture Documentation Guide

**Context:** How to document data architecture decisions, models, and flows for software projects. Applies LLM instruction design principles for clarity and reliability.

**See:** `@.safeword/guides/llm-writing-guide.md` for comprehensive framework on writing LLM-consumable documentation.

---

## When to Document Data Architecture

**Decision Tree (Answer IN ORDER, stop at first match):**

1. **Project initialization?** → Create `DATA_ARCHITECTURE.md` or `ARCHITECTURE.md` with data section
2. **Adding new data store?** (database, cache, file system) → Update architecture doc
3. **Changing data model?** (schema, entities, relationships) → Update architecture doc
4. **Data flow integration?** (API, ETL, sync) → Update architecture doc
5. **Single feature implementation?** → Use design doc (reference architecture doc)

**Tie-breaking rule:** If multiple apply, stop at first match (earlier = more general).

**Edge cases:**

- Single feature but adds 3+ entities → Architecture doc (impacts data model)
- Bug fix changes schema → Architecture doc (schema changes always documented)
- Feature uses existing data model → Design doc only

---

## Core Principles (Define First, Then Apply)

### 1. Data Quality

**What:** Ensure data is accurate, complete, consistent, and timely.

**Why:** Poor data quality cascades to business logic bugs, corrupted state, and user-facing errors.

**Document:**

- Validation rules (types, constraints, ranges)
- Data source of truth (which store is canonical)
- Quality checkpoints (where validation happens)

**Example format:**

```markdown
**[Entity] state** (source of truth: [storage type])

- `field1`: constraint (e.g., 0-100 integer)
- `field2[]`: max N entries, validation rule
  **Validation checkpoint:** `validateFunction()` in `file.ts:line`
```

### 2. Data Governance

**What:** Policies that govern data access, modification, and lifecycle.

**Why:** Prevents unauthorized access, conflicting writes, and data loss.

**Document:**

- Who can read/write each data entity
- When data is created/updated/deleted
- Conflict resolution strategies

**Example format:**

```markdown
**[Entity] state**:

- Read: [roles with read access]
- Write: [roles with write access] (via `updateFunction()`)
- Delete: [strategy] (e.g., soft delete with `deletedAt`)
- Conflict: [resolution strategy] (e.g., last-write-wins, CRDT merge)
```

### 3. Data Accessibility

**What:** Ensure data is available when needed, performantly.

**Why:** Users expect instant feedback; slow queries degrade UX.

**Document:**

- Access patterns (how data is queried)
- Performance targets (max query time)
- Caching strategies

**Example format:**

```markdown
**[Entity] list** (accessed on [trigger]):

- Target: <Nms load time
- Strategy: [database index/optimization]
- Cache: [caching approach] or "No cache needed"
```

### 4. Living Documentation

**What:** Documentation stays current with code, not a one-time artifact.

**Why:** Outdated docs are worse than no docs (mislead developers).

**Document:**

- Version/status (Production/Proposed)
- Last updated date
- Migration strategy when changing

**Example format:**

```markdown
**Version:** X.Y
**Status:** Production (vX) + Proposed (vY)
**Last Updated:** YYYY-MM-DD

## Current Schema (vX - Production)

## Proposed Schema (vY - Feature Name)

## Migration Strategy
```

---

## What to Document

### 1. Data Models

**Three levels (conceptual → logical → physical):**

- **Conceptual**: High-level entities with descriptions (e.g., "User - person with account", "Order - purchase transaction")
- **Logical**: Attributes, types, relationships, constraints (e.g., `userId: UUID`, `orders: Order[]` 1:N relationship)
- **Physical**: Storage technology, tables/collections, indexes, WHY this tech (trade-offs) - see Core Principles → Data Quality (lines 41-47) for format

### 2. Data Flows

**Document:** Sources → Transformations → Destinations + Error Handling

**Include:** Input validation, business logic transformations, persistence steps, UI updates, error handling for each step.

**Example format:**

```markdown
**[Flow Name]** (trigger: [user action/event])

1. **Input** → Validation (`validateFn()`) | Error: return 400
2. **Transform** → Business logic | Error: rollback + notify
3. **Persist** → Database write | Error: retry 3x, then fail
4. **UI Update** → Optimistic update | Error: revert state
```

### 3. Data Policies

**Document:** Access control (who reads/writes), validation rules, lifecycle (creation, updates, deletion, purging).

### 4. Data Integration

**Document:** External systems (APIs, files, services), sync strategies, conflict resolution, error handling.

---

## Integration with TDD Workflow

**See:** `@.safeword/guides/architecture-guide.md` for full TDD workflow integration.

**Data-specific triggers for updating architecture doc:**

- Adding new data entities
- Changing schema (new fields, relationships)
- Changing storage technology
- Discovering performance bottlenecks

---

## Common Mistakes

❌ **No source of truth defined** → Conflicting data in multiple stores
❌ **Missing validation rules** → Invalid data written to persistence
❌ **No migration strategy** → Breaking changes brick user data
❌ **Outdated documentation** → Schema and docs don't match (worse than no docs)
❌ **Implementation details in architecture doc** → Save for design docs
❌ **Ignoring performance targets** → Slow queries degrade UX

---

## Best Practices Checklist

Before finalizing data architecture doc:

- [ ] Principles follow What/Why/Document/Example format (4 principles minimum)
- [ ] All entities defined with descriptions (3+ entities for conceptual model)
- [ ] Each entity has attributes, types, relationships (logical model complete)
- [ ] Storage tech documented with WHY + trade-offs (physical model includes rationale)
- [ ] Each data flow includes error handling (not just happy path)
- [ ] Validation checkpoints specified with line numbers (where validation happens)
- [ ] Performance targets use concrete numbers (<Nms, not "fast")
- [ ] Migration strategy covers both additive and breaking changes
- [ ] Version and status match codebase (verify with git/deployment)
- [ ] Cross-referenced from root ARCHITECTURE.md or SAFEWORD.md (link exists)

---

## Key Takeaways

- Data quality, governance, accessibility are core principles
- Every entity needs: attributes, types, relationships, constraints
- Performance targets use concrete numbers (e.g., <100ms, not "fast")
- Migration strategy covers both additive and breaking changes
