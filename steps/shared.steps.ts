/**
 * Shared shell-out steps — the language-agnostic core of the acceptance lane.
 * They run a command and assert on its result, so TypeScript steps can test an
 * app written in any language (`go test ./...`, `cargo test`, an HTTP call via
 * `curl`). Add domain steps in new files here in `steps/`; keep them thin and
 * push logic into helpers.
 */

import { strict as assert } from 'node:assert';
import { exec } from 'node:child_process';
import { promisify } from 'node:util';

import { Then, When } from '@cucumber/cucumber';

import type { SafewordWorld } from './world.js';

const execAsync = promisify(exec);

When('I run shell command {string}', async function (this: SafewordWorld, command: string) {
  try {
    const { stdout, stderr } = await execAsync(command);
    this.result = { stdout, stderr, exitCode: 0 };
  } catch (error: unknown) {
    const failure = error as { stdout?: string; stderr?: string; code?: number };
    this.result = {
      stdout: failure.stdout ?? '',
      stderr: failure.stderr ?? '',
      exitCode: failure.code ?? 1,
    };
  }
});

Then('the shell exit code is {int}', function (this: SafewordWorld, expected: number) {
  assert.equal(this.result.exitCode, expected, `stderr: ${this.result.stderr}`);
});

Then('the shell output contains {string}', function (this: SafewordWorld, text: string) {
  const combined = `${this.result.stdout}${this.result.stderr}`;
  assert.ok(combined.includes(text), `output did not contain "${text}"\n${combined}`);
});
