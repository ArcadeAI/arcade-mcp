#!/usr/bin/env bun
// Safeword: Bypass Pattern Warning (PostToolUse)
// Warns when bypass patterns are added to code

import { existsSync } from 'node:fs';

interface HookInput {
  tool_name?: string;
  tool_input?: {
    file_path?: string;
    notebook_path?: string;
    new_string?: string; // For Edit tool
    content?: string; // For Write tool
  };
}

// Bypass patterns to detect
const BYPASS_PATTERNS: Array<{
  pattern: RegExp;
  category: string;
  example: string;
}> = [
  // ESLint disables
  {
    pattern: /eslint-disable(?:-next-line|-line)?/,
    category: 'ESLint disable',
    example: 'eslint-disable-next-line',
  },

  // TypeScript bypasses
  {
    pattern: /@ts-ignore/,
    category: 'TypeScript bypass',
    example: '@ts-ignore',
  },
  {
    pattern: /@ts-expect-error/,
    category: 'TypeScript bypass',
    example: '@ts-expect-error',
  },
  {
    pattern: /@ts-nocheck/,
    category: 'TypeScript bypass',
    example: '@ts-nocheck',
  },
  { pattern: /\bas\s+any\b/, category: 'Type assertion', example: 'as any' },
  // Note: `as unknown` is NOT flagged - it's the safe alternative to `as any`

  // Test skips
  {
    pattern: /\b(it|test|describe)\.(skip|only)\s*\(/,
    category: 'Test skip/only',
    example: 'it.skip(',
  },
];

const projectDir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const safewordDir = `${projectDir}/.safeword`;

// Not a safeword project, skip silently
if (!existsSync(safewordDir)) {
  process.exit(0);
}

// Read hook input from stdin
let input: HookInput;
try {
  input = await Bun.stdin.json();
} catch {
  process.exit(0);
}

// Get the content that was written/edited
const content = input.tool_input?.new_string ?? input.tool_input?.content;

// No content to check, skip
if (!content) {
  process.exit(0);
}

// Check for bypass patterns
const foundPatterns: string[] = [];
for (const { pattern, category, example } of BYPASS_PATTERNS) {
  if (pattern.test(content)) {
    foundPatterns.push(`  • ${category} (${example})`);
  }
}

// If bypass patterns found, output warning
if (foundPatterns.length > 0) {
  const filePath = input.tool_input?.file_path ?? input.tool_input?.notebook_path ?? 'unknown';
  console.log(`⚠️ SAFEWORD: Bypass pattern detected in ${filePath}

Found:
${foundPatterns.join('\n')}

Per SAFEWORD policy: Fix code, don't weaken enforcement.
Scope suppressions to the problem: line > block > file > project.
If this is justified, document the evidence in a comment.`);
}

process.exit(0);
