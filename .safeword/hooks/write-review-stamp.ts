#!/usr/bin/env bun
// Safeword: the review-stamp earning step (ticket NMSD94).
//
// Appends a `review:<scope>` line to the skill-invocation-log so the review
// gates in pre-tool-quality.ts read it back and allow the next step. Two callers:
//   - Tier 1 (per-asset): the `/self-review` skill's render-time injection runs
//     this to stamp the just-reviewed artifact at its CURRENT content.
//   - Tier 2 (phase exit): the working agent runs this AFTER a fork review
//     passes, to stamp the phase being exited.
//
// Scope is built with the SAME reviewScope()/hashArtifact() the gate uses (same
// hook lib, same runtime), so the stamp matches by construction — no
// cross-language hash contract to drift. Trust boundary: this writes a stamp on
// invocation, which is the cheap Tier 1 floor; Tier 2's real independence is the
// fork reviewer, not this script.
//
// Usage:
//   bun write-review-stamp.ts [--ticket <folder>] <artifact> [skip reason…]      # stamp <artifact>.md
//   bun write-review-stamp.ts [--ticket <folder>] --phase <phase> [skip reason…] # stamp a phase exit
// With more than one in_progress ticket, pass --ticket to disambiguate; without
// it the step fails rather than guess a ticket the gate may not be checking.

import { appendFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import nodePath from 'node:path';
import process from 'node:process';

import { getInProgressTicketFolders } from './lib/active-ticket.ts';
import { formatReviewStamp, hashArtifact, reviewScope } from './lib/review-ledger.ts';
import { resolveNamespaceRoot } from './lib/namespace-root.ts';

const projectDirectory = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const sessionId = process.env.CLAUDE_SESSION_ID ?? 'unknown-session';
const ticketsDirectory = nodePath.join(resolveNamespaceRoot(projectDirectory), 'tickets');

function fail(message: string): never {
  process.stdout.write(`[skill-invocation-log] FAILED — ${message}\n`);
  process.exit(1);
}

// Collapse all whitespace (incl. newlines) to single spaces. The log is one
// stamp per line, so an un-collapsed reason could inject a second, forged line.
function singleLine(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

// A bare path component — no whitespace, separators, or `..`. The ticket and
// artifact names index into `tickets/<folder>/<artifact>.md`, so a separator
// would let the path escape the tickets dir; reject it at the boundary.
function bareName(value: string, label: string): string {
  if (/[\s/\\]/.test(value) || value.includes('..')) {
    fail(`${label} must be a bare name (no whitespace, slashes, or "..")`);
  }
  return value;
}

// Optional leading flags `--ticket <folder>` and `--model <id>` (any order),
// then the positional command. `--model` is the reviewing model, supplied by the
// orchestrator that assigned it (NOT self-reported by the reviewer — Claude Code
// withholds model identity from subagents, ticket MR5M3A).
let positional = process.argv.slice(2);
let explicitTicket: string | undefined;
let reviewerModel: string | undefined;
while (positional[0] === '--ticket' || positional[0] === '--model') {
  const flag = positional[0];
  const value = positional[1];
  if (value === undefined || value === '') fail(`${flag} requires a value`);
  if (flag === '--ticket') {
    explicitTicket = bareName(value, '--ticket');
  } else {
    if (/\s/.test(value)) fail('--model id must not contain whitespace');
    reviewerModel = value;
  }
  positional = positional.slice(2);
}

// Resolve the ticket the same way the gate does conceptually (the one being worked),
// failing loudly on ambiguity instead of stamping a ticket the gate isn't checking.
function resolveTicketFolder(): string {
  if (explicitTicket !== undefined) {
    if (!existsSync(nodePath.join(ticketsDirectory, explicitTicket, 'ticket.md'))) {
      fail(`--ticket "${explicitTicket}" not found`);
    }
    return explicitTicket;
  }
  const inProgress = getInProgressTicketFolders(projectDirectory);
  if (inProgress.length === 0) fail('no in_progress ticket found — nothing to stamp');
  if (inProgress.length > 1) {
    fail(
      `multiple in_progress tickets (${inProgress.join(', ')}) — pass --ticket <folder> to disambiguate`,
    );
  }
  return inProgress[0] ?? fail('no in_progress ticket found — nothing to stamp');
}

const isPhase = positional[0] === '--phase';
const skipReason = singleLine(positional.slice(isPhase ? 2 : 1).join(' ')) || undefined;

function resolveScope(ticketFolder: string): { scope: string; label: string } {
  if (isPhase) {
    const value = positional[1];
    if (value === undefined || value === '') fail('--phase requires a phase name');
    const phase = bareName(value, 'phase name');
    return { scope: reviewScope(ticketFolder, 'phase', phase), label: `phase ${phase}` };
  }
  const artifact = bareName(positional[0] ?? 'spec', 'artifact name');
  const artifactFile = nodePath.join(ticketsDirectory, ticketFolder, `${artifact}.md`);
  if (!existsSync(artifactFile)) fail(`artifact not found: ${artifact}.md in ${ticketFolder}`);
  return {
    scope: reviewScope(ticketFolder, artifact, hashArtifact(readFileSync(artifactFile, 'utf8'))),
    label: `${artifact}.md`,
  };
}

const { scope, label } = resolveScope(resolveTicketFolder());

const logDirectory = nodePath.join(resolveNamespaceRoot(projectDirectory));
const logFile = nodePath.join(logDirectory, 'skill-invocations.log');
mkdirSync(logDirectory, { recursive: true });
appendFileSync(
  logFile,
  `${new Date().toISOString()} ${sessionId} ${formatReviewStamp(scope, skipReason, reviewerModel)}\n`,
);

const kind = skipReason === undefined ? 'review' : `skip (${skipReason})`;
process.stdout.write(`[skill-invocation-log] ${kind} stamped for ${label} ✓\n`);
