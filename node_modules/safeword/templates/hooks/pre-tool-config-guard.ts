#!/usr/bin/env bun
// Safeword: Config Guard (PreToolUse)
// Requires user approval before modifying quality config files

import { existsSync } from 'node:fs';

interface HookInput {
  tool_name?: string;
  tool_input?: {
    file_path?: string;
    notebook_path?: string;
  };
}

interface HookOutput {
  hookSpecificOutput: {
    hookEventName: 'PreToolUse';
    permissionDecision: 'ask' | 'allow' | 'deny';
    permissionDecisionReason: string;
  };
}

// Protected file patterns (glob-like matching)
const PROTECTED_PATTERNS: Array<{ pattern: RegExp; category: string }> = [
  // ESLint configs
  { pattern: /eslint\.config\.[mc]?[jt]s$/, category: 'ESLint config' },
  { pattern: /\.eslintrc(?:\.(?:json|ya?ml|c?js|mjs))?$/, category: 'ESLint config' },
  { pattern: /eslint-configs\/.*\.[jt]s$/, category: 'ESLint preset' },

  // TypeScript configs
  { pattern: /tsconfig.*\.json$/, category: 'TypeScript config' },

  // Vitest/Jest configs
  { pattern: /vitest\.config\.[mc]?[jt]s$/, category: 'Vitest config' },
  { pattern: /jest\.config\.[mc]?[jt]s$/, category: 'Jest config' },

  // Prettier configs
  { pattern: /\.prettierrc(?:\.(?:json|ya?ml|c?js|mjs))?$/, category: 'Prettier config' },
  { pattern: /prettier\.config\.[mc]?[jt]s$/, category: 'Prettier config' },

  // Presets (affects all customers)
  { pattern: /\/presets\/.*\.[jt]s$/, category: 'Quality preset' },

  // CI workflows
  { pattern: /\.github\/workflows\/.*\.ya?ml$/, category: 'CI workflow' },
  { pattern: /\.gitlab-ci\.ya?ml$/, category: 'CI config' },
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

const filePath = input.tool_input?.file_path ?? input.tool_input?.notebook_path;

// No file path, allow
if (!filePath) {
  process.exit(0);
}

// Check if file matches any protected pattern
for (const { pattern, category } of PROTECTED_PATTERNS) {
  if (pattern.test(filePath)) {
    const output: HookOutput = {
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'ask',
        permissionDecisionReason: `⚠️ ${category} change requires approval.\n\nFile: ${filePath}\n\nPer SAFEWORD policy: Fix code, don't weaken configs.\nIf this is a justified change, explain the evidence.`,
      },
    };
    console.log(JSON.stringify(output));
    process.exit(0);
  }
}

// Not a protected file, allow
process.exit(0);
