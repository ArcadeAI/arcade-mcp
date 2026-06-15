---
name: quality-review
description: Deep code review with web research. Use when double-checking code
  against latest docs, verifying dependency versions, or reviewing security
  concerns. Complements automatic quality hook with ecosystem verification.
allowed-tools: '*'
---

# Quality Reviewing

Deep review with web research to verify against current ecosystem. Complements automatic hook.

**When to use this skill (not automatic hook):**

- **Explicit web research**: "double check against latest docs", "verify versions", "check security"
- **Deep dive needed**: Performance, architecture, trade-offs beyond automatic hook
- **Pre-change review**: Review before making changes (hook only triggers after)

**Relationship:** Automatic hook does fast check with existing knowledge. This skill does deep dive with web research (2-3 min).

## 1. Detect Phase

If in BDD workflow, read the current ticket from `<namespace-root>/tickets/` and apply phase-appropriate research:

| Phase           | Research Focus                                  |
| --------------- | ----------------------------------------------- |
| intake          | Similar features in ecosystem, scope patterns   |
| define-behavior | Testing patterns, BDD research and patterns     |
| scenario-gate   | Architecture patterns, test layer strategy      |
| implement       | **Library versions, deprecated APIs, security** |
| done            | CI/CD patterns, release checklists              |

## 2. Verify Versions (Primary Value)

**CRITICAL**: This is your main differentiator from automatic hook.

Search for: "[library name] latest stable version 2025"
Search for: "[library name] security vulnerabilities"

**Flag if outdated:**

- Major versions behind -> WARN (e.g., React 17 when 19 is stable)
- Minor versions behind -> NOTE
- Security vulnerabilities -> CRITICAL (must upgrade)
- Using latest -> Confirm

## 3. Verify Documentation (Primary Value)

Fetch official documentation for libraries in use.

**Look for:**

- Deprecated APIs being used?
- Newer, better patterns available?
- Recent recommendation changes?

## Output Format

```markdown
## Quality Review

**Versions:** [✓/⚠️/❌] [Latest version check]
**Documentation:** [✓/⚠️/❌] [Current docs check]
**Security:** [✓/⚠️/❌] [Vulnerability check]

**Verdict:** [APPROVE / REQUEST CHANGES / NEEDS DISCUSSION]

**Critical issues:** [List or "None"]
**Suggested improvements:** [List or "None"]
**Provenance:** For version/API claims:

- (verified: [source URL or doc title]) — fetched this session
- (training data: may be outdated) — not verified
- (uncertain) — could not verify

**Next:** [concrete action — upgrade X from a.b.c to x.y.z, refactor {file}:{line}, ask team about Z, or proceed to implementation if APPROVE]
```

The `**Next:**` line is required. On APPROVE, name what to do now (proceed, commit, run /verify). On REQUEST CHANGES, name the specific edit and re-review trigger. On NEEDS DISCUSSION, name the question to ask. A verdict that doesn't tell the reader what to do next is incomplete.

## Reminders

1. **Primary value: Web research** - Verify versions, docs, security
2. **Complement automatic hook** - Hook prompts for the decision-brief verdict and per-phase evidence; you verify versions, primary-literature claims, and ecosystem context the hook can't see
3. **Phase matters** - Adapt research focus to current BDD phase
4. **Be concise** - Hook already prompts for general quality, focus on what it can't do

**Voice:** plainspoken and concise — write to be scanned.
