# Hyperlex installer audit (SHADOW)

Re-implemented from closed PR #5 onto current `main`. Hyperlex-only: no
neon-genie or sigil-forge CHECKS. Stage-validate before activation, preserve
legacy `out`, target-keyed backups, operator-owned locks. Two-rename activation
is not crash-atomic. Locks are never automatically reclaimed.

Source identity is `VERSION` plus `git rev-parse HEAD`. Mutation packets stay
advisory (`brier: null`, `forecast_eligible: false`).
