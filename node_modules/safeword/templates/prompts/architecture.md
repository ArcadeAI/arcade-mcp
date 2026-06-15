# Architecture Review Prompt

Review the following code changes for architectural issues.

## Check for:

1. **Misplaced logic** - Business rules in wrong layer?
2. **God module** - Too many responsibilities (>10 dependents or >500 lines)?
3. **Leaky abstraction** - Implementation details exposed to callers?
4. **Tight coupling** - Changes would cascade unnecessarily?
5. **Boundary violation** - Import from disallowed layer?

## Context

Read the project's ARCHITECTURE.md for:

- Defined layers and their responsibilities
- Allowed dependencies between layers
- Project-specific patterns and conventions

## Response Format

Return JSON:

```json
{
  "issues": [
    {
      "type": "misplaced_logic | god_module | leaky_abstraction | tight_coupling | boundary_violation",
      "location": "file:line or module name",
      "description": "What's wrong",
      "fix": "How to fix it"
    }
  ],
  "verdict": "clean | minor | refactor_needed"
}
```

### Verdict definitions:

- **clean**: No issues found
- **minor**: Small issues that should be noted but don't block commit
- **refactor_needed**: Significant issues that should be addressed before commit
