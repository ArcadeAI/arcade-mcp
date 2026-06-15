---
name: explain
description: Use when you need safeword's dense artifacts or current state
  translated into plain English — what this is, why it matters, what to do next,
  with the internal jargon stripped. Targets a safeword ticket, a blocked gate, or
  a verdict; with no target it recaps where you are in the current safeword work.
  Read-only. Do NOT use to explain code diffs or PRs (base Claude handles those),
  for general status questions unrelated to safeword artifacts, or to make any
  change.
allowed-tools: Read, Grep, Glob, Bash
disallowed-tools: Edit, Write
disable-model-invocation: true
---

# Explain

Translate safeword's dense artifacts and current state into plain English — what
this is, why it matters, what to do next. **Read-only.** It reads the artifact or
state; it never changes it.

## The one rule

Obey SAFEWORD.md "Talking to the user": lead with the answer, front-load the
load-bearing words, end with a `**Next:**` line. Strip safeword's internal
vocabulary — no "phase / gate / sizing / propose-and-converge / done_when /
verdict." If you must name one, define it in the same breath. Write for a
teammate with zero safeword context.

## Pick the target

`/explain` takes an optional target:

- **No target** → current state: "where am I, what's next" (the default).
- **A ticket id or slug** → that ticket: what it builds, why, where it stands.
- **A gate-block or verdict** → what it's asking for and how to clear it.

Code diffs and PRs are out of scope — base Claude already explains those well.

### Default — current state ("catch me up")

Gather the durable trail safeword already keeps, then narrate it. Run:

```bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2> /dev/null || pwd)}"
NS_ROOT="$(node -e 'const fs=require("fs"),path=require("path");const project=process.argv[1];const directory=name=>path.join(project,name);const isDir=file=>{try{return fs.statSync(file).isDirectory()}catch{return false}};let configured;try{const parsed=JSON.parse(fs.readFileSync(path.join(project,".safeword","config.json"),"utf8"));const raw=parsed&&parsed.paths&&parsed.paths.projectRoot;if(typeof raw==="string"&&raw.length>0)configured=path.isAbsolute(raw)?raw:path.join(project,raw)}catch{}process.stdout.write(configured||(isDir(directory(".project"))?directory(".project"):isDir(directory(".safeword-project"))?directory(".safeword-project"):directory(".project")));' "$PROJECT_DIR")"
# What you're on now: the last re-entry line names the current ticket + Next
tail -3 "$NS_ROOT/re-entry.md" 2> /dev/null
# Fallback when re-entry is empty: in_progress tickets (not epics)
for f in "$NS_ROOT"/tickets/*/ticket.md; do
  [ -f "$f" ] || continue
  grep -q "^status: in_progress" "$f" && ! grep -q "^type: epic" "$f" && echo "$f"
done
# What landed recently
git log --oneline -5 2> /dev/null
```

The last re-entry line is the authoritative "current ticket" — prefer it over the
in_progress scan (a repo can carry many in_progress tickets at once). From that
ticket's `ticket.md`, read the `# H1` goal, the work-log tail, and any unchecked
`- [ ]` items under `done_when` (what's left). Then emit ONE brief:

> **You're on `<slug (ID)>`** — `<one plain line of what it is>`. Landed:
> `<recent commits, plainly>`. Left to do: `<the unchecked items, plainly>`.
> **Next:** `<the next concrete step>`.

If no ticket is active, say so plainly and point at the ticket list (`INDEX.md`)
plus the recent commits. Keep it to a few lines.

### A named ticket or artifact

Resolve `$NS_ROOT`, then read `$NS_ROOT/tickets/<id-or-slug>*/ticket.md` and translate, in order:

- **What it is** — the goal in one plain sentence (no "scope / done_when" labels).
- **Why it matters** — the problem it removes.
- **Done looks like** — the `done_when`, rewritten as observable outcomes.
- **Where it stands** — status in plain words: "not started", "in progress,
  tests next", "shipped".

End with **Next:** the immediate action.

### A gate-block or verdict

Read the message — the last block shown, or what the user pasted. Say, plainly:

- **What happened** — which rule fired, in one sentence.
- **Why** — the reason it exists, one clause.
- **How to clear it** — the exact next action.

Translate "phase gate / LOC gate / done gate" into the thing the user actually
has to do, not the internal name.

## Output shape

One scannable brief, not an essay. For an oversized artifact (an epic spec), lead
with a one-liner and offer "want the detail on X?" rather than dumping it all.

## Summary

`/explain` makes safeword legible on demand — current state by default, any
artifact on request — without diluting the precise artifacts themselves. It
reads; it never writes.
