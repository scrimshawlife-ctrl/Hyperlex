# `name_gate` yes — `seed-morph78` (2026-09-24)

**Operator:** Danny · **Sentence:** `flip name_gate` · **Amendment:** A6 (`amendments.md`)

## Decision

Product-level `name_gate=true` for pin **`seed-morph78`**. That pin may be called **Hyperlexical**.

## Basis (receipts, not re-run)

| Requirement | Evidence |
|---|---|
| T1 tier: ModernBERT-base trunk (A2), unbind heads | `receipts/morph78-val-settle-20260924/train-receipt.json` (`trunk: answerdotai/ModernBERT-base`) |
| Trained E2 vs Spec 004 probe | `receipts/morph78-val-settle-20260924/e2-unbind-morph78.json` — `e2_pass: true`, unbind_exact 1.0, trunk_forward |
| BEST pinned | `receipts/20260924-morph78-soft-ceiling-promote-best.md` — PROMOTE_BEST, broad 0.98828125 vs 0.88671875 n=256 |
| Dataset buckets | `milestones.md` — gaps 0/0/0 |
| Danny explicit yes | this sentence |

Operator product review of `HYPERLEXICAL-PRODUCT-PLAN.md` was not separately recorded before the flip.

## Scope — what this does not do

- No card/package identifier rename. `hyperlex-encoder-*` stays until a separate change (locked C31 target `hyperlex-structure-149m`).
- No change to SHADOW packet/schema `name_gate` fields. Code and `schemas/eval_unbind.v0.1.schema.json` / `contracts/training/v1.schema.json` still emit and require `false` per packet; reconciling them is part of the rename change.
- No Hub upload. No T13. No new climb. Brier stays `null`.
- Earlier receipts (including the morph78 promote receipt, which records `name_gate=false` at promote time) are unchanged.
- Applies to `seed-morph78` only. No other checkpoint, stub, seed smoke or harvest dump is Hyperlexical.
