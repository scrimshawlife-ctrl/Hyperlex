# RECEIPT — accept7 adversarial gold + famcls11 hard-neg reject (2026-09-14)

**Authority:** Spec 007. Agent classification ownership.
**BEST:** untouched. `name_gate` false.

## Famcls9 dump (accept6-test)

family_exact **0.481**, 28 mistakes — mainly `brainrot-aura → gaming-meta`, crypto mixups, short kinship→gaming.

Artifact: `~/hlx-private/p1-classify-accept6-20260914/famcls9_accept6_errors.json`

## Accept7 (data)

Parent: accept6. **+211** agent adversarial contrastive surfaces (not lexicon spray).

Pin: `~/hlx-private/p1-classify-accept7-20260914/prepare`.

Fair famcls9 accept7-test: family **0.452**, structure/role/pointer **1.0**.

## Famcls11 (weights)

Recipe: init famcls9 → freeze encoder+structure → family-head with inv-freq CE **+ hard-neg softplus margin** on dump rivals (λ=0.5, margin=0.5, 40 ep).

Pre-registered gate: family > 0.452 (famcls9 accept7-test) AND structure/role/pointer = 1.0.

| ckpt | structure | role | pointer | family |
|------|-----------|------|---------|--------|
| famcls9 baseline | **1.0** | **1.0** | **1.0** | **0.452** |
| famcls11 | **1.0** | **1.0** | **1.0** | 0.435 |

**REJECT.** Family Δ −0.016. Structure hold OK.

## Pins after

- Weights: **famcls9** (unchanged)
- Data: **accept7**
- BEST: morph19 unchanged

## Artifacts

- `~/hlx-private/p1-classify-accept7-20260914/`
- `~/hlx-private/p1-structure-unbind-famcls11-20260914/{REJECTED.md,GATE.md,out/SMOKE_SUMMARY.json}`

## Lesson

Head-only climbs (inv-freq CE and hard-neg margin) both fail the fair gate while holding structure. Next recipe must be allowed to move encoder (last-N) under a structure-hold gate — or wait for harder reviewed gold.
