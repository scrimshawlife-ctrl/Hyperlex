# Post-rc1 HOLD sync — 2026-09-26

**Lane:** SHADOW / advisory · docs only · no train · no Hub · no T13  
**Canonical remote:** `scrimshawlife-ctrl/Hyperlex` @ sync time `efbb30b` (main tip at agent start)

## OBSERVED

1. Spark rc1 decision is **REJECT** (`receipts/rc1-result-20260924/OPERATOR-CARD.md`). BEST remains `seed-morph78`. `name_gate` unchanged (true for morph78 only, A6).
2. Holdout `holdout-manifest-rc1.json` is **`SCORED_SPENT`**. Selection-surface audit published **`NO_RULE_MATCH` / HOLD**.
3. Operator docs on main still said “rc1 … launching” in `NEXT_MOVES_007.md` after the reject receipts landed — stale.
4. Open PR #105 (infer path) is superseded by merged #106 on main (`mergeable_state: dirty`).
5. Org mirror `Zero-State-LLC/Hyperlex` HEAD `49196d9` remains behind personal main; do not train from it.

## Operator surface after this sync

| Machine | State |
|---|---|
| TRAIN | `BEST_PINNED(seed-morph78)` · soft_ceiling spent · rc1 not RC |
| NAME | `NAME_GATE_APPROVED(seed-morph78)` |
| PUBLISH | `LOCAL_ONLY` · audit: do not publish |
| INTEGRATION | `SHADOW` · T13 not authorized |

## Default next

**HOLD morph78.** Separate Danny sentences only for Hub, T13, D3, or a new climb (new holdout + authorize card).

## Hard nos (unchanged)

Hub upload · extend `name_gate` beyond morph78 · re-score spent rc1 holdout for selection · train from org mirror · empty morph acquires · Qwen re-enable without yes.
