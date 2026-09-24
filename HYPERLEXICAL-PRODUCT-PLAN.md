# Hyperlexical model product — completion plan

**Status:** DRAFT (operator review) · **Reconciled:** 2026-09-24  
**Naming:** repo **Hyperlex** = transitional shell. Public ingest = **ne0l0gist**. Public trained-model product = **Hyperlexical**, still gated. Hermes skill ≠ Hyperlexical.

**Hard locks:** `name_gate=false` until Danny explicit yes · no Hub upload · no invented OBSERVED · upsample freeze **11+** · no `SECOND_SLOT=4` · schemes `positional|type_slot` only · Brier `null` on every 007 packet.

This plan supersedes the 2026-09-23 morph65/empty-morph78 snapshot. It does not flip `name_gate`.

## Current honest state

| Layer | State |
|---|---|
| Hermes skill | **Ready** v0.4.0 |
| Spec 007 trained pin | **BEST=`seed-morph78`** |
| Promotion | **PROMOTE_BEST** via soft_ceiling ceiling escape |
| Broad OBSERVED | **0.9883 n=256** |
| PRIOR | morph65 **0.8867 n=256** |
| E2 | **PASS** on trained trunk-forward path |
| Force/hard | **236 / 277** |
| soft_ceiling | **SPENT / CLOSED for this climb** |
| name_gate | **false** |
| Hub | unpublished |
| T13 | not authorized |
| Model card | reconciliation required before publication |

Verdict: training produced a viable pinned candidate. The remaining product boundary is naming/publication/integration authority, not proof that training can succeed.

## Product completion states

### TRAIN
`UNTRAINED → TRAINED → E2_PASS → BEST_PINNED`

**Current:** `BEST_PINNED(seed-morph78)`

### NAME
`UNNAMED_PUBLICLY → NAME_GATE_APPROVED`

**Current:** `UNNAMED_PUBLICLY`

### PUBLISH
`LOCAL_ONLY → CARD_READY → HUB_AUTHORIZED → HUB_PUBLISHED`

**Current:** `LOCAL_ONLY`

### INTEGRATION
`SHADOW → T13_AUTHORIZED → SRC_PROMOTED`

**Current:** `SHADOW`

## Definition of complete

Hyperlexical is complete for this product cycle when:
1. a pinned BEST has receipts and E2 PASS;
2. dataset provenance remains honest;
3. the model card reflects the live pin without inventing metrics;
4. Danny explicitly approves `name_gate`;
5. any Hub upload is separately authorized;
6. any T13 promotion is separately authorized and tested.

Until item 4, artifact naming remains `hyperlex-encoder-*`.

## Workstreams

### A. Training / gold — CLOSED FOR CURRENT CLIMB

- [x] morph78 phrases settled
- [x] force/hard 236/277
- [x] broad comparison on same n=256 surface
- [x] 0.9883 > 0.8867 PRIOR
- [x] E2 PASS
- [x] PROMOTE_BEST
- [x] BEST pin updated to morph78

**Rule:** do not start another climb without a new operator-authorized acquire/card.

### B. Engineering hygiene

- [x] VERSION ↔ pyproject = 0.4.0
- [x] current STATUS/NEXT_MOVES show morph78
- [ ] model-card publish shape updated from stale pre-train E2 wording
- [ ] Notion Operator Hub current-work block reconciled to morph78
- [ ] verify no operator-facing page still calls morph65 current BEST

### C. Product packaging — post-name_gate

- [ ] operator reviews this reconciled plan
- [ ] Danny explicit `name_gate yes` / explicit Hyperlexical naming
- [ ] finalize public model card from pinned receipts
- [ ] separately authorize Hub upload or explicitly close cycle with no Hub
- [ ] optional T13 in separate PR + tests

### D. Adjacent track

HYPERLEX-Q1 remains separate from product naming. It stays **UNQUALIFIED** until its own evidence/review gate clears; Hyperlex → Noesis remains blocked by that track's requirements.

## Explicit non-goals

- restarting morph78 work already completed
- inventing OBSERVED fillers
- treating E2 PASS as automatic naming authority
- Hub upload without a named operator action
- T13 without separate authorization
- using Q1 qualification status as a substitute for Spec 007 product completion
- changing Brier from null on 007 packets

## Definition of done — current cycle

- [x] BEST pinned: morph78
- [x] trained E2 PASS
- [x] soft_ceiling climb closed
- [x] version hygiene
- [ ] model card reflects live morph78 evidence
- [ ] Notion parity restored
- [ ] Danny `name_gate` decision
- [ ] Hub decision: upload authorized or explicit no-Hub this cycle
- [ ] optional T13 decision
