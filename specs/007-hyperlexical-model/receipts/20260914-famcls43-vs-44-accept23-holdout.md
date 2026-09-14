# Receipt — famcls43 vs famcls44 on fixed accept23 holdout

**Prepare (fixed):** `~/hlx-private/p1-classify-accept23-20260914/prepare`  
**Spark dumps:** `~/hlx-private/p1-classify-accept23-20260914/compare_famcls43_44/`  
**BEST:** morph19 untouched. No promotion.

## Metrics (test / holdout)

| model | aux | upsample | family_exact | structure_exact | role_exact | filler_pointer_exact | family misses | structure misses |
|-------|-----|----------|--------------|-----------------|------------|----------------------|---------------|------------------|
| **famcls43** | 0.12 | 4 | **0.9848** (195/198) | 0.9583 (23/24) | 1.0 | 0.9583 | 3 | 1 |
| **famcls44** | 0.18 | 4 | **0.9697** (192/198) | 0.9583 (23/24) | 1.0 | 0.9583 | 6 | 1 |

Both REJECT on climb gate (structure/pointer ≠ 1.0). Raising aux 0.12→0.18 **hurt family** (−3 exact) and **did not** close the structure hole.

## Structure / pointer (shared)

Identical single miss on both:

- text: `sheesh moment` · scheme `positional`
- role OK; pointer miss on slot1 `moment` (gold_start **3** → pred_start **2**)

## Family mistakes

### Shared (both wrong)
| text | gold | pred |
|------|------|------|
| `flop era` | brainrot-aura | gaming-meta |
| `clanker take` | ai-native | gaming-meta |

### famcls43 only
| text | gold | pred |
|------|------|------|
| `abliterated merge softens refusals` | ai-native | gaming-meta |

### famcls44 only
| text | gold | pred |
|------|------|------|
| `noob` | gaming-meta | kinship-address |
| `sigma grindset` | brainrot-aura | ai-native |
| `copium overdose` | political-status | crypto-degen |
| `ser so back onchain` | crypto-degen | betting-sharp |

## Verdict
- Prefer **famcls43** over famcls44 on this holdout if choosing among REJECT runs (higher family, same structure failure).
- Structure fix required stronger aux+upsample (**famcls45** aux=0.25 / up=8) — see preserve + KEEP receipts; still **not** BEST.

## Artifacts
- `COMPARE_SUMMARY.json`, `famcls43_accept23_errors.json`, `famcls44_accept23_errors.json`
- Script: `compare_famcls43_44_holdout.py` (same prepare)
