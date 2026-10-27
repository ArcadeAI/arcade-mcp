# PR Scope Discipline

Monitor PR growth continuously. When **any** threshold is crossed, stop current work and re-evaluate:

| Metric                  | Threshold |
| ----------------------- | --------- |
| Commits on branch       | 5         |
| Lines changed (add+del) | 1,000     |
| Files changed           | 15        |
| Review fix-up rounds    | 2         |

## Required agent behavior when triggered

1. STOP. Announce: "PR scope check — [metric] at [value]/[threshold]."
2. Summarize what the PR currently contains (group by logical concern).
3. Propose 2–3 ways to break it down (stacked PRs, ship-what's-done + follow-up, extract standalone changes).
4. Wait for user direction before continuing.
