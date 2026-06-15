# Testing Guide

Test methodology, TDD workflow, and test type selection.

---

## Test Philosophy

**Behavior-biased testing:** At every test level, assert on what the system _does_ (outputs, side effects, user-visible outcomes) — never on _how_ it does it (internal state, mock call counts, private methods). Tests coupled to implementation break on every refactor. Behavioral tests survive.

**Prefer highest practical scope:** When multiple test types can verify a behavior, prefer the one that exercises more of the real system. Higher scope = more confidence. Drop to lower scope only when higher scope is impractical (combinatorial inputs, pure algorithms, isolated contracts).

**Always test what you build** — Run tests yourself before completion. Don't ask the user to verify.

---

## Test Integrity (CRITICAL)

**NEVER modify, skip, or delete tests without explicit human approval.**

Tests are the specification. When a test fails, the implementation is wrong—not the test.

### Forbidden Actions (Require Approval)

| Action                                          | Why It's Forbidden                |
| ----------------------------------------------- | --------------------------------- |
| Changing assertions to match broken code        | Hides bugs instead of fixing them |
| Adding `.skip()`, `.only()`, `xit()`, `.todo()` | Makes failures invisible          |
| Deleting tests you can't get passing            | Removes coverage for edge cases   |
| Weakening assertions (`toBe` → `toBeTruthy`)    | Reduces test precision            |
| Commenting out test code                        | Same as skipping                  |

### What To Do Instead

1. **Test fails?** → Fix the implementation, not the test
2. **Test seems wrong?** → Explain why and ask before updating
3. **Requirements changed?** → Explain the change and ask before updating tests
4. **Test is flaky?** → Fix the flakiness (usually async issues), don't skip it
5. **Test blocks progress?** → Ask for guidance, don't work around it

---

## Test Type Hierarchy

**Rule:** Prefer the highest-scope type that's practical. Higher scope = more confidence in real behavior. Drop to lower scope for combinatorial inputs or pure algorithms.

```text
E2E (seconds-minutes)    ← Full browser, user flows         ↑ prefer
  ↑
LLM Eval (seconds)       ← AI judgment, costs $0.01-0.30
  ↑
Integration (seconds)    ← Multiple modules, database, API
  ↑
Unit (milliseconds)      ← Pure functions, no I/O           ↑ fallback
```

---

## When to Use Each Test Type

Answer these questions in order. Stop at first match.

```text
1. Does this test AI-generated content quality (tone, reasoning, creativity)?
   └─ YES → LLM Evaluation
   └─ NO → Continue to question 2

2. Does this test require a real browser (Playwright/Cypress)?
   └─ YES → E2E test
      Examples: Multi-page navigation, browser-specific behavior, visual regression
      Note: React Testing Library does NOT require a browser - that's integration
   └─ NO → Continue to question 3

3. Does this test interactions between multiple components/services?
   └─ YES → Integration test
      Examples: API + database, React component + state store
   └─ NO → Continue to question 4

4. Does this test a pure function (input → output, no I/O)?
   └─ YES → Unit test
      Examples: Calculations, formatters, validators, pure algorithms
   └─ NO → Re-evaluate: What are you actually testing?
```

**Edge cases:**

- Non-deterministic functions (Math.random, Date.now) → Unit test with mocked randomness
- Functions with environment dependencies (process.env) → Integration test
- Mixed pure + I/O logic → Extract pure logic, unit test it, integration test I/O

---

## Bug Detection Matrix

Which test type catches which bug?

| Bug Type                             | Unit? | Integration? | E2E? | Best Choice     |
| ------------------------------------ | ----- | ------------ | ---- | --------------- |
| Calculation error                    | ✅    | ✅           | ✅   | Unit (fastest)  |
| Invalid input handling               | ✅    | ✅           | ✅   | Unit (fastest)  |
| Database query returning wrong data  | ❌    | ✅           | ✅   | Integration     |
| API endpoint contract violation      | ❌    | ✅           | ✅   | Integration     |
| Race condition between services      | ❌    | ✅           | ✅   | Integration     |
| State management bug                 | ❌    | ✅           | ✅   | Integration     |
| React component rendering wrong data | ❌    | ✅           | ✅   | Integration     |
| CSS layout broken                    | ❌    | ❌           | ✅   | E2E (only)      |
| Multi-page navigation broken         | ❌    | ❌           | ✅   | E2E (only)      |
| Browser-specific rendering           | ❌    | ❌           | ✅   | E2E (only)      |
| AI prompt quality degradation        | ❌    | ❌           | ❌   | LLM Eval (only) |
| AI reasoning accuracy                | ❌    | ❌           | ❌   | LLM Eval (only) |

**Key principle:** If multiple test types can catch the bug, prefer the highest scope that's practical. Use lower scope for pure logic with many edge cases.

---

## TDD Quick Reference (Tasks)

For tasks (1-2 files), follow this cycle:

1. **RED** - Write one failing test for the expected behavior
2. **GREEN** - Write minimum code to pass the test
3. **REFACTOR** - Clean up, run `/refactor` if needed

Commit after each GREEN phase.

### Escalation Check

If during implementation you discover:

- 3+ files need changes, OR
- Multiple user flows affected, OR
- New state management needed

**Stop and escalate:** "This is bigger than expected. Switching to `/bdd` for proper behavior definition."

For full TDD workflow with verification gates, red flags, walking skeleton, and phase orchestration, start feature work or run `/bdd`.

---

## Test Type Examples

### Unit Tests

```typescript
// ✅ GOOD - Pure function
it('applies 20% discount for VIP users', () => {
  expect(calculateDiscount(100, { tier: 'VIP' })).toBe(80);
});

// ❌ BAD - Testing implementation details
it('calls setState with correct value', () => {
  expect(setState).toHaveBeenCalledWith({ count: 1 });
});
```

### Integration Tests

```typescript
describe('Agent + State Integration', () => {
  it('updates character state after agent processes action', async () => {
    const agent = new GameAgent();
    const store = useGameStore.getState();

    await agent.processAction('attack guard');

    expect(store.character.stress).toBeGreaterThan(0);
    expect(store.messages).toHaveLength(2);
  });
});
```

### E2E Tests

```typescript
test('user creates account and first item', async ({ page }) => {
  await page.goto('/signup');
  await page.fill('[name="email"]', 'test@example.com');
  await page.fill('[name="password"]', 'secure123');
  await page.click('button:has-text("Sign Up")');
  await expect(page).toHaveURL('/dashboard');

  await page.click('text=New Item');
  await page.fill('[name="title"]', 'My First Item');
  await page.click('text=Save');
  await expect(page.getByText('My First Item')).toBeVisible();
});
```

### LLM Evaluations

```yaml
- description: 'Infer user intent from casual input'
  vars:
    input: 'I want to order a large pepperoni'
  assert:
    - type: javascript
      value: JSON.parse(output).intent === 'order_pizza'
    - type: llm-rubric
      value: |
        PASS: Correctly identifies pizza order, confirms size and type
        FAIL: Wrong intent, ignores key details, or generic response
```

---

## E2E Testing with Persistent Dev Servers

Isolate persistent dev instances from test instances to avoid port conflicts.

**Port Isolation Strategy:**

- **Dev instance**: Project's configured port (e.g., 3000) - runs persistently
- **Test instances**: `devPort + 1000` (e.g., 4000) - managed by Playwright

**Playwright Configuration:**

```typescript
// playwright.config.ts
export default defineConfig({
  webServer: {
    command: 'bun run dev:test',
    port: 4000,
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
  use: {
    baseURL: 'http://localhost:4000',
  },
});
```

**Package.json Scripts:**

```json
{
  "scripts": {
    "dev": "vite --port 3000",
    "dev:test": "vite --port 4000",
    "test:e2e": "playwright test"
  }
}
```

**Cleanup:** See `.safeword/guides/zombie-process-cleanup.md` for killing zombie servers.

---

## Writing Effective Tests

### AAA Pattern (Arrange-Act-Assert)

```typescript
it('applies discount to VIP users', () => {
  const user = { tier: 'VIP' },
    cart = { total: 100 }; // Arrange
  const result = applyDiscount(user, cart); // Act
  expect(result.total).toBe(80); // Assert
});
```

### Test Naming

Be descriptive and specific:

```typescript
// ✅ GOOD
it('returns 401 when API key is missing');
it('preserves user input after validation error');

// ❌ BAD
it('works correctly');
it('should call setState');
```

### Test Independence

Each test should:

- Run in any order
- Not depend on other tests
- Clean up its own state
- Use fresh fixtures/data

```typescript
// ✅ GOOD - Fresh state per test
beforeEach(() => {
  gameState = createFreshGameState();
});

// ❌ BAD - Shared state
let sharedUser = createUser();
it('test A', () => {
  sharedUser.name = 'Alice';
});
it('test B', () => {
  expect(sharedUser.name).toBe('Alice'); // Depends on A!
});
```

### Test Data Builders

Use builders for complex test data:

```typescript
function buildCharacter(overrides = {}) {
  return {
    id: 'test-char-1',
    name: 'Cutter',
    playbook: 'Cutter',
    stress: 0,
    ...overrides,
  };
}

it('should increase stress when resisting', () => {
  const character = buildCharacter({ stress: 3 });
  // Test uses character with stress=3
});
```

### Async Testing

**NEVER use arbitrary timeouts:**

```typescript
// ❌ BAD - Arbitrary timeout
await page.waitForTimeout(3000);
await sleep(500);

// ✅ GOOD - Poll until condition
await expect.poll(() => getStatus()).toBe('ready');
await page.waitForSelector('[data-testid="loaded"]');
await waitFor(() => expect(screen.getByText('Success')).toBeVisible());
```

---

## What Not to Test

❌ **Implementation details** - Private methods, CSS classes, internal state
❌ **Third-party libraries** - Assume React/Axios work, test YOUR code
❌ **Trivial code** - Getters/setters with no logic, pass-through functions
❌ **UI copy** - Use regex `/submit/i`, not exact text matching

---

## Coverage Goals

- **Unit tests:** 80%+ coverage of pure functions
- **Integration tests:** All critical paths covered
- **E2E tests:** All critical multi-page user flows
- **LLM evals:** All AI features have evaluation scenarios

**What are "critical paths"?**

- **Always critical:** Authentication, payment/checkout, data loss scenarios
- **Usually critical:** Core user workflows, primary feature flows
- **Rarely critical:** UI polish, admin-only features with low usage
- **Rule of thumb:** If it breaks, would users notice immediately?

---

## LLM Eval Cost Considerations

**Cost:** $0.01-0.30 per run depending on prompt size.

**Prompt caching reduces costs by 90%** (30 scenarios: $0.30 → $0.03 after first run).

**Cost reduction strategies:**

- Cache static content (system prompts, examples, rules)
- Batch multiple scenarios in one run
- Run full evals on PR/schedule, not every commit

---

## CI/CD Integration

- Run unit + integration tests on every commit (fast feedback)
- Run E2E tests on every PR
- Run LLM evals on schedule (weekly catches regressions without per-commit cost)

---

## Quick Reference

| Need to test...      | Test type   | Technology | Speed  | Cost       |
| -------------------- | ----------- | ---------- | ------ | ---------- |
| Pure function        | Unit        | Vitest     | Fast   | Free       |
| Service integration  | Integration | Vitest     | Medium | Free       |
| Full user flow       | E2E         | Playwright | Slow   | Free       |
| AI reasoning quality | LLM eval    | Promptfoo  | Slow   | $0.01-0.30 |

---

## Project-Specific Testing Documentation

**Location:** `tests/SAFEWORD.md` or `tests/AGENTS.md`

**What to include:**

- Tech stack (Vitest/Jest, Playwright/Cypress, Promptfoo)
- Test commands (how to run tests, single-file execution)
- Setup requirements (API keys, build steps, database)
- File structure and naming conventions
- Coverage requirements and PR requirements

**If not found:** Ask user "Where are the testing docs?"
