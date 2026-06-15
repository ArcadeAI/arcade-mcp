#!/usr/bin/env bun
// Safeword: Cursor adapter for afterFileEdit
// Auto-lints changed files, sets marker for stop hook

import { existsSync } from 'node:fs';

import { lintFile } from '../lib/lint.ts';

interface CursorInput {
  workspace_roots?: string[];
  file_path?: string;
  conversation_id?: string;
}

// Read hook input from stdin
let input: CursorInput;
try {
  input = await Bun.stdin.json();
} catch {
  process.exit(0);
}

const workspace = input.workspace_roots?.[0];
const file = input.file_path;
const convId = input.conversation_id ?? 'default';

// Exit silently if no file or file doesn't exist
if (!file || !(await Bun.file(file).exists())) {
  process.exit(0);
}

// Change to workspace directory
if (workspace) {
  process.chdir(workspace);
}

// Check for .safeword directory
if (!existsSync('.safeword')) {
  process.exit(0);
}

// Set marker file for stop hook to know edits were made
const markerFile = `/tmp/safeword-cursor-edited-${convId}`;
await Bun.write(markerFile, '');

// Lint the file
await lintFile(file, process.cwd());
