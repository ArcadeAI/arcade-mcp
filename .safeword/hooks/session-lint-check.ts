#!/usr/bin/env bun
// Safeword: Lint configuration sync check (SessionStart)
// Warns if ESLint or Prettier configs are missing or out of sync

import { existsSync, readdirSync } from 'node:fs';

import { detectEslintConfig, detectPrettierConfig } from './lib/lint-config.ts';

const projectDir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const safewordDir = `${projectDir}/.safeword`;

// Not a safeword project, skip silently
if (!existsSync(safewordDir)) {
  process.exit(0);
}

const warnings: string[] = [];

// List the project dir once; detect config presence by filename prefix so new
// eslint/prettier config extensions are covered without enumerating each.
const entries = (() => {
  try {
    return readdirSync(projectDir);
  } catch {
    return [];
  }
})();

if (!detectEslintConfig(entries)) {
  warnings.push("ESLint config not found - run 'bun run lint' may fail");
}

if (!detectPrettierConfig(entries)) {
  warnings.push('Prettier config not found - formatting may be inconsistent');
}

// Check for required dependencies in package.json
const pkgJsonFile = Bun.file(`${projectDir}/package.json`);
if (await pkgJsonFile.exists()) {
  try {
    const pkgJson = await pkgJsonFile.text();
    if (!pkgJson.includes('"eslint"')) {
      warnings.push("ESLint not in package.json - run 'bun add -D eslint'");
    }
    if (!pkgJson.includes('"prettier"')) {
      warnings.push("Prettier not in package.json - run 'bun add -D prettier'");
    }
  } catch (error) {
    if (process.env.DEBUG) console.error('[session-lint-check] package.json parse error:', error);
  }
}

// Output warnings if any
if (warnings.length > 0) {
  console.log('SAFEWORD Lint Check:');
  for (const warning of warnings) {
    console.log(`  ⚠️  ${warning}`);
  }
}
