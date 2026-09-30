# Classification v3 — evidence-gate preregistration

```text
HYPERLEX_CLASSIFICATION_V3_EVIDENCE_GATE = PREREGISTERED
surface = HYPERLEX_V3_EVIDENCE_SURFACE_V1
train = false
BEST = UNCHANGED (9fba0f66…)
spent_v2_reserve_reuse = false
```

Frozen before surface acquisition results. No reinterpretation without a version bump.

## Stage A labels

```text
NO_EVIDENCE
EVIDENCE_PRESENT
UNCERTAIN
```

## Decision semantics (frozen)

| Stage A | End-to-end |
|---|---|
| `NO_EVIDENCE` | `NONE` |
| `UNCERTAIN` | `ABSTAIN` |
| `EVIDENCE_PRESENT` | Stage B retrieval |

## Evaluation gates (frozen)

Primary:

```text
false_evidence_entry_rate_on_none <= 0.05
```

Secondary (only after primary passes):

```text
family_emission_precision >= 0.80
```

Not fitted from the spent v2 reserve.

## Frozen schema hashes

| Schema | sha256 |
|---|---|
| `evidence_example.v1` | `6981f65816a94630f9929e92feda96ddd72f74ab9aacfe3bd86764efbccf5141` |
| `evidence_decision.v1` | `bce1caaae235a5c7482012a8bd06619b8e70dc44e5a95fd6d84ad5730ce810ba` |
| `family_candidates.v1` | `49e364fea1e86111a194021cc302ab09a3bbdffe8dd94fe383101cd688f2c521` |
| `decision.v1` | `ec40356757c5a9e0b639603c6fc14b9650e8d2ecfe956123a0121e6559a12782` |

## Surface floors

Acquisition:

```text
POSITIVE_EVIDENCE >= 500
HARD_NONE >= 250
NEAR_DOMAIN_NONE >= 250
GENERIC_NONE >= 250
AMBIGUOUS_EVIDENCE >= 150
```

Validation (disjoint by identity / source hash / parent / lineage):

```text
POSITIVE_EVIDENCE >= 100
HARD_NONE >= 50
NEAR_DOMAIN_NONE >= 50
GENERIC_NONE >= 50
AMBIGUOUS_EVIDENCE >= 30
```

No v3 reserve in this pass.

## Explicit non-goals

```text
do not train Stage A
do not create or score a fresh reserve
do not reuse spent v2 reserve
do not move BEST
```
