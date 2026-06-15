#!/usr/bin/env bun
// Safeword: Auto-lint changed files (PostToolUse)
// Auto-fixes what it can, then surfaces remaining errors to Claude via additionalContext.
// Also surfaces missing tool warnings via plain stdout.

import { lintFile } from './lib/lint.ts';

interface HookInput {
  tool_input?: {
    file_path?: string;
    notebook_path?: string;
  };
}

// Read hook input from stdin
let input: HookInput;
try {
  input = await Bun.stdin.json();
} catch (error) {
  if (process.env.DEBUG) console.error('[post-tool-lint] stdin parse error:', error);
  process.exit(0);
}

const file = input.tool_input?.file_path ?? input.tool_input?.notebook_path;

// Exit silently if no file or file doesn't exist
if (!file || !(await Bun.file(file).exists())) {
  process.exit(0);
}

const projectDir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
process.chdir(projectDir);

const result = await lintFile(file, projectDir);

// Build output parts
const parts: string[] = [];

// Surface warnings as plain text (missing tool binaries)
if (result.warnings.length > 0) {
  parts.push(result.warnings.map(w => `SAFEWORD: ${w}`).join('\n'));
}

// Surface remaining lint errors via additionalContext so Claude can fix them
if (result.errors) {
  const output = {
    hookSpecificOutput: {
      hookEventName: 'PostToolUse',
      additionalContext: `Lint errors remain after auto-fix in ${file}:\n${result.errors}`,
    },
  };
  console.log(JSON.stringify(output));
} else if (parts.length > 0) {
  // Only plain text warnings (no errors) — output as before
  console.log(parts.join('\n'));
}
