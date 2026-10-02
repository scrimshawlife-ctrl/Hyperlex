# BUILD_SEAL_EXECUTE_V6_CORE_QUALIFICATION_AND_RELEASE_DECISION

```text
QUALIFICATION_DISPOSITION = V6_CORE_QUALIFICATION_FAIL
RELEASE_OUTCOME           = V6_CORE_RELEASE_CANDIDATE_REJECTED
RELEASE_ELIGIBLE          = false
NEXT_ACTION               = REVIEW_V6_CORE_QUALIFICATION_FAILURE
failure_class             = MIXED_CORE_GENERALIZATION_FAILURE
HUB_PUBLISH_AUTHORIZED    = false
```

## 1–3. Qualification surface state / ID / distribution

```text
QUALIFICATION_ID   = HYPERLEX_V6_CORE_QUALIFICATION_001
SURFACE_STATE      = V6_CORE_QUALIFICATION_SURFACE_SEALED
QUALIFICATION_STATE (pre-score) = SEALED_UNSCORED
QUALIFICATION_STATE (post)      = EVALUATION_SPENT
n_rows             = 761
zero_label_share   = 0.623
no_evidence_share  = 0.601
active_domain_labels = 11
mediation.internet_register support = 27
cardinality 0/1/2/3+ = 474 / 197 / 76 / 14
length short/med/long ≈ 0 / 50 / 711
max_source_family_share ≈ 0.22
forbidden_overlap = 0
```

Fresh NATURAL/OBSERVED holdout. Disjoint from TRAIN/DEV/REP V3 and spent QUAL-001/002/003 evaluation rows. FUNCTION not used for inclusion or balancing.

## 4–6. Annotation / identifiability / disjointness

```text
n_annotators = 2 (independent dual protocol + adjudication)
mean_core_jaccard (domain+mediation) = 1.000
mean_set_jaccard (incl. advisory function) = 0.999
stage_kappa = 1.000
n_adjudicated_disagreement = 21
stability = QUALIFICATION_GOLD_STABLE
identifiability_pass = true
forbidden_overlap = 0
```

## 7. Seal / hash identities

```text
seal_sha256              = 1c36342ea3dcc68e6b70befebf678e378dd56655b8129fd7125f9c421f7c8c27
PACKAGE_SHA256 (bound)   = 035e1b7e21e97ed36f79750f1f643262540fba1546f488af2a0af04e8a7c1605
PACKAGE_ID               = HYPERLEX_V6_CORE_PRODUCT_PACKAGE_V1
execute receipt          = 20fcbda1dd6e8794c7ab7ca61213b6995768f53c0857a4a19b83dc7aa1f220b1
surface receipt          = 43022090bf09a5a60a701fdba1496a1e974bcaaa04d012f6050b900d243b5cb9
```

## 8–9. Package preflight / executions

```text
preflight_ok = true
cold_load_ok = true
round_trip_ok = true
encoder_trainable_parameters = 0
qualification_model_executions = 1
evaluation_spent = true
```

Exact package `035e1b7e…` cold-loaded; no substitute package; no retries; no threshold/head changes.

## 10–15. Core metrics (single execution)

```text
core system macro-F1              = 0.0944
DOMAIN   macro / micro-F1         = 0.1422 / 0.2099
MEDIATION macro / micro-F1        = 0.0465 / 0.0465
zero-label FP                     = 0.2131
zero-label exact rejection        = 0.7869
mean predicted labels on zero-gold = 0.4557
sample-F1 / Jaccard               = 0.5558 / 0.5426
raw hierarchy violation           = 0.0131
post-constraint hierarchy viol    = 0.0000
FUNCTION advisory macro-F1        = 0.0000  (ADVISORY_ONLY / NON_BLOCKING)
```

## 16. REP_V3 → QUAL retention

```text
REP core = 0.3484 → QUAL core = 0.0944
absolute_degradation = 0.2541
relative_retention   = 0.271
band                 = SEVERE_GENERALIZATION_DROP
DOMAIN retention     = 0.1422 / 0.3548 ≈ 0.401
MEDIATION retention  = 0.0465 / 0.3421 ≈ 0.136
NONE exact retention = 0.7869 / 0.9226 ≈ 0.853
```

Retention is diagnostic only (not a hard gate).

## 17. Frozen gate table (unchanged after results)

| gate | threshold | value | pass |
|---|---:|---:|:---:|
| core_system_macro_f1 | ≥ 0.30 | 0.0944 | no |
| DOMAIN_macro_f1 | ≥ 0.28 | 0.1422 | no |
| MEDIATION_macro_f1 | ≥ 0.28 | 0.0465 | no |
| zero_label_false_positive_rate | ≤ 0.20 | 0.2131 | no |
| zero_label_exact_rejection | ≥ 0.80 | 0.7869 | no |
| hierarchy_violation | ≤ 0.02 | 0.0000 | yes |
| mean_predicted_labels_on_zero_gold | ≤ 1.0 | 0.4557 | yes |
| FUNCTION | n/a | advisory | excluded |

## 18–20. Disposition / release eligibility / RC state

```text
QUALIFICATION_DISPOSITION = V6_CORE_QUALIFICATION_FAIL
RELEASE_OUTCOME           = V6_CORE_RELEASE_CANDIDATE_REJECTED
RELEASE_ELIGIBLE          = false
V6_CORE_RELEASE_CANDIDATE pointer = not created
failure_class = MIXED_CORE_GENERALIZATION_FAILURE
```

No retrain. No automatic modeling cycle. Gates not lowered.

## 21. Required vs optional runtime outputs

```text
required: evidence_decision, domain_labels[], mediation_labels[]
optional: function_labels[]  # advisory only
diagnostics: raw scores, constraint adjustments, artifact identities
```

## 22–23. Artifacts / limitations

- Surface: `artifacts/experiments/HLX-CLASSIFICATION-V6-CORE-QUALIFICATION-SURFACE-001/`
- Execute: `artifacts/experiments/HLX-CLASSIFICATION-V6-CORE-QUALIFICATION-EXECUTE-001/`
- Specs: `classification-v6-core-qualification-{surface,execute}-20261002.md`
- Private: `~/hlx-private/classification-v6-core-qualification-{001,execute-001}-20261002/`

Limitations retained:

- FUNCTION is not release-qualified as a required capability
- memetic_form is research-only
- contextual pragmatic inference is outside core text-only scope
- qualification evidence applies to the final core contract only
- HUB_PUBLISH_AUTHORIZED remains false

## 24–25. Tests / commits

- CPU: `tests/shadow/test_classification_v6_core_qualification.py`
- Contract: `scripts/shadow/hyperlexical/classification_v6_core_qualification.py`
- Surface runner / execute runner under `scripts/spark/`

## 26–27. Remaining blockers / next action

```text
blockers = MIXED_CORE_GENERALIZATION_FAILURE on fresh holdout
           (DOMAIN + MEDIATION + NONE floors all missed; SEVERE_GENERALIZATION_DROP vs REP_V3)
NEXT_ACTION = REVIEW_V6_CORE_QUALIFICATION_FAILURE
```

Do not reuse this spent QUAL surface for training, calibration, threshold tuning, or model selection.
