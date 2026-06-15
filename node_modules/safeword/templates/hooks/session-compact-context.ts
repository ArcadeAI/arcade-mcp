#!/usr/bin/env bun
// Safeword: Re-inject active ticket context after compaction
// Fires on SessionStart(compact) — outputs to stdout for Claude's context

import { existsSync, readFileSync } from 'node:fs';
import nodePath from 'node:path';

import { getTicketInfo } from './lib/active-ticket.ts';
import { getStateFilePath } from './lib/quality-state.ts';
import { resolveNamespaceRoot } from './lib/namespace-root.ts';

interface HookInput {
  session_id?: string;
}

const projectDir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const namespaceRoot = resolveNamespaceRoot(projectDir);
const namespaceLabel = nodePath.relative(projectDir, namespaceRoot);
const ticketsDir = `${namespaceRoot}/tickets`;

// Read hook input from stdin for session_id
let input: HookInput;
try {
  input = await Bun.stdin.json();
} catch {
  input = {};
}

// Belt-and-suspenders for ticket #130: re-inject the learnings pointer after
// compaction in case CLAUDE.md → @./.safeword/SAFEWORD.md re-expansion didn't
// fire reliably (GitHub #22085 reports sporadic issues). Emit only if the
// project has learnings to point at.
const learningsIndex = `${namespaceRoot}/learnings/INDEX.md`;
if (existsSync(learningsIndex)) {
  console.log(
    `Project learnings: read \`${namespaceLabel}/learnings/INDEX.md\` before non-trivial work to avoid re-making previously-solved mistakes.`,
  );
}

// Read per-session state file (not legacy shared file)
const stateFile = getStateFilePath(projectDir, input.session_id);

if (!existsSync(stateFile)) {
  process.exit(0);
}

let state: { activeTicket: string | null; gate: string | null };
try {
  state = JSON.parse(readFileSync(stateFile, 'utf8'));
} catch {
  process.exit(0);
}

if (!state.activeTicket) {
  process.exit(0);
}

// Derive phase from ticket file (not cache) — with freshness check
const ticketInfo = getTicketInfo(projectDir, state.activeTicket);

if (!ticketInfo.folder || (ticketInfo.status && ticketInfo.status !== 'in_progress')) {
  // Ticket missing or no longer active — skip context injection
  process.exit(0);
}

// Read ticket content for title and goal
let ticketContent = '';
try {
  const ticketPath = `${ticketsDir}/${ticketInfo.folder}/ticket.md`;
  if (existsSync(ticketPath)) {
    ticketContent = readFileSync(ticketPath, 'utf8');
  }
} catch {
  process.exit(0);
}

if (!ticketContent) {
  process.exit(0);
}

// Read the goal from content; the ticket label is the slug (ZRXM6Q), derived
// once in getTicketInfo and shared with the per-turn prompt hook.
const goalMatch = ticketContent.match(/\*\*Goal:\*\*\s*(.+)/m);

const goal = goalMatch?.[1] ?? '';
const phase = ticketInfo.phase ?? 'unknown';
const type = ticketInfo.type ?? 'task';
const gate = state.gate ?? 'none';

const lines = [
  `SAFEWORD Context (restored after compaction):`,
  `Ticket: ${ticketInfo.slug ?? ticketInfo.folder} (${state.activeTicket})`,
  `Type: ${type} | Phase: ${phase} | Gate: ${gate}`,
];
if (goal) {
  lines.push(`Goal: ${goal}`);
}
lines.push(`Re-read ${namespaceLabel}/tickets/${ticketInfo.folder}/ticket.md for full context.`);

console.log(lines.join('\n'));
