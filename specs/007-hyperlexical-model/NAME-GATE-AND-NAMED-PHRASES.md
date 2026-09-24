# Name gate + named phrases — operator plan

**Status:** `name_gate` **FLIPPED** for `seed-morph78` (Danny, 2026-09-24, A6) · **Date:** 2026-09-24  
**Locks:** `name_gate=true` (morph78 only) · no Hub · no invented OBSERVED · upsample freeze **11+** · no `SECOND_SLOT=4` · soft_ceiling spent (morph78 BEST)

Companion to `HYPERLEXICAL-PRODUCT-PLAN.md`.

## Current product boundary — 2026-09-24

- BEST = `seed-morph78`
- soft_ceiling climb = **CLOSED / SPENT**
- broad OBSERVED = **0.9883** n=256
- PRIOR morph65 = **0.8867** n=256
- trained trunk-forward E2 = **PASS**
- next climb = **not authorized**
- `name_gate=true` for `seed-morph78` (Danny `flip name_gate`)
- Hub = unpublished
- T13 = not authorized

Receipt: `receipts/20260924-morph78-soft-ceiling-promote-best.md`. Do not re-run the completed morph78 climb as if it were pending work.

### Operator name (ingest)

Danny: **`name neologist as in repo`**. Public ingest product = **`ne0l0gist`** (repo spelling with zeros). Receipt: `receipts/20260924-name-ne0l0gist-as-in-repo.md`. This does **not** flip Hyperlexical `name_gate`.

## Two walls

| Wall | Current state |
|------|---------------|
| Dataset readiness (`milestones.md`) | bucket gaps 0/0/0 on the operator `--include-live` surface |
| Public model name | **APPROVED** for `seed-morph78` (2026-09-24) |
| Publish (Hub) | **BLOCKED** — separate sentence |

Volume readiness ≠ public naming. E2 PASS ≠ public naming. Danny's sentence named it.

## Gold / climb

morph78 is settled and promoted. Earlier empty-gold and morph77 cards are evidence, not reusable progress.

### Already OBSERVED — do not re-settle as new gold

| phrase | settled by | receipt |
|--------|-----------|---------|
| `we're so back` | morph77 val-settle | `receipts/20260923-morph77-val-settle-cancelled-fair-ceiling.md` |
| `clutch up` | morph77 val-settle | same |
| `bet that up` | morph77 val-settle | same |
| `real talk` | morph77 val-settle | same |
| `have fun staying poor` | morph78 val-settle | `receipts/20260924-morph78-val-settle-soft-ceiling-inflight.md` |
| `fr fr no cap` | morph78 val-settle | same |

### Future climb (not authorized)

A future climb needs a **new** acquire/authorize card and compares against morph78 as PRIOR (broad 0.9883 n=256 + E2). Accepted sentence shapes:

1. Named phrases from that new card's acquire/qualify pool: `authorize val-settle: <phrase>, <phrase>, …`
2. A new acquire that clears Jev `force_expand_safe` with non-empty `authorize_card_phrases`, then explicit authorize listing those phrases.

Still forbidden: empty settle, invented OBSERVED, recycled settled phrases, UPSAMPLE 11+, `SECOND_SLOT=4`.

## `name_gate` flip — done (Danny)

Receipt: `receipts/20260924-name-gate-yes-morph78.md`. No agent flipped it without the sentence.

- [x] Dataset bucket gaps 0/0/0 (met 2026-09-10)
- [x] Trained trunk-forward E2 PASS on `seed-morph78`
- [x] soft_ceiling climb closed with morph78 PROMOTE_BEST
- [x] Hygiene: `VERSION` ↔ `pyproject.toml`; stale "E2 Spark-blocked" current-state wording scrubbed (PR #102)
- [x] Product-state reconciliation drafted (PR #102)
- [ ] Operator product review of `HYPERLEXICAL-PRODUCT-PLAN.md` — not separately recorded; Danny flipped without it
- [x] Danny explicit `flip name_gate` (2026-09-24)

Actions stay separate:

1. change governed `name_gate` surfaces — **done** (A6);
2. update public card naming (`hyperlex-encoder-*` → Hyperlexical per `model-card.draft.md`);
3. Hub upload only on a separate named operator action;
4. optional T13 only on separate authorization + tests.

## Pointers

- Product plan: `HYPERLEXICAL-PRODUCT-PLAN.md`
- Current climb state: root `NEXT_MOVES_007.md`
- Naming SoT: `docs/NAMING.md`
- Historical (2026-09-23): `receipts/20260923-authorize-gate-soft-ceiling.md` · `receipts/20260923-morph78-fresh-acquire-hold-empty.md` · `receipts/morph77-val-acquire-label-hold-20260923/`
