# Model card

Canonical draft for Hub shape: `hf-package/README.md`.

**Current trained pin:** `seed-morph78` · soft_ceiling `PROMOTE_BEST` 2026-09-24 · broad OBSERVED **0.9883** n=256 vs PRIOR morph65 **0.8867** n=256 · trained trunk-forward E2 **PASS**. Receipt: `receipts/20260924-morph78-soft-ceiling-promote-best.md`. E1/E3 on this pin: NOT_COMPUTABLE.

**Name:** `name_gate` **true** for `seed-morph78` (Danny `flip name_gate`, 2026-09-24, amendment A6). This pin may be called **Hyperlexical**.

Do not upload (Hub not authorized). Hub card name: `hyperlex-structure-149m` (locked C31). Local train-out paths keep `hyperlex-encoder-modernbert-base-seed-*`. Weights stay off git.

---

## V5 Stage-A / Stage-B pipeline (2026-10-01)

**Canonical Stage A:** `HYPERLEX_V5_STAGE_A_CANONICAL_V1`

| Pin | Value |
| --- | --- |
| `STAGE_A_BEST` | `f2b00c5dfeb087288fc1686c901fbc8b52a8ba7a7b51cb83ff038656f93617fa` |
| `MODEL_WIDE_BEST` | `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6` |
| Objective | `HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1` |
| Surface | `HYPERLEX_V5_STAGE_A_IDENTIFIABILITY_FILTERED_SURFACE_V1R2` |
| Input | `text` only (`AUTO_RELABEL=false`) |
| Thresholds | relation `0.60`, resolvability `0.75` |

**Decision:** `p_resolvable < 0.75 → UNCERTAIN`; else `p_relation ≥ 0.60 → EVIDENCE_PRESENT`; else `NO_EVIDENCE`.

**Validation (sealed):** false_entry `0.03357`; PRESENT recall `0.951`; NONE recall `0.965`.

**Limitations (do not overclaim):**

- `DOMAIN_IRRELEVANT_GENERALIZATION = NOT_ESTABLISHED`
- `SHORT_ATOM_POSITIVE_GENERALIZATION = LOW_SUPPORT`
- `CONTEXT_DEPENDENT_GOLD = OUTSIDE_CURRENT_TEXT_ONLY_STAGE_A_CONTRACT`

**Stage B (V1R2-aligned):** enters only on `EVIDENCE_PRESENT`. Active index/floors frozen (`index_sha256=4febe96e…`, n=948, score `0.83`, margin `0.01`). Historical V1R9 index `3fd6c87a…` / floors 0.64/0.07 retained as HISTORICAL.

**Pipeline:** `HYPERLEX_V5_STAGE_A_B_PIPELINE_V1` · Stage-A `CANONICAL_FROZEN` · Stage-B `CANONICAL_FOR_V1R2_PIPELINE` · Pipeline `CANONICAL_FROZEN` · research loop closed for the current failure class.

**Package:** `HYPERLEX_V5_STAGE_A_B_V1R2_PACKAGE_V1` · Hub `NOT_AUTHORIZED`.
