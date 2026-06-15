# Task: [Name]

**Guide**: `.safeword/guides/planning-guide.md`
**Template**: `.safeword/templates/task-spec-template.md`

---

## Standard Task (task)

Use for: bugs, improvements, internal work, refactors.

```markdown
# Task: [Name]

**Type:** Bug | Improvement | Internal | Refactor

**Scope:** [1-2 sentences describing what this task accomplishes]

**Out of Scope:** [Explicit boundaries - what this task does NOT include]

**Done When:**

- [ ] [Observable outcome 1]
- [ ] [Observable outcome 2]

**Tests:**

- [ ] [Test scenario 1 - what behavior to verify]
- [ ] [Test scenario 2 - edge case or secondary behavior]
```

**Location:** `<namespace-root>/tickets/{id}-{slug}/ticket.md`

---

## Micro Task (patch)

Use for: typos, config changes, trivial fixes. Still scoped to prevent creep.

```markdown
# Task: [Name]

**Type:** Micro

**Scope:** [One sentence - exactly what is changing]

**Out of Scope:** [Boundaries - prevents "while I'm here" expansion]

**Done When:**

- [ ] [Single observable outcome]

**Tests:**

- [ ] Existing tests pass (no new test needed)
```

**Location:** `<namespace-root>/tickets/{id}-{slug}/ticket.md`

---

## Examples

### task: Bug Fix

```markdown
# Task: Fix login timeout after 30 minutes

**Type:** Bug

**Scope:** Session refresh logic in auth middleware. User stays logged in if active.

**Out of Scope:** Session duration settings, auth flow changes, UI modifications.

**Done When:**

- [ ] User stays logged in if active within session window
- [ ] Session refreshes on API calls

**Tests:**

- [ ] Unit: session refresh extends expiry timestamp
- [ ] Unit: inactive session expires correctly after timeout
```

### task: Improvement

```markdown
# Task: Add retry logic to API client

**Type:** Improvement

**Scope:** Add exponential backoff retry for failed API requests in http client.

**Out of Scope:** Circuit breaker, rate limiting, request queuing, UI loading states.

**Done When:**

- [ ] Failed requests retry up to 3 times with exponential backoff
- [ ] Permanent failures (4xx) do not retry

**Tests:**

- [ ] Unit: retries on 5xx errors with backoff
- [ ] Unit: does not retry on 4xx errors
- [ ] Unit: gives up after max retries
```

### patch: Micro

```markdown
# Task: Fix typo in auth error message

**Type:** Micro

**Scope:** Typo in login error ("authetication" → "authentication").

**Out of Scope:** Error handling logic, other error messages, refactoring.

**Done When:**

- [ ] Typo fixed in error message string

**Tests:**

- [ ] Existing auth tests pass
```

---

## Why patch Needs Scope

Even trivial tasks need boundaries. Without explicit "Out of Scope":

- "Fix typo" becomes "improve all error messages"
- "Update config" becomes "refactor config system"
- "Rename variable" becomes "rename all related functions"

The spec takes 30 seconds to write and prevents hours of scope creep.

---

## Relationship to Feature Specs

| Type                       | Use When                                | Artifacts                            |
| -------------------------- | --------------------------------------- | ------------------------------------ |
| **Feature Spec (feature)** | User-facing feature with business value | Feature spec + test definitions file |
| **Task Spec (task)**       | Bug, improvement, internal, refactor    | Task spec with inline tests          |
| **Task Spec (patch)**      | Typo, config, trivial                   | Minimal task spec, existing tests    |

For features, use: `.safeword/templates/feature-spec-template.md`
