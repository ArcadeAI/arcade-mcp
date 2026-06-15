# Done: Close Ticket

**Entry:** verify.md exists in ticket folder (written by /verify in the verify phase).

Done means the ticket is closed. All verification happened in the verify phase.

## Close

1. Update parent epic if applicable (add completion entry to parent's work log; if all children done → update parent `status: done`)
2. Update ticket: `phase: done`, `status: done`
3. Final commit: `feat(scope): [summary]`

The stop hook hard-blocks if verify.md is missing or empty — you cannot reach done without completing the verify phase first.
