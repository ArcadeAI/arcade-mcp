# [Project Name] Architecture

**Version:** 1.0  
**Last Updated:** YYYY-MM-DD  
**Status:** Design | Production | Proposed | Deprecated

---

## Table of Contents

- [Overview](#overview)
- [Layers & Boundaries](#layers--boundaries)
- [Data Model](#data-model)
- [Key Decisions](#key-decisions)
- [Best Practices](#best-practices)
- [Migration Strategy](#migration-strategy)

---

## Overview

[High-level description of the system architecture, technology choices, and design philosophy.]

### Tech Stack

| Category         | Choice | Rationale |
| ---------------- | ------ | --------- |
| Language         |        |           |
| Framework        |        |           |
| Database         |        |           |
| State Management |        |           |

---

## Layers & Boundaries

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

### Boundary Enforcement

Boundaries enforced via `eslint-plugin-boundaries`. See `.safeword/guides/architecture-guide.md` → Enforcement with eslint-plugin-boundaries for setup.

---

## Data Model

### Entities

| Entity | Table/Collection | Description |
| ------ | ---------------- | ----------- |
|        |                  |             |

### Relationships

```text
[Entity A] 1──n [Entity B]
[Entity B] n──n [Entity C]
```

### Schema Notes

- [Key constraints, indexes, etc.]

---

## Key Decisions

### [Decision Title]

**Status:** Active | Superseded | Deprecated  
**Date:** YYYY-MM-DD

| Field          | Value                                         |
| -------------- | --------------------------------------------- |
| What           | [The decision in 1-2 sentences]               |
| Why            | [Rationale with specifics - numbers, metrics] |
| Trade-off      | [What we gave up or accepted]                 |
| Alternatives   | [Other options considered and why rejected]   |
| Implementation | [File references: `src/path/file.ts:12-45`]   |

---

## Best Practices

### [Pattern Name]

**What:** [Brief description]  
**Why:** [Rationale]  
**Example:** See `src/path/example.ts`

---

## Migration Strategy

### From [Previous State] to [Target State]

**Trigger:** [When to migrate]  
**Steps:**

1. [Step 1]
2. [Step 2]

**Rollback:** [How to revert if needed]

---

## Appendix

### References

- [Link to relevant docs]
- [Link to ADRs if migrating from ADR system]
