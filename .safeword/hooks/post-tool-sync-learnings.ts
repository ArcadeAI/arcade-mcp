#!/usr/bin/env bun
// Safeword: Regenerate <namespace-root>/learnings/INDEX.md when a learning file changes (PostToolUse)
// Ticket #130. Verification-stamp warning added in ticket XV72DT.

import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import nodePath from 'node:path';

import { hasVerificationStamp } from './lib/learning-verification-stamps.ts';
import { resolveNamespaceRoot } from './lib/namespace-root.ts';

interface HookInput {
  tool_input?: {
    file_path?: string;
    notebook_path?: string;
  };
}

let input: HookInput;
try {
  input = await Bun.stdin.json();
} catch (error) {
  if (process.env.DEBUG) console.error('[post-tool-sync-learnings] stdin parse error:', error);
  process.exit(0);
}

const file = input.tool_input?.file_path ?? input.tool_input?.notebook_path;
if (!file) process.exit(0);

const projectDir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const learningsDirectory = nodePath.join(resolveNamespaceRoot(projectDir), 'learnings');

// Only fire for files inside the learnings directory.
const resolvedFile = nodePath.resolve(file);
if (!resolvedFile.startsWith(`${nodePath.resolve(learningsDirectory)}${nodePath.sep}`)) {
  process.exit(0);
}
if (!resolvedFile.endsWith('.md')) process.exit(0);

// Prefer local source in dev/dogfood, fall back to published CLI.
// Best-effort: never block an edit.
const localCli = nodePath.join(projectDir, 'packages/cli/src/cli.ts');
const [command, args] = existsSync(localCli)
  ? ['bun', [localCli, 'sync-learnings', '--quiet']]
  : ['bunx', ['safeword@latest', 'sync-learnings', '--quiet']];
spawnSync(command as string, args as string[], {
  cwd: projectDir,
  stdio: 'inherit',
  timeout: 30_000,
});

// Scan the just-written file for fabricated verification stamps and emit a
// PostToolUse `additionalContext` warning. See lib/learning-verification-stamps.ts
// for the detection policy and the research backing the warn-not-block choice.
try {
  const content = readFileSync(resolvedFile, 'utf8');
  if (hasVerificationStamp(content)) {
    const relativePath = nodePath.relative(projectDir, resolvedFile);
    const output = {
      hookSpecificOutput: {
        hookEventName: 'PostToolUse',
        additionalContext: [
          `Verification stamp detected in ${relativePath}.`,
          'Learnings describe forward-looking principles; they cannot vouch for current project state (code drifts).',
          'If you really verified something, put the claim in verify.md for the active ticket — it pins to a commit.',
          'In the learning, state the principle without the verification verb (e.g. "Astro 6 requires src/content.config.ts", not "we use src/content.config.ts — verified").',
        ].join(' '),
      },
    };
    console.log(JSON.stringify(output));
  }
} catch (error) {
  if (process.env.DEBUG) console.error('[post-tool-sync-learnings] scan error:', error);
}

process.exit(0);
