# Name gate + named phrases — operator plan

**Status:** DRAFT (does **not** flip `name_gate`) · **Date:** 2026-09-24  
**Locks:** `name_gate=false` · no Hub · no invented OBSERVED · upsample freeze **11+** · no `SECOND_SLOT=4` · soft_ceiling spent (morph78 BEST)

Companion to `HYPERLEXICAL-PRODUCT-PLAN.md` workstreams A (climb/gold) and C (post–name_gate packaging).

### Operator name (ingest) — 2026-09-24

Danny: **`name neologist as in repo`**. Public ingest product = **`ne0l0gist`** (repo spelling with zeros). Receipt: `receipts/20260924-name-ne0l0gist-as-in-repo.md`. This does **not** flip Hyperlexical `name_gate`.

---

## Two walls (do not conflate)

| Wall | What it gates | Current state |
|------|----------------|---------------|
| **Dataset name-gate buckets** (`milestones.md`) | Settled gold floors before *planning* a T1 name | Gaps **0 / 0 / 0** on operator `--include-live` (classify ≥2k / unbind ≥200 / negatives ≥200) |
| **`name_gate` flag** | Public **Hyperlexical** name + Hub/T13 packaging | **false** — Danny explicit yes required. Trained E2 PASS on Spark does **not** flip this. Ingest **`ne0l0gist`** is already named (separate product). |

Volume readiness ≠ name. Seed smoke ≠ T1. Stub E2 FAIL remains expected.

---

## Named phrases (gold authorize)

Empty `authorize_card_phrases` → Jev **`cancel_empty_gold`**. Do not invent OBSERVED to fill a card.

### Last non-empty HOLD card (morph77 · already settled)

Receipt: `receipts/20260923-morph77-val-acquire-label-hold.md` · card `receipts/morph77-val-acquire-label-hold-20260923/HOLD_AUTHORIZE_CARD.json`.

| # | phrase | lineage (card) |
|--:|--------|----------------|
| 1 | `we're so back` | brainrot-aura |
| 2 | `clutch up` | gaming-meta |
| 3 | `bet that up` | kinship-address |
| 4 | `real talk` | kinship-address |

`authorize val-settle` on morph77 **kept** these as OBSERVED `split=val` and grew force/hard **224→232 / 265→273**. Train was **CANCELLED_FAIR_CEILING** (fair stayed 1.0 n=164). See `receipts/20260923-morph77-val-settle-cancelled-fair-ceiling.md`.

**Do not re-authorize / re-settle these four** — they are already OBSERVED. Re-listing them as “new gold” would be inventing progress.

### Cards after morph77

| card | `authorize_card_phrases` |
|------|--------------------------|
| morph78 fresh acquire | **PROMOTE_BEST 2026-09-24:** settled phrases + soft_ceiling ceiling_escape (broad 0.9883 > 0.8867) |
| morph65 live broad residual reprobe | `[]` |

Operator bare `authorize val-settle` → **CANCELLED_EMPTY_GOLD** (`receipts/20260923-authorize-val-settle-cancelled-empty-gold.md`). Force tip remains morph77 **232/273**. Live broad prior **0.88671875** n=256.

### Authorize sentence shapes (required)

One of:

1. **Named phrases on a live empty card** — operator lists exact norms from that card’s acquire/qualify pool (not from memory, not morph77’s already-settled four unless the new card independently contains them as unsettled AUTHORIZE):
   - `authorize val-settle: <phrase>, <phrase>, …`
   - `authorize morph78: <phrase>, <phrase>, …`
2. **New acquire** that clears Jev `force_expand_safe` with a non-empty `authorize_card_phrases` after `card_high_conf_new` (or equivalent), then explicit authorize listing those phrases.
3. **Climb without new force-only gold** — under soft_ceiling, fair = 1.0 path is **broad OBSERVED > PRIOR** live + E2 (`gate_soft_ceiling_decide.py`), not another force-only morph at n=164.

Still forbidden: empty settle, invented OBSERVED, UPSAMPLE 11+, `SECOND_SLOT=4`.

---

## `name_gate` flip plan (Danny only)

This section is a checklist. **No agent flips the flag.**

### Preconditions (all must already be true or explicitly waved)

- [x] Dataset bucket gaps 0/0/0 on the harvest surface (met 2026-09-10)
- [x] Trained trunk-forward E2 PASS on pinned BEST (`seed-morph78`)
- [x] Soft_ceiling climb closed: morph78 PROMOTE_BEST 2026-09-24
- [ ] Operator product review of `HYPERLEXICAL-PRODUCT-PLAN.md`
- [x] Hygiene B2–B3 landed (`VERSION` ↔ `pyproject.toml`; stale “E2 Spark-blocked” scrubbed from operator ROADMAP/STATUS copies)
- [ ] Danny sentence that explicitly says **`name_gate` yes** (or “name Hyperlexical”)

### On Danny yes (separate PRs / sentences)

1. Set `name_gate` true in the locked operator surfaces only (STATUS / milestones note / dual-use gate as required by engineering.md) — not by silent agent edit.
2. Allow card rename path: `hyperlex-encoder-*` → Hyperlexical naming per `model-card.draft.md`.
3. Hub upload = **named** operator action (C2). Weights stay out of git until then.
4. Optional T13 promote of `scripts/shadow/hyperlexical/` into `src/hyperlex/` = separate authorize + tests.

### Explicit non-goals

- Flipping `name_gate` because E2 PASS, volume, or soft_ceiling ARMED
- Treating morph77’s four settled phrases as a name_gate unlock
- Hub / T13 without Danny

---

## Sequencing

```
Hygiene (this branch) ──► operator review product plan
        │
        ├──► named-phrase authorize OR new force_expand_safe acquire ──► soft_ceiling decide
        │
        └──► Danny name_gate yes (only when ready) ──► card / Hub / optional T13
```

---

## Pointers

- Product plan: `HYPERLEXICAL-PRODUCT-PLAN.md`
- Climb next: root `NEXT_MOVES_007.md` · this pack `NEXT_MOVES_007.md`
- morph77 card: `receipts/morph77-val-acquire-label-hold-20260923/`
- Empty morph78: `receipts/20260923-morph78-fresh-acquire-hold-empty.md`
- Soft ceiling: `receipts/20260923-authorize-gate-soft-ceiling.md`
