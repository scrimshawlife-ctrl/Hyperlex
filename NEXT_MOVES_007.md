# Spec 007 — status after second-slot family + morph34 longer climb

**Authority:** Spec 007 only. `name_gate` stays false. No Hub. No invented OBSERVED gold.
**BEST:** `seed-morph19` — `unbind_exact≈0.4545`. Ladder **0.45 cleared**; **0.55 not reached**.

## Why prior waits looked idle

Spark morph trains take ~15–25 min on a co-tenant GPU. Long polls wait on Docker train, not local idle sleep.

## Second-slot family + longer climb

| Morph | Lever | exact | vs BEST | E2 | Decision |
|------:|-------|------:|--------:|----|----------|
| 19 | head_slot=2 | **0.4545** | — | PASS | **BEST** |
| 31 | second_slot=2 | 0.4270 | −0.028 | PASS | REJECT |
| 32 | second_slot=1.5 | 0.4353 | −0.019 | PASS | REJECT |
| 33 | 2-epoch bounded seed | ≈0.047 | far below | PASS (probe) | seed only |
| 34 | morph19 envelope @ 6ep (no new lever) | 0.3829 | −0.0716 | PASS (probe) | REJECT |

Private receipt: `~/hlx-private/p1-spark-morph34-climb-20260913/SMOKE_SUMMARY.json`. BEST path + mtime unchanged.

Harness PR: https://github.com/scrimshawlife-ctrl/Hyperlex/pull/61 (draft)

## Exhausted on morph19 envelope

- Weight knobs (22–24)
- Schedule/capacity (25–29)
- Hard-atom set expand (30)
- Second-slot CE (31–32)
- 6-epoch envelope replication (34)

## Next (Danny)

Need a lever beyond current env/loss-index knobs — e.g. SoT OBSERVED gold policy for `partial_slot_miss`, or a loss/structure change not exposed as a single slot weight. Human structure gold spans remain the ordered gate (first-25 worksheet). Hold further envelope-only morphs.
