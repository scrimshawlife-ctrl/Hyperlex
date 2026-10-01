# QUALIFY_HYPERLEX_V5_PIPELINE_ON_FRESH_EVALUATION_SURFACE

One-shot qualification of sealed package
`HYPERLEX_V5_STAGE_A_B_V1R2_PACKAGE_V1` on a fresh text-identifiable surface.
No train / retune / index rebuild / V1R2 mutation / reserve reuse / Hub publish.

```text
QUALIFICATION_DISPOSITION = QUALIFICATION_FAIL
QUALIFICATION_ID = HYPERLEX_V5_PIPELINE_QUALIFICATION_001
n_rows = 500
labels = {EVIDENCE_PRESENT: 243, NO_EVIDENCE: 203, UNCERTAIN: 54}
families = 15
false_entry = 0.31527093596059114
PRESENT_recall = 0.5843621399176955
NONE_recall = 0.6847290640394089
UNCERTAIN_recall = 0.0
family_precision = 0.12280701754385964
selective_accuracy = 0.425
RELEASE_ELIGIBLE = false
HUB_PUBLISH_AUTHORIZED = false
evaluation_spent = true (all 500 identities)
RECEIPT = 88ed9fb5566a3ae359328e7eed1b0eb2aefa34acc580f15fd1505b6831d944e2
NEXT_ACTION = REVIEW_V5_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL
```

## Binding (frozen)

| Pin | Value |
|-----|-------|
| pipeline | `HYPERLEX_V5_STAGE_A_B_PIPELINE_V1` |
| package | `HYPERLEX_V5_STAGE_A_B_V1R2_PACKAGE_V1` |
| MODEL_WIDE_BEST | `9fba0f66…` |
| STAGE_A_BEST | `f2b00c5d…` |
| STAGE_B_INDEX | `4febe96e…` |
| dependency_manifest | `c2d19bef…` |
| pipeline_seal | `0e468234…` |
| Stage-A thresholds | relation 0.60 / resolvability 0.75 |
| Stage-B floors | score 0.83 / margin 0.01 |

## Surface seal

| Hash | Value |
|------|-------|
| qualification_rows_sha256 | `7f7cd2a0…` |
| qualification_identity_sha256 | `bacd12ba…` |
| qualification_manifest_sha256 | `99da3d7f…` |
| qualification_seal_sha256 | `fec23f96…` |
| sealed_at | 2026-10-01T08:34:36Z |
| disjointness | PASS (0 overlap vs 16796 blocked) |
| identifiability | PASS (contract V1; MODEL_INPUT=text) |
| composition | PASS (SHORT_ATOM PRESENT shortfall reported) |

## Primary gates (frozen before scoring)

| Gate | Bound | Observed | Pass |
|------|------:|---------:|:----:|
| false_entry_on_NONE | ≤ 0.05 | 0.3153 | no |
| PRESENT recall | ≥ 0.70 | 0.5844 | no |
| NONE recall | ≥ 0.90 | 0.6847 | no |
| family emission precision | ≥ 0.80 | 0.1228 | no |

## Secondary / diagnostics

| Metric | Value |
|--------|------:|
| UNCERTAIN recall | 0.0 |
| selective accuracy | 0.425 |
| family emission coverage | 0.469 |
| family emission recall | 0.058 |
| top1 family accuracy (admitted PRESENT) | 0.099 |
| top2 family accuracy (admitted PRESENT) | 0.197 |
| FAMILY / AMBIGUOUS / ABSTAIN / NO_EVIDENCE | 114 / 45 / 95 / 246 |
| overall abstention rate | 0.28 |
| SHORT_ATOM NONE support | 43 (≥40) |
| SHORT_ATOM NONE false-entry | 0.0 |
| SHORT_ATOM PRESENT support | 0 (target 30; shortfall — not text-identifiable) |
| domain-irrelevant NONE | not supported (n=0) |
| OBSERVED share | 1.0 |
| STAGE_A_FALSE_ENTRY / STAGE_B_WRONG_FAMILY / COMPOUND | 63 / 37 / 0 |

## Known limitations (unchanged)

```text
DOMAIN_IRRELEVANT_GENERALIZATION = NOT_ESTABLISHED
SHORT_ATOM_POSITIVE_GENERALIZATION = LOW_SUPPORT
CONTEXT_DEPENDENT_GOLD = OUTSIDE_CURRENT_TEXT_ONLY_STAGE_A_CONTRACT
```

## Artifacts

- Private (Spark): `/home/morpheus/hlx-private/classification-v5-pipeline-qualification-001-20261001/`
- Repo: `artifacts/experiments/HLX-CLASSIFICATION-V5-PIPELINE-QUALIFICATION-001/`
- Receipt JSON: `specs/007-hyperlexical-model/classification-v5-pipeline-qualification-receipt-20261001.json`
