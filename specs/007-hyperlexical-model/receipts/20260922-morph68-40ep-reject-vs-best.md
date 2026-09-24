# morph68 REJECT_VS_BEST — residual gold (2026-09-22)

`name_gate=false`. Exclusive mem 0.3. Qwen stopped+disabled.

## Gate

| | |
|--|--|
| best | **0.9695431472081218** (ep27, 191/197) |
| fair morph65 | **0.9695431472081218** (191/197) |
| decision | **REJECT_VS_BEST** (tie — PIN needs strictly greater) |
| E2 trunk-forward | **PASS** (`unbind_exact=1.0`) |
| container | `hlx-train-morph68-1790047095` exit 0 |
| BEST | stays **morph65** |

## Knob

morph67 residual AUTHORIZE force/hard expand (166/208). Warm morph65. UPSAMPLE=8 + SECOND_SLOT=2 held. Hang-fix `loop.py` (drop per-step `.cpu()` sync).

## Residuals (best epoch)

themes: `partial_slot_miss` 6, `type_slot_token_miss` 3. METHOD label AUTHORIZE **0** / ABSTAIN **6** (scaffolding). Do not burn force_added=0.

## Next

morph69: unused METHOD AUTHORIZE morph43/morph50 gold **force_added=26**. Fair morph65 **0.9649122807017544** n=171. See `receipts/20260922-morph69-unused-method-gold.md`.
