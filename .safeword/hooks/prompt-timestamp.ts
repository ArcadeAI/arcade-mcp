#!/usr/bin/env bun
// Safeword: Inject timestamp (UserPromptSubmit)
// Outputs current timestamp for Claude's context awareness
// Helps with accurate ticket timestamps and time-based reasoning

const now = new Date();

// Natural language day/time in UTC
const natural = now.toLocaleDateString('en-US', {
  weekday: 'long',
  year: 'numeric',
  month: 'long',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
  timeZoneName: 'short',
});

// ISO 8601 UTC
const iso = now.toISOString();

// Local timezone
const local = now.toLocaleTimeString('en-US', {
  hour: '2-digit',
  minute: '2-digit',
  timeZoneName: 'short',
});

console.log(`Current time: ${natural} (${iso}) | Local: ${local}`);
