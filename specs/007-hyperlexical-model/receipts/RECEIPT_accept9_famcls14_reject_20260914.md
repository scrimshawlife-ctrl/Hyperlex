# RECEIPT — accept9 residual gold + famcls14 reject (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Merge

Operator: merge and continue from famcls13 KEEP.

## Famcls13 dump (accept8-test)

family_exact **0.614**, 27 mistakes — mainly short `brainrot-aura → gaming-meta`, `ai-native → gaming-meta`, `crypto-degen → gaming-meta`, kinship shorts → gaming.

## Accept9 (data)

Parent: accept8. **+174** residual-miss contrastive surfaces.

Pin: `~/hlx-private/p1-classify-accept9-20260914/prepare`.

## Famcls14 (weights)

Recipe: init famcls13 → freeze structure → last N=2 encoder + family head (inv-freq CE).

Pre-registered gate: family > 0.615 (famcls13 accept9-test) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls13 baseline | **1.0** | **1.0** | **1.0** | **0.615** |
| famcls14 | **1.0** | **1.0** | **1.0** | 0.615 |

**REJECT.** Family Δ 0.000 (tie). Structure hold OK.

## Pins after

- Weights: **famcls13** (unchanged)
- Data: **accept9**
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-classify-accept9-20260914/`
- `~/hlx-private/p1-structure-unbind-famcls14-20260914/{REJECTED.md,GATE.md,out/}`

## Lesson

Identical last-N=2 climbs plateaued. Need harder gold or a new pre-registered recipe — not another same-recipe clone.
