# REBASE_V6_ON_STRONGER_PRETRAINED_SEMANTIC_ENCODER

```text
REBASE_STATE = V6_REPRESENTATION_REBASE_ADVANCE
NEXT_ACTION = HARDEN_V6_SEMANTIC_REPRESENTATION_AND_PREPARE_QUALIFICATION
RECEIPT = eb4851e5c854641b97f7cb27d3f331386c4f1b4c30754e7340239de31bdb7c5b
selected = FROZEN_NONLINEAR__C_MSMARCO
MINIMUM_ADVANCE = True
REPRESENTATION_IMPROVEMENT = True
MPNet_witness = 0.205558
BGE_zero_shot_REP = 0.242726
selected_REP = 0.442602
MODEL_WIDE_BEST = UNCHANGED historical control
QUAL = sealed / uninspected
```

## 1. Rebase state

**`V6_REPRESENTATION_REBASE_ADVANCE`** — frozen nonlinear heads on a semantic embedding 
clear locked floors and beat the 0.206 MPNet witness. No production promotion.

## 2. Semantic encoders tested

| Tag | Model | Role |
|---|---|---|
| A_MPNET | `sentence-transformers/all-mpnet-base-v2` | frozen witness / semantic family |
| B_BGE_BASE | `BAAI/bge-base-en-v1.5` | modern general sentence embedding |
| C_MSMARCO | `sentence-transformers/msmarco-distilbert-base-v4` | retrieval-oriented |

ModernBERT `MODEL_WIDE_BEST` (`9fba0f66…`) remains historical control only; not an init source.

## 3. Zero-shot results (DEV-thresholded, short definitions)

| Encoder | REP system | domain | function | mediation |
|---|---:|---:|---:|---:|
| MPNet short | 0.2056 | 0.2233 | 0.1777 | 0.1212 |
| BGE short | 0.2427 | 0.2640 | 0.1903 | 0.2188 |
| MSMARCO short | 0.1807 | 0.1708 | 0.2001 | 0.2119 |
| MPNet full contract | 0.1521 | 0.1501 | 0.1488 | 0.1867 |
| BGE full contract | 0.1675 | 0.1532 | 0.1794 | 0.2769 |
| MSMARCO full contract | 0.1363 | 0.1258 | 0.1503 | 0.1947 |

Short definitions beat full boundary contracts for all three encoders. 
**BGE short zero-shot 0.243 already exceeds the MPNet 0.206 witness.**

## 4. Axis-level results

Zero-shot axis-best encoders: `{'domain': {'encoder': 'B_BGE_BASE', 'macro_f1': 0.26396400628512157}, 'function': {'encoder': 'C_MSMARCO', 'macro_f1': 0.2001344479247944}, 'mediation': {'encoder': 'B_BGE_BASE', 'macro_f1': 0.21875}}` → **`AXIS_SPECIFIC_ENCODERS_SUPPORTED`**.
Material enough to record, but **not** enough to authorize separate encoder stacks; 
axis-specific *projections/heads* on one encoder are sufficient.

## 5. Label-description representation

Fixed pair only: short definition vs full boundary contract. 
Short wins (MPNet 0.206 vs 0.152; BGE 0.243 vs 0.167). 
No further prompt search.

## 6–8. Frozen heads and calibrated similarity (REP system macro-F1)

| Candidate | REP | DEV | gap | domain | function | mediation |
|---|---:|---:|---:|---:|---:|---:|
| `FROZEN_NONLINEAR__C_MSMARCO` | 0.4426 | 0.4275 | -0.0151 | 0.457 | 0.430 | 0.333 |
| `FROZEN_NONLINEAR__A_MPNET` | 0.3745 | 0.4552 | 0.0807 | 0.363 | 0.395 | 0.423 |
| `FROZEN_NONLINEAR__B_BGE_BASE` | 0.3356 | 0.3376 | 0.0021 | 0.285 | 0.452 | 0.427 |
| `AXIS_PROJ__A_MPNET` | 0.2679 | 0.3069 | 0.0389 | 0.229 | 0.338 | 0.419 |
| `ZERO_SHOT__B_BGE_BASE__short` | 0.2427 | 0.2692 | 0.0265 | 0.264 | 0.190 | 0.219 |
| `AXIS_PROJ__C_MSMARCO` | 0.2357 | 0.2463 | 0.0106 | 0.202 | 0.314 | 0.293 |
| `FROZEN_LINEAR__B_BGE_BASE` | 0.2136 | 0.1951 | -0.0185 | 0.211 | 0.201 | 0.289 |
| `PEFT_ADAPTER__B_BGE_BASE` | 0.2134 | 0.1997 | -0.0137 | 0.210 | 0.201 | 0.296 |
| `ZERO_SHOT__A_MPNET__short` | 0.2056 | 0.3029 | 0.0974 | 0.223 | 0.178 | 0.121 |
| `PEFT_ADAPTER__A_MPNET` | 0.1931 | 0.2425 | 0.0494 | 0.189 | 0.179 | 0.295 |
| `FROZEN_LINEAR__A_MPNET` | 0.1924 | 0.2403 | 0.0479 | 0.189 | 0.182 | 0.276 |
| `ZERO_SHOT__C_MSMARCO__short` | 0.1807 | 0.2268 | 0.0461 | 0.171 | 0.200 | 0.212 |
| `FROZEN_LINEAR__C_MSMARCO` | 0.1706 | 0.1995 | 0.0289 | 0.179 | 0.159 | 0.122 |
| `ZERO_SHOT__B_BGE_BASE__full` | 0.1675 | 0.2210 | 0.0536 | 0.153 | 0.179 | 0.277 |
| `PEFT_ADAPTER__C_MSMARCO` | 0.1636 | 0.2010 | 0.0374 | 0.173 | 0.147 | 0.128 |
| `ZERO_SHOT__A_MPNET__full` | 0.1521 | 0.1871 | 0.0350 | 0.150 | 0.149 | 0.187 |
| `ZERO_SHOT__C_MSMARCO__full` | 0.1363 | 0.2191 | 0.0828 | 0.126 | 0.150 | 0.195 |
| `AXIS_PROJ__B_BGE_BASE` | 0.1293 | 0.1308 | 0.0015 | 0.120 | 0.127 | 0.235 |
| `CALIBRATED_SIM__C_MSMARCO` | 0.1271 | 0.1295 | 0.0024 | 0.123 | 0.127 | 0.174 |
| `CALIBRATED_SIM__A_MPNET` | 0.1267 | 0.1300 | 0.0032 | 0.122 | 0.133 | 0.150 |
| `CALIBRATED_SIM__B_BGE_BASE` | 0.1240 | 0.1236 | -0.0004 | 0.120 | 0.127 | 0.150 |

Calibrated similarity **hurt** vs raw cosine (≈0.12). 
Frozen **nonlinear** heads are the first trained systems that clearly add value.

## 9. PEFT result

Embedding-space residual adapter + linear heads ≈ frozen linear (no extra lift). 
Geometry `SEMANTIC_GEOMETRY_PRESERVED` (cos=1.00, NN retention=1.00) — adapter 
did not move embeddings. Full fine-tune not justified.

## 10. Shared vs axis-specific projections

Axis-specific linear projections help MPNet (0.268) vs shared linear (0.192) 
but lose to shared frozen nonlinear heads. Separate encoder stacks **not** authorized.

## 11–12. Drift / geometry

PEFT left pretrained neighborhoods intact. Nonlinear heads train only on frozen 
vectors (no encoder update) → geometry of the encoder is preserved by construction.

## 13–15. DEV/REP, gaps, hierarchy (selected + MPNet nonlinear + BGE zs)

- `FROZEN_NONLINEAR__C_MSMARCO`: DEV=0.4275 REP=0.4426 gap=-0.0151; raw_hier=0.0037593984962406013 post=0.0
- `FROZEN_NONLINEAR__A_MPNET`: DEV=0.4552 REP=0.3745 gap=0.0807; raw_hier=0.0 post=0.0
- `ZERO_SHOT__B_BGE_BASE__short`: DEV=0.2692 REP=0.2427 gap=0.0265; raw_hier=0.0018796992481203006 post=0.0

No V5-style DEV overfit. Post-constraint hierarchy violation = 0.0 for selected.

## 16. Per-label (selected MSMARCO nonlinear, REP)

| Label | supp | P | R | F1 | strength |
|---|---:|---:|---:|---:|---|
| `domain.crypto` | 3 | 0.667 | 0.667 | 0.667 | LOW_SUPPORT |
| `domain.entertainment` | 35 | 0.611 | 0.314 | 0.415 | STRONG_LABEL |
| `domain.fashion` | 40 | 0.750 | 0.225 | 0.346 | STABLE_LABEL |
| `domain.gambling` | 5 | 0.333 | 0.600 | 0.429 | LOW_SUPPORT |
| `domain.gaming` | 47 | 0.421 | 0.170 | 0.242 | STABLE_LABEL |
| `domain.politics` | 28 | 0.536 | 0.536 | 0.536 | STRONG_LABEL |
| `domain.spiritual` | 41 | 0.600 | 0.366 | 0.455 | STRONG_LABEL |
| `domain.sports` | 37 | 0.222 | 0.541 | 0.315 | STABLE_LABEL |
| `domain.technology` | 79 | 0.549 | 0.570 | 0.559 | STRONG_LABEL |
| `domain.technology.ai_discourse` | 41 | 0.527 | 0.707 | 0.604 | STRONG_LABEL |
| `domain.workplace` | 35 | 0.538 | 0.400 | 0.459 | STRONG_LABEL |
| `function.conflictive_force` | 31 | 0.462 | 0.581 | 0.514 | STRONG_LABEL |
| `function.evaluative_stance` | 34 | 0.452 | 0.412 | 0.431 | STRONG_LABEL |
| `function.memetic_form` | 38 | 0.643 | 0.237 | 0.346 | STABLE_LABEL |
| `function.relational_intimacy` | 42 | 0.609 | 0.333 | 0.431 | STRONG_LABEL |
| `mediation.internet_register` | 43 | 0.319 | 0.349 | 0.333 | STABLE_LABEL |

No material axis collapse. Gambling/crypto remain LOW_SUPPORT, not DEAD on the selected model.

## 17. Error decomposition vs MPNet zero-shot

MPNet nonlinear vs MPNet zs: `{'axis_confusion_moved': 0, 'fixed_fn': 129, 'fixed_fp': 1974, 'fn_a': 355, 'fn_b': 311, 'fp_a': 2173, 'fp_b': 533, 'new_fn': 85, 'new_fp': 334}`
Available: `['AXIS_PROJ__A_MPNET', 'CALIBRATED_SIM__A_MPNET', 'FROZEN_LINEAR__A_MPNET', 'FROZEN_NONLINEAR__A_MPNET', 'PEFT_ADAPTER__A_MPNET']`
`AXIS_PROJ__A_MPNET`: {'axis_confusion_moved': 0, 'fixed_fn': 141, 'fixed_fp': 1543, 'fn_a': 355, 'fn_b': 292, 'fp_a': 2173, 'fp_b': 1368, 'new_fn': 78, 'new_fp': 738}
Trained heads fix a large FN/FP mass rather than only swapping errors.

## 18. vs ModernBERT zero-shot 0.162

Selected 0.443 and BGE zs 0.243 both dominate 0.162. Representation family, not heads-on-ModernBERT, was the missing piece.

## 19. vs MPNet witness 0.206

- BGE zero-shot: **0.243** (read-only improvement)
- MPNet frozen nonlinear: **0.374**
- MSMARCO frozen nonlinear (selected): **0.443**
Training on frozen semantic embeddings **does** add value when the prior is a sentence/retrieval encoder.

## 20. Advancement gates

- REP ≥ 0.20: **PASS** (0.443)
- hierarchy ≤ 0.05: **PASS** (0.0 post-constraint)
- axis floors ≥ 0.10: **PASS** (dom 0.457 / fun 0.430 / med 0.333)
- trained > 0.206 witness: **PASS** (`REPRESENTATION_IMPROVEMENT`)
- floors not lowered; QUAL unused; MODEL_WIDE_BEST unmoved

## 21. Selected V6 representation candidate

`FROZEN_NONLINEAR__C_MSMARCO` — frozen `msmarco-distilbert-base-v4` embeddings + 
shallow nonlinear multi-label heads per axis + DEV-only thresholds + deterministic hierarchy.

Conservative semantic-family alternative: `FROZEN_NONLINEAR__A_MPNET` (REP 0.374) 
or read-only `ZERO_SHOT__B_BGE_BASE__short` (REP 0.243).

## 22. V6 pointer state

`{'MODEL_WIDE_BEST': '9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6', 'MODEL_WIDE_BEST_MUTATED': False, 'MODEL_WIDE_BEST_ROLE': 'HISTORICAL_CONTROL_REPRESENTATION', 'V6_REPRESENTATION_CANDIDATE': {'encoder': 'C_MSMARCO', 'formulation': 'frozen_embedding_nonlinear_heads', 'id': 'FROZEN_NONLINEAR__C_MSMARCO', 'status': 'CANDIDATE_NOT_PROMOTED'}}`
No production promotion. V5 / MODEL_WIDE_BEST / STAGE_A_BEST unchanged.

## 23. Artifacts / receipts

- Private: `/home/morpheus/hlx-private/classification-v6-representation-rebase-20261001/`
- Repo: `artifacts/experiments/HLX-CLASSIFICATION-V6-REPRESENTATION-REBASE-001/`
- Receipt: `eb4851e5c854641b97f7cb27d3f331386c4f1b4c30754e7340239de31bdb7c5b`

## 24. Tests / commits

- `tests/shadow/test_classification_v6_representation_rebase.py`
- Scaffold: `aca40c4`; seal = this change

## 25. Exact next phase-level action

```text
HARDEN_V6_SEMANTIC_REPRESENTATION_AND_PREPARE_QUALIFICATION
```

Harden the frozen-embedding + axis-head semantic matching pipeline (selected MSMARCO 
nonlinear, with MPNet/BGE as controls), lock DEV thresholds, keep QUAL sealed until 
hardening, and only then design a fresh V6 qualification surface. Do not reopen A–F.
