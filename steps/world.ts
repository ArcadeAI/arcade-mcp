/**
 * Shared world for safeword's BDD acceptance lane. Each scenario gets a fresh
 * instance; step definitions stash the last command result here. Extend this
 * class with your own state as your features grow.
 */

import { setWorldConstructor, World } from '@cucumber/cucumber';

export interface CommandResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

export class SafewordWorld extends World {
  result: CommandResult = { stdout: '', stderr: '', exitCode: 0 };
}

setWorldConstructor(SafewordWorld);
