#!/usr/bin/env bun
// Safeword: Verify AGENTS.md link (SessionStart)
// Self-heals by restoring the link if removed

import { existsSync } from 'node:fs';

const LINK = '**⚠️ ALWAYS READ FIRST:** `.safeword/SAFEWORD.md`';

const projectDir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const safewordDir = `${projectDir}/.safeword`;

// Not a safeword project, skip silently
if (!existsSync(safewordDir)) {
  process.exit(0);
}

const agentsFile = Bun.file(`${projectDir}/AGENTS.md`);

if (!(await agentsFile.exists())) {
  // AGENTS.md doesn't exist, create it
  await Bun.write(agentsFile, `${LINK}\n`);
  console.log('SAFEWORD: Created AGENTS.md with safeword link');
  process.exit(0);
}

// Check if link is present
const content = await agentsFile.text();
if (!content.includes('.safeword/SAFEWORD.md')) {
  // Link missing, prepend it
  await Bun.write(agentsFile, `${LINK}\n\n${content}`);
  console.log('SAFEWORD: Restored AGENTS.md link (was removed)');
}
