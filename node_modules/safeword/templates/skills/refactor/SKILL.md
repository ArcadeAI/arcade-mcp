---
name: refactor
description: Improve code structure without changing behavior. Use when
  refactoring, restructuring, simplifying, or extracting code. Also for reducing
  duplication, renaming for clarity, or addressing code smells. Enforces one
  change → test → commit cycle. NOT for style/formatting (use /lint), features,
  or bug fixes.
allowed-tools: '*'
---

# Refactoring

Improve code structure without changing behavior. One small step at a time.

**Iron Law:** ONE REFACTORING → TEST → COMMIT. Never batch changes.

## When to Use

Answer IN ORDER. Stop at first match:

1. User says "refactor", "clean up", "restructure"? → Use this skill
2. User asks to "extract", "rename", "simplify"? → Use this skill
3. Code smell identified? → Use this skill
4. User wants to add feature or fix bug? → Skip (use tdd-enforcer)
5. User wants formatting/style fixes? → Skip (use /lint)

**Code smells** (common triggers):

- Duplicated code (same logic in multiple places)
- Long function (>30 lines, doing too much)
- Magic numbers/strings (unexplained literals)
- Deep nesting (>3 levels of indentation)
- Dead code (unused functions, unreachable branches)
- Poor naming (unclear what something does)

---

## Phase 1: ASSESS

**Is this actually refactoring?**

| User Intent         | Action                                          |
| ------------------- | ----------------------------------------------- |
| "Make this cleaner" | ✓ Refactoring                                   |
| "Add validation"    | ✗ New behavior → tdd-enforcer                   |
| "Fix this bug"      | ✗ Bug fix → tdd-enforcer or systematic-debugger |
| "Format this code"  | ✗ Style → /lint                                 |

**If not refactoring:** Explain and suggest correct approach.

---

## Phase 2: PROTECT

**Does the code have tests?**

| Coverage         | Action                                        |
| ---------------- | --------------------------------------------- |
| Well-tested      | Skip to Phase 3                               |
| Partial coverage | Add characterization tests for untested parts |
| No tests         | Add characterization tests first              |

**When writing characterization tests:** Characterization tests are still tests — apply behavioral testing principles (assert on what the system does, not how).

### Characterization Tests

Capture current behavior before refactoring:

```typescript
// Characterization test - captures ACTUAL behavior
it('processOrder returns current behavior', () => {
  const result = processOrder({ items: [], user: null });
  // Whatever it returns NOW is the expected value
  expect(result).toEqual({ status: 'empty', total: 0 });
});
```

**Purpose:** Safety net, not specification. Test what the code DOES, not what it SHOULD do.

---

## Phase 3: REFACTOR

**Iron Law:** ONE refactoring at a time. Run tests after EVERY change.

### Refactoring Catalog

**Tier 1 - Always Safe** (no behavior change possible):

| Smell                | Refactoring          | Example                                |
| -------------------- | -------------------- | -------------------------------------- |
| Unclear name         | **Rename**           | `d` → `discountAmount`                 |
| Long function        | **Extract Function** | Pull 10 lines into `calculateTax()`    |
| Unnecessary variable | **Inline Variable**  | Remove `temp = x; return temp;`        |
| Misplaced code       | **Move Function**    | Move `validate()` to `Validator` class |

```typescript
// ❌ Before: unclear name
const d = price * 0.2;

// ✅ After: Rename
const discountAmount = price * 0.2;
```

**Tier 2 - Safe with Tests** (low risk if tests exist):

| Smell               | Refactoring               | Example                                           |
| ------------------- | ------------------------- | ------------------------------------------------- |
| Repeated expression | **Extract Variable**      | `order.items.length > 0` → `const hasItems = ...` |
| Complex conditional | **Decompose Conditional** | Extract `if` branches to named functions          |
| Nested conditionals | **Guard Clauses**         | Early returns instead of deep nesting             |
| Magic literal       | **Replace Magic Literal** | `0.2` → `VIP_DISCOUNT_RATE`                       |
| Unused code         | **Remove Dead Code**      | Delete unreachable branches                       |

```typescript
// ❌ Before: nested conditionals
function getDiscount(user) {
  if (user) {
    if (user.isVIP) {
      return 0.2;
    } else {
      return 0.1;
    }
  }
  return 0;
}

// ✅ After: Guard Clauses
function getDiscount(user) {
  if (!user) return 0;
  if (user.isVIP) return 0.2;
  return 0.1;
}
```

**Tier 3 - Requires Care** (higher risk, break into smaller steps):

| Smell                      | Refactoring                    | Caution                                     |
| -------------------------- | ------------------------------ | ------------------------------------------- |
| God class                  | **Extract Class**              | Do incrementally, move one method at a time |
| Type-checking conditionals | **Replace with Polymorphism**  | Requires class hierarchy                    |
| Too many parameters        | **Introduce Parameter Object** | Changes function signature                  |
| Complex loop               | **Replace Loop with Pipeline** | Ensure equivalent behavior                  |

**Tie-breaker:** If multiple refactorings apply, choose smallest scope first (Rename < Extract Variable < Extract Function < Extract Class).

---

## Phase 4: VERIFY

After each refactoring:

1. **Run tests** - Must pass
2. **If tests pass:** Commit with `refactor: [what changed]`
3. **If tests fail:** Revert immediately

### Revert Protocol

```bash
git checkout -- <changed-files>
```

**After revert:**

- Was the refactoring too large? → Try smaller step
- Did it accidentally change behavior? → Reconsider approach
- DO NOT attempt to "fix" a failed refactoring

### After 2 Failed Attempts

**STOP.** Ask user:

> "I've attempted this refactoring twice and tests keep failing. This suggests either:
>
> 1. The refactoring is too large (need smaller steps)
> 2. The code has hidden dependencies
> 3. Tests are brittle
>
> How would you like to proceed?"

---

## Phase 5: ITERATE

```text
More refactoring needed?
├─ Yes → Return to Phase 3 (one more refactoring)
└─ No → Done
    ├─ Run `/audit` to verify no dead code or new issues
    └─ Report: "Refactoring complete. Changes: [summary]"
```

**Audit catches:** Dead code left behind, new duplication (should decrease!), architecture violations.

---

## Edge Cases

**Partial test coverage:**

- Identify which functions are tested vs untested
- Add characterization tests only for code you're about to refactor
- Don't boil the ocean - test what you touch

**Refactoring reveals a bug:**

- STOP refactoring
- Note the bug location
- Ask user: "Found potential bug at X. Fix it now (switching to tdd-enforcer) or continue refactoring?"

**User requests large refactoring:**

- Break into steps: "I'll refactor this incrementally. First: [step 1]"
- Complete each step fully before next
- Never batch multiple refactorings in one edit

---

## Anti-Patterns

| Don't                           | Do                                    |
| ------------------------------- | ------------------------------------- |
| Batch multiple refactorings     | One refactoring → test → commit       |
| "Fix" a failed refactoring      | Revert, then try smaller step         |
| Refactor without tests          | Add characterization tests first      |
| Change behavior during refactor | That's a feature/fix, not refactoring |
| Skip the commit                 | Commit after every green test         |

---

## Key Takeaways

1. **One change at a time** - Never batch refactorings
2. **Tests before refactoring** - No safety net = no refactoring
3. **Revert on failure** - Don't fix, revert and retry smaller
4. **Commit after each success** - `refactor: [description]`
5. **Smallest scope first** - Rename < Extract < Move < Restructure
6. **Audit when done** - Run `/audit` to verify no dead code or new issues
