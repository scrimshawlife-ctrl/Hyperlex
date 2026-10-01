# CONTINUE_V6_ARCHITECTURE_BAKEOFF — architecture reset (D/E/F)

```text
BAKEOFF_STATE = V6_ARCHITECTURE_BAKEOFF_EXHAUSTED
NEXT_ACTION = REASSESS_V6_TASK_SIGNAL_AND_PRETRAINED_REPRESENTATION
RECEIPT = e7264a0f140dee6536b4ca9d4de69a0ae2139c29a5c3a4572214fa1ae52b58eb
selected = None
advance = False
best_trained_REP_system_macro_F1 = 0.133779
zero_shot_best_REP_system_macro_F1 = 0.162237
abc_best_REP_system_macro_F1 = 0.023839
primary_failure_diagnosis = LABEL_SEMANTICS_PRIOR_STRONGER_THAN_CURRENT_TRAINED_REPRESENTATION
QUAL = sealed / uninspected
floors_locked = true (REP>=0.20, hier_viol<=0.05, axis>=0.10)
```

## 1. Bakeoff state

- **V6_ARCHITECTURE_BAKEOFF_EXHAUSTED** — no D/E/F candidate cleared locked floors.
- Selected: `None`
- Next: `REASSESS_V6_TASK_SIGNAL_AND_PRETRAINED_REPRESENTATION`

## 2. D/E/F architecture definitions

| Track | Assumption |
|---|---|
| **D_LABEL_DESCRIPTION_NLI** | Text–label entailment/compatibility against frozen ontology definitions |
| **E_LABEL_EMBEDDING_JOINT** | Shared space for text + label definitions; instance–label alignment + multi-label + hierarchy constraint |
| **F_HIERARCHY_AWARE_CONTRASTIVE** | Instance–instance, label–label, instance–label objectives reflecting hierarchy |

No A/B/C retuning. No legacy Stage-B exemplar index. No LLM-generated label reinterpretation.

## 3. Encoder controls

| Control | Meaning |
|---|---|
| **CONTROL** | `MODEL_WIDE_BEST` (`9fba0f66…`) on ModernBERT trunk |
| **EXTERNAL** | ModernBERT trunk only — no Hyperlex-specific adaptation |

Identical TRAIN/DEV/REP, ontology, label definitions, metrics, gates, seed, budget class.

## 4. Zero/few-shot semantic baseline (read-only)

- `ZERO_SHOT_SEMANTIC_MATCH__CONTROL`: system macro-F1 **0.1622** (domain 0.1871, function 0.1010, mediation 0.1333)
- `ZERO_SHOT_SEMANTIC_MATCH__EXTERNAL`: system macro-F1 **0.1335** (domain 0.1360, function 0.1227, mediation 0.1496)

Recorded: **`LABEL_SEMANTICS_PRIOR_STRONGER_THAN_CURRENT_TRAINED_REPRESENTATION`** (zero-shot 0.1622 > trained 0.1338 > ABC 0.0238).

## 5–8. Axis and system metrics (REP macro-F1)

| Track | system | domain | function | mediation | hier_viol |
|---|---:|---:|---:|---:|---:|
| `D_LABEL_DESCRIPTION_NLI__CONTROL` | 0.1338 | 0.1328 | 0.1270 | 0.1714 | 0.0000 |
| `D_LABEL_DESCRIPTION_NLI__EXTERNAL` | 0.1211 | 0.1114 | 0.1313 | 0.1879 | 0.0000 |
| `E_LABEL_EMBEDDING_JOINT__CONTROL` | 0.0151 | 0.0220 | 0.0000 | 0.0000 | 0.0000 |
| `E_LABEL_EMBEDDING_JOINT__EXTERNAL` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `F_HIERARCHY_AWARE_CONTRASTIVE__CONTROL` | 0.1255 | 0.1231 | 0.1289 | 0.1389 | 0.0000 |
| `F_HIERARCHY_AWARE_CONTRASTIVE__EXTERNAL` | 0.1298 | 0.1231 | 0.1267 | 0.2157 | 0.0000 |
| `ZERO_SHOT_SEMANTIC_MATCH__CONTROL` | 0.1622 | 0.1871 | 0.1010 | 0.1333 | 0.0000 |
| `ZERO_SHOT_SEMANTIC_MATCH__EXTERNAL` | 0.1335 | 0.1360 | 0.1227 | 0.1496 | 0.0000 |

## 9. DEV→REP gaps (system macro-F1)

| Track | gap (DEV−REP) |
|---|---:|
| `D_LABEL_DESCRIPTION_NLI__CONTROL` | 0.0327 |
| `D_LABEL_DESCRIPTION_NLI__EXTERNAL` | 0.0497 |
| `E_LABEL_EMBEDDING_JOINT__CONTROL` | -0.0034 |
| `E_LABEL_EMBEDDING_JOINT__EXTERNAL` | 0.0000 |
| `F_HIERARCHY_AWARE_CONTRASTIVE__CONTROL` | 0.0008 |
| `F_HIERARCHY_AWARE_CONTRASTIVE__EXTERNAL` | -0.0018 |
| `ZERO_SHOT_SEMANTIC_MATCH__CONTROL` | 0.0767 |
| `ZERO_SHOT_SEMANTIC_MATCH__EXTERNAL` | 0.0051 |

## 10. Hierarchy violations

All D/E/F and zero-shot runs report **hierarchy_violation_rate = 0.0** on REP (constraint decoding / soft parent push). Hierarchy consistency is not the binding failure.

## 11–12. Label-semantic margins / representation diagnostics (REP)

| Track | pos sim | hard-neg sim | margin | hier order ok |
|---|---:|---:|---:|---:|
| `D_LABEL_DESCRIPTION_NLI__CONTROL` | 0.2335 | 0.1914 | 0.0421 | n/a |
| `D_LABEL_DESCRIPTION_NLI__EXTERNAL` | 0.2253 | 0.1903 | 0.0350 | n/a |
| `E_LABEL_EMBEDDING_JOINT__CONTROL` | -0.1523 | -0.1885 | 0.0362 | n/a |
| `E_LABEL_EMBEDDING_JOINT__EXTERNAL` | -0.1741 | -0.1832 | 0.0091 | n/a |
| `F_HIERARCHY_AWARE_CONTRASTIVE__CONTROL` | -0.0523 | -0.1411 | 0.0888 | 0.9268 |
| `F_HIERARCHY_AWARE_CONTRASTIVE__EXTERNAL` | -0.1550 | -0.1642 | 0.0092 | 0.7805 |
| `ZERO_SHOT_SEMANTIC_MATCH__CONTROL` | 0.5380 | 0.5022 | 0.0358 | n/a |
| `ZERO_SHOT_SEMANTIC_MATCH__EXTERNAL` | 0.8925 | 0.8889 | 0.0036 | n/a |

## 13. Error decomposition (REP, Track D CONTROL — primary semantic track)

- **domain** (n=532): FALSE_POSITIVE_LABEL=514, CO_LABEL_FAILURE=485, ENCODER_SEPARATION_FAILURE=323, FALSE_NEGATIVE_LABEL=200, AXIS_CONFUSION=191
- **function** (n=532): FALSE_POSITIVE_LABEL=493, ENCODER_SEPARATION_FAILURE=436, FALSE_NEGATIVE_LABEL=59, AXIS_CONFUSION=57, ANNOTATION_BOUNDARY_CASE=0
- **mediation** (n=532): ENCODER_SEPARATION_FAILURE=213, FALSE_POSITIVE_LABEL=213, FALSE_NEGATIVE_LABEL=19, ANNOTATION_BOUNDARY_CASE=0, AXIS_CONFUSION=0

## 14. Comparison to A/B/C

- ABC best REP system macro-F1: **0.0238**
- Reset best trained REP system macro-F1: **0.1338**
- Delta vs ABC: **+0.1099**
- Label-semantic formulations (zero-shot / D / F) lift far above atomic multi-head A/B/C, but still miss the 0.20 advancement floor.

## 15. Advancement gate results

Locked floors unchanged:
- REP system macro-F1 ≥ 0.20 → **FAIL** (best trained 0.134; best zero-shot 0.162)
- hierarchy violation ≤ 0.05 → **PASS** (0.0)
- each material axis macro-F1 ≥ 0.10 → mixed; system floor still binds
- GENERALIZATION_GAP_ACCEPTABLE → generally PASS (no catastrophic DEV≫REP)

Selection ranking (eligible=false for all trained tracks):
- `D_LABEL_DESCRIPTION_NLI__CONTROL`: REP=0.1338, abs_ok=False, axis_ok=True, eligible=False
- `F_HIERARCHY_AWARE_CONTRASTIVE__EXTERNAL`: REP=0.1298, abs_ok=False, axis_ok=True, eligible=False
- `D_LABEL_DESCRIPTION_NLI__EXTERNAL`: REP=0.1211, abs_ok=False, axis_ok=True, eligible=False
- `F_HIERARCHY_AWARE_CONTRASTIVE__CONTROL`: REP=0.1255, abs_ok=False, axis_ok=True, eligible=False
- `E_LABEL_EMBEDDING_JOINT__CONTROL`: REP=0.0151, abs_ok=False, axis_ok=False, eligible=False
- `E_LABEL_EMBEDDING_JOINT__EXTERNAL`: REP=0.0000, abs_ok=False, axis_ok=False, eligible=False

## 16. Selected candidate

`null` — no advance.

## 17. Primary failure diagnosis

**`LABEL_SEMANTICS_PRIOR_STRONGER_THAN_CURRENT_TRAINED_REPRESENTATION`**
- zero-shot REP macro-F1=0.1622 > trained/ABC (~0.1338)
- best REP system macro-F1=0.1338 < 0.2

Interpretation: frozen ontology label descriptions already contain transferable signal that Hyperlex-adapted / trained heads dilute or fail to exploit. Architecture is no longer the primary unknown; task signal and pretrained representation alignment are.

## 18. Artifacts / receipts

- Private: `/home/morpheus/hlx-private/classification-v6-architecture-reset-bakeoff-20261001/`
- Repo: `artifacts/experiments/HLX-CLASSIFICATION-V6-ARCHITECTURE-RESET-BAKEOFF-001/`
- Receipt SHA256: `e7264a0f140dee6536b4ca9d4de69a0ae2139c29a5c3a4572214fa1ae52b58eb`
- Code revision at run: `da76948f58eb9cbda208a7342ba146b0619fbda7`

## 19. Tests

- `tests/shadow/test_classification_v6_architecture_reset_bakeoff.py` (contracts, floors, exhaustion, zero-shot diagnosis)

## 20. Commits

- Scaffold: `da76948` feat(007): architecture-reset bakeoff tracks D/E/F
- Seal commit: this change

## 21. Exact next phase-level action

```text
REASSESS_V6_TASK_SIGNAL_AND_PRETRAINED_REPRESENTATION
```

Do **not** start a fourth local architecture cycle. Investigate whether text-only signal + data scale can support the settled ontology distinctions, and whether Hyperlex fine-tuning is destroying useful pretrained geometry that zero-shot label-description matching still has.
