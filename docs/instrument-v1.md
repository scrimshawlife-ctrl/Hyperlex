# Hyperlex Instrument V1

```text
HYPERLEX_PRODUCT_ROLE     = REPRESENTATION_AND_MEASUREMENT_LAYER
HYPERLEX_OPERATION_MODE   = SHADOW_INSTRUMENT_ONLY
HYPERLEX_CLASSIFIER_RELEASE = REJECTED
HYPERLEX_INSTRUMENT_V1    = READY_FOR_ABRAXAS_SHADOW_USE
```

## What it is

A **versioned semantic instrumentation dependency** for Abraxas.

```text
text → observe() → HyperlexObservation → Abraxas evidence adapter → Abraxas reasoning
```

It provides:

- semantic representation (deterministic offline embedding; frozen encoder pin identity)
- evidence / NONE / abstention signal
- advisory candidate concepts
- semantic neighborhood evidence
- margin / ambiguity diagnostics
- honest unavailable states for unsupported diagnostics
- full provenance (instrument, ontology, schema, manifest, settlement)

## What it is not

- Not an authoritative classifier
- Not semantic truth, gold, or canonical Abraxas state
- Not an authorization surface
- Not a promotion of DOMAIN / MEDIATION / FUNCTION / memetic_form to product truth

```text
HYPERLEX_OUTPUT != SEMANTIC_TRUTH
```

Classification-program settlement (authoritative history):

[`specs/007-hyperlexical-model/classification-v6-program-settlement-20261002.md`](../specs/007-hyperlexical-model/classification-v6-program-settlement-20261002.md)

V6 core classification **failed** fresh qualification and remains **REJECTED**.

## Authority semantics

| Hyperlex may | Hyperlex must not |
|---|---|
| provide evidence | establish canonical interpretation |
| emit advisory candidates | mutate Abraxas governing state |
| emit similarities / ambiguity | authorize actions |
| emit abstention / NONE | override provenance |
| support downstream verification | serve as gold authority |

Any promotion into Abraxas canonical state happens **downstream under Abraxas rules**.

## How Abraxas calls it

### In-process SDK (preferred)

```python
from hyperlex.instrument import InstrumentClient
from hyperlex.compat.abraxas import to_abraxas_evidence, assert_not_authoritative

client = InstrumentClient()
obs = client.observe(
    "ethereum defi airdrop",
    requested=["evidence", "candidates", "neighborhood", "diagnostics"],
)
evidence = to_abraxas_evidence(obs, role="SHADOW_SIGNAL")
assert_not_authoritative(evidence)
# Abraxas may consume `evidence` as advisory SHADOW_SIGNAL only.
```

### HTTP

```bash
PYTHONPATH=src python3 -m hyperlex.instrument.api --port 8741

curl -s http://127.0.0.1:8741/v1/health
curl -s http://127.0.0.1:8741/v1/manifest
curl -s http://127.0.0.1:8741/v1/capabilities
curl -s -X POST http://127.0.0.1:8741/v1/observe \
  -H 'content-type: application/json' \
  -d '{"text":"nba tournament","requested":["evidence","candidates"]}'
```

## Observation schema

Canonical contract: `hyperlex.instrument.v1`

- Schema file: `schemas/hyperlex.instrument.v1.schema.json`
- Package copy: `src/hyperlex/schemas/hyperlex.instrument.v1.schema.json`

Primary fields: `evidence`, `representation`, `candidates[]` (always `advisory=true`),
`neighborhood[]`, `diagnostics`, `provenance`, `authority`.

Forbidden wire fields include `domain_labels`, `function_labels`, `gold`,
`canonical_state`, `authorized_action`.

## Capabilities

Programmatic discovery: `GET /v1/capabilities` or `get_capabilities()`.

| Capability | Status |
|---|---|
| evidence_signal | supported |
| representation | supported |
| domain_candidates | advisory |
| mediation_candidates | advisory |
| function_candidates | experimental_or_advisory |
| memetic_form | research_only (not emitted) |
| final_classification | unsupported |
| distribution_distance | unavailable (null) |
| representation_drift | unavailable (null) |

## Abstention behavior

Valid result:

```json
{
  "evidence": {"present": false, "score": 0.0, "abstain": true},
  "candidates": []
}
```

Do not force a semantic candidate when evidence does not support one.

## Provenance / versions

Every observation carries:

- `instrument_version` = `HYPERLEX_INSTRUMENT_V1`
- `contract_version` = `hyperlex.instrument.v1`
- ontology version / receipt
- schema + manifest SHA256
- settlement reference + receipt (`4ae7cddf…`)
- runtime commit / package version

Cold-load: `cold_load_manifest()`.

## Runtime setup

```bash
pip install -e ".[dev]"   # jsonschema for full validation
PYTHONPATH=src python3 -c "from hyperlex.instrument import observe; print(observe('crypto')['observation_id'])"
PYTHONPATH=src python3 -m pytest tests/test_instrument_v1.py -q
```

No GPU / Hub weights required for SHADOW_INSTRUMENT_ONLY.

## Research-history boundary

Preserved under `specs/007-hyperlexical-model/`, `artifacts/experiments/`,
`scripts/shadow/hyperlexical/` — **not** required for Abraxas runtime use.

Normal operation must not depend on training datasets, spent QUAL surfaces,
failed V6 classifier packages, or bakeoff artifacts.

## Limitations

- Offline representation uses deterministic `STATIC_HASH_EMBEDDING`; the settled
  MSMARCO family pin is identity/provenance, not a required weight load.
- Candidates are cue-neighborhood advisory scores, not release-qualified labels.
- Distribution-distance and representation-drift remain explicitly unavailable.
