# Learning Extraction Process

Extract reusable knowledge from debugging sessions and implementation discoveries. Ensures insights compound across sessions.

**LLM Instruction Design:** Learnings are documentation that LLMs read and follow. Apply best practices from `@.safeword/guides/llm-writing-guide.md` when writing learning files (concrete examples, explicit definitions, MECE principles).

---

## When to Extract (Recognition Triggers)

**Note:** LLMs cannot sense time. Use observable signals instead of duration.

Extract after experiencing ANY of these:

1. **Observable debugging complexity** - Any of these signals:
   - User says "still debugging", "been stuck on this", "tried many things"
   - 5+ debug cycles (Read → Edit → Bash pattern repeated)
   - 3+ different error states encountered
   - Modified 3+ files while debugging same issue
2. **Trial and error** - Tried 3+ different approaches before finding the right one
3. **Undocumented gotcha** - Not in official library/framework docs
4. **Integration struggle** - Two tools that don't work together smoothly
5. **Testing trap** - Tests pass but UX is broken (or vice versa)
6. **Architectural insight** - Discovered during implementation, not planned upfront

**Key question:** "Would this save time on future work in this codebase (or any codebase)?"

---

## File Locations

**Project learnings** (`<namespace-root>/learnings/[concept].md`):

- **Why**: Specific to THIS codebase (custom architecture, unique patterns)
- **Scope**: Shared via git (team knowledge base)
- **Use case**: Project-specific gotchas

**Historical archives** (`<namespace-root>/learnings/archive/[bug-fix].md`):

- **Why**: One-time debugging narratives (not forward-looking)
- **Scope**: Shared via git (learning history)
- **Use case**: Reference when similar bugs occur

**Precedence:**

1. Explicit user instruction (highest priority)
2. Project `<namespace-root>/learnings/` (project-specific)
3. Project `./SAFEWORD.md` → Common Gotchas (inline reference)

---

## Using Existing Learnings

**CRITICAL**: Before extracting new learnings, ALWAYS check if similar learnings already exist. This prevents duplication and keeps knowledge organized.

### When to Check for Existing Learnings

**Check PROACTIVELY in these situations:**

1. **Before debugging** - Check if similar issue has learning already

   ```text
   ls <namespace-root>/learnings/*[technology]*.md
   ls <namespace-root>/learnings/*[pattern]*.md
   ```

2. **When user mentions technology/pattern** - Check for relevant learnings
   - User says "React hooks" → Check for `*hooks*.md`
   - User says "Electron IPC" → Check for `*electron*.md` or `*ipc*.md`
   - User says "state management" → Check for `*state*.md`

3. **During architectural discussions** - Check for pattern learnings
   - Discussing patterns → Check for `*pattern*.md` or `*architecture*.md`

4. **After suggesting extraction** - Check if learning already exists
   - If found → Suggest updating existing learning instead of creating duplicate
   - If not found → Proceed with extraction

### How to Check

```text
# Project learnings
ls <namespace-root>/learnings/

# Search by keyword
ls <namespace-root>/learnings/*keyword*.md
```

### When to Reference Existing Learnings

**Found existing learning** → Read and apply it:

```text
"I found an existing learning about [concept] at [path]. Let me read it and apply to your case..."
[Read the file]
"Based on the learning, here's how to handle this: [specific guidance from learning]"
```

**No existing learning** → Proceed normally (no message needed)

**Similar but different** → Reference and note difference:

```text
"This is similar to the [existing learning] at [path], but differs in [specific way].
The existing learning covers [X], but your case involves [Y]."
```

### Example Workflow

**Scenario 1: Found relevant learning**

```text
User: "I'm getting an async state update error with React hooks"
→ Check: ls <namespace-root>/learnings/*react*.md *hooks*.md *async*.md
→ Found: react-hooks-async.md
→ Read: [file contents]
→ Apply: "I found a learning about async React hooks. It mentions you should use useEffect
         for side effects, not setState directly in callbacks. Applying this to your case..."
```

**Scenario 2: No existing learning**

```text
User: "IndexedDB quota is behaving strangely in Safari"
→ Check: ls <namespace-root>/learnings/*indexeddb*.md *safari*.md *quota*.md
→ Not found
→ Proceed: Continue debugging normally, suggest extraction if triggers match
```

**Scenario 3: Update existing learning**

```text
User: Debugging for 6 cycles, discovers new IndexedDB quirk
→ Suggest extraction
→ Check: ls <namespace-root>/learnings/*indexeddb*.md
→ Found: indexeddb-quota-api.md
→ Suggest: "I found an existing learning about IndexedDB quota. Should I update it with
           this new discovery instead of creating a separate learning?"
```

### Benefits of Checking Existing Learnings

✅ **Prevents duplication** - One learning per concept, easier to find
✅ **Compounds knowledge** - Update existing learnings with new discoveries
✅ **Faster problem solving** - Apply known patterns immediately
✅ **Better organization** - Learnings directory stays clean and navigable

---

## Decision Tree

```text
Just learned something valuable
│
├─ Forward-looking? (useful on FUTURE work, not just this bug)
│  ├─ YES → Continue
│  └─ NO → <namespace-root>/learnings/archive/[bug-fix].md (optional)
│
├─ Choose destination:
│  │
│  ├─ Architectural? (why we chose X over Y)
│  │  └─ YES → Add to: SAFEWORD.md "Architecture Decisions"
│  │
│  ├─ Short gotcha? (1-2 sentences + code snippet)
│  │  └─ YES → Add to: SAFEWORD.md "Common Gotchas"
│  │
│  └─ Needs examples/explanation?
│     └─ YES → Extract to: <namespace-root>/learnings/[concept].md
│        Then cross-reference in SAFEWORD.md
```

---

## Templates

### Forward-Looking Learning (<namespace-root>/learnings/)

**Use when:** Pattern applies to 2+ features/files, needs explanation

**Structure:**

```markdown
# [Concept Name]

**Principle:** One-sentence summary

## The Gotcha

What breaks if you don't know this:

❌ **Bad:** [Anti-pattern]
✅ **Good:** [Correct pattern]

**Why it matters:** [User impact or technical consequence]

## Examples

[2-3 concrete before/after code examples]

## Testing Trap (if applicable)

[How tests might pass while UX is broken]

## Reference

See `<namespace-root>/learnings/archive/[investigation].md` for full debugging narrative.
```

### Debugging Narrative (<namespace-root>/learnings/archive/)

**Use when:** One-time bug fix, historical record

**Structure:**

````markdown
# [Issue Title]

**Date:** YYYY-MM-DD
**Root Cause:** One-sentence explanation

## Problem

Expected: [What should happen]
Actual: [What happened]

## Investigation

1. [Hypothesis] → [Outcome]
2. [Hypothesis] → [Outcome]
3. [Discovery] → [Fix]

## Solution

```diff
- Old broken code
+ New fixed code
```
````

## Lesson

[One-sentence takeaway]

````text

---

## SAFEWORD.md Integration

**CRITICAL**: ALWAYS cross-reference in SAFEWORD.md after creating learning file.

After extracting to `<namespace-root>/learnings/`, add cross-reference in SAFEWORD.md:

```markdown
## Common Gotchas

Project-specific gotchas in `<namespace-root>/learnings/`:

- **Persistent UI Placement** - Controls in LayoutBar (always visible), not EditorTabBar (conditional) → `<namespace-root>/learnings/persistent-ui.md`
- **Electron Renderer Context** - Renderer = browser, not Node.js; use `split(/[/\\]/)` for paths → `<namespace-root>/learnings/electron-contexts.md`

**Additional gotchas:**
- Tab state timing: Add tab first (trigger render), wait 50ms, load content
- File validation: Whitelist extensions before operations
````

**Pattern:** Bold name + one-sentence summary + optional link

---

## Examples: What Goes Where

### ✅ Project Architecture (SAFEWORD.md)

**Learning:** "Why Zustand over Redux?"

**Why SAFEWORD.md:** Architectural decision unique to this project

**Location:** `SAFEWORD.md` → Architecture Decisions section

```markdown
### Why Zustand over Redux/MobX?

**Decision:** Zustand for all UI state

**Why:**

- Single-user desktop app = simple state
- 1KB vs Redux's 10KB+ boilerplate
- Hooks-based, TypeScript-first

**Trade-off:** No time-travel debugging, but not needed

**Gotcha:** NEVER import stores in store definitions (circular deps)
```

---

### ✅ Project Learning (<namespace-root>/learnings/)

**Learning:** "UI controls must be in persistent areas, not conditional components"

**Why learnings/:** Applies to multiple features (layout, toolbar, status) in THIS project

**File:** `<namespace-root>/learnings/persistent-ui.md`

**Cross-ref:** Link from `SAFEWORD.md` → Common Gotchas

---

### ❌ Archive (<namespace-root>/learnings/archive/)

**Learning:** "Electron tests failed because forgot to build"

**Why archive:** One-time gotcha - after learning once, don't need full narrative

**File:** `<namespace-root>/learnings/archive/electron-build-forgotten.md`

**Note:** Short gotcha goes in SAFEWORD.md: "Electron tests use built files - run `bun run build` first"

---

## When Claude Should Suggest Extraction

**High confidence - Suggest IMMEDIATELY DURING debugging:**

- Observable debugging complexity (5+ debug cycles, 3+ error states, user says "stuck")
- Just discovered gotcha not in official docs
- Just found anti-pattern (violated best practice)
- Say: "I notice this pattern could save time on future work. Should I extract a learning after we fix this?"

**Medium confidence - Ask AFTER completing task:**

- "I noticed [pattern X] during implementation - should I document this as a learning?"

**Low confidence - Don't suggest:**

- Simple fix (1 debug cycle, typo, user says "quick fix")
- Well-documented in official library docs
- One-off implementation detail

---

## Iteration & Refinement

**Living Documentation**: This process evolves with your needs.

**Review Cycle**:

1. **Monthly**: Review existing learnings for relevance
2. **Quarterly**: Archive obsolete learnings (technology changed, pattern no longer used)
3. **Per feature**: After major features, assess if new learnings emerged

**Test the Process**:

- Did extracting this learning actually help on the next feature?
- Are learnings being referenced in future conversations?
- Are the examples clear and actionable?

**Remove When**:

- Technology deprecated (e.g., "Webpack 4 gotchas" when using Vite)
- Pattern no longer used (e.g., class components → functional components)
- Merged into official documentation (library now documents the gotcha)

**Refactor When**:

- Multiple learnings cover similar topics → consolidate
- Learning file >200 lines → split into focused topics
- Examples are outdated → update or remove
- Wording is unclear → simplify

**Feedback Loop**:

- After suggesting extraction: Note if user accepted or declined
- After user accepts: Monitor if learning is referenced in future sessions
- Adjust suggestion threshold based on acceptance rate (if <30% accepted, raise the bar)

---

## Workflow Integration

### During Development

1. **Recognize trigger** - Spent 45 min debugging race condition
2. **Assess scope** - Forward-looking? (YES) Global or project? (Project)
3. **Choose location** - Needs examples → `<namespace-root>/learnings/race-conditions.md`
4. **Extract** - Use template, write before/after examples
5. **Cross-reference** - Add to SAFEWORD.md Common Gotchas

### After Completing Feature

1. **Review** - Did we learn anything reusable?
2. **Extract** - If threshold met (>30min debug, non-obvious pattern)
3. **Update** - Add SAFEWORD.md cross-reference if needed
4. **Commit** - Include learning in commit message

---

## Anti-Patterns (Don't Extract)

❌ **Well-documented in official docs**

- "React useState is async" → Already in React docs

❌ **One-line fixes without context**

- "Changed `==` to `===`" → Trivial

❌ **Implementation without principle**

- "File X uses pattern Y" → No reusable insight

❌ **Opinions without justification**

- "Prefer tabs over spaces" → Not a gotcha

❌ **Debugging steps without lesson**

- "Tried 5 things, #4 worked" → What's the takeaway?

❌ **Extracting mid-debugging**

- Wait until fix is confirmed and working
- Premature extraction leads to incorrect learnings

❌ **Forgetting to delete old code comments after extraction**

- Learning file should REPLACE inline code comments
- Keep code clean by removing debugging notes after documenting

❌ **Keeping obsolete learnings**

- Remove when technology deprecated or pattern no longer used
- Archive instead of delete (move to archive/ with "OBSOLETE:" prefix)
- Update SAFEWORD.md references to point to replacement learning
- Example: "React class components gotchas" → OBSOLETE when project migrates to hooks

❌ **Verification stamps on project state**

A learning describes a principle that holds across sessions. It cannot vouch for current project state — code drifts. Sentences like `✅ Verified by bun run build` or `we use path X (verified)` belong in `verify.md` for the ticket that produced them, where they're pinned to a commit. In a learning file, drop the verification verb and state the principle.

- ❌ "We use `src/content.config.ts` (new Astro 6 path). ✅ Verified by `bun run build` completing cleanly."
- ✅ "Astro 6 requires `src/content.config.ts`; the legacy `src/content/config.ts` path is removed in 6.0."

The `post-tool-sync-learnings` hook flags `✅ Verified` and `Verified by …` stamps on write — if you see the warning, either drop the verb or move the claim to `verify.md`. Legitimate research-methodology uses ("verified gap in literature", "empirically verified across tickets") are not flagged.

---

## Quick Reference

| Situation             | Location                                        | Example                          |
| --------------------- | ----------------------------------------------- | -------------------------------- |
| Architecture decision | `SAFEWORD.md` → Architecture                    | Why Zustand? Why Electron-only?  |
| Short gotcha          | `SAFEWORD.md` → Gotchas                         | "Validate paths before file ops" |
| Detailed gotcha       | `<namespace-root>/learnings/` + SAFEWORD.md ref | Persistent UI, race conditions   |
| One-time bug          | `<namespace-root>/learnings/archive/`           | Forgot to build before testing   |

---

## Directory Structure

```plaintext
# Project learnings (this project)
<namespace-root>/learnings/
├── persistent-ui.md
├── electron-contexts.md
├── race-conditions.md
└── archive/
    ├── electron-build-forgotten.md
    └── test-grep-compatibility.md
```

**File Size Guidelines**:

- Forward-looking learning: 50-150 lines (includes 2-3 examples)
- Debugging narrative: 30-100 lines (problem → investigation → solution)
- If >200 lines: Split into multiple focused learnings

**When to Split**:

```text
# TOO BIG (250 lines covering 3 separate concepts)
<namespace-root>/learnings/electron-gotchas.md

# BETTER (3 focused files)
<namespace-root>/learnings/electron-renderer-context.md      (80 lines)
<namespace-root>/learnings/electron-ipc-patterns.md         (60 lines)
<namespace-root>/learnings/electron-path-validation.md      (50 lines)
```

---

## Summary

This is a **living process** - iterate and refine based on what works.

**Core Principle**: Extract knowledge that **compounds over time**. Each learning should save time on 2+ future features.

**Decision Framework**:

1. **Forward-looking?** → Extract (helps future work)
2. **Global or project?** → Choose directory
3. **Architectural or gotcha?** → Choose SAFEWORD.md or separate file
4. **ALWAYS cross-reference** → Update SAFEWORD.md

**Continuous Improvement**:

- Monthly: Review existing learnings for relevance
- Quarterly: Archive obsolete learnings
- Per feature: Assess if new learnings emerged
- Test: Did extracting this actually help on the next feature?

**When in Doubt**:

- Extract more rather than less (can archive later)
- Prefer separate file over inline comments (keeps code clean)
- Update immediately while fresh (don't defer to "later")

**Maintenance**:

- Remove when technology deprecated or pattern no longer used
- Refactor when multiple learnings cover similar topics (consolidate)
- Split when learning file >200 lines (focus on single concept)
- Update SAFEWORD.md references when learnings move or merge

---

## Key Takeaways

- Extract after 5+ debug cycles or 3+ approaches tried
- Check existing learnings first—update, don't duplicate
- One concept per file, under 200 lines
- Extract immediately while fresh (don't defer to "later")
