#!/usr/bin/env bun
// Safeword: Display version on session start (SessionStart)
// Shows current safeword version and confirms hooks are active

import { existsSync } from 'node:fs';

const projectDir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const safewordDir = `${projectDir}/.safeword`;

// Not a safeword project, skip silently
if (!existsSync(safewordDir)) {
  process.exit(0);
}

const versionFile = Bun.file(`${safewordDir}/version`);
const version = (await versionFile.exists()) ? (await versionFile.text()).trim() : 'unknown';

console.log(
  `SAFE WORD Claude Config v${version} installed - auto-linting and quality review active`,
);
