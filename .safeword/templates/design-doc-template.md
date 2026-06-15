# Design: [Feature Name]

**Guide**: `.safeword/guides/design-doc-guide.md` - Principles, structure guidelines, and avoiding bloat
**Template**: `.safeword/templates/design-doc-template.md`

**Related**: Feature Spec: `[path]` | Test Definitions: `[path]`

**TDD Note**: This design implements tests from Test Definitions. Reference specific test scenarios (e.g., "Test 3.1: Component X enables keyboard shortcut Y").

## Architecture

[1-2 paragraphs: High-level approach. What are we building and how does it fit together?]

**Diagram** (if applicable):
[Text diagram or link to visual]

## Components

### Component [N]: [ComponentName]

**What**: [Responsibility in 1 sentence]
**Where** (if applicable): `[file/path/component.ts]`
**Interface**:

```typescript
// Key types/interfaces
interface Example {
  id: string;
  // ...
}

// Key methods
function doSomething(input: Example): Result;
```

**Dependencies**: [What it uses]
**Tests**: [Which test scenarios this component enables]

### Component [N+1]: [AnotherComponentName]

**What**: [Different responsibility than Component N]
**Where** (if applicable): `[different/file/path.ts]`
**Interface**:

```typescript
// Different example
interface AnotherExample {
  value: string;
}

function anotherMethod(input: AnotherExample): Output;
```

**Dependencies**: [Different dependencies]
**Tests**: [Different test scenarios this enables]

## Data Model (if applicable)

[Describe state shape, database schema, or data structures. Include relationships between types and how data flows through the system.]

```typescript
// Core data structures
interface FeatureState {
  items: Item[];
  selectedId: string | null;
}

interface Item {
  id: string;
  name: string;
  // ...
}
```

## Component Interaction (if applicable)

[How components communicate and data flows between them]

**Flow:**
Component [N] → Component [N+1]

**Events/Calls:**

- Component [N] triggers [event/method] in Component [N+1]
- Component [N+1] updates [state/data] consumed by [other components/system]

## User Flow

1. User [action, e.g., clicks "Toggle AI Pane" button, presses Cmd+J]
2. System [response, e.g., updates state, triggers re-render, calls API]
3. User sees [outcome, e.g., AI pane appears/disappears, loading spinner, error message]

## Key Decisions

### Decision [N]: [Technical choice]

**What**: [What we're using/doing]
**Why**: [Rationale with specifics - include metrics, benchmarks, or analysis]
**Trade-off**: [What we're giving up]

### Decision [N+1]: [Technical choice]

**What**: [Different choice than Decision N]
**Why**: [Rationale with specifics - include metrics, benchmarks, or analysis]
**Trade-off**: [Different trade-off]

## Implementation Notes (if applicable)

**Constraints**:

- [Technical limitation, e.g., "Must support Safari 14+", "No Node.js dependencies"]
- [Performance requirement, e.g., "< 200ms response time", "Bundle size < 100KB"]

**Error Handling**:

- [How errors are caught and handled]
- [User-facing vs internal errors]
- [Retry/fallback strategies]

**Gotchas**:

- [Edge case or common mistake]
- [Thing to watch out for]

**Open Questions**:

- [ ] [Blocking question]
- [ ] [Needs research]

## References (if applicable)

- [ADR-XXX: Related decision]
- [External docs or examples]
- [Proof of concept]
