# Classification v2 — final settlement

```text
HYPERLEX_CLASSIFICATION_V2 = RESERVE_FAILED
primary_failure = APPLICABILITY_GENERALIZATION_FAILURE
family_retrieval = VALIDATION_SUPPORTED_RESERVE_UNSUPPORTED
production_promotion = REJECTED
BEST = UNCHANGED
```

Settlement date: 2026-09-30. Rule path closed after one authorized reserve score under frozen retrieval thresholds. No retune against the spent reserve. No BEST move.

## Verdict

Classification v2 is a **completed failed architecture**. Validation selective emission looked viable; the sealed reserve did not generalize. The dominant failure was evidence gating, not ontology width:

```text
NONE -> false FAMILY_PRESENT -> confident wrong family emission
```

Family retrieval (`HYPERLEX_FAMILY_RETRIEVAL_DECISION_V1`) is recorded as:

```text
VALIDATION_SUPPORTED_RESERVE_UNSUPPORTED
```

Production promotion of retrieval v1 (or any residual 18-way head) is **REJECTED**.

## Sealed failure reason

| Field | Value |
|---|---|
| Disposition | `RESERVE_FAIL` |
| Primary failure | `APPLICABILITY_GENERALIZATION_FAILURE` |
| Mechanism | Binary `NONE \| FAMILY_PRESENT` applicability admitted none-like inputs into family retrieval |
| Reserve family-emission precision | 0.409091 |
| Validation family-emission precision | 0.808219 |
| Reserve applicability macro-F1 | 0.500842 |
| Reserve NONE recall | 0.275 |
| Frozen thresholds | `minimum_family_score=0.85`, `minimum_top1_top2_margin=0.03` |

Wrong reserve FAMILY emissions were dominated by gold=`none` → predicted=`ai-native` after false evidence entry. This is not an ontology collapse of `social-evaluation`; it is an upstream gate failure.

## Preserved artifacts (unchanged)

Do not rewrite, retune, or delete these seals.

| Artifact | Hash / pin |
|---|---|
| BEST | `9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6` |
| Forward-hub weights | `adf5db93dfe258290be531f0a25035dfaae03873bd800fd929bee43b38c9f89c` |
| Hub export `civilian.v0.7.hub.jsonl` | `0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1` |
| Retrieval artifact | `4030e6a36ca1fea34dc728ae913bc96697e7484be532260f7b580ba5eadf2c8f` |
| Embedding index | `b1cd64d9e50e35f2c195f2e115ffdbd77f0a28089f8bd90792f36f1abc4b0177` |
| Reserve eval artifact | `7d8dd3d1338a6c2e241eef6de3432df60de057cb874788de537814393b17ad27` |
| Reserve rows | `8c5276442ce37cf99fff597653a28917b3b4dc69ac87ad01f815fa458416ed36` |
| Reserve identity list | `0af4e64fdbf109c194f4499dd729f0cd6262d774d2b44d0cb8bd39a21e3bbf93` |
| Error decomposition | `2ac0e911b64768d3b30417144e3075391ca2d8ba67a065c1edc56a49077bd429` |
| Hub boundary | `96a0587c06fac352872e462445f2eaaf773e35a48ab4c987e267b479cab72a83` |
| Ontology merge pair | `c901badb70c0c72f1af20fe4dd0b64bcbdfad917568682e9abb2cc9321ad69d5` |

Public receipts remain under `specs/007-hyperlexical-model/*-20260930.json`. Private seals remain under `/home/morpheus/hlx-private/classification-v2-*`.

## What is preserved forward

Compatible assets may inform Classification v3 **without** carrying v2 applicability as canonical truth:

- 18-family forward ontology and `social-evaluation` merge
- cleaned / hub-filtered training corpus concepts
- boundary contracts and provenance (`OBSERVED` / `INFERRED`)
- family exemplar-index *concept* (train-side positives only)
- unbind architecture
- Jev = OFF default; reserve isolation discipline

## What is not carried forward as truth

- binary applicability as the sole evidence gate
- residual 18-way softmax as semantic truth
- validation-only selective thresholds as production authorization
- any retune derived from the spent v2 reserve

## Lifecycle

```text
SETTLED_FAIL
```

Next architecture: `HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE` (spec only in this pass; no train).
