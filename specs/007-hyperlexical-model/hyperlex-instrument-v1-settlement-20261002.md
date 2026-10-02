# HYPERLEX_INSTRUMENT_V1 — packaging + Abraxas shadow integration

```text
HYPERLEX_PRODUCT_ROLE       = REPRESENTATION_AND_MEASUREMENT_LAYER
HYPERLEX_OPERATION_MODE     = SHADOW_INSTRUMENT_ONLY
HYPERLEX_CLASSIFIER_RELEASE = REJECTED
HYPERLEX_INSTRUMENT_V1      = READY_FOR_ABRAXAS_SHADOW_USE
```

Parent settlement: `classification-v6-program-settlement-20261002.md` (receipt `4ae7cddf…`).

No classifier research reopened. No QUAL cycle. DOMAIN/MEDIATION/FUNCTION remain non-authoritative.

## Package / module layout

Hyperlex (this repo) — equivalent to logical packages without churn:

| Logical package | Path |
|---|---|
| `@zero-state/hyperlex-contracts` | `schemas/hyperlex.instrument.v1.schema.json` + `src/hyperlex/schemas/` |
| `@zero-state/hyperlex-instrument` | `src/hyperlex/instrument/` |
| `@zero-state/hyperlex-abraxas` | `src/hyperlex/compat/abraxas/instrument_evidence.py` |

Abraxas:

| Piece | Path |
|---|---|
| Adapter | `abraxas/evidence/hyperlex_instrument.py` |
| Docs | `docs/integration/hyperlex_instrument_v1.md` |
| Subsystem | `.abraxas/subsystems/hyperlex_instrument_v1.yaml` |
| Registry | `.abraxas/registries/expected_subsystems.yaml` (+ `hyperlex_instrument_v1`) |
| Tests | `tests/test_hyperlex_instrument_evidence.py` |

## Versions

| Field | Value |
|---|---|
| instrument | `HYPERLEX_INSTRUMENT_V1` |
| contract | `hyperlex.instrument.v1` |
| ontology | `HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL` |
| encoder pin | `sentence-transformers/msmarco-distilbert-base-v4@b2f66c95…` |
| default embed mode | `STATIC_HASH_EMBEDDING` |

## Runtime entry points

```text
from hyperlex.instrument import observe, InstrumentClient
python -m hyperlex.instrument observe "…"
python -m hyperlex.instrument serve --port 8741
POST /v1/observe | GET /v1/health | GET /v1/manifest | GET /v1/capabilities
```

## Authority boundary

Encoded in schema, manifest, adapter, and tests:

```text
HYPERLEX_OUTPUT != SEMANTIC_TRUTH
promote_to_canonical_state → raises
```

## Capabilities

Supported: evidence, representation, neighborhood, margin, ambiguity.  
Advisory: domain/mediation candidates.  
Experimental/advisory: function candidates.  
Research-only: memetic_form (not emitted).  
Unsupported: final_classification.  
Unavailable (null): distribution_distance, representation_drift.

## Invoke from Abraxas

```bash
export ABX_HYPERLEX_INSTRUMENT=1
export PYTHONPATH=/path/to/Hyperlex/src:$PYTHONPATH
python -c "from abraxas.evidence.hyperlex_instrument import observe_text; print(observe_text('crypto defi')['ok'])"
```

Default flag off → shadow integration inert.
