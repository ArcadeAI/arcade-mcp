# Project Context Files (CLAUDE.md, CURSOR.md, AGENTS.md)

## When to Create Context Files

Create the file(s) that best match your tooling. It’s okay to have more than one if different tools are used.

- `CLAUDE.md` (Claude-specific)
  - Claude/Desktop or Claude Code-specific guidance (hooks, skills, MCP gateways)
  - Prompts, behaviors, and non-obvious conventions for Claude
- `CURSOR.md` (Cursor-specific)
  - Editor/extension conventions, quick commands, keybindings, gotchas for Cursor
- `AGENTS.md` (tool-agnostic)
  - Generic “project context” consumed by multiple agents/editors

All project context files should:

- **CRITICAL:** Reference `.safeword/SAFEWORD.md` at the top
- Architecture decisions with "why" (not just "what")
- Design philosophy and conventions
- Common gotchas specific to this codebase
- Cross-references to subdirectory files

**Subdirectory files** (e.g., `tests/AGENTS.md`, `packages/app/CLAUDE.md`) - Create when:

- > 3 unique rules that don't fit in root
- Working in that directory needs specialized context
- **Skip if:** Directory is straightforward or already covered in root

**Naming convention summary:**

- `CLAUDE.md` for Claude-specific guidance
- `CURSOR.md` for Cursor-specific guidance
- `AGENTS.md` for cross-agent compatibility (tests, docs, most projects)

## SAFEWORD Trigger (Required)

**MANDATORY:** Every project-level context file (CLAUDE.md, CURSOR.md, AGENTS.md) must start with a trigger to SAFEWORD:

```markdown
# Project Name - Developer Context

**⚠️ ALWAYS READ FIRST:** `.safeword/SAFEWORD.md`

The SAFEWORD.md file contains core development patterns, workflows, and conventions.
Read it BEFORE working on any task in this project.

---

[Rest of project-specific content...]
```

**Why:** `.safeword/SAFEWORD.md` contains universal workflows (TDD, feature development, etc.) that apply across all projects. Project files should only contain project-specific context.

## Agent Context Auto-Loading Behavior

**How Context Loading Works:**

1. Tools typically load a root context file (CLAUDE.md, CURSOR.md, AGENTS.md)
2. Subdirectory context files may load when working inside those dirs
3. Hierarchical loading (root + subdirectory) is common

**Example:**

```text
Working in: /project/src/feature/
Loaded context:
  ✓ /project/CLAUDE.md (Claude-specific guidance)
  ✓ /project/src/feature/AGENTS.md (feature-specific rules)
```

**Design implication:** Subdirectory files should assume root context is available

- Use "See root SAFEWORD.md or AGENTS.md for architecture" cross-references
- Don't duplicate root content in subdirectory files
- Focus subdirectory files on specialized conventions for that area

```markdown
❌ BAD - tests/AGENTS.md duplicates root TDD workflow:

## TDD Workflow

1. Write failing tests first (RED)
2. Implement minimum code (GREEN)
3. Refactor while green

✅ GOOD - tests/AGENTS.md references root:

## Testing Conventions

See root AGENTS.md for TDD workflow. This file covers test-specific patterns.
```

**Reliability note:** Auto-loading works best when you explicitly reference your file in conversation (e.g., "following the guidelines in CLAUDE.md"). Implicit automatic reference can be less reliable.

**Deprecated:** `*.local.md` is no longer recommended - use imports instead for better multi-worktree support

## File Structure Pattern

```plaintext
project/
├─ SAFEWORD.md                  # Project context (references guides)
├─ CLAUDE.md                    # Claude-specific context
├─ CURSOR.md                    # Cursor-specific context (optional)
└─ tests/AGENTS.md              # Test conventions (cross-agent)
```

**Modular Approach (Recommended):**

```plaintext
project/
├─ AGENTS.md / CLAUDE.md        # 50 lines: imports + structure
├─ docs/architecture.md         # 100 lines: architecture decisions
└─ docs/conventions.md          # 80 lines: coding conventions
```

Main context file imports modules:

```markdown
@docs/architecture.md
@docs/conventions.md
```

## Skills (`.claude/skills/`)

Skills inject context on demand — loaded when relevant, not every session like CLAUDE.md.

**When to use a skill vs. CLAUDE.md:**

| Use CLAUDE.md for                        | Use a skill for                           |
| ---------------------------------------- | ----------------------------------------- |
| Always-on rules and conventions          | Reference material needed sometimes       |
| Behavioral principles                    | Workflow procedures                       |
| Things the agent must know every session | Things the agent needs for specific tasks |

**Writing skill descriptions:** Claude matches semantically, not by keyword. Describe the **situation** where the skill applies, not words the user might say.

```yaml
# Bad — keyword list, brittle
description: Use when user says 'refactor', 'clean up', 'restructure'

# Good — semantic intent + natural phrases + negative constraint
description: Improve code structure without changing behavior. Use when
  refactoring, restructuring, or simplifying code. NOT for style/formatting,
  features, or bug fixes.
```

**Key constraints:**

- Combined description + when_to_use capped at 1,536 chars — front-load the key use case
- Skills compete for 25K token compaction budget (most recent first) — keep under 500 tokens
- CLAUDE.md survives compaction; skills may be dropped — critical instructions belong in CLAUDE.md
- No priority order between skills and CLAUDE.md — avoid contradictions rather than relying on override

**See also:** `<namespace-root>/learnings/skill-description-design.md` for anti-patterns and examples.

---

## Content Guidelines

**Include:**

- "Why" over "what" - Explain architectural trade-offs, not features
- Project-specific conventions - Unique to THIS codebase
- Domain requirements - Specialized knowledge (game mechanics, industry standards, UX patterns)
- Concrete examples - Good vs bad patterns
- Gotchas - Common mistakes developers make HERE
- Cross-references - Link to subdirectories, don't duplicate

**Exclude:**

- Generic advice ("follow best practices")
- Feature lists (put in README.md)
- Setup instructions (put in README.md)
- Phase tracking (put in ROADMAP.md)
- API documentation (put in code comments)

## Target Line Counts

- Root: 100-200 lines (architecture + philosophy)
- Subdirectories: 60-100 lines (focused conventions)
- Total project: <500 lines across all files
- **With imports:** Main file 50 lines, modules 100-150 lines each

**Rule:** If >200 lines, extract to subdirectory or use imports.

**File size:** Keep under 50KB for optimal performance (though no hard limit)

## Anti-Patterns to Avoid

❌ **Redundancy between root and subdirectory files** (#1 source of bloat)

- Don't list all stores in root if packages/web/AGENTS.md covers them
- Don't document testing patterns in root if tests/AGENTS.md exists
- Don't repeat gotchas - reference subdirectory for details
- Each fact stated exactly once, use cross-references elsewhere

❌ **Implementation details in root file**

- File paths (store.ts:127-137) belong in subdirectory files
- Specific line numbers change frequently
- File trees and directory structures
- Line counts and feature status lists

❌ **Testing sections in non-test files**

- Testing philosophy → tests/AGENTS.md (always)
- Test commands → tests/AGENTS.md or README.md
- Test patterns → tests/AGENTS.md

❌ **User-facing documentation**

- Setup instructions → README.md
- Development commands → README.md
- Feature lists → ROADMAP.md
- API documentation → Code comments or separate docs

❌ **Generic advice**

- "Use TypeScript" (not project-specific)
- "Follow best practices" (too vague)
- "Write tests" (duh - say WHICH tests for WHAT)

❌ **Meta-commentary**

- "Last Updated: 2025-01-19"
- "This file was reduced from 634 → 152 lines"
- Commit history (that's what git is for)

❌ **Outdated information**

- Revisit after major architectural changes
- Remove sections when they no longer apply
- Update cross-references when files move

## Cross-Reference Pattern

**Root file:**

```markdown
**Agents** (`app/src/agents/`) - LLM logic. See `/AGENTS.md`.
```

**Subdirectory file:**

```markdown
**Context:** Working with AI agents. See root `SAFEWORD.md`/`AGENTS.md` for architecture.
```

**Import pattern:**

```markdown
# Project Context

See @README for project overview and @package.json for available npm commands.

## Architecture

@docs/architecture.md

## Coding Standards

@.safeword/guides/llm-writing-guide.md

## Git Workflow

Details in @docs/git-workflow.md
```

**Import features:**

- **Relative paths:** `@docs/file.md` (relative to AGENTS.md location)
- **Absolute paths:** `@/path/to/file.md`
- **Home directory:** `@.safeword/guides/file.md` (personal conventions across all projects)
- **Recursive imports:** Imported files can import others (max depth: 5 hops)
- **Inline usage:** Can reference imports in text, not just standalone lines
- **Code blocks:** Imports ignored inside `` `code spans` `` and code blocks

## Example: Well-Structured Root (AGENTS.md / CLAUDE.md / CURSOR.md)

```markdown
# Project Name - Developer Context

**⚠️ ALWAYS READ FIRST:** `.safeword/SAFEWORD.md`

The SAFEWORD.md file contains core development patterns, workflows, and conventions.
Read it BEFORE working on any task in this project.

---

Brief description. Current status.

## Design Philosophy

1. **Test-Driven Development (TDD):** Write tests before implementation
2. **Core principle:** Why we chose this approach
3. **Core principle:** Trade-offs we accepted

## Architecture Decisions

### Tech Choice 1

**Decision:** What we chose
**Why:** Reduces X, improves Y (specific numbers)
**Trade-off:** Harder to debug, but worth it for UX
**Gotcha:** Must do Z or it breaks

## Domain Requirements

### Game Mechanics (Blades in the Dark)

- Position/effect system (rulebook p.8-12)
- Fiction-first approach

**Key principles:**

- Position telegraphed before roll
- Consequences flow from fiction

### Document Editor UX

- Performance <16ms per keystroke
- Standard OS text editing conventions

**Key principles:**

- Fast is a feature
- Don't reinvent native behavior

## Common Gotchas

1. **Thing:** Why it breaks (see Design Philosophy → Section)

## File Organization

**Dir** (`path/`) - Purpose. See `path/AGENTS.md`.
```

## Maintenance

- Update when architecture changes
- Remove outdated sections immediately
- Consolidate if multiple files reference same concept
- Test: Can new developer understand "why" from reading this?
- **Use imports** to keep main file under 200 lines
- Verify loaded context matches intent (check hierarchical loading behavior)

---

## Domain Requirements Section (Optional)

**When to add:**

- Project has specialized domain knowledge (game mechanics, industry standards, UX patterns)
- Domain concerns are non-obvious from codebase alone
- You find yourself repeatedly explaining domain rules to AI

**When to skip:**

- Domain is obvious from code structure (REST API patterns)
- Tech stack IS the domain (generic CRUD app)
- Simple projects without specialized knowledge

**Structure (easy to parse):**

```markdown
## Domain Requirements

### [Domain Name 1]

- [Key principle or rule]
- [Key principle or rule]
- [Resource reference if applicable]

**Key principles:**

- [Specific guideline with rationale]
- [Specific guideline with rationale]

### [Domain Name 2]

- [Key principle or rule]
- [Key principle or rule]

**Key principles:**

- [Specific guideline with rationale]
```

**Examples:**

```markdown
## Domain Requirements

### Blades in the Dark Mechanics

- Position/effect system (BITD rulebook p.8-12)
- Stress and harm tracking (p.13-15)
- Downtime and long-term projects (p.16-20)

**Key principles:**

- Fiction drives mechanics (not dice → narrative)
- Position must be telegraphed before roll
- Effect established collaboratively with player
- Consequences flow from fiction, not arbitrary

### Document Editor UX

- Text editing performance (<16ms per keystroke)
- Undo/redo granularity (word-level, not character)
- Selection handling (standard OS conventions)

**Key principles:**

- Performance over features (fast is a feature)
- Native OS behavior (don't reinvent text editing)
- Accessibility first (screen readers, keyboard nav)

### Conversational AI Patterns

- GM tone: Collaborative, not dictatorial
- Player agency: Always offer meaningful choices
- Emergent narrative: Build on player ideas

**Key principles:**

- Ask questions, don't declare outcomes
- "Yes, and..." over "No, but..."
- Telegraph consequences before they happen
```

**Why this structure:**

- ✅ **Easy to parse** - Simple markdown hierarchy (##, ###, bullets)
- ✅ **Scannable** - Domain names as headers, principles as bullets
- ✅ **Rationale included** - Explains "why" not just "what"
- ✅ **Resource references** - Links to rulebooks, docs, standards
- ✅ **Concrete** - Specific guidelines, not vague advice

**Integration with auto-quality-review hook:**

- Hook prompts: "Does it adhere to... domain requirements?"
- Claude checks CLAUDE.md/AGENTS.md for Domain Requirements section
- If present → Reviews against documented principles
- If absent → Infers domain from context as usual

---

## Writing for LLM Comprehension

**Critical:** These files are instructions consumed by LLMs.

**See:** `@.safeword/guides/llm-writing-guide.md` for core principles and quality checklist.

---

## Best Practices from Anthropic

**Conciseness:**

- Use short, declarative bullet points (not narrative paragraphs)
- Trim redundancy (don't explain obvious folder names like "components folder contains components")
- Don't include commentary or nice-to-have information
- Files are loaded with every request - keep lean

**Effectiveness:**

- **Treat as living document** - Constantly refine based on what works
- Periodically review and refactor for clarity
- At Anthropic, teams use prompt improver to tune instructions
- Add emphasis ("IMPORTANT", "YOU MUST") for critical rules
- Explicitly reference your context file in prompts ("following CLAUDE.md guidelines") for better adherence

**Token Budget:**

- Context files are often prepended to prompts - they consume context with each interaction
- Bloated files cost more tokens and introduce noise
- Keep under 50KB for optimal performance (though no hard limit)
- Use imports to modularize instead of monolithic files

---

## Key Takeaways

- Keep context files under 200 lines—use imports to modularize
- Short declarative bullets, not narrative paragraphs
- Update immediately when architecture changes (stale docs = confusion)
- Avoid burying critical rules in the middle — use clear structure over position tricks
