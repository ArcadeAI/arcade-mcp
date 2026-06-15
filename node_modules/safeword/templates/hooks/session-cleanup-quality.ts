#!/usr/bin/env bun
// Safeword: Quality Gates - SessionEnd cleanup
// Garbage-collects per-session quality state files older than 7 days.
// Fires on SessionEnd.

import { readdirSync, statSync, unlinkSync } from 'node:fs';
import nodePath from 'node:path';
import { resolveNamespaceRoot } from './lib/namespace-root.ts';

const projectDirectory = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const stateDirectory = nodePath.join(resolveNamespaceRoot(projectDirectory));
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

try {
  const now = Date.now();
  for (const file of readdirSync(stateDirectory)) {
    if (!file.startsWith('quality-state-') || !file.endsWith('.json')) continue;
    const filePath = nodePath.join(stateDirectory, file);
    const age = now - statSync(filePath).mtimeMs;
    if (age > MAX_AGE_MS) {
      unlinkSync(filePath);
    }
  }
} catch {
  // Best-effort cleanup — stale files are harmless (gitignored, never re-read)
}

process.exit(0);
