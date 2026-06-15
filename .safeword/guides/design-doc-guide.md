# Design Doc Guide for Claude Code

## How to Fill Out Design Doc

**Template:** `@.safeword/templates/design-doc-template.md`

**When user asks:** "Create design doc for [feature]" or "Design [system/component]"

---

## What You Do

1. **Verify Prerequisites**
   - Confirm user stories exist (if not, create them first)
   - Confirm test definitions exist (if not, create them first)
   - Reference both in the design doc

2. **Read Template**
   - Read `@.safeword/templates/design-doc-template.md`
   - Use it as the structure for the design doc

3. **Fill In Sections**

   **Architecture:**
   - 1-2 paragraphs: High-level approach
   - What are we building and how does it fit together?
   - Add diagram if helpful (optional)

   **Components:**
   - Define Component [N] with full example (name, responsibility, interface, dependencies, tests)
   - Define Component [N+1] with different example (show the [N]/[N+1] pattern)
   - Add more components as needed (N+2, N+3, etc.)

   **Data Model (if applicable):**
   - State shape, database schema, or data structures
   - Show relationships between types
   - How data flows through the system

   **Component Interaction (if applicable):**
   - How components communicate
   - Data flow between them (Component [N] → Component [N+1])
   - Events/method calls

   **User Flow:**
   - Step-by-step user interaction
   - Use concrete examples (e.g., "clicks 'Toggle AI Pane' button, presses Cmd+J")

   **Key Decisions:**
   - Decision [N]: What we're using/doing, why (with specifics), trade-off
   - Decision [N+1]: Different decision (show the [N]/[N+1] pattern)
   - Add more decisions as needed

   **Implementation Notes (if applicable):**
   - Constraints (technical limitations, performance requirements)
   - Error Handling (how errors are caught, user-facing vs internal)
   - Gotchas (edge cases, common mistakes)
   - Open Questions (blocking questions, needs research)

   **References (if applicable):**
   - Link to relevant ADRs, external docs, proof of concepts

4. **Save to Project**
   - Save to `planning/design/[feature-name]-design.md` or similar location
   - Follow project's convention for design doc location

---

## DO Include

- ✅ Clear component interfaces with TypeScript examples
- ✅ Full [N] and [N+1] examples (like user stories and test definitions templates)
- ✅ References to user stories and test definitions (don't duplicate them)
- ✅ User flow with concrete examples
- ✅ Key decisions with "what, why, trade-off"
- ✅ Rationale with specifics (metrics, benchmarks, analysis)

---

## DON'T Include

- ❌ Duplicating user stories (reference them instead)
- ❌ Duplicating test definitions (reference them instead)
- ❌ Project-wide architecture decisions (those go in ARCHITECTURE.md)
- ❌ Implementation details that should be in code comments
- ❌ Generic advice without project-specific context

---

## When to Use Design Doc vs Architecture Doc

**Use Design Doc when:**

- Designing a specific feature implementation
- Need component breakdown and interactions
- Feature-specific technical decisions
- 2-3 pages (~121 lines)

**Use Architecture Doc when:**

- Project-wide technology choices
- Data model for entire system
- Principles and patterns for the whole project
- Comprehensive (10+ pages)

**Reference:** `@.safeword/guides/architecture-guide.md` for detailed comparison

---

## Re-evaluation Path (When Unclear)

**If unsure whether feature needs a design doc:**

1. **Count components** — Does implementation touch >3 components?
   - Yes → Design doc needed
   - No → Continue to question 2

2. **Check user story count** — Does feature span 2+ user stories?
   - Yes → Design doc needed
   - No → Continue to question 3

3. **Check complexity signals** — Any of these present?
   - New data model or schema changes
   - Non-obvious component interactions
   - Multiple technical decisions with trade-offs
   - Yes to any → Design doc needed
   - No to all → Skip design doc, implement directly

**If prerequisites don't exist:**

1. Feature spec missing → Create it first (guide: `.safeword/guides/planning-guide.md`)
2. Test definitions missing → Create them after feature spec (guide: `.safeword/guides/planning-guide.md`)
3. Then create design doc referencing both

---

## Example Commands

**Creating design doc:**

```text
User: "Create design doc for three-pane layout"
You: [Read user stories and test definitions, then create design doc]
```

**Updating design doc:**

```text
User: "Update design doc to add error handling section"
You: [Read existing design doc, add Implementation Notes section with error handling]
```

---

## Quality Checklist

Before saving, verify:

- ✓ References user stories and test definitions (not duplicates them)
- ✓ Has Component [N] and Component [N+1] examples
- ✓ User flow has concrete examples
- ✓ Key decisions have "what, why, trade-off"
- ✓ All optional sections marked "(if applicable)"
- ✓ ~121 lines (concise, LLM-optimized)

---

## LLM Instruction Design

**Important:** Design docs are instructions that LLMs read and follow.

**See:** `@.safeword/guides/llm-writing-guide.md` for comprehensive framework on writing clear, actionable documentation that LLMs can reliably follow.

---

## Key Takeaways

- Escalate to Architecture Doc if: new tech, new schema, or pattern affects 2+ features
- Reference user stories and test definitions—don't duplicate them
- Every decision needs: what, why, trade-off
- ~121 lines target (concise, LLM-optimized)
