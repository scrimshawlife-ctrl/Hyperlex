# REVIEW_V6_QUALIFICATION_003_FAILURE

```text
PRIMARY_DIAGNOSIS = MIXED_POSITIVE_SEMANTIC_GENERALIZATION_FAILURE
FUNCTION_FAILURE_MODE = MIXED
POSITIVE_REPRESENTATIVENESS = POSITIVE_REPRESENTATIVENESS_PARTIAL
REPRESENTATION_VS_HEAD = MIXED_GEOMETRY_AND_HEAD
FUNCTION_LEARNABILITY = UNDERREPRESENTED
NONE_GATE_STATUS = NONE_GATE_FROZEN_RETAIN

gate_reject_on_positives = 0.312
final_empty_on_positives = 0.503
post_admission_share_of_empty = 0.379
function_gold n = 33 (REP 151)
function_gate_reject = 0.485
function_admitted_mean_recall = 0.098

NEXT_ACTION = EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION
```

## Positive false rejection

- Positives n=189; gate-reject 59 (31.2%); final-empty 95 (50.3%).
- Of final-empty: 62% gate-induced, **38% empty after admission** → class
  `MOSTLY_POST_ADMISSION_POSITIVE_ERRORS` (not gate-primary).
- Gate-reject concentrated on: has_function 48.5%, long text 41.0%,
  encyclopedic_none_cue 97.1%, single-label 35.8%.
- Wiktionary positives gate-reject only 16.2% — gate is not uniformly hostile
  to all positives.

## FUNCTION failure (REP≈0.223 → QUAL≈0.025)

| label | qual_n | rep_n | gate_rej | adm_recall | head_would_fire | qual_len_p50 | rep_len_p50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| relational_intimacy | 17 | 45 | 0.59 | 0.14 | 0.14 | 500 | 100 |
| conflictive_force | 8 | 33 | 0.50 | 0.25 | 0.00 | 441 | 77 |
| evaluative_stance | 5 | 35 | 0.20 | 0.00 | 0.00 | 248 | 74 |
| memetic_form | 3 | 38 | 0.33 | 0.00 | 0.00 | 238 | 80 |

- Support ratio QUAL/REP function rows = **0.22** (33 vs 151).
- QUAL function length p50 **415** vs REP **82** (severe length shift).
- REP function style = 100% wiktionary; QUAL = 39% wiki_none + 61% wikt.
- Admitted mean recall **0.098**; most admitted heads would not fire.
- Mode = **MIXED** (gate + head + diversity).

## REP_V2 → QUAL positive distribution

- REP positives: n=538, 100% wikt, length p50=83, function prevalence 28%.
- QUAL positives: n=189, 81% wikt / 19% wiki_none, length p50=283,
  function prevalence 17%.
- style L1=0.19, length-bucket L1=0.46 →
  **`POSITIVE_REPRESENTATIVENESS_PARTIAL`** (not global OVERFIT; positive/
  function traffic still under-covered).

## Representation vs head (frozen encoder)

- mean sim function→train centroid: REP 0.242 vs QUAL 0.125 (drop 0.116).
- Gate-rejected function mean sim 0.030 vs admitted 0.215.
- Among admitted with intact geometry (sim ≥ REP p20): miss rate **0.857**.
- Finding: **`MIXED_GEOMETRY_AND_HEAD`** — neighborhoods weaken on operating
  text *and* heads miss even when geometry is intact.

## Function learnability

- Human dual-annotate mean set-Jaccard **0.9993** (stable).
- QUAL function n=33; 3/4 labels support <10; wiki_none share 0.39.
- Class: **`UNDERREPRESENTED`** (not ontology reopen).

## NONE gate

Operating zero-label gates **PASS**. Function loss is not predominantly
gate-induced with intact post-admission recall → **`NONE_GATE_FROZEN_RETAIN`**.
Do not retune ANY_LABEL.

## Rejected micro-fixes

retune_ANY_LABEL · modify_NONE · retrain_encoder · change_ontology ·
another_QUAL_now · use_QUAL_003_for_opt · architecture_bakeoff · seed_sweep.

NONE operating gates remain passed; do not retune ANY_LABEL here.
QUAL-003 stays EVALUATION_SPENT / unused for optimization.
MODEL_WIDE_BEST unchanged. HUB_PUBLISH_AUTHORIZED = false.
Package `8ed1a4d4…`. Review receipt `cf36ef3a…`.
