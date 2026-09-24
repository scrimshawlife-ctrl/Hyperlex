# Hyperlexical model product — completion plan

**Status:** DRAFT (operator review) · **Reconciled:** 2026-09-24 (PR #102)

**Naming:** repo **Hyperlex** = transitional shell. Public ingest = **ne0l0gist** (named). Public trained-model product = **Hyperlexical**, still gated. Hermes skill ≠ Hyperlexical. SoT: `docs/NAMING.md`.

**Hard locks:** `name_gate=false` until Danny explicit yes · no Hub upload · no invented OBSERVED · upsample freeze **11+** · no `SECOND_SLOT=4` · schemes `positional|type_slot` only · Brier `null` on every 007 packet.

This plan supersedes the 2026-09-23 draft (morph65 BEST, soft_ceiling ARMED, morph78 acquire empty). That draft was accurate on 2026-09-23 and remains in git history. This plan does not flip `name_gate`.

## Current honest state

| Layer | State | Evidence |
|---|---|---|
| Hermes skill | **Ready** v0.4.0 | `VERSION`, `pyproject.toml` |
| Spec 007 lane | **SHADOW** | `spec.md`; code under `scripts/shadow/hyperlexical/` |
| Trained pin | **BEST=`seed-morph78`** | `receipts/morph78-val-settle-20260924/pin-promote-best.json` |
| Promotion | **PROMOTE_BEST**, soft_ceiling `ceiling_escape`, 2026-09-24 | `receipts/morph78-val-settle-20260924/GATE_LOCK.json` |
| Broad OBSERVED | **0.98828125** n=256 | `receipts/morph78-val-settle-20260924/broad-eval-morph78.json` |
| PRIOR | morph65 **0.88671875** n=256 (same live surface) | `receipts/morph78-val-settle-20260924/broad-eval-prior-morph65-at-finish.json` |
| E2 | **PASS** — trained trunk-forward, unbind_exact 1.0, n_unbind_eval 24 | `receipts/morph78-val-settle-20260924/e2-unbind-morph78.json` |
| Force fair (advisory at ceiling) | 1.0 n=164 | `receipts/morph78-val-settle-20260924/fair-eval-morph65-morph78.json` |
| Force/hard | **236 / 277** | `receipts/morph78-val-settle-20260924/ACQUIRE_SETTLE_SUMMARY.json` |
| soft_ceiling | **SPENT / CLOSED** for this climb | `receipts/20260924-morph78-soft-ceiling-promote-best.md` |
| E1 / E3 on `seed-morph78` | **NOT_COMPUTABLE** — no receipt | — |
| `name_gate` | **false** | STATUS, pin, E2 JSON |
| Hub | unpublished | — |
| T13 | not authorized | — |

Verdict: training produced a pinned candidate that passes E2. What is left is naming, publication and integration authority. Training is no longer the blocker.

## Product state machines

These are independent. Do not collapse them into one "product ready" flag.

| Machine | Path | Current |
|---|---|---|
| TRAIN | `UNTRAINED → TRAINED → E2_PASS → BEST_PINNED` | `BEST_PINNED(seed-morph78)` |
| NAME | `UNNAMED_PUBLICLY → NAME_GATE_APPROVED` | `UNNAMED_PUBLICLY` |
| PUBLISH | `LOCAL_ONLY → CARD_READY → HUB_AUTHORIZED → HUB_PUBLISHED` | `LOCAL_ONLY` |
| INTEGRATION | `SHADOW → T13_AUTHORIZED → SRC_PROMOTED` | `SHADOW` |

Only an operator sentence advances NAME, PUBLISH past `CARD_READY`, or INTEGRATION. TRAIN advancing does not advance any other machine.

## Definition of complete

Hyperlexical is complete for this product cycle when:

1. a pinned BEST has receipts and E2 PASS;
2. dataset provenance remains honest (OBSERVED only from settled/authorized gold);
3. the model card reflects the live pin without inventing metrics;
4. Danny explicitly approves `name_gate`;
5. any Hub upload is separately authorized;
6. any T13 promotion is separately authorized and tested.

Until item 4, artifact naming remains `hyperlex-encoder-*`.

## Workstreams

### A. Training / gold — CLOSED FOR CURRENT CLIMB

- [x] morph78 phrases settled OBSERVED `split=val`: `have fun staying poor`, `fr fr no cap`
- [x] force/hard 232/273 → 236/277
- [x] broad comparison on the same n=256 surface: 0.98828125 > 0.88671875
- [x] E2 PASS on `seed-morph78`
- [x] PROMOTE_BEST; Spark `BEST` → `seed-morph78`

**Rule:** do not start another climb without a new operator-authorized acquire/card. A future climb compares against morph78 as PRIOR.

### B. Engineering hygiene

- [x] `VERSION` ↔ `pyproject.toml` = 0.4.0
- [x] STATUS / NEXT_MOVES show morph78
- [x] model-card publish shape updated from pre-train E2 wording (PR #102)
- [x] Notion Operator Hub has a 2026-09-24 morph78 block; 2026-09-23 block kept as history
- [x] operator-facing pages no longer present morph65 as current BEST (PR #102 audit)

### C. Product packaging — post-`name_gate`

- [ ] operator reviews this reconciled plan
- [ ] Danny explicit `name_gate yes` / "name Hyperlexical"
- [ ] finalize public model card from pinned receipts
- [ ] separately authorize Hub upload, or explicitly close the cycle with no Hub
- [ ] optional T13 in a separate PR with tests

### D. Adjacent tracks (not product naming)

| Track | State |
|---|---|
| HYPERLEX-Q1 (#95) | draft · **UNQUALIFIED** until its own evidence/review gate clears |
| Hyperlex → Noesis pairwise qualification | **BLOCKED** on Q1 |
| #99 / #100 / #101 | merged |

Q1 status is not a substitute for Spec 007 product completion, and Spec 007 progress does not qualify Q1.

## Default recommendation

**HOLD morph78.** Resolve NAME and PUBLISH decisions before authorizing another training climb.

## Explicit non-goals

- restarting the completed morph78 climb
- inventing OBSERVED fillers or recycling settled phrases as new gold
- treating E2 PASS as naming authority
- Hub upload without a named operator action
- T13 without separate authorization
- changing Brier from `null` on 007 packets

## Definition of done — current cycle

- [x] BEST pinned: morph78
- [x] trained E2 PASS
- [x] soft_ceiling climb closed
- [x] version hygiene
- [x] model card reflects live morph78 evidence (E1/E3 marked NOT_COMPUTABLE)
- [x] Notion Operator Hub parity
- [ ] operator product review
- [ ] Danny `name_gate` decision
- [ ] Hub decision: upload authorized, or explicit no-Hub this cycle
- [ ] optional T13 decision

## Pointers

- Name gate + phrases: `NAME-GATE-AND-NAMED-PHRASES.md`
- Next moves: root `NEXT_MOVES_007.md`
- Promote receipt: `receipts/20260924-morph78-soft-ceiling-promote-best.md`
- Historical gate authorize: `receipts/20260923-authorize-gate-soft-ceiling.md`
