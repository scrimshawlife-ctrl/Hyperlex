# REVIEW_V5_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL

Read-only system review after `HYPERLEX_V5_PIPELINE_QUALIFICATION_001`
`QUALIFICATION_FAIL`. No train / retune / index rebuild / BEST move /
qualification optimization.

```text
SYSTEM_DIAGNOSIS = MIXED_SYSTEM_GENERALIZATION_FAILURE
V5_DISPOSITION = V5_RESEARCH_PROTOTYPE
PRIMARY_REMEDIATION_PHASE = BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION
QUALIFICATION_SURFACE_VALIDITY = QUALIFICATION_SURFACE_HARD_BUT_VALID
NEXT_ACTION = BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION
RECEIPT = 6ba921e12fa7e0d4afc212d17ea7038de3050b7d9d72fa8fd996aaa0da112496
```

## Binding (unchanged)

| Pin | Value |
|-----|-------|
| MODEL_WIDE_BEST | `9fba0f66…` |
| STAGE_A_BEST | `f2b00c5d…` |
| STAGE_B_INDEX | `4febe96e…` |
| qualification | `HYPERLEX_V5_PIPELINE_QUALIFICATION_001` (spent) |
| package seal | `0e468234…` / manifest `c2d19bef…` |

## Distribution: V1R2 vs qualification

| Axis | V1R2 validation | Qualification |
|------|-----------------|---------------|
| n | 848 | 500 |
| provenance | 57% INFERRED / 43% OBSERVED | **100% OBSERVED** |
| paired/contrast share | pair_group ≈80% | **0%** |
| NONE domains | botany/chemistry/ornithology | mycology/entomology/numismatics… |
| source style | inferred POSITIVE/LOOKALIKE buckets | fresh Wiktionary/Wikipedia |
| mean max token Jaccard → train | — | **0.165** (p50 0.167) |
| Stage-B index NN sim (PRESENT) | mean **0.950** | mean **0.836** |

Shift class (both stages): **MATERIAL_DISTRIBUTION_SHIFT**.

Validation-selection bias: **OVERFIT_DEVELOPMENT_SURFACE** (matched
contrasts, inferred templates, domain set that does not cover fresh NONE
domains, floors/index tuned on the same V1R2 geometry).

## Stage A

| Metric | V1R2 val | Qualification |
|--------|---------:|--------------:|
| false_entry | 0.0336 | **0.3153** |
| PRESENT recall | 0.951 | **0.584** |
| NONE recall | 0.965 | **0.685** |
| UNCERTAIN recall | ~1.0 (n=15) | **0.0** (n=54) |

NONE subtypes on qualification:

| Subtype | n | false_entry | none_recall |
|---------|--:|------------:|------------:|
| SHORT_ATOM_NONE | 43 | **0.000** | **1.000** |
| ORDINARY_DOMAIN_NONE | 132 | 0.394 | 0.606 |
| LEXICAL_LOOKALIKE_NONE | 28 | 0.429 | 0.571 |

UNCERTAIN rows: 48/54 → PRESENT (p_resolvable≈1.0). Length: short NONE
holds; med/long NONE false_entry 0.37–0.46.

Learned: V1R2-specific lexical/source/domain boundaries — not a true
relation detector under the fresh text-only contract.

Threshold counterfactual (diagnostic only): **no** relation/resolvability
region rescues primary gates → **STRUCTURAL_OVERLAP**.

## Identifiability repair scope

```text
LOCAL_CAUSAL_SUCCESS: SHORT_ATOM NONE false_entry = 0.0 on qualification
GLOBAL_GENERALIZATION_FAILURE: ordinary/lookalike NONE, UNCERTAIN, PRESENT,
and Stage B remain broken
```

Do not erase the identifiability result; it repaired a real local class.

## Stage B (A-correct PRESENT only)

| Metric | Value |
|--------|------:|
| support | 142 |
| family emits | 51 |
| family precision | **0.275** |
| coverage | 0.359 |
| V1R2 family precision (reference) | 0.809 |

Wrong attractor: **ai-native** (24/37 wrong emits); index mass ai-native
**42.6%** (404/948). Wrong-emit mean score ≥ correct-emit mean score →
**STRUCTURAL_OVERLAP**, not a floor tweak.

Independent Stage-B generalization failure: **yes**.

## Representation / ontology (CLS, sealed load path)

| Geometry | Value |
|----------|------:|
| qual correct-family best index sim | 0.737 |
| qual wrong-family best index sim | **0.831** |
| qual index top1 family accuracy | **0.132** |
| within-family pairwise sim | 0.646 |
| between-family centroid sim | **0.854** |
| qual PRESENT↔NONE centroid cosine | 0.917 |
| val PRESENT↔NONE centroid cosine | 0.803 |

```text
ontology_separability = ONTOLOGY_NOT_RELIABLY_SEPARABLE
representation_class = MIXED_REPRESENTATION_FAILURE
```

## Qualification surface sanity

```text
QUALIFICATION_SURFACE_HARD_BUT_VALID
```

Harder and unpaired vs V1R2, but text-identifiable, disjoint, OBSERVED,
family-covered. Failure is not dismissed as pathological labeling.

## Intended vs development distribution

Product contract (v3 architecture): fresh text-only evidence gating then
family retrieval for active-family slang/domain inputs.

- V1R2: targeted diagnostic / overfit development surface
- Index: train-support skewed (ai-native attractor)
- Qualification: closer to fresh observed operating input

Development data does **not** represent the intended operating environment.

## Preserved truths

- gold identifiability mattered
- serialization defect was real
- factorized checkpoint is loadable
- SHORT_ATOM NONE historical failure was repaired
- Stage B works on its original V1R2 validation surface

## Rejected micro-fixes

| Action | Justified? |
|--------|:----------:|
| more Stage-A threshold tuning | **NO** |
| another Stage-A matched surface | **NO** |
| another Stage-B floor tune | **NO** |
| simply enlarging the existing index | **NO** |
| another reserve | **NO** |
| another local loss change | **NO** |

## Disposition

V5 is a **research prototype**: locally successful repairs on overfit
surfaces; system-level generalization failed on fresh text-only inputs.
Next unit of work is a V6 representative data foundation — not another
component patch cycle.

```text
NEXT_ACTION = BUILD_REPRESENTATIVE_V6_DATA_FOUNDATION
```
