# Local-only integration probes

This directory is intentionally **gitignored** (see `.gitignore`). It exists as
a scratchpad for one-shot investigation scripts that hit live vendor APIs to
verify error mappings in the TDK adapters.

These probes are **not** part of the standard test suite and must never be
committed. They typically require vendor API credentials in the local
environment (e.g. `LINEAR_API_KEY`).

Current probes (when present locally):

- `test_linear_adapter_live.py` — hits `https://api.linear.app/graphql` with
  deliberately-broken queries to confirm the wire-format taxonomy used by
  `LinearGraphQLAdapter`.
