#!/usr/bin/env bun
// Safeword: Quality Gates - PostToolUse observer
// Counts LOC via git diff --stat HEAD, detects phase changes and TDD step transitions,
// updates per-session quality state. Fires on Edit|Write|MultiEdit|NotebookEdit|Bash

import { execFileSync, execSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import nodePath from 'node:path';

import { collectNewTransitions } from './lib/checkbox-transitions.ts';
import { isGitOperationInProgress } from './lib/git-operation.ts';
import { getQualityMessage } from './lib/quality.ts';
import {
  getStateFilePath,
  LOC_THRESHOLD,
  META_PATHS,
  type QualityState,
} from './lib/quality-state.ts';
import { selectMostAdvancedStep, shouldReviewPhase } from './lib/review-trigger.ts';
import { isNamespacePath } from './lib/namespace-root.ts';

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
  };
}

const projectDirectory = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();

// Read hook input from stdin
let input: HookInput;
try {
  input = await Bun.stdin.json();
} catch {
  process.exit(0);
}

const stateFile = getStateFilePath(projectDirectory, input.session_id);
const editedFile = input.tool_input?.file_path ?? input.tool_input?.notebook_path ?? '';

// Load or create state
function loadState(): QualityState {
  if (existsSync(stateFile)) {
    try {
      return JSON.parse(readFileSync(stateFile, 'utf8'));
    } catch {
      // Corrupted file — reinitialize
    }
  }
  return {
    locSinceCommit: 0,
    lastCommitHash: '',
    activeTicket: null,
    gate: null,
    recentFailures: [],
    incrementedPatterns: [],
  };
}

function saveState(state: QualityState): void {
  const dir = nodePath.dirname(stateFile);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
  writeFileSync(stateFile, JSON.stringify(state, null, 2));
}

function getHeadHash(): string {
  try {
    return execSync('git rev-parse --short HEAD', {
      cwd: projectDirectory,
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
  } catch {
    return '';
  }
}

function countLoc(): number {
  try {
    // execFileSync (no shell): pathspecs are args, so no shell-quoting needed
    // (`:!path`, not the shell-escaped `':!path'`).
    const excludes = META_PATHS.map(p => `:!${p}`);
    const diffStat = execFileSync('git', ['diff', '--stat', 'HEAD', '--', '.', ...excludes], {
      cwd: projectDirectory,
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    const insMatch = diffStat.match(/(\d+) insertions?\(\+\)/);
    const delMatch = diffStat.match(/(\d+) deletions?\(-\)/);
    return (insMatch ? parseInt(insMatch[1]) : 0) + (delMatch ? parseInt(delMatch[1]) : 0);
  } catch {
    return 0;
  }
}

// --- Main ---

const state = loadState();
const currentHead = getHeadHash();

// If no commits yet, skip enforcement
if (!currentHead) {
  process.exit(0);
}

// Check if commit happened (gate clears)
if (state.lastCommitHash !== currentHead) {
  state.locSinceCommit = 0;
  state.lastCommitHash = currentHead;
  state.gate = null;
}

// Count LOC
state.locSinceCommit = countLoc();

// LOC gate (only hard gate remaining — blast radius control). Stands down while
// a git merge/rebase/cherry-pick/revert is in progress: those incoming lines are
// not agent edits and must not block conflict resolution (ticket MT27QG).
if (state.locSinceCommit >= LOC_THRESHOLD && !isGitOperationInProgress(projectDirectory)) {
  state.gate = 'loc';
}

// Quality review surfaced as additionalContext when a boundary is crossed
// (ticket SXSCJQ). At most one fires per edit — an edit touches either
// test-definitions.md (a TDD-step flip) or ticket.md (a phase change).
let reviewMessage: string | null = null;

// Active ticket binding (phase/TDD step no longer cached — derived at read time)
if (isNamespacePath(editedFile, 'tickets/') && editedFile.endsWith('ticket.md')) {
  const fullPath = editedFile.startsWith('/')
    ? editedFile
    : nodePath.join(projectDirectory, editedFile);
  if (existsSync(fullPath)) {
    const content = readFileSync(fullPath, 'utf8');

    // Track active ticket
    const idMatch = content.match(/^id:\s*(\S+)/m);
    if (idMatch) {
      state.activeTicket = idMatch[1];
    }

    // Auto-clear binding when ticket reaches done or backlog
    const statusMatch = content.match(/^status:\s*(\S+)/m);
    const ticketStatus = statusMatch?.[1];
    if (ticketStatus === 'done' || ticketStatus === 'backlog') {
      state.activeTicket = null;
    }

    // Per-phase review (enter-semantics, deduped). Fires on the first edit that
    // brings the ticket into an un-reviewed phase — autonomous-safe, since it
    // does not wait for a Stop. The Stop backstop covers non-edit phase bumps.
    const phase = content.match(/^phase:\s*(\S+)/m)?.[1];
    if (shouldReviewPhase(phase, state.lastReviewedPhase)) {
      reviewMessage = getQualityMessage(phase);
      state.lastReviewedPhase = phase;
    }
  }
}

// Per-TDD-step review. Each `[ ]→[x]` RED/GREEN/REFACTOR flip is one edit, so
// this fires once per step boundary (structurally idempotent). Batched flips in
// one edit surface the most-advanced step.
if (isNamespacePath(editedFile, 'tickets/') && editedFile.endsWith('test-definitions.md')) {
  const step = selectMostAdvancedStep(collectNewTransitions(input, editedFile));
  if (step) {
    reviewMessage = getQualityMessage('implement', step);
    state.lastReviewedStep = step;
  }
}

// Novel-claim nudge: append the edited learnings file to the per-session
// pending set. Per-fingerprint dedup — if we've already armed for this file
// this session (whether pending or acknowledged), don't re-arm. Monotonic
// append-only state replaces the prior single-bit boolean (ticket 4N5Y28).
if (isNamespacePath(editedFile, 'learnings/') && editedFile.endsWith('.md')) {
  state.learningsNudgesPending ??= [];
  state.learningsNudgesAcknowledged ??= [];
  const alreadyArmed =
    state.learningsNudgesPending.includes(editedFile) ||
    state.learningsNudgesAcknowledged.includes(editedFile);
  if (!alreadyArmed) {
    state.learningsNudgesPending.push(editedFile);
  }
}

saveState(state);

if (reviewMessage) {
  console.log(
    JSON.stringify({
      hookSpecificOutput: { hookEventName: 'PostToolUse', additionalContext: reviewMessage },
    }),
  );
}
process.exit(0);
