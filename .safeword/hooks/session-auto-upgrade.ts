#!/usr/bin/env bun
// Safeword: Auto-upgrade at session start (SessionStart)
// Reads .safeword/.update-cache.json, applies patch + minor upgrades silently with a dedicated commit.
// Skips if: major bump, dirty working tree, autoUpgrade disabled, or CI environment.
// Policy reference: .claude/skills/versioning/SKILL.md

import { execFileSync, execSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';

import { isDogfoodRepo } from './lib/dogfood.ts';
import { filterSafewordFiles } from './lib/owned-paths.ts';
import { releaseAgeStatus, type UpdateCache } from './lib/update-cache.ts';
import { bumpType, upgradeDecision } from './lib/version.ts';

const projectDir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const safewordDir = `${projectDir}/.safeword`;

if (!existsSync(safewordDir)) {
  process.exit(0);
}

// Skip the safeword dev (dogfood) repo entirely (ticket 975N5T). Its `.safeword/`
// + `.claude/` are deployed mirrors of the LOCAL `packages/cli/templates/` source
// (routinely ahead of npm); installing the published package would regress
// unreleased work, and the follow-up commit is blocked by the dogfood-direction
// pre-commit guard. No version compare, no "available" message, no install.
if (isDogfoodRepo(projectDir)) {
  process.exit(0);
}

// --- Read current version ---
const versionPath = `${safewordDir}/version`;
const currentVersion = existsSync(versionPath) ? readFileSync(versionPath, 'utf8').trim() : '0.0.0';

// --- Read update cache ---
const cachePath = `${safewordDir}/.update-cache.json`;
const cacheFile = Bun.file(cachePath);
if (!(await cacheFile.exists())) {
  process.exit(0); // No cache yet, first session — async hook will populate it
}

let cache: UpdateCache;
try {
  cache = (await cacheFile.json()) as UpdateCache;
} catch {
  process.exit(0); // Corrupted cache
}

if (!cache.latestVersion) {
  process.exit(0);
}

const latest = cache.latestVersion;

// --- Version comparison + policy decision ---
// Policy is defined in lib/version.ts:upgradeDecision and pinned by unit tests.
const bump = bumpType(currentVersion, latest);
const decision = upgradeDecision(bump);

if (decision === 'skip') {
  process.exit(0); // No update needed (latest <= current)
}

if (decision === 'notify') {
  console.log(
    `SAFEWORD: v${latest} available (${bump}) — run \`bunx safeword@${latest} upgrade\` to update`,
  );
  process.exit(0);
}

// decision === 'apply' (patch or minor) — proceed to opt-out checks and upgrade

// --- Check opt-out ---
if (process.env.SAFEWORD_NO_AUTO_UPGRADE || process.env.CI) {
  console.log(`SAFEWORD: v${latest} available — auto-upgrade disabled`);
  process.exit(0);
}

// Check config file opt-out
try {
  const configPath = `${safewordDir}/config.json`;
  if (existsSync(configPath)) {
    const config = JSON.parse(readFileSync(configPath, 'utf8')) as { autoUpgrade?: boolean };
    if (config.autoUpgrade === false) {
      console.log(`SAFEWORD: v${latest} available — auto-upgrade disabled in config`);
      process.exit(0);
    }
  }
} catch {
  // Config parse error, proceed with upgrade
}

// --- Check release-age cooldown ---
// Supply-chain defense: don't install versions published <24h ago. See
// lib/update-cache.ts for rationale and threat model.
const ageStatus = releaseAgeStatus(cache.publishedAt, Date.now());
if (ageStatus.state === 'unknown') {
  console.log(
    `SAFEWORD: v${latest} available — waiting on release-age info (cache refreshes on next update check)`,
  );
  process.exit(0);
}
if (ageStatus.state === 'cooling') {
  console.log(
    `SAFEWORD: v${latest} available — applying after release-age cooldown (${ageStatus.remainingHours}h remaining)`,
  );
  process.exit(0);
}

// Node's execSync defaults to a 1MB stdout/stderr buffer and kills the subprocess
// with ENOBUFS on overflow. `safeword upgrade` output exceeds that on a real
// install, so we raise the ceiling for every shell-out. 50MB is generous; real
// upgrade output is well under 1MB but headroom is cheap.
const execOpts = {
  cwd: projectDir,
  encoding: 'utf8' as const,
  maxBuffer: 50 * 1024 * 1024,
};

// --- Check dirty working tree ---
try {
  const status = execSync('git status --porcelain', execOpts).trim();
  if (status) {
    console.log(`SAFEWORD: v${latest} available — will apply when working tree is clean`);
    process.exit(0);
  }
} catch {
  // Not a git repo or git not available — skip auto-upgrade
  process.exit(0);
}

// --- Perform upgrade ---
try {
  console.log(`SAFEWORD: Auto-upgrading v${currentVersion} → v${latest}...`);

  // Run the exact version (not @latest) to avoid supply chain ambiguity
  execSync(`bunx safeword@${latest} upgrade`, { ...execOpts, stdio: 'pipe' });

  // Stage only safeword-managed files that changed
  const changedFiles = execSync('git diff --name-only', execOpts)
    .trim()
    .split('\n')
    .filter(Boolean);
  const untrackedFiles = execSync('git ls-files --others --exclude-standard', execOpts)
    .trim()
    .split('\n')
    .filter(Boolean);

  const filesToStage = filterSafewordFiles(changedFiles, untrackedFiles);

  if (filesToStage.length > 0) {
    // execFileSync (no shell): filenames pass as args — no fragile manual
    // quoting that breaks on a name containing a quote or shell metacharacter.
    execFileSync('git', ['add', ...filesToStage], execOpts);
    execFileSync(
      'git',
      ['commit', '-m', `chore: safeword auto-upgrade v${currentVersion} → v${latest}`],
      { ...execOpts, stdio: 'pipe' },
    );
  }

  console.log(`SAFEWORD: Auto-upgraded v${currentVersion} → v${latest}`);
} catch (error) {
  const message = error instanceof Error ? error.message : 'Unknown error';
  console.log(`SAFEWORD: Auto-upgrade to v${latest} failed — will retry next session. ${message}`);
}
