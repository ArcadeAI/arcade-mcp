# Decomposition Checkpoints & Splitting

Splitting is **suggested, not mandatory** — user decides.

## When to Split

| Checkpoint          | Trigger                               | Action                     |
| ------------------- | ------------------------------------- | -------------------------- |
| **Entry**           | 2+ user stories OR vague scope        | Split into epic + features |
| **define-behavior** | >15 scenarios OR 3+ distinct clusters | Split by user journey      |
| **scenario-gate**   | >20 tasks OR 5+ major components      | Split by component/layer   |
| **implement**       | >10 tests per slice                   | Break into smaller slices  |
| **TDD Loop**        | >5 unit tests for single E2E          | Break E2E into steps       |

## Entry Checkpoint Reasoning

```text
STEP 1: Count distinct user stories
- 1 story → feature
- 2 parallel stories → suggest 2 features
- 2 coupled stories (shared state) → 1 feature with 2 journeys
- 3+ stories OR can't enumerate → epic

STEP 2: Assess depth
- 6+ sequential steps, state machines → likely epic
```

## Split Protocol

**New ticket:**

1. Create epic with `children:` array
2. Create child tickets with `parent:` link
3. Commit: "chore: split [name] into N features"

**Existing ticket (promote):**

1. Change `type: feature` → `type: epic`
2. Add `children:` array
3. Create child tickets with `parent:` link

## Restart Points After Split

| Split At        | Child Restarts From |
| --------------- | ------------------- |
| Entry           | `intake`            |
| define-behavior | `scenario-gate`     |
| scenario-gate+  | `implement`         |

## User Override

User can decline: "Proceed anyway"

- Log: "Split suggested but user declined"
- Continue at current phase
- Don't re-suggest at same checkpoint this session
