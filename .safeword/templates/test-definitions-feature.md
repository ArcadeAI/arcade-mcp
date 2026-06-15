# Test Definitions: [Feature Name]

Feature source: `features/<slug>.feature`

test-definitions.md is the R/G/R ledger. Keep executable Given/When/Then
scenarios in the `.feature` file; keep only scenario progress here so hooks can
derive the active RED/GREEN/REFACTOR step.

## Rule: [Business rule the scenarios below cover]

### Scenario: [Scenario name from the feature file]

- [ ] RED
- [ ] GREEN
- [ ] REFACTOR

### Scenario: [Second scenario name]

- [ ] RED
- [ ] GREEN
- [ ] REFACTOR

## Rule: [Another business rule]

### Scenario: [Scenario name]

- [ ] RED
- [ ] GREEN
- [ ] REFACTOR

---

## Feature-level cross-scenario refactor

Marked at verify-phase: either `<sha>` (the refactor commit) or `skip: <non-empty reason>` (no shared fixtures or duplication emerged). The done-gate hard-blocks if this row is missing or has an empty skip reason on tickets that use the annotated checkbox format.

- [ ] cross-scenario
