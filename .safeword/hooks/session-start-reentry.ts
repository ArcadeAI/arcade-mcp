#!/usr/bin/env bun
/**
 * SessionStart hook: inject the re-entry brief into Claude's context.
 *
 * Ticket 645W8H. Slice 2.
 *
 * Reads `<namespace-root>/re-entry.md`, filters entries to the current
 * session_id, and emits the last 3 matching lines via additionalContext
 * (silent — not shown in chat; for Claude recall when the user asks
 * "where were we?"). The status-line script (Slice 3) is the user-facing
 * surface.
 *
 * Also detects conflict: when another session's transcript has Edit/Write
 * tool calls on files that are currently dirty in `git status`, append a
 * warning line so the agent (and via Slice 3, the user) knows to step
 * lightly around those files.
 */

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

import { detectConflictFiles, type Entry, parseLogLine, resolveProjectRoot } from './lib/re-entry';
import { resolveNamespaceRoot } from './lib/namespace-root.ts';

interface HookInput {
  session_id?: string;
  source?: 'startup' | 'resume' | 'clear' | 'compact';
  cwd?: string;
  transcript_path?: string;
}

function renderBrief(entries: Entry[], options: { fromAnotherSession?: boolean } = {}): string {
  const header = options.fromAnotherSession
    ? 'Re-entry brief — most recent entry (from another session):'
    : `Re-entry brief — last ${entries.length} entries from this session:`;
  const lines = entries.map(e => `- ${e.timestamp} [${e.ticket}] ${e.nextImperative}`);
  return `${header}\n${lines.join('\n')}`;
}

function renderConflictWarning(files: string[]): string {
  if (files.length === 0) return '';
  const quoted = files.map(f => `\`${f}\``).join(', ');
  return `\n\n⚠️ Conflict: another session edited ${quoted} (still dirty in the working tree).`;
}

async function main(): Promise<void> {
  const stdinText = await new Response(Bun.stdin.stream()).text();
  let input: HookInput;
  try {
    input = JSON.parse(stdinText) as HookInput;
  } catch {
    return;
  }

  const { session_id, cwd, source, transcript_path } = input;
  if (!session_id || !cwd) return;

  // Same cwd-drift defense as stop-reentry: resolve real project root.
  const projectRoot = resolveProjectRoot(cwd);
  if (!projectRoot) return;

  const logPath = join(resolveNamespaceRoot(projectRoot), 're-entry.md');
  const logExists = existsSync(logPath);
  const content = logExists ? readFileSync(logPath, 'utf8').trim() : '';

  const allEntries = content
    .split('\n')
    .map(parseLogLine)
    .filter((e): e is Entry => e !== null);

  const currentEntries = allEntries.filter(e => e.sessionId === session_id);

  let briefBody = '';
  if (currentEntries.length > 0) {
    briefBody = renderBrief(currentEntries.slice(-3));
  } else if (source === 'startup' && allEntries.length > 0) {
    briefBody = renderBrief([allEntries[allEntries.length - 1]], { fromAnotherSession: true });
  }

  const conflictFiles = detectConflictFiles(projectRoot, transcript_path);
  const conflictWarning = renderConflictWarning(conflictFiles);

  // Nothing to inject in either channel → stay silent.
  if (briefBody.length === 0 && conflictWarning.length === 0) return;

  const output = {
    hookSpecificOutput: {
      hookEventName: 'SessionStart',
      additionalContext: `${briefBody}${conflictWarning}`,
    },
  };
  process.stdout.write(`${JSON.stringify(output)}\n`);
}

main().catch((error: unknown) => {
  process.stderr.write(
    `session-start-reentry: ${error instanceof Error ? error.message : String(error)}\n`,
  );
  process.exit(1);
});
