# RETRY_PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE

Component promotion of the REPRO-001 complete checkpoint to `STAGE_A_BEST`.

## Result

```text
STAGE_A_PROMOTION = APPLIED
STAGE_A_BEST = f2b00c5dfeb087288fc1686c901fbc8b52a8ba7a7b51cb83ff038656f93617fa
PREVIOUS_STAGE_A_BEST = cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c
MODEL_WIDE_BEST = 9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6
MODEL_WIDE_BEST_MUTATED = false
PROMOTION_LOADABLE = true
RESERVE_CONSUMED = false
STAGE_A_PROMOTION_RECEIPT_SHA256 = 9541664c87b27e56d25171579f2ef0b5810a1ebcbbc023298ce2919749f9b370
```

## Candidate

- Promotion candidate: `f2b00c5d…` (selected epoch 11, selection_score 0.9673)
- Factorized heads cold-loadable: `n_keys = 16`
- Historical incomplete `8b2de447…` frozen as scientific reference / non-promotable packaging artifact / superseded by reproduction

## Preflight

All fail-closed gates passed: `SETTLED_PASS`,
`SCIENTIFICALLY_EQUIVALENT_REPRODUCTION`, REPRO experiment identity,
checkpoint/epoch/score/thresholds, V1R2 / annotation / exclusion pins,
`MODEL_WIDE_BEST = 9fba0f66…`, `CURRENT_STAGE_A_BEST = cd2829c1…`.

## Canonical load path

```text
ModernBERT trunk
  → MODEL_WIDE_BEST 9fba0f66…
  → STAGE_A_BEST f2b00c5d… (layers 20/21 + factorized heads)
  → relation_head / resolvability_head
```

`parent_model_wide_best = 9fba0f66…` (mismatch fails closed).

## Inference / Stage B

```text
if P(RESOLVABLE) < 0.75 → UNCERTAIN
elif P(EVIDENCE_RELATION_PRESENT) >= 0.60 → EVIDENCE_PRESENT
else → NO_EVIDENCE
```

Stage-B entry unchanged: PRESENT → permit; NONE → stop; UNCERTAIN → abstain.
Stage-B index/floors/ontology not modified.

## Post-promotion verification

| Check | Result |
| --- | --- |
| Cold-load | pass (`n_keys=16`, both heads) |
| V1R2 replay | pass (`ce26435e50a34602fbafd7e0504ce9b9931b986ff3b6a1ec8612fab244da4a48`) |
| false_entry | 0.03357 |
| PRESENT recall | 0.951 |
| NONE recall | 0.965 |
| SHORT_ATOM NONE relation FPR | 0.013157894736842105 |
| Round-trip decisions | mismatch_count = 0 |
| Round-trip logits | max_abs_delta = 0.0 |

## Lineage

```text
original scientific experiment (…-001)
  → original SETTLED_PASS (4a7d565c…)
  → packaging failure (8b2de447… encoder-only)
  → repair impossible (6b041947…)
  → authorized reproduction (09f3d456…)
  → scientifically equivalent SETTLED_PASS (8b8585a8…)
  → complete promotion-loadable checkpoint (f2b00c5d…)
  → STAGE_A_BEST applied
```

## Known limitations (unchanged)

- `DOMAIN_IRRELEVANT_GENERALIZATION = NOT_ESTABLISHED`
- `SHORT_ATOM_POSITIVE_GENERALIZATION = LOW_SUPPORT`
- `CONTEXT_DEPENDENT_GOLD = OUTSIDE_CURRENT_TEXT_ONLY_STAGE_A_CONTRACT`

Central conclusion preserved: gold/input identifiability repair, not
architecture escalation, resolved the dominant Stage-A failure.

## Reserve

`HYPERLEX_V5_PROMOTION_RESERVE_001` remains `SPENT`. Not scored.

## Next

```text
NEXT_ACTION = FREEZE_V5_STAGE_A_CANONICAL_AND_UPDATE_DOWNSTREAM_PROVENANCE
```
