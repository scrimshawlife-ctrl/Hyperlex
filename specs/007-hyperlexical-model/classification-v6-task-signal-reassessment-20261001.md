# REASSESS_V6_TASK_SIGNAL_AND_PRETRAINED_REPRESENTATION

```text
REASSESSMENT_STATE = V6_TASK_SIGNAL_REASSESSMENT_COMPLETE
PRIMARY_DIAGNOSIS = PRETRAINED_REPRESENTATION_MISMATCH
GOAL_HYPOTHESIS = D. PRETRAINED_REPRESENTATION_MISMATCH
NEXT_ACTION = REBASE_V6_ON_STRONGER_PRETRAINED_SEMANTIC_ENCODER
RECEIPT = 8703b73df6aca08ed5cfa6b847fe753997af537b4d15bcf0650a14113d5e2549
ZERO_SHOT_CONTROL_REFERENCE = 0.162237
SENTENCE_MPNET_REP = 0.205558
architecture_restart_allowed = True
QUAL = sealed / uninspected
floors_locked = true
```

## 1. Reassessment state

**`V6_TASK_SIGNAL_REASSESSMENT_COMPLETE`** — diagnostic phase complete; no architecture-family bakeoff.

## 2. Zero-shot reference baseline

Frozen reference: **0.162237** 
(`ZERO_SHOT_SEMANTIC_MATCH__CONTROL`, receipt `e7264a0f140d…`).
Re-measured CONTROL zero-shot on this run: **0.162237** (matches).

## 3. Axis-level zero-shot (CONTROL)

| Axis | macro-F1 | micro-F1 |
|---|---:|---:|
| domain | 0.1871 | 0.1294 |
| function | 0.1010 | 0.1170 |
| mediation | 0.1333 | 0.1333 |

Structure: **few_strong_labels_many_unusable** — 
strong labels: `['domain.crypto', 'domain.technology', 'domain.technology.ai_discourse']`; 
weak count: 13.
Domain carries most of the 0.162; function is the weakest axis.

## 4. Per-label performance (CONTROL zero-shot REP)

| Label | support | P | R | F1 | pos mean | neg mean | margin |
|---|---:|---:|---:|---:|---:|---:|---:|
| `domain.crypto` | 3 | 0.250 | 0.667 | 0.364 | 0.6184 | 0.3715 | 0.2469 |
| `domain.entertainment` | 35 | 0.091 | 0.057 | 0.070 | 0.5532 | 0.5404 | 0.0128 |
| `domain.fashion` | 40 | 0.263 | 0.125 | 0.169 | 0.6195 | 0.5927 | 0.0268 |
| `domain.gambling` | 5 | 0.009 | 1.000 | 0.019 | 0.6234 | 0.5298 | 0.0936 |
| `domain.gaming` | 47 | 0.500 | 0.043 | 0.078 | 0.4746 | 0.4515 | 0.0230 |
| `domain.politics` | 28 | 0.100 | 0.179 | 0.128 | 0.6211 | 0.5748 | 0.0463 |
| `domain.spiritual` | 41 | 0.087 | 0.854 | 0.158 | 0.5928 | 0.5612 | 0.0316 |
| `domain.sports` | 37 | 0.072 | 0.973 | 0.134 | 0.5380 | 0.5120 | 0.0260 |
| `domain.technology` | 79 | 0.441 | 0.329 | 0.377 | 0.4231 | 0.3205 | 0.1026 |
| `domain.technology.ai_discourse` | 41 | 0.615 | 0.390 | 0.478 | 0.5108 | 0.3227 | 0.1881 |
| `domain.workplace` | 35 | 0.048 | 0.314 | 0.083 | 0.5813 | 0.5673 | 0.0140 |
| `function.conflictive_force` | 31 | 0.010 | 0.032 | 0.015 | 0.5048 | 0.5145 | -0.0097 |
| `function.evaluative_stance` | 34 | 0.066 | 1.000 | 0.123 | 0.5391 | 0.5234 | 0.0157 |
| `function.memetic_form` | 38 | 0.072 | 0.605 | 0.128 | 0.5197 | 0.5115 | 0.0082 |
| `function.relational_intimacy` | 42 | 0.080 | 0.500 | 0.137 | 0.5460 | 0.5295 | 0.0165 |
| `mediation.internet_register` | 43 | 0.093 | 0.233 | 0.133 | 0.6303 | 0.6013 | 0.0290 |

## 5. Label-description adequacy

Counts: `{'DESCRIPTION_OVERBROAD': 0, 'DESCRIPTION_OVERLAPS_NEIGHBOR': 7, 'DESCRIPTION_REQUIRES_CONTEXT': 1, 'DESCRIPTION_SUFFICIENT': 7, 'DESCRIPTION_UNDERSPECIFIED': 1}`
- 7/16 `DESCRIPTION_SUFFICIENT`; 7 `DESCRIPTION_OVERLAPS_NEIGHBOR`; 
1 underspecified; 1 requires context (mediation).
No rewrites performed this phase.

## 6. Description sensitivity

- `canonical_full_definition`: REP system macro-F1 **0.1622**
- `canonical_name`: REP system macro-F1 **0.1474**
- `definition_plus_exclusion`: REP system macro-F1 **0.1622**
- `positive_core`: REP system macro-F1 **0.1419**
- Spread: **0.0203** → `LABEL_DESCRIPTION_INSTABILITY` = **False**
(Diagnostic only; canonical full definition remains reference.)

## 7. Human-vs-model learnability

| Stratum | human κ | zs F1 | trained F1 | class |
|---|---:|---:|---:|---|
| domain:crypto_markets | 1.0000 | 0.3636 | 0.0112 | LOW_SUPPORT |
| domain:gambling_betting | 0.7647 | 0.0187 | 0.0106 | HUMAN_STABLE_MODEL_WEAK |
| function:evaluative_stance | 1.0000 | 0.1234 | 0.1321 | LOW_SUPPORT |
| function:relational_intimacy | 0.9396 | 0.1373 | 0.1840 | HUMAN_STABLE_MODEL_WEAK |
| mediation:internet_register | 1.0000 | 0.1333 | 0.1770 | LOW_SUPPORT |

## 8. Learning curves (D-style, CONTROL, last-2)

| frac | n | DEV macro | REP macro | margin |
|---:|---:|---:|---:|---:|
| 0.10 | 121 | 0.1547 | 0.1216 | 0.0185 |
| 0.25 | 302 | 0.1437 | 0.1406 | 0.0190 |
| 0.50 | 604 | 0.1567 | 0.1408 | 0.0332 |
| 0.75 | 907 | 0.1587 | 0.1264 | 0.0380 |
| 1.00 | 1209 | 0.1615 | 0.1462 | 0.0491 |

Classification: **`EARLY_SATURATION`** (max REP=0.1462; Δ10→100=0.0246).
Saturates well below 0.20 under ModernBERT/CONTROL training — more of the same data/head does not clear the floor.

## 9. Frozen vs partial vs full fine-tuning

| Regime | REP macro | DEV→REP note | text-label margin | cos-to-init |
|---|---:|---|---:|---:|
| A_ENCODER_FROZEN | 0.1163 | gap=0.0237 | 0.0173 | 1.0000 |
| B_LAST_1_LAYER | 0.1261 | gap=0.0275 | 0.0288 | 0.9923 |
| C_LAST_2_LAYERS | 0.1283 | gap=0.0276 | 0.0410 | 0.9852 |
| D_FULL_FINETUNE | 0.1440 | gap=0.0544 | 0.0409 | 0.6958 |

Full FT (0.144) > frozen heads-only (0.116), but **both remain below the 0.162 zero-shot reference** — 
training still fails to beat read-only semantic matching on this encoder.

## 10. Representation drift

Last-layer regimes retain high cosine-to-init (≥0.99). Full FT shows more movement but does not 
produce `CATASTROPHIC_TASK_ADAPTATION` relative to frozen in this run; the binding issue is 
**pretrained family choice**, not layer-destruction alone.

## 11. Linear / nonlinear probes

| Encoder | domain | function | mediation |
|---|---|---|---|
| CONTROL | NONLINEARLY_AVAILABLE (lin=0.1756) | NONLINEARLY_AVAILABLE | LINEARLY_AVAILABLE |
| EXTERNAL | LINEARLY_AVAILABLE (lin=0.1398) | NONLINEARLY_AVAILABLE | LINEARLY_AVAILABLE |

Signal is partially recoverable from frozen ModernBERT features, but not to the 0.20 system floor.

## 12. Pretrained representation comparison (read-only)

| Representation | REP system macro-F1 | domain | function | mediation |
|---|---:|---:|---:|---:|
| ModernBERT CONTROL (Hyperlex BEST) | 0.1622 | 0.1871 | 0.1010 | 0.1333 |
| sentence-transformers/all-mpnet-base-v2 | 0.2056 | 0.2233 | 0.1777 | 0.1212 |
| cross-encoder/nli-deberta-v3-base | 0.0452 | 0.0462 | 0.0122 | 0.1667 |

**MPNet clears the 0.20 floor in read-only semantic matching.** Generic NLI-DeBERTa does not transfer here.

## 13. Axis-specific representation finding

**`AXIS_SPECIFIC_REPRESENTATIONS_JUSTIFIED`** — best-per-axis macros: `{'domain': 0.2233436888659714, 'function': 0.17773212335712335, 'mediation': 0.16666666666666666}`.

## 14. Cardinality effects

REP buckets: `{'multi_2_3': {'mean_domain': 1.826086956521739, 'mean_function': 0.08695652173913043, 'n': 46}, 'single': {'mean_domain': 0.6316872427983539, 'mean_function': 0.29012345679012347, 'n': 486}}`
Failure is not isolated to high-cardinality rows; single-label mass remains large on REP.

## 15. Co-label sparsity

n_pairs=17; rare TRAIN≤2 but REP≥1 shown: 5.
Composition sparsity is a secondary contributor, not the primary blocker given MPNet’s zero-shot lift.

## 16. Supervision density

Per-label classes: `{'LOW_POSITIVE_SUPPORT': 2, 'ADEQUATELY_SUPERVISED': 14}`.

## 17. Hard-negative margins

Regime margins: frozen=0.01730373145737457, 
full FT=0.04092012758024016.
Training improves some margins vs early curve points but does not surpass MPNet’s pretrained geometry.

## 18. Source shortcut findings

`insufficient_source_fields_for_holdout`

## 19. Text-only signal assessment

Protocol: `dual_operator_text_only_annotation` (model scores withheld).
Label classes: `{'domain.crypto': 'TEXT_SIGNAL_SUBTLE', 'domain.gambling': 'TEXT_SIGNAL_SUBTLE', 'function.evaluative_stance': 'TEXT_SIGNAL_SUBTLE', 'function.relational_intimacy': 'TEXT_SIGNAL_SUBTLE', 'mediation.internet_register': 'POTENTIALLY_CONTEXT_DEPENDENT'}`.

## 20. Strong semantic-model diagnostic

- MPNet sentence embedding zero-shot: **0.2056** (>0.20 floor)
- NLI DeBERTa cross-encoder zero-shot: **0.0452**
- vs frozen CONTROL reference **0.162**
A substantially stronger *sentence-embedding* prior extracts the task without Hyperlex training.

## 21. Primary diagnosis

**`PRETRAINED_REPRESENTATION_MISMATCH`** (D. PRETRAINED_REPRESENTATION_MISMATCH)

## 22. Secondary contributors

['AXIS_SPECIFIC_REPRESENTATIONS_JUSTIFIED']

## 23. Architecture-restart justification

Allowed: **True** — reasons `['REP_DIAGNOSTIC_ABOVE_FLOOR']`; 
best diagnostic REP=0.2056 beats zero-shot reference and exceeds 0.20.
Restart is justified only as a **representation rebase** (sentence-embedding family), 
not another ModernBERT head-architecture carousel.

## 24. Artifacts / tests / commits

- Private: `/home/morpheus/hlx-private/classification-v6-task-signal-reassessment-20261001/`
- Repo: `artifacts/experiments/HLX-CLASSIFICATION-V6-TASK-SIGNAL-REASSESSMENT-001/`
- Receipt: `8703b73df6aca08ed5cfa6b847fe753997af537b4d15bcf0650a14113d5e2549`
- Tests: `tests/shadow/test_classification_v6_task_signal_reassessment.py`
- Commits: scaffold `811d294`; seal = this change

## 25. Exact next phase-level action

```text
REBASE_V6_ON_STRONGER_PRETRAINED_SEMANTIC_ENCODER
```

Rebase Stage-B label-semantic matching onto a strong general sentence/text embedding 
encoder (MPNet-class or better), preserve locked floors, keep QUAL sealed, and treat 
Hyperlex ModernBERT BEST as a control—not the default backbone.
