#!/usr/bin/env bun
// Safeword: Background update check (SessionStart, async)
// Queries npm registry for latest version, writes result to .safeword/.update-cache.json
// Respects 24h cooldown to avoid unnecessary network requests.

import { existsSync } from 'node:fs';

const projectDir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const safewordDir = `${projectDir}/.safeword`;

if (!existsSync(safewordDir)) {
  process.exit(0);
}

const COOLDOWN_MS = 24 * 60 * 60 * 1000; // 24 hours
const cachePath = `${safewordDir}/.update-cache.json`;

// Check cooldown
const cacheFile = Bun.file(cachePath);
if (await cacheFile.exists()) {
  try {
    const cache = (await cacheFile.json()) as { checkedAt?: number };
    if (cache.checkedAt && Date.now() - cache.checkedAt < COOLDOWN_MS) {
      process.exit(0); // Still within cooldown
    }
  } catch {
    // Corrupted cache, proceed with check
  }
}

// Fetch latest version + per-version publish times from npm registry.
// Use the full packument (not /safeword/latest) so we can read `time[version]`,
// which is npm-generated (tamper-resistant) and lets us enforce a release-age
// cooldown in session-auto-upgrade.ts. The cooldown blocks installation of
// versions published <24h ago — gives the community time to detect and yank
// malicious releases (2026 best practice; mirrors pnpm's minimumReleaseAge).
try {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, 3000);

  const response = await fetch('https://registry.npmjs.org/safeword', {
    signal: controller.signal,
  });

  clearTimeout(timeoutId);

  if (!response.ok) {
    process.exit(0);
  }

  const data = (await response.json()) as {
    'dist-tags'?: { latest?: string };
    time?: Record<string, string>;
  };

  const latestVersion = data['dist-tags']?.latest;
  const publishedAtIso = latestVersion ? data.time?.[latestVersion] : undefined;

  // Fail closed: if either field is missing or the timestamp is malformed,
  // don't write a partial cache. The auto-upgrade hook treats missing
  // publishedAt as "too new" and skips, so a partial cache would block
  // upgrades indefinitely.
  if (!latestVersion || !publishedAtIso) {
    process.exit(0);
  }

  const publishedAt = Date.parse(publishedAtIso);
  if (Number.isNaN(publishedAt)) {
    process.exit(0);
  }

  // Write cache atomically (temp file + rename)
  const tempPath = `${cachePath}.tmp-${Date.now()}`;
  await Bun.write(tempPath, JSON.stringify({ latestVersion, publishedAt, checkedAt: Date.now() }));
  const { renameSync } = await import('node:fs');
  renameSync(tempPath, cachePath);
} catch {
  // Network failure is fine — we'll try again next session
}
