# HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION

```text
OUTCOME     = V6_CORE_PRODUCT_HARDENED
NEXT_ACTION = BUILD_AND_SEAL_FRESH_V6_CORE_QUALIFICATION_SURFACE
PACKAGE_ID  = HYPERLEX_V6_CORE_PRODUCT_PACKAGE_V1
PACKAGE_SHA256 = 035e1b7e21e97ed36f79750f1f643262540fba1546f488af2a0af04e8a7c1605
RECEIPT     = 2c84712af4008a1c9e8ba0cd1ebca2b1337699df2f1cb683633a6f0a06bf98f4
QUAL_CORE_ID = HYPERLEX_V6_CORE_QUALIFICATION_001 (PREPARED_NOT_SEALED)
POINTER_ID  = V6_CORE_PRODUCT_CANDIDATE
RELEASE_ELIGIBLE = true
```

## Final core contract

```text
CORE_REQUIRED =
  evidence_gate
  DOMAIN
  MEDIATION
FUNCTION =
  OPTIONAL_BEST_EFFORT
  reporting = ADVISORY_ONLY / NON_BLOCKING
memetic_form =
  RESEARCH_ONLY
contextual function enrichment =
  PARALLEL_RESEARCH_TRACK
```

Required outputs: `evidence_gate`, `domain`, `mediation`.  
Optional outputs: `function_best_effort` (metadata only; never blocks release/QUAL).  
Research-only: `function.memetic_form`.

Flow: text → frozen encoder → ANY_LABEL gate → (empty | DOMAIN+MEDIATION) → hierarchy constraints → core multi-label; optional FUNCTION advisory attached without affecting pass/fail.

## Package / immutability

Cold-loaded frozen operating-pipeline package (encoder, NONE gate, DOMAIN/MEDIATION heads, thresholds, ontology, hierarchy rules). No retrain; no ontology change; no QUAL-002/003 rescore.

```text
cold_load_ok = true
round_trip_ok = true
encoder_immutable = true
NONE_GATE_MUTATED = false
DOMAIN_HEAD_MUTATED = false
MEDIATION_HEAD_MUTATED = false
ONTOLOGY_MUTATED = false
FUNCTION_REQUIRED = false
MODEL_WIDE_BEST_MUTATED = false
```

Parent product disposition receipt prefix: `c488a39d…` (`FUNCTION_RETAIN_OPTIONAL`).

## DEV_V3 / REP_V3 replay (reduced-core eval)

### REP_V3 (release witness; gates bind here)

```text
core system macro-F1              = 0.3484
DOMAIN macro / micro-F1           = 0.3548 / 0.3740
MEDIATION macro / micro-F1        = 0.3421 / 0.3421
zero-label FP                     = 0.0774
zero-label exact rejection        = 0.9226
mean predicted labels on zero-gold = 0.1219
sample-F1                         = 0.6992
Jaccard                           = 0.6912
hierarchy violation (post-corr)   = 0.0000
hierarchy pre-correction rate     = 0.001985
FUNCTION advisory macro-F1        = 0.2964  (ADVISORY_ONLY / NON_BLOCKING)
rep_gates_pass                    = true
```

### DEV_V3 (selection surface; not release-binding)

```text
core system macro-F1              = 0.2063
DOMAIN macro / micro-F1           = 0.2557 / 0.2721
MEDIATION macro / micro-F1        = 0.1569 / 0.1569
zero-label FP                     = 0.0836
zero-label exact rejection        = 0.9164
mean predicted labels on zero-gold = 0.1222
sample-F1                         = 0.6691
Jaccard                           = 0.6636
hierarchy violation (post-corr)   = 0.0000
FUNCTION advisory macro-F1        = 0.2740  (ADVISORY_ONLY / NON_BLOCKING)
dev_gates_pass                    = false  (expected; selection surface weaker)
```

Zero-label core accounting ignores FUNCTION predictions. Hierarchy post-correction rate is the gate metric; pre-correction ≈0.002 matches the prior product witness.

## Frozen core qualification gates

Preregistered before any fresh QUAL surface opens. FUNCTION excluded from pass/fail.

```text
core_system_macro_f1_min              = 0.30
DOMAIN_macro_f1_min                   = 0.28
MEDIATION_macro_f1_min                = 0.28
zero_label_false_positive_rate_max    = 0.20
zero_label_exact_rejection_min        = 0.80
mean_predicted_labels_on_zero_gold_max = 1.0
hierarchy_violation_max               = 0.02
FUNCTION_in_pass_fail                 = false
FUNCTION_role                         = ADVISORY_ONLY_NON_BLOCKING
QUAL_CORE_id                          = HYPERLEX_V6_CORE_QUALIFICATION_001
QUAL_002 / QUAL_003                   = EVALUATION_SPENT (reuse forbidden)
scoring_authorized                    = false
```

## FUNCTION advisory handling

```text
role = ADVISORY_ONLY
blocking = false
excluded_from_core_system_macro = true
excluded_from_qualification_pass_fail = true
excluded_from_zero_label_core_accounting = true
memetic_form = RESEARCH_ONLY
```

Outputs remain available as optional metadata when the head is present; they never affect core package pass/fail, release eligibility, or axis-collapse gates.

## Artifacts / tests / commit

- Contract: `scripts/shadow/hyperlexical/classification_v6_core_product_harden.py`
- Runner: `scripts/spark/run_classification_v6_core_product_harden.py`
- CPU tests: `tests/shadow/test_classification_v6_core_product_harden.py`
- Public: `artifacts/experiments/HLX-CLASSIFICATION-V6-CORE-PRODUCT-HARDEN-001/`
- Spec receipt: `specs/007-hyperlexical-model/classification-v6-core-product-harden-receipt-20261002.json`
- Private: `~/hlx-private/classification-v6-core-product-harden-20261002/`

## Next phase-level action

```text
NEXT_ACTION = BUILD_AND_SEAL_FRESH_V6_CORE_QUALIFICATION_SURFACE
```

Do not reuse QUAL-002 or QUAL-003. Optional FUNCTION research track may continue in parallel without blocking the core.
