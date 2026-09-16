# Spec 007 — morph43/44 REJECT; residual gold exhausted; BEST=morph40 — ESCALATE

**Authority:** Spec 007 only. `name_gate` false. No Hub. **Labeler authorized.** No invent beyond labeled set.  
**BEST held:** **morph40** — prior fair n=228 `unbind_exact≈0.7368` (ep9). morph36 preserved.

## Status

Warm-only morph41/42 REJECT (0.7149). Data lever morph43 (+51 gold) REJECT (0.9379 < fair 0.9492 n=177). Last gold morph44 (`boogie`) REJECT (0.9432 < fair 0.9489 n=176).  
Post-morph44 residuals: **0** high-conf / **10** prior abstain → **gold exhausted**. See escalate receipt.

## Marks status (2026-09-16)

| mark | status |
|------|--------|
| morph40 PIN BEST | **HIT** (held) |
| morph41 / morph42 warm-only | **REJECT_VS_BEST** |
| morph43 held residual gold | **REJECT_VS_BEST** (0.9379 < 0.9492) |
| morph44 last residual gold | **REJECT_VS_BEST** (0.9432 < 0.9489) |
| Residual high-conf gold | **EXHAUSTED** → **ESCALATE** |
| Ladder ≥0.55 on n=228 | **HIT** (0.7368) |

## Civilian scores

| model | val n | unbind_exact | note |
|-------|------:|-------------:|------|
| **morph40 BEST** | 228 | **0.7368** | PIN |
| morph40 fair morph43 | 177 | **0.9492** | |
| morph43 best | 177 | **0.9379** | REJECT |
| morph40 fair morph44 | 176 | **0.9489** | |
| morph44 best | 176 | **0.9432** | REJECT |

## Next

**ESCALATE** — `receipts/20260916-escalate-residual-gold-exhausted.md`. Do not schedule another warm+force clone on this residual set. Operator picks next family.

## Policy

`name_gate=false`. Labeler authorized. Fair-eval when val changes. No invent beyond labeled set.
