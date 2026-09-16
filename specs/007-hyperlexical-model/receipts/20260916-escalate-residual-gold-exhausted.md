# ESCALATE — Spec 007 civilian unbind climb blocked (2026-09-16)

**Authority:** Spec 007. `name_gate=false`. Labeler authorized (positional|type_slot only).  
**BEST held:** **morph40** (`unbind_exact≈0.7368` ep9 on prior fair val n=228). morph36 artifacts preserved.

## Why escalate

Goal required: beat morph40 fair on the same surface **and** exhaust high-confidence unlabeled train-ready residual gold — or escalate if blocked.

| attempt | lever | result |
|---------|-------|--------|
| morph41 | warm morph40 only @ mem 0.015 | REJECT (0.7149 < 0.7368 n=228) |
| morph42 | warm morph40 only @ mem **0.3** | REJECT (0.7149 < 0.7368; ~87 min; no wall speedup) |
| morph43 | +51 residual gold (force 186) | REJECT (0.9379 < fair morph40 **0.9492** n=177; ~93 min) |
| morph44 | +1 last residual `boogie` (force 187) | REJECT (0.9432 < fair morph40 **0.9489** n=176; ~93 min) |

Post-morph44 residual dump **n=10**: **0** authorize / **10** prior abstain (wiki/url/empty-slot/etymology/scaffolding). **No high-confidence unlabeled train-ready gold left.**

## Blocked on

1. **Fair gate after gold expand:** promoting residuals removes morph40’s misses from val, so fair morph40 on the new surface rises to ~0.95. Warm morph40 + new gold peaked **0.9379 / 0.9432** — below fair, above prior n=228 BEST score but **not** a same-surface beat.
2. **Gold exhausted:** remaining residuals are prior abstains only; METHOD forbids inventing gold.
3. Warm-clone / mem-fraction levers already failed twice before the data lever.

## Ask operator

Pick a next family (not another warm+force clone on this residual set):

- Operator-directed new gold / SoT expansion beyond civilian residual dumps
- Recipe lever (head-slot / curriculum / LR / last-N) with explicit one-lever card
- Accept morph40 BEST hold and pause civilian unbind climb
- Re-open abstains only with Danny override (not recommended without review)

## Artifacts

- morph43: `receipts/20260916-morph43-40ep-reject-vs-best.md`
- morph44: `receipts/20260916-morph44-40ep-reject-vs-best.md`
- post-residual labels: `receipts/morph44-40ep-boogie-20260916/POST_RESIDUAL_LABEL_COUNTS.json`
- Spark BEST: `~/.hyperlex/models/BEST` → `...-seed-morph40`
