---
name: tdd-review
description: Use when completing a TDD step and wanting a quality check. Reviews test quality after RED, implementation correctness after GREEN, and scenario completeness after REFACTOR.
allowed-tools: '*'
---

# TDD Review

Step-aware quality review at TDD phase boundaries. Fires when a sub-checkbox is marked in test-definitions.md during implement phase.

## Detect Step

Read the gate message to determine which TDD step is next:

| Gate triggered | Step just completed           | Review focus              |
| -------------- | ----------------------------- | ------------------------- |
| `tdd:green`    | RED (test written)            | Review test quality       |
| `tdd:refactor` | GREEN (implementation passes) | Review implementation     |
| `tdd:red`      | REFACTOR (cleanup done)       | Review completed scenario |

## GREEN Gate (RED just completed — review test)

Focused review (~1 minute). Check the test that was just written:

- **Atomic?** Tests ONE behavior. Red flag: multiple When/Then pairs.
- **Right assertions?** Meaningful expectations, not `.toBeTruthy()` or `.not.toThrow()`.
- **Behavior, not implementation?** Tests observable outcomes. Red flag: mocking internals, checking call counts.
- **Fails for the right reason?** Missing behavior, not syntax errors.
- **Right test type?** Load the testing skill and consult its scope hierarchy (E2E > Integration > Unit). Was a higher-scope test practical here? Did we drop to unit when integration would catch more?
- **Coverage adequacy?** Consult testing guide's bug detection matrix. Ask: "What could still break that this test wouldn't catch?" Flag gaps — missing edge cases, error paths, or boundary values — as candidates for additional scenarios.

If issues found: fix before implementing. If clean: commit and proceed to implementation.

## REFACTOR Gate (GREEN just completed — review implementation)

Moderate review (~1-2 minutes). Check the implementation:

- **Minimal?** Only code the test requires. No anticipatory design.
- **Correct?** Does it actually satisfy the test's intent, not just make it pass by coincidence?
- **No regressions?** Full test suite still passes.
- **Run /refactor** for structural cleanup.

If issues found: fix before refactoring. If clean: run /refactor, commit, proceed.

## RED Gate (REFACTOR just completed — review completed scenario)

Full review (~2-3 minutes). The entire scenario is done. Review the complete unit:

- **Test + implementation alignment?** Does the test cover the scenario's Given/When/Then?
- **Run /quality-review** for ecosystem verification (versions, deprecated APIs, security).
- **Ready for next scenario?** Any loose ends or technical debt to note?

If issues found: address before starting next scenario. If clean: commit and proceed to next `[ ] RED`.

### Concrete example (GREEN gate)

**Context:** Agent just wrote a failing test for scenario 2 (verbose shows passing files). The `tdd:green` gate fires.

**Agent review:**

> **Atomic?** Yes — tests one behavior (passing files appear in verbose output).
> **Right assertions?** `expect(output).toContain('src/index.ts: pass')` — asserts on observable output, not internals. Good.
> **Behavior, not implementation?** Yes — checks CLI output string, not internal formatter state.
> **Fails for the right reason?** `Expected string to contain 'src/index.ts: pass'` — verbose output doesn't include passing files yet. Correct failure.
> **Right test type?** Integration — needs real linter execution to produce output. Unit wouldn't cover the formatter→CLI pipeline. Correct scope.
> **Coverage gaps?** Test only checks one file. Could miss edge case where zero files pass. Acceptable for now — boundary cases are in scenario 3.
>
> Clean.
>
> **Next:** implement minimum code in `packages/cli/src/lint.ts` to make `expect(output).toContain('src/index.ts: pass')` pass, then commit.

## Output discipline

Every review ends with a **Next:** line on its own line — imperative, name the file/command/scenario. Don't end with "proceed" or "commit and move on" alone; name what to do.

- GREEN gate clean → `**Next:** implement minimum code in {file} to make this test pass.`
- GREEN gate issues → `**Next:** rewrite assertion in {file}:{line} to check observable output, then re-review.`
- REFACTOR gate clean → `**Next:** run /refactor on {file}, then commit and mark next [ ] RED.`
- RED gate clean → `**Next:** commit, then start scenario {N} — write the failing test in {file}.`

A review without a Next: line is incomplete.

## Reminders

1. **Depth matches step** — lightweight for GREEN, moderate for REFACTOR, full for RED
2. **Single source of truth** — this skill owns all TDD review content
3. **Commit clears the gate** — review, then commit to proceed
4. **Mark sub-checkbox** — ensure the current step's `[x]` is marked in test-definitions.md

**Voice:** plainspoken and concise — write to be scanned.
