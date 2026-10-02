# HARDEN_V6_SEMANTIC_REPRESENTATION_AND_PREPARE_QUALIFICATION

```text
HARDENING_STATE = V6_SEMANTIC_PIPELINE_HARDENED
QUALIFICATION_READINESS = V6_QUALIFICATION_BLOCKED_QUAL_SURFACE
NEXT_ACTION = BUILD_AND_SEAL_FRESH_V6_QUALIFICATION_SURFACE
RECEIPT = 1ab3274a40198d0a9ac41be68abd0f2da7c75281509115adb8a81aeb17815e93
PACKAGE = a88275837b341b4c549a9c973f5c5190a8f3878be57dffd302e72269d2d560c4
reproduction = SCIENTIFICALLY_EQUIVALENT_REPRODUCTION
DEV = 0.3707
REP = 0.4322
encoder_immutable = True
cold_load_ok = True
round_trip_ok = True
QUAL = sealed / uninspected → NEW_QUAL_REQUIRED
MODEL_WIDE_BEST = UNCHANGED
V6_REPRESENTATION_CANDIDATE = a88275837b341b4c549a9c973f5c5190a8f3878be57dffd302e72269d2d560c4
```

## 1. Hardening state

**`V6_SEMANTIC_PIPELINE_HARDENED`** — selected frozen MS MARCO + nonlinear heads packaged.
Qualification is blocked only by the sealed QUAL surface ontology mismatch.

## 2. Selected encoder identity / hash

| Field | Value |
|---|---|
| tag | `C_MSMARCO` |
| model_id | `sentence-transformers/msmarco-distilbert-base-v4` |
| revision | `b2f66c95aba1481a880479165582020c2b9b64d7` |
| state_hash | `586fe515fa74674a62563cedbf65262fbfe165f9edefed1928029865a12e0a53` |
| file_sha256 | `3083803ab54614d7c0627b19aa2d7070cd4c49116dc8efd6fae3016526a10015` |

## 3. Encoder immutability

`encoder_trainable_parameters = 0`  
pre = post = runtime = `586fe515fa74674a62563cedbf65262fbfe165f9edefed1928029865a12e0a53` → **ok=True**

## 4. Head architecture

Per-axis MLP identical topology: `Linear(768→128) → ReLU → Linear(128→n_labels)`.  
dropout=0, normalization=none, loss=`BCEWithLogitsLoss`, AdamW lr=1e-2, epochs=40, seed=20261001.  
Outputs: domain n=11, function n=4, mediation n=1.

## 5. Ontology / hashes

- ontology_version = `HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL`
- structure = `HIERARCHICAL_MULTI_LABEL`
- label_schema_hash = `d4e76b88d9ff859c62cf0f38c26dbda2a17e04ea81070c5061a20b37e674efbb`
- hierarchy_hash = `18c449b749aae03cd19da7e7d773357801925a55c896ae711a3375183053cf30`
- compatibility_rule_hash = `2e1f1425fd9e60dc02d1ff240922b2d104effebe9906bc69e5972b56dd5d2850`

## 6. Hierarchy constraint hash

`HYPERLEX_V6_HIERARCHY_CONSTRAINTS_V1` sha = `2e51ed0865bc5431b92b94ba0e99ff3c9e4803ffb72e1fb80c5ead8ab839bc1c`  
Rule: `ai_discourse => technology` (force parent after raw heads).

## 7. Thresholds

`V6_THRESHOLD_MANIFEST` status=**FROZEN**, DEV-only from rebase bakeoff (reused exactly).  
domain=[0.25, 0.05, 0.1, 0.1, 0.3, 0.45, 0.2, 0.25, 0.3, 0.45, 0.25]  
function=[0.3, 0.4, 0.2, 0.4]  
mediation=[0.35]

## 8. Reproduction

**`SCIENTIFICALLY_EQUIVALENT_REPRODUCTION`**  
DEV 0.3707 (witness 0.4275); REP 0.4322 (witness 0.4426); post-constraint hierarchy 0.0.

## 9–10. Cold-load / round-trip

cold-load raw/constrained mismatch = 0 / 0  
clean-process round-trip raw/constrained mismatch = 0 / 0

## 11–14. DEV / REP / axes / per-label

See `artifacts/.../metrics.json` and receipt `per_label_metrics`.  
REP axes macro-F1: domain 0.446, function 0.404, mediation 0.391.  
REP micro-F1 0.429, sample-F1 0.331, Jaccard 0.305.

## 15. DEV→REP stability

absolute Δ = -0.0615; relative Δ = -0.1660.

## 16. Low-support labels

Retained: `domain.gambling`, `domain.crypto` (and any TRAIN<40). Not dropped for QUAL odds.

## 17–18. Robustness / source

Source classification = **SOURCE_DEPENDENT** (legacy_gold_family slices; no source tuning).  
Length / cardinality / axis-composition slices in receipt `robustness_slices`.

## 19. Semantic geometry witness

Diagnostic only; encoder frozen so pretrained geometry unchanged (`state_hash` lock).

## 20. Constraint contribution

raw hierarchy violation = 0.0056  
corrected = 3; degraded = 0  
post-constraint violation = 0.0

## 21. Ablation sanity

| System | REP macro-F1 |
|---|---:|
| Selected MS MARCO frozen nonlinear | 0.4322 |
| MPNet frozen nonlinear | 0.3501 |
| BGE zero-shot | 0.2427 |

selected_remains_superior = **True**

## 22. Runtime schema

`hyperlex.classification.v6.semantic_hierarchical_forward.v1`

## 23. Package candidate / hash

`HYPERLEX_V6_SEMANTIC_PIPELINE_PACKAGE_CANDIDATE_V1`  
PACKAGE_SHA256 = `a88275837b341b4c549a9c973f5c5190a8f3878be57dffd302e72269d2d560c4`  
head_bundle_sha = `2a0724b5a22b67523d56b8a0117533e4d4d63bf2f775f78097735f9518b64942` (private weights)

## 24–25. Qualification gates / metric contract

Preregistered before QUAL open:
- system macro-F1 ≥ **0.30** (retention; legacy 0.20 recorded only)
- hierarchy violation ≤ 0.05
- no complete axis collapse (per-axis macro ≥ 0.10)
- frozen error taxonomy + metric list in `qualification_gates.json`

## 26. QUAL metadata compatibility

**`NEW_QUAL_REQUIRED`** — sealed QUAL_001 exposes legacy `family_counts` / gold_family, not hierarchical domain/function/mediation axis gold under `HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL`. Rows not inspected.

## 27. Qualification readiness

**`V6_QUALIFICATION_BLOCKED_QUAL_SURFACE`**

## 28. Candidate pointer

```text
V6_REPRESENTATION_CANDIDATE = a88275837b341b4c549a9c973f5c5190a8f3878be57dffd302e72269d2d560c4
MODEL_WIDE_BEST = UNCHANGED
STAGE_A_BEST = UNCHANGED
V5 pointers = UNCHANGED
```

## 29. Artifacts / receipts

- `artifacts/experiments/HLX-CLASSIFICATION-V6-SEMANTIC-PIPELINE-HARDEN-001/`
- `specs/007-hyperlexical-model/classification-v6-semantic-pipeline-harden-receipt-20261001.json`
- private: `/home/morpheus/hlx-private/classification-v6-semantic-pipeline-harden-20261001/`

## 30. Tests / commits

- `tests/shadow/test_classification_v6_semantic_pipeline_harden.py`
- contracts + Spark runner on branch `cursor/select-001-holdout-admit-41af`

## 31. Next phase-level action

```text
NEXT_ACTION = BUILD_AND_SEAL_FRESH_V6_QUALIFICATION_SURFACE
```
