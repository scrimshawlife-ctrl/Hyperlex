# Threshold artifact schema contract

Workstream A is `THRESHOLD_ARTIFACT_SCHEMA_HARDENING`. Its state machine is separate from semantic-evidence v2.

```text
UNSPECIFIED
  -> SCHEMA_FAMILY_DRAFTED
  -> SCHEMA_FAMILY_FROZEN
  -> HISTORICAL_VALIDATION_COMPLETE
```

Failure states are `SCHEMA_CONFORMANCE_GAP` and `SCHEMA_SEMANTIC_VALIDATION_FAILURE`. A schema failure does not mutate a frozen historical artifact.

## Family

The contract family is `specs/007-hyperlexical-model/schemas/hyperlex/residual-threshold/`. It is not one schema. The earlier retrospective family under `specs/007-hyperlexical-model/schemas/residual-threshold/` remains the emission-matched check from the previous hardening pass. This family is the named contract. Both are validate-only.

Files:

- `common.schema.json`
- `surface-manifest-row.schema.json`
- `surface-draw-receipt.schema.json`
- `resolution-row.schema.json`
- `resolution-receipt.schema.json`
- `score-row.schema.json`
- `score-receipt.schema.json`
- `operator-label-row.schema.json`
- `operator-labeling-receipt.schema.json`
- `support-join-row.schema.json`
- `support-reassessment.schema.json`
- `direction-analysis.schema.json`
- `direction-decision.schema.json`
- `confound-analysis.schema.json`
- `confound-decision.schema.json`
- `threshold-search.schema.json`
- `threshold-decision.schema.json`
- `calibration-failure.schema.json`
- `completion-receipt.schema.json`

## Canonical terms

`common.schema.json` closes sha256 as `^[0-9a-f]{64}$`. Operator labels are HIGH, SECONDARY, REJECT, QUARANTINE, and UNRESOLVED. Parent row resolution is RESIDUAL_READY or UNKNOWN. Constituent resolution status stays EXACT, RESOLVED, AMBIGUOUS, or UNRESOLVED. Those are different fields. Score status stays SCORED or UNKNOWN. SCORED is the emitted form of a residual-ready parent.

Threshold state is closed to the emitted lane states: `THRESHOLD_PROCEDURE_PREREGISTERED`, `SURFACES_FROZEN`, `CALIBRATION_INSUFFICIENT_SUPPORT`, `SUPPORT_GATE_PASSED`, `SUPPORTED_DIRECTION`, `NO_DIRECTIONAL_SIGNAL`, `CALIBRATION_CONFOUND_REVIEW`, `NO_THRESHOLD_PASSES_PRECISION_GATE`, and `THRESHOLD_FROZEN`. Direction results keep `INVERTED_DIRECTION` and `NO_DIRECTIONAL_SEPARATION` on their own enum. `NO_DIRECTIONAL_SIGNAL` is the threshold-lane name and is not a substitute for `NO_DIRECTIONAL_SEPARATION`.

Measurement state allows SEALED, ELIGIBLE, and EXECUTED. The only emitted value is SEALED. When `measurement_state` is SEALED, present execution flags (`measurement_resolved`, `measurement_scored`, `measurement_labeled`, `measurement_touched`, and the GlossBERT and MiniLM run flags) must be false. Historical receipts use false, not null.

An unfrozen record requires `threshold_value` null. A frozen record requires the 10-decimal residual string, `predicted_yes_support` at least 8, precision, Wilson bounds, HIGH recall, leave-one-out PASS, and zero REJECT and QUARANTINE predicted-YES counts. Those names are the selector's names. No frozen success file was emitted. `threshold-decision.schema.json` holds that branch as a contract only.

Historical `json_schema_exists` stays false. That field records emission time.

## Semantic checks

JSON Schema does not check cross-artifact identity. `scripts/shadow/hyperlexical/residual_threshold_contract.py` checks, for the v2 calibration lane:

- calibration manifest, operator labels, and support join each have 200 rows and the same row-id sequence
- ready plus unknown is 200
- calibration synsets are unique, measurement synsets are unique, and the two synset sets are disjoint
- manifest order is the frozen draw order
- label inventory totals 200
- join, draw, direction, and resolution receipts match the hashes of the files they name
- the measurement manifest hash remains `78ca09ab14912681d028e8b9b1c77a8daf1d0c8c81561434eb9b6ade45a753e5`

The public report is `CONTRACT_VALIDATION.json`. The current outcome is `HISTORICAL_VALIDATION_COMPLETE`. Gap records contain the artifact, schema, field path, a redacted observed value, and `historical_artifact_mutated: false`. Surface text is not copied into the report.

## What this workstream does not do

It does not retune threshold v2, redraw either surface, execute measurement, change the 0.80 precision floor or the Wilson floor, weaken the REJECT or QUARANTINE vetoes, or select a threshold from the failed candidates.
