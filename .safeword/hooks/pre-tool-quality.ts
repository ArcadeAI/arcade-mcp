#!/usr/bin/env bun
// Safeword: Quality Gates - PreToolUse enforcer
// Two-purpose: LOC gate (blast radius control) + artifact prerequisite check
// Fires on Edit|Write|MultiEdit|NotebookEdit

import { execSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import nodePath from 'node:path';

import { getTicketInfo, parseTddStep } from './lib/active-ticket.ts';
import { isGitOperationInProgress } from './lib/git-operation.ts';
import { collectNewTransitions } from './lib/checkbox-transitions.ts';
import { parseFrontmatter } from './lib/hierarchy.ts';
import { evaluateAcGate, evaluateJtbdGate } from './lib/jtbd.ts';
import { classifyAnnotation, isValidSkipReason } from './lib/parse-annotation.ts';
import {
  detectPhaseAdvance,
  gatePhaseAdvance,
  hashArtifact,
  isReviewGateEnabled,
  parseReviewStamps,
  type ReviewStamp,
  reviewGateForNextAsset,
  reviewScope,
} from './lib/review-ledger.ts';
import {
  EXPLAIN_HINT,
  getStateFilePath,
  LOC_THRESHOLD,
  META_PATHS,
  type QualityState,
  recordFailure,
} from './lib/quality-state.ts';
import { isNamespacePath, resolveNamespaceRoot } from './lib/namespace-root.ts';

const EDIT_TOOLS = ['Edit', 'Write', 'MultiEdit', 'NotebookEdit'];

interface HookInput {
  session_id?: string;
  tool_name?: string;
  tool_input?: {
    file_path?: string;
    notebook_path?: string;
    old_string?: string;
    new_string?: string;
    content?: string;
    edits?: Array<{ old_string?: string; new_string?: string }>;
    command?: string;
  };
}

/**
 * Matches `git commit` (any flags / message after) but rejects `git commit-tree`,
 * `git commit-graph`, etc. The trailing (?!-) lookahead is what distinguishes them.
 */
const GIT_COMMIT_COMMAND = /\bgit\s+commit\b(?!-)/;

/**
 * Heuristic: a path is a test file if it matches *.test.* or *.spec.*, or lives
 * inside a tests/ or __tests__/ directory. Covers safeword's convention plus the
 * broader JS/TS ecosystem; intentionally permissive — false negatives just mean
 * the gate doesn't fire, false positives would block legitimate refactors.
 */
function isTestFile(path: string): boolean {
  return (
    /\.(test|spec)\.[cm]?[jt]sx?$/.test(path) ||
    path.includes('/tests/') ||
    path.startsWith('tests/') ||
    path.includes('/__tests__/')
  );
}

/**
 * Read personas.md for the JTBD gate, honoring a configured `paths.personas`
 * (ticket K7N2QM). Degrades to '' when the file or config is absent/unreadable
 * — knownPersonaRefs('') yields an empty set, so unresolved refs are denied.
 */
function readPersonasForGate(ticketDirectory: string): string {
  const projectRoot = nodePath.join(ticketDirectory, '..', '..', '..');
  const personasPath = resolvePersonasPath(projectRoot);
  return existsSync(personasPath) ? readFileSync(personasPath, 'utf8') : '';
}

function resolvePersonasPath(projectRoot: string): string {
  const defaultPath = nodePath.join(resolveNamespaceRoot(projectRoot), 'personas.md');
  const configFile = nodePath.join(projectRoot, '.safeword', 'config.json');
  if (!existsSync(configFile)) return defaultPath;
  const configured = readConfiguredPersonasPath(readFileSync(configFile, 'utf8'));
  if (configured === undefined) return defaultPath;
  return nodePath.isAbsolute(configured) ? configured : nodePath.join(projectRoot, configured);
}

function readConfiguredPersonasPath(rawConfig: string): string | undefined {
  try {
    const parsed = JSON.parse(rawConfig) as { paths?: { personas?: unknown } };
    const configured = parsed.paths?.personas;
    return typeof configured === 'string' && configured.trim() !== '' ? configured : undefined;
  } catch {
    // Malformed config.json is pre-tool-config-guard's concern; the JTBD gate
    // degrades to the default personas path rather than blocking the edit.
    return undefined;
  }
}

function deny(reason: string, additionalContext?: string): never {
  const output: Record<string, unknown> = {
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: `${reason}\n\n${EXPLAIN_HINT}`,
      ...(additionalContext ? { additionalContext } : {}),
    },
  };
  console.log(JSON.stringify(output));
  process.exit(0);
}

/**
 * A required frontmatter field counts as missing when it is absent, the literal
 * string `'null'`, or empty — including an empty block sequence (which parses to
 * `[]`) or a list of only blank items.
 */
function isMissingFrontmatterField(value: string | string[] | undefined): boolean {
  if (value === undefined || value === 'null') return true;
  return Array.isArray(value) ? value.every(item => item.trim() === '') : value.trim() === '';
}

const projectDirectory = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();

// Both review gates (NMSD94, Tier 1 + Tier 2) are off unless `.safeword/config.json`
// sets `reviewGate: true`. Shared so the two call sites can't drift on the path.
function isReviewGateOn(): boolean {
  const configFile = nodePath.join(projectDirectory, '.safeword', 'config.json');
  return isReviewGateEnabled(existsSync(configFile) ? readFileSync(configFile, 'utf8') : undefined);
}

// The review stamps both gates read from the shared skill-invocation-log
// (write-review-stamp.ts appends to the same file).
function readReviewStamps(): ReviewStamp[] {
  const logFile = nodePath.join(resolveNamespaceRoot(projectDirectory), 'skill-invocations.log');
  return existsSync(logFile) ? parseReviewStamps(readFileSync(logFile, 'utf8')) : [];
}

/**
 * REFACTOR commit gate: if the active ticket is in `phase: implement` and the
 * current TDD step (parsed from test-definitions.md) is REFACTOR, inspect
 * `git diff --cached --name-only` and deny if any staged file is a test file.
 * Permissive on every other path — missing state, missing ticket, wrong phase,
 * wrong step, or unreachable git all silently allow.
 */
function enforceRefactorCommitGate(sessionId?: string): void {
  const stateFile = getStateFilePath(projectDirectory, sessionId);
  if (!existsSync(stateFile)) return;

  let state: QualityState;
  try {
    state = JSON.parse(readFileSync(stateFile, 'utf8'));
  } catch {
    return;
  }
  if (!state.activeTicket) return;

  const ticket = getTicketInfo(projectDirectory, state.activeTicket);
  if (ticket.phase !== 'implement' || !ticket.folder) return;

  const testDefinitionsPath = nodePath.join(
    resolveNamespaceRoot(projectDirectory),
    'tickets',
    ticket.folder,
    'test-definitions.md',
  );
  if (!existsSync(testDefinitionsPath)) return;

  // parseTddStep returns the LAST CHECKED step. The agent is doing REFACTOR
  // work when RED + GREEN are checked and REFACTOR is still pending — i.e.,
  // when parseTddStep returns 'green'. ('refactor' means scenario complete.)
  const step = parseTddStep(readFileSync(testDefinitionsPath, 'utf8'));
  if (step !== 'green') return;

  let staged: string;
  try {
    staged = execSync('git diff --cached --name-only', {
      cwd: projectDirectory,
      encoding: 'utf8',
    });
  } catch {
    return; // Can't inspect staged files — be permissive rather than wrong.
  }

  const stagedFiles = staged.split('\n').filter(line => line.trim() !== '');
  const offendingTestFile = stagedFiles.find(isTestFile);
  if (offendingTestFile) {
    deny(
      `REFACTOR commit may not touch test file: ${offendingTestFile}. Refactor preserves behavior — changing tests during REFACTOR is a behavior change in disguise.`,
      'If the refactor genuinely needs a test edit (e.g., function rename across imports), commit the test change as part of GREEN, or mark REFACTOR as skip: <reason explaining why test edits were required>.',
    );
  }
}

// Read hook input from stdin
let input: HookInput;
try {
  input = await Bun.stdin.json();
} catch {
  process.exit(0);
}

const tool = input.tool_name ?? '';
const editedFile = input.tool_input?.file_path ?? input.tool_input?.notebook_path ?? '';

// ---------------------------------------------------------------------------
// Bash gate: REFACTOR commits must not touch test files (ticket J7VBGJ, Rule 2)
// The only file-path commit rule that survived scope reduction — see
// <namespace-root>/learnings/procedural-gates-generalize-beyond-tdd.md for why
// the RED/GREEN file-path rules were dropped.
// ---------------------------------------------------------------------------

if (tool === 'Bash') {
  const command = input.tool_input?.command ?? '';
  if (GIT_COMMIT_COMMAND.test(command)) {
    enforceRefactorCommitGate(input.session_id);
  }
  process.exit(0);
}

// Only gate edit tools (Bash already handled above)
if (!EDIT_TOOLS.includes(tool)) {
  process.exit(0);
}

// ---------------------------------------------------------------------------
// Artifact prerequisite check: test-definitions.md requires a complete ticket spec
// Runs BEFORE META_PATHS exemption because test-definitions.md lives in .safeword-project/
// This is the one structural gate at the highest-leverage transition point.
// Understanding determines the quality of everything downstream.
// ---------------------------------------------------------------------------

if (
  editedFile.endsWith('test-definitions.md') &&
  isNamespacePath(editedFile, 'tickets/') &&
  !existsSync(editedFile) // Only gate creation, not edits to existing files
) {
  const ticketDirectory = nodePath.dirname(editedFile);
  const ticketFile = nodePath.join(ticketDirectory, 'ticket.md');

  if (!existsSync(ticketFile)) {
    deny(
      'Cannot create test definitions without a ticket spec. Create ticket.md with Scope, Out of Scope, and Done When sections first.',
      'Complete understanding (propose-and-converge) before writing scenarios.',
    );
  }

  const ticketContent = readFileSync(ticketFile, 'utf8');
  const frontmatterMatch = ticketContent.match(/^---\n([\s\S]*?)\n---/);

  if (!frontmatterMatch) {
    deny(
      'Ticket spec has no YAML frontmatter. Add scope, out_of_scope, and done_when fields.',
      'Complete understanding (propose-and-converge) before writing scenarios.',
    );
  }

  const meta = parseFrontmatter(frontmatterMatch![1] ?? '');
  const required = ['scope', 'out_of_scope', 'done_when'] as const;
  const missing = required.filter(field => isMissingFrontmatterField(meta[field]));

  if (missing.length > 0) {
    deny(
      `Ticket frontmatter is missing: ${missing.join(', ')}. Complete understanding before writing scenarios.`,
      'Add the missing fields to ticket.md frontmatter, then create test-definitions.md.',
    );
  }

  // Phase gate: must have advanced past intake before writing scenarios.
  if (meta.phase === 'intake') {
    deny(
      'Ticket is still in intake phase. Update phase to define-behavior before writing scenarios.',
      'Complete understanding, then set phase: define-behavior in ticket frontmatter.',
    );
  }

  // Dimension artifact gate: features require dimensions.md before test-definitions.md.
  // Natural gate — next step's input doesn't exist if prior step was skipped.
  // The artifact may be a real dimension table OR a single `skip: <non-empty reason>`
  // line (ticket MKVNFB) — the escape valve for tiny features with one obvious dimension.
  if (meta.type === 'feature') {
    const dimensionsFile = nodePath.join(ticketDirectory, 'dimensions.md');
    if (!existsSync(dimensionsFile)) {
      deny(
        'Features require dimensions.md before test-definitions.md. Document behavioral dimensions and partitions first.',
        'Create dimensions.md with a dimension table, or write `skip: <non-empty reason>` as the entire content to deliberately omit.',
      );
    }
    // If the file is a pure `skip: <reason>` declaration, validate the reason.
    // Multi-line content-bearing files don't match this regex and pass through.
    const dimensionsContent = readFileSync(dimensionsFile, 'utf8').trim();
    const skipMatch = /^skip:(.*)$/i.exec(dimensionsContent);
    if (skipMatch && !isValidSkipReason(skipMatch[1])) {
      deny(
        'dimensions.md `skip:` declaration requires a non-empty reason after the colon.',
        'Either write a real dimension table, or use `skip: <reason>` where the reason explains why no dimensions need enumerating (e.g., `skip: single behavioral dimension, no partitioning to enumerate`).',
      );
    }
  }

  // spec.md gate (ticket 9EA27P): features fail closed. A `type: feature`
  // ticket with no spec.md is denied here, rather than silently skipping the
  // JTBD/AC gates below — without a spec.md those gates have nothing to check,
  // so a feature could otherwise reach done with no jobs or criteria. Tasks and
  // patches don't require a spec.md. The CLI scaffolds spec.md for new features,
  // so this only bites pre-product-layer (epic DZ2NM5) tickets, which pay a lazy
  // two-line `## Jobs To Be Done` + `skip: <reason>` the next time they advance.
  const specFile = nodePath.join(ticketDirectory, 'spec.md');
  const specExists = existsSync(specFile);
  if (meta.type === 'feature' && !specExists) {
    deny(
      'Features require a spec.md before test-definitions.md. Without one the JTBD and Acceptance-Criteria gates have nothing to check.',
      'Author a Job To Be Done in spec.md under `## Jobs To Be Done` (persona from personas.md, in the "When I…, I want…, so I can…" form), or write `skip: <reason>` there to deliberately omit.',
    );
  }

  // JTBD gate (ticket Y2HCNJ): require ≥1 JTBD whose persona resolves against
  // personas.md, or a `skip: <reason>` in the Jobs To Be Done section. The
  // guard below now only spares tasks and patches — a feature with no spec.md
  // was already denied above.
  if (specExists) {
    const specContent = readFileSync(specFile, 'utf8');

    const jtbdVerdict = evaluateJtbdGate(specContent, readPersonasForGate(ticketDirectory));
    if (!jtbdVerdict.ok) {
      deny(
        `spec.md JTBD gate: ${jtbdVerdict.reason}.`,
        'Author a Job To Be Done in spec.md under `## Jobs To Be Done` (persona from personas.md, in the "When I…, I want…, so I can…" form), or write `skip: <reason>` there to deliberately omit.',
      );
    }

    // AC gate (ticket 31W8M3): each JTBD needs ≥1 Acceptance Criterion — a
    // `#### <jtbd-id>.AC<n>` heading under it — or a per-JTBD `skip: <reason>`.
    const acVerdict = evaluateAcGate(specContent);
    if (!acVerdict.ok) {
      deny(
        `spec.md AC gate: ${acVerdict.reason}.`,
        'Add an Acceptance Criterion under each JTBD as `#### <jtbd-id>.AC<n> — <capability>` (a product-level guarantee, not implementation), or `skip: <reason>` under that JTBD to omit it deliberately.',
      );
    }

    // Review gate (NMSD94, Tier 1) — DEFAULT-OFF: only fires when
    // `.safeword/config.json` sets `reviewGate: true`. Scenarios require a review
    // stamp bound to THIS ticket's spec.md at its CURRENT content (so a stale or
    // cross-ticket review doesn't satisfy it). Inert until enabled, so it can't
    // brick a workflow before the stamp-earning step ships.
    if (isReviewGateOn()) {
      const stamps = readReviewStamps();
      const priorScope = reviewScope(
        nodePath.basename(ticketDirectory),
        'spec',
        hashArtifact(specContent),
      );
      if (!reviewGateForNextAsset(priorScope, stamps).ok) {
        deny(
          'spec.md has not been reviewed at its current content. Review it (or log a skip with a reason) before writing scenarios.',
          'Run `/self-review` (or log a skip), then create test-definitions.md.',
        );
      }
    }
  }
}

// Reconstruct the file content an Edit/Write/MultiEdit would produce, so a gate
// can compare it against the on-disk content. Write/NotebookEdit carry the full
// new content; Edit/MultiEdit carry replacement regions applied to the prior text.
function nextContentAfterEdit(toolInput: HookInput['tool_input'], priorContent: string): string {
  if (toolInput?.content !== undefined) return toolInput.content;
  if (toolInput?.edits) {
    return toolInput.edits.reduce(
      (text, edit) => text.replace(edit.old_string ?? '', edit.new_string ?? ''),
      priorContent,
    );
  }
  if (toolInput?.old_string !== undefined) {
    return priorContent.replace(toolInput.old_string, toolInput.new_string ?? '');
  }
  return priorContent;
}

// Review gate (NMSD94, Tier 2) — DEFAULT-OFF, same flag as Tier 1. On a
// ticket.md edit that changes `phase:`, block leaving the phase until an
// independent phase-exit review stamp exists for it. The stamp is produced by a
// fresh (context:fork) reviewer and logged via `write-review-stamp.ts --phase`,
// so the author can't grade their own phase. Inert until reviewGate is enabled.
if (editedFile.endsWith('ticket.md') && isNamespacePath(editedFile, 'tickets/')) {
  if (isReviewGateOn()) {
    const priorContent = existsSync(editedFile) ? readFileSync(editedFile, 'utf8') : '';
    const exitedPhase = detectPhaseAdvance(
      priorContent,
      nextContentAfterEdit(input.tool_input, priorContent),
    );
    if (exitedPhase !== undefined) {
      const ticketDirectory = nodePath.dirname(editedFile);
      const stamps = readReviewStamps();
      const phaseScope = reviewScope(nodePath.basename(ticketDirectory), 'phase', exitedPhase);
      if (!gatePhaseAdvance(phaseScope, stamps).ok) {
        deny(
          `Phase "${exitedPhase}" has no independent review stamp — advancing is blocked until a fork review of the phase is logged.`,
          `Spawn a fresh (context:fork) reviewer for the ${exitedPhase} phase, then run \`bun .safeword/hooks/write-review-stamp.ts --phase ${exitedPhase}\` on pass (or append a skip reason to log a deliberate skip).`,
        );
      }
    }
  }
}

// ---------------------------------------------------------------------------
// SHA-or-skip annotation gate (ticket J7VBGJ, Rule 1)
// On Edit/Write/MultiEdit of test-definitions.md, any [ ] → [x] transition
// must carry either a SHA (`- [x] RED abc1234`) or `skip: <non-empty reason>`.
// Pre-existing [x] without annotation is silently allowed (forward-looking).
// ---------------------------------------------------------------------------

if (editedFile.endsWith('test-definitions.md') && isNamespacePath(editedFile, 'tickets/')) {
  const transitions = collectNewTransitions(input, editedFile);
  for (const transition of transitions) {
    if (transition.annotation === '') {
      deny(
        `Cannot mark "[x] ${transition.step}" without an annotation. Use "${transition.step} <sha>" or "${transition.step} skip: <non-empty reason>".`,
        'Every checkbox transition needs a commit SHA (proof of the work) or a deliberate skip with reason (auditable omission).',
      );
    }
    const kind = classifyAnnotation(transition.annotation);
    if (kind.kind === 'skip' && !isValidSkipReason(kind.reason)) {
      deny(
        `Cannot mark "[x] ${transition.step}" with empty skip reason. Use "skip: <non-empty reason>".`,
        'The text after "skip:" must not be empty or whitespace-only. A real reason is the audit trail.',
      );
    }
  }
}

// Never block edits to tooling/meta files — these are not application code.
// (After artifact prerequisite check, which targets files in .safeword-project/)
if (META_PATHS.some(p => editedFile.includes(p))) {
  process.exit(0);
}

// ---------------------------------------------------------------------------
// Shared state read — used by both implement phase gate and LOC gate below.
// ---------------------------------------------------------------------------

const stateFile = getStateFilePath(projectDirectory, input.session_id);

if (!existsSync(stateFile)) {
  process.exit(0);
}

let state: QualityState;
try {
  state = JSON.parse(readFileSync(stateFile, 'utf8'));
} catch {
  process.exit(0);
}

// ---------------------------------------------------------------------------
// Implement phase gate: features need test-definitions.md before app code (#128)
// Tasks are exempt (per #126 retro — sizing boundary makes tasks lighter).
// Reads ticket state directly from disk (per #124 — no cached phase).
// ---------------------------------------------------------------------------

if (state.activeTicket) {
  const ticketInfo = getTicketInfo(projectDirectory, state.activeTicket);

  if (ticketInfo.type === 'feature' && ticketInfo.phase === 'implement' && ticketInfo.folder) {
    const testDefinitionsPath = nodePath.join(
      resolveNamespaceRoot(projectDirectory),
      'tickets',
      ticketInfo.folder,
      'test-definitions.md',
    );

    if (!existsSync(testDefinitionsPath)) {
      recordFailure(projectDirectory, input.session_id, 'implement-without-test-definitions');
      deny(
        'Feature at implement phase requires test-definitions.md before writing application code. Create test-definitions.md with scenarios first.',
        'Write scenarios (RED/GREEN/REFACTOR checkboxes) before implementation. Tasks are exempt from this gate.',
      );
    }
  }
}

// ---------------------------------------------------------------------------
// LOC gate: blast radius control — commit every ~400 LOC
// ---------------------------------------------------------------------------

// Check if commit happened → gate clears
const currentHead = (() => {
  try {
    return execSync('git rev-parse --short HEAD', {
      cwd: projectDirectory,
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
  } catch {
    return '';
  }
})();

if (state.lastCommitHash !== currentHead) {
  process.exit(0);
}

if (!state.gate) {
  process.exit(0);
}

// LOC gate stands down during a git merge/rebase/cherry-pick/revert so it can't
// block the edits that resolve the operation (ticket MT27QG).
if (state.gate === 'loc' && !isGitOperationInProgress(projectDirectory)) {
  recordFailure(projectDirectory, input.session_id, 'loc-exceeded');
  deny(`${state.locSinceCommit} LOC since last commit (threshold: ${LOC_THRESHOLD}).

Commit your progress before continuing.`);
}

// Remaining gates (tdd:*, phase:*) are reminders via prompt hook, not hard blocks.
// Exception: implement-without-test-definitions gate above (#128). See #109 / #114.
process.exit(0);
