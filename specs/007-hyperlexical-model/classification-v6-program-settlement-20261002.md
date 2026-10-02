# SETTLE_HYPERLEX_PROGRAM_END_STATE

```text
PRIMARY_DISPOSITION = HYPERLEX_REPRESENTATION_AND_MEASUREMENT_LAYER
RELEASE_STATUS      = SHADOW_INSTRUMENT_ONLY
HUB_PUBLISH_AUTHORIZED = false
CLASSIFIER_RELEASE_ELIGIBLE = false
classifier_candidate   = CONCLUSIVELY_REJECTED (CORE QUAL FAIL)
NEXT_ACTION         = EXECUTE_REPRESENTATION_MEASUREMENT_ROADMAP
EXPERIMENT_ID       = HLX-CLASSIFICATION-V6-PROGRAM-SETTLEMENT-001
PHASE_RULE          = SETTLE_HYPERLEX_PROGRAM_END_STATE
```

This document is the consolidated Hyperlex program settlement. It answers
what Hyperlex can defensibly be, not which head to try next.

**Notion mirror (Instrument V1 packaging follow-on):** [Instrument V1 — settlement + Abraxas shadow | 2026-10-02](https://app.notion.com/p/3ed3e8ba2f5c81ea854de3dcb6a10958).

---

## 1. Canonical V5/V6 scientific findings

### V5 demonstrated

- Gold identifiability matters (SHORT_ATOM NONE local repair was real).
- Factorized Stage-A checkpoints load; serialization defects were real.
- Stage-B family retrieval works on its matched diagnostic validation surface.
- Fresh OBSERVED unpaired qualification exposed MIXED_SYSTEM_GENERALIZATION_FAILURE.
- Flat family ontology was not reliably separable in representation geometry.
- Disposition: **V5_RESEARCH_PROTOTYPE** — not release-qualified.

### V6 demonstrated

- Hierarchical multi-label ontology is the correct semantic direction
  (`HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL`).
- Natural OBSERVED representative data is required; positive-only `usable()`
  REP produced REPRESENTATIVE_VALIDATION_OVERFIT (REP≈0.43 vs QUAL-002≈0.19).
- Frozen sentence/retrieval encoders outperform Hyperlex-trained ModernBERT
  (MPNet zs 0.206 > ModernBERT 0.162; MSMARCO frozen nonlinear REP 0.443).
- Encoder fine-tuning / PEFT not justified.
- Explicit NONE / ANY_LABEL rejection materially improves operating behavior
  on REP (zero-FP 0.788 → 0.088).
- FUNCTION is human-coherent but hits TEXT_SIGNAL_CEILING ≈0.30 as required
  text-only output → ADVISORY_ONLY / RESEARCH for memetic_form.
- Core package (evidence + DOMAIN + MEDIATION) hardened and **failed** fresh
  CORE QUAL: core macro-F1 **0.094** (floor 0.30), SEVERE_GENERALIZATION_DROP
  vs REP_V3 (retention 0.271).

### Failures that repeated

| Pattern | V5 | V6 |
|---|---|---|
| DEV/diagnostic optimism ≠ fresh QUAL | yes | yes (002, 003, CORE) |
| Final hard labels collapse under operating text | yes | yes |
| Local repair ≠ global generalization | SHORT_ATOM | NONE gate / core harden |
| Source / length / NONE-mass shift | yes | yes |
| Micro-cycle (threshold/head/seed) insufficient | yes | yes |

### Interventions that worked locally but failed globally

- Identifiability filter / SHORT_ATOM NONE repair
- Positive-only hardened REP scores
- FUNCTION redesign / pragmatic objective / diversity expand
- Core product harden without required FUNCTION (REP gates pass → QUAL fail)

### Survived fresh qualification (relatively)

- **NONE exact rejection** retention ≈0.86 (best axis; still missed absolute floors)
- Hierarchy post-constraint discipline (0.0 on CORE QUAL)
- Human gold stability on CORE QUAL (core Jaccard 1.0)
- Frozen encoder immutability / cold-load package integrity

### Collapsed repeatedly

- DOMAIN / MEDIATION / FUNCTION hard labels as product outputs
- DEV→QUAL predictive numeric level
- ModernBERT Hyperlex BEST as semantic backbone

### Misleading validation practices

- Positive-only / contrast-paired diagnostic surfaces as operating proxies
- Treating REP numeric floors as QUAL certainty without retention diagnostics
- Re-using spent QUAL for optimization (forbidden; must remain excluded)

---

## 2. Final assessment — what Hyperlex can and cannot reliably do

| Capability | Grade |
|---|---|
| Hierarchical ontology as concept space | **PROVEN** |
| Gold identifiability + natural OBSERVED data discipline | **PROVEN** |
| Frozen semantic encoder superiority vs Hyperlex ModernBERT | **PROVEN** |
| Encoder fine-tuning for this task | **DISPROVEN_FOR_CURRENT_FORMULATION** |
| NONE / evidence abstention as a signal | **SUPPORTED_BUT_LIMITED** |
| DOMAIN / MEDIATION hard text-only labels | **DISPROVEN_FOR_CURRENT_FORMULATION** |
| FUNCTION as required text-only output | **DISPROVEN_FOR_CURRENT_FORMULATION** |
| V6 core production classifier | **DISPROVEN_FOR_CURRENT_FORMULATION** |
| Semantic representation / candidates / diagnostics | **SUPPORTED_BUT_LIMITED** |
| Contextual reasoner as final judge | **UNRESOLVED** (deferred) |
| Hybrid representation + verifier | **UNRESOLVED** (deferred) |

Full table: `scripts/shadow/hyperlexical/classification_v6_program_settlement.py`
→ `CAPABILITY_BASELINE`.

---

## 3. Actual product requirements

Consumers need:

1. **Embeddings** for similarity / clustering / drift (Noesis, retrieval).
2. **Ranked semantic candidates + margins** for humans or downstream verifiers.
3. **Evidence / abstention signal** (prefer omit over false emit).
4. **Ambiguity / distribution-distance / ontology-neighborhood diagnostics**.

They do **not** need Hyperlex to silently emit hard DOMAIN/MEDIATION/FUNCTION
labels that fail fresh operating qualification.

---

## 4. Recommended Hyperlex system role

```text
HYPERLEX_REPRESENTATION_AND_MEASUREMENT_LAYER
```

Hyperlex is an upstream semantic instrument: representation, candidates,
abstention, and measurement — not a release-grade final-label classifier.

---

## 5. Final task formulation

**Central answer:** Hyperlex failed as a production classifier because
**final semantic judgment is not the right job for a lightweight text-only
classifier** under the operating distribution — not because the last head
was wrong.

| Primary | `representation_only_output` |
| Secondary | `candidate_generation`, `abstaining_decision_system`, `semantic_matching` |
| Deferred | `contextual_reasoning`, `retrieval_plus_verification` |
| Rejected primary | `classification` |

---

## 6. Architecture direction

**Selected:** frozen semantic encoder + evidence signal + ontology-neighborhood
candidate generator + ambiguity/drift diagnostics.

**Rejected:** text-only final-label classifier; ModernBERT FT; head/threshold/seed
micro-cycles.

**Deferred:** contextual semantic reasoner; hybrid verifier (follow-on only).

---

## 7. Representation strategy

- Encoder family: frozen sentence/retrieval embeddings (MSMARCO / MPNet / BGE class).
- Reference pin: `sentence-transformers/msmarco-distilbert-base-v4` (selected V6 rebase).
- Hyperlex ModernBERT `MODEL_WIDE_BEST`: **HISTORICAL_CONTROL_ONLY**.
- Fine-tuning: **not justified**.
- Shallow probes: candidates only — never release-binding hard labels.

---

## 8. Contextual-reasoning strategy

Not authorized as the V6 rescue path. Justified later **only** when:

- a downstream owner needs final FUNCTION/pragmatic judgments, and
- document/conversation context is in the input contract, and
- Hyperlex supplies candidates rather than final labels, and
- a fresh QUAL surface is sealed under that new contract.

Absence of GPU in this settlement session is recorded; it does **not** block
the primary disposition because final text-only judgments already lack
evidence-supported product value.

---

## 9. Role of DOMAIN / MEDIATION / FUNCTION / NONE

| Axis | Role |
|---|---|
| evidence / NONE | **REQUIRED_SIGNAL** (abstention / admit) |
| DOMAIN | **ADVISORY_CANDIDATES** — not hard release output |
| MEDIATION | **ADVISORY_CANDIDATES** — not hard release output |
| FUNCTION | **ADVISORY_OR_CONTEXTUAL_RESEARCH** |
| memetic_form | **RESEARCH_ONLY** |

---

## 10. Data and evaluation architecture

```text
TRAIN → DEV_SELECTION → REPRESENTATIVE_VALIDATION → FRESH_QUALIFICATION
```

- TRAIN/DEV may tune candidate scorers and gates.
- REP must mirror operating traffic including NONE/NO_EVIDENCE; never
  silently filter to easier positives.
- QUAL is blind, one-shot, permanently spent.
- Spent surfaces (V5 QUAL, V6 QUAL-002/003, CORE QUAL-001) remain
  permanently excluded from training, calibration, and model selection.

---

## 11. Representative-validation contract

- Include zero-label / NO_EVIDENCE mass at operating prevalence.
- Report development, representative, generalization gap, source sensitivity,
  zero-label behavior, positive semantic behavior, subgroup behavior.
- Success criterion: predict the **shape** of fresh QUAL failure/success modes
  (NONE vs positive, axis ordering), not merely maximize a filtered F1.

---

## 12. Fresh-qualification protocol

- Seal before score; package identity bound; gates frozen.
- Score exactly once; settle without post-hoc gate changes; spend forever.
- No retries without a **materially changed** scientific or product hypothesis.
- Further **classifier** QUAL without task reformulation: **FORBIDDEN**.
- Future QUAL, if any, must ask a **representation-signal stability** product
  question — not recycle label-F1 floors to rescue classification.

---

## 13. Final candidate implementation

```text
candidate_family = representation_measurement_layer
package_status   = SHADOW_INSTRUMENT_ONLY (contract + settlement sealed)
classifier_pkg   = HYPERLEX_V6_CORE_PRODUCT_PACKAGE_V1 (035e1b7e…)
                   retained as scientific evidence; NOT release candidate
```

Contract / receipt machinery:

- `scripts/shadow/hyperlexical/classification_v6_program_settlement.py`
- `scripts/spark/run_classification_v6_program_settlement.py`
- `artifacts/experiments/HLX-CLASSIFICATION-V6-PROGRAM-SETTLEMENT-001/`
- CPU tests: `tests/shadow/test_classification_v6_program_settlement.py`

---

## 14. Qualification result

| Candidate | Surface | Result |
|---|---|---|
| V6 core classifier `035e1b7e…` | `HYPERLEX_V6_CORE_QUALIFICATION_001` (seal `1c36342e…`) | **FAIL / RC REJECTED** |
| V6 three-axis packages | QUAL-002, QUAL-003 | **FAIL / SPENT** |
| V5 pipeline | V5 PIPELINE QUAL | **FAIL / SPENT** |
| Representation layer hard-label QUAL | — | **not applicable** (labels not the product) |

Classifier path is **conclusively rejected**. Representation layer does not
inherit classifier label floors; its release path is instrument/shadow until
a representation-stability QUAL is separately authorized.

---

## 15. Final product/research disposition

```text
PRIMARY_DISPOSITION = HYPERLEX_REPRESENTATION_AND_MEASUREMENT_LAYER
```

Exactly one. Not limbo. Classification as a production final-label program
is closed; scientific artifacts are preserved.

---

## 16. Release status

```text
RELEASE_STATUS           = SHADOW_INSTRUMENT_ONLY
HUB_PUBLISH_AUTHORIZED   = false
CLASSIFIER_RELEASE_ELIGIBLE = false
V6_CORE_RELEASE_CANDIDATE   = not created / rejected
```

---

## 17. Preserved artifacts and provenance

Preserve all prior receipts, datasets, ontologies, failure analyses, and QUAL
results under `specs/007-hyperlexical-model/`, `artifacts/experiments/HLX-*`,
and private `~/hlx-private/…` mirrors. Key identities:

| Artifact | Identity |
|---|---|
| CORE package | `035e1b7e21e97ed36f79750f1f643262540fba1546f488af2a0af04e8a7c1605` |
| CORE QUAL seal | `1c36342ea3dcc68e6b70befebf678e378dd56655b8129fd7125f9c421f7c8c27` |
| Ontology | `HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL` |
| MODEL_WIDE_BEST | historical control only (`9fba0f66…`) |
| morph78 structure pin | separate Hyperlexical product track |

---

## 18. Deprecated paths

- V5 flat-family production classifier
- V6 required FUNCTION release path
- V6 core DOMAIN+MEDIATION hard-label release path
- ModernBERT Hyperlex BEST as default semantic backbone
- Encoder fine-tuning for V6 classification
- Positive-only representative validation
- Threshold/seed/optimizer/head micro-cycles without task reformulation
- Any use of spent QUAL rows for train/select/calibrate
- Mandatory emission of every ontology concept as classifier output

---

## 19. Integration implications (Zero State ecosystem)

| System | Implication |
|---|---|
| **Noesis** | Consume embeddings + candidates; do not treat Hyperlex hard labels as truth; pairwise path unblocked from classifier dependency |
| **Abraxas** | Diagnostics/experiment coordination only; no forecast/rune coupling |
| **Trutina** | Distribution-distance / drift / separability signals |
| **Semion** | Ontology-neighborhood and ambiguity observability |
| **Contextual reasoners** | Hyperlex narrows search space; does not finalize |
| **Hyperlexical morph78** | Remains a separate structure-encoder track |

---

## 20. Follow-on roadmap

1. Ship frozen-encoder embedding + candidate API under `SHADOW_INSTRUMENT_ONLY`.
2. Instrument NONE/evidence, margin, ambiguity, drift on live OBSERVED traffic.
3. Define representation-signal stability QUAL (not label F1 floors).
4. Optional hybrid: Hyperlex candidates → external contextual verifier (new hypothesis).
5. Keep FUNCTION/pragmatics contextual/research; never re-mandate text-only.
6. **Do not** open another classifier QUAL without material task reformulation.

---

## Decision authority

Evidence → product role → disposition. Local experiment momentum does not
override spent QUAL failures or the capability grade table. Stop for human
judgment only on data-integrity, safety, product-contract owner override, or
direct contradiction of this settled baseline.

## Success criteria checklist

- [x] Product role explicit
- [x] Required vs advisory/research outputs separated
- [x] Task formulation matches available signal
- [x] Evaluation loop roles defined (TRAIN/DEV/REP/FRESH)
- [x] Classifier candidate conclusively rejected on fresh QUAL
- [x] Spent evaluation data remains excluded
- [x] Operating contract documented
- [x] Deployment/release status explicit (`SHADOW_INSTRUMENT_ONLY`)
- [x] Unresolved research (contextual/hybrid) separated from product blockers
- [x] Roadmap follows settled role, not experimental inertia
