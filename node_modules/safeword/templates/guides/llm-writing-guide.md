# LLM Writing Guide

How to write documentation that LLMs will read and follow: CLAUDE.md, SAFEWORD.md, guides, skills, commands, hooks.

---

## Core Principles

### 1. MECE (Mutually Exclusive, Collectively Exhaustive)

Decision trees must have no overlap and cover all cases.

```markdown
❌ BAD - Overlapping:
├─ Pure function?
├─ Multiple components?
├─ Full user flow?

✅ GOOD - Sequential, stop at first match:

1. AI content quality? → LLM Eval
2. Requires real browser? → E2E test
3. Multiple components? → Integration test
4. Pure function? → Unit test
```

### 2. Explicit Over Implicit

Define all terms. Never assume LLMs know what you mean.

```markdown
❌ BAD: "Test at the lowest level"
✅ GOOD: "Test with the fastest test type that can catch the bug"

Define: "Critical paths" → auth, payment (always); UI polish (rarely)
Define: "Browser" → Real browser (Playwright), not jsdom
```

### 3. Concrete Examples Over Abstract Rules

For every rule, include 2-3 good vs bad examples.

```markdown
❌ BAD: "Follow best practices for testing"

✅ GOOD:
// ❌ Testing business logic with E2E (slow)
test('discount', async ({ page }) => { await page.goto('/checkout')... })

// ✅ Unit test (fast)
it('applies 20% discount', () => { expect(calculateDiscount(100, 0.20)).toBe(80) })
```

### 4. Edge Cases Must Be Explicit

After stating a rule, add edge cases.

```markdown
Rule: "Unit test pure functions"

Edge cases:

- Math.random(), Date.now() → Unit test with mocked randomness/time
- process.env dependencies → Integration test
- Mixed pure + I/O → Extract pure part, unit test separately
```

### 5. No Contradictions

Different sections must align. Grep for related terms when updating.

```markdown
❌ Section A: "E2E tests only for critical paths"
Section B: "All user-facing features have E2E tests"

✅ Both sections use same definition of "critical"
```

---

## Decision Tree Patterns

### Sequential Over Parallel

Structure as ordered steps, not simultaneous checks.

```markdown
❌ BAD - Parallel:
├─ Pure function?
├─ Multiple components?
└─ Full user flow?

✅ GOOD - Sequential:
Answer IN ORDER, stop at first match:

1. Pure function? → Unit
2. Multiple components? → Integration
3. Full user flow? → E2E
```

### Tie-Breaking Rules

When multiple options apply, tell LLMs how to choose.

```markdown
"If multiple test types can catch the bug, choose the fastest one."
```

### Lookup Tables for Complex Decisions

When 3+ branches exist, provide a table.

```markdown
| Bug Type          | Unit? | Integration? | E2E? | Best Choice    |
| ----------------- | ----- | ------------ | ---- | -------------- |
| Calculation error | ✅    | ✅           | ✅   | Unit (fastest) |
| Database bug      | ❌    | ✅           | ✅   | Integration    |
| CSS layout broken | ❌    | ❌           | ✅   | E2E            |
```

---

## Document Structure

### Position-Aware Writing

Claude 4 models show reduced positional bias — the "lost in the middle" problem is less severe. Focus on clarity over position tricks.

**Guidelines:**

- Place large reference documents at TOP with instructions below (Anthropic long-context tips)
- For short config files (CLAUDE.md, SAFEWORD.md), position matters less — focus on clear structure
- Avoid burying critical rules in the middle of long documents (still the weakest position)
- Use "Key Takeaways" sections at the end for reinforcement, not as the sole location for critical rules

### Re-evaluation Paths

Provide concrete next steps for dead ends.

```markdown
❌ BAD: "If none apply, re-evaluate"

✅ GOOD: "If doesn't fit categories:

1. Break it down: Separate pure logic from I/O/UI
2. Test each piece: Pure → Unit, I/O → Integration, Multi-page → E2E"
```

---

## Anti-Patterns

| Don't                                 | Why                                                |
| ------------------------------------- | -------------------------------------------------- |
| Visual metaphors (pyramids, icebergs) | LLMs don't process visuals                         |
| Undefined jargon                      | "Technical debt" needs definition                  |
| Percentages without context           | "70/20/10" meaningless without adjustment guidance |
| Caveats in tables                     | Parentheticals break pattern matching              |
| Critical info in middle               | Lost-in-middle phenomenon                          |

---

## Quality Checklist

- [ ] Decision trees: MECE, sequential, with tie-breakers
- [ ] All terms explicitly defined
- [ ] Every rule has good vs bad examples
- [ ] Edge cases covered
- [ ] No contradictions between sections
- [ ] Complex decisions have lookup tables
- [ ] Dead-end paths have re-evaluation steps
- [ ] Critical rules not buried in the middle of long documents

---

## Key Takeaways

- Decision trees: sequential, MECE, with tie-breakers
- Every rule needs concrete examples (good vs bad)
- Define all terms explicitly—assume nothing is obvious
- Avoid burying critical rules in the middle — use clear structure over position tricks
