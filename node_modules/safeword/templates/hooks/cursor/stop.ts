#!/usr/bin/env bun
// Safeword: Cursor adapter for stop hook
// Checks for marker file from afterFileEdit to determine if files were modified
// Uses followup_message to inject quality review prompt into conversation

import { existsSync } from 'node:fs';
import { unlink } from 'node:fs/promises';

import { QUALITY_REVIEW_MESSAGE } from '../lib/quality.ts';

interface CursorInput {
  workspace_roots?: string[];
  conversation_id?: string;
  status?: string;
}

interface StopOutput {
  followup_message?: string;
}

// Read hook input from stdin
let input: CursorInput;
try {
  input = await Bun.stdin.json();
} catch {
  console.log('{}');
  process.exit(0);
}

const workspace = input.workspace_roots?.[0];

// Change to workspace directory
if (workspace) {
  process.chdir(workspace);
}

// Check for .safeword directory
if (!existsSync('.safeword')) {
  console.log('{}');
  process.exit(0);
}

// Check status - only proceed on completed (not aborted/error)
if (input.status !== 'completed') {
  console.log('{}');
  process.exit(0);
}

// Cursor enforces max 5 auto-submissions, no additional limit needed

// Check if any file edits occurred in this session by looking for marker file
const convId = input.conversation_id ?? 'default';
const markerFile = `/tmp/safeword-cursor-edited-${convId}`;

if (await Bun.file(markerFile).exists()) {
  // Clean up marker (best-effort; missing file or perm issue is non-fatal)
  await unlink(markerFile).catch(error => {
    if (process.env.DEBUG) console.error('[cursor/stop] marker cleanup failed:', error);
  });

  const output: StopOutput = {
    followup_message: QUALITY_REVIEW_MESSAGE,
  };
  console.log(JSON.stringify(output));
} else {
  console.log('{}');
}
