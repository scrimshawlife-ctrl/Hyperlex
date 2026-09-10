# Plan 007 — Hyperlexical model (SHADOW)

**Status**: PLAN drafted with specify pack. Implement not started.  
**Constitution check**: I–X hold. No API_V1. No Abraxas import. Settled Brier only. Detector over generator. Human gate on Hub / promote.

## Approach

Three implement units, each separately mergeable:

| Unit | Scope | Touches src/? | Operator phrase |
|------|-------|---------------|-----------------|
| U1 | Schema + stub helper + tests | no | implement 007 U1 |
| U2 | Dataset exporter from existing fixtures/receipts (civilian) | no | implement 007 U2 |
| U3 | Training recipe + eval harness vs 004 probe | no | implement 007 U3 |

U1 is the only unit this plan authorizes without a second operator sentence.

## U1 design

```
scripts/shadow/hyperlexical/
  infer.py          # stdlib-first stub; optional torch later
  packet.py         # build + validate inference packet
  __init__.py
tests/test_hyperlexical_shadow.py
specs/007-hyperlexical-model/schemas/hyperlexical_inference.v0.1.schema.json
```

- Default path: stub embeddings (hash-to-vector) so CI needs no GPU and no Hub download.
- Packet always `brier: null`, `forecast_eligible: false`, no `semantic`.
- CLI: `python3 scripts/shadow/hyperlexical/infer.py --text "rizz" --offline`
- Receipt optional, schema `hyperlex.hyperlexical.inference.v0.1`.

## U2 design (later)

Export JSONL from `examples/` + golden receipts + 004 fixtures.

Fields: `text`, `lineage`, `typology`, `stage`, `roles`, `split`, `provenance`.

Lexical split. Hash the export. Do not copy `~/.hyperlex/` ledgers into git.

## U3 design (later)

Training lives outside `src/hyperlex/`. Recipe doc + eval script comparing unbind accuracy to Spec 004 probe on shared fixtures. Weights stay out of git. Hub upload is a named operator action.

## Risks

| Risk | Mitigation |
|------|------------|
| Scope creep into chat LM | C1, C6, N1 |
| Semantic-route claim | C4, schema enum |
| Brier leak | schema const + tests |
| Dual-use generate | dual-use-gate; no generate verb |
| API_V1 drift | U1 shadow-only |
| 006 collision | C10 |

## Definition of done for this plan cycle

Specify + plan + tasks + schema + Notion pages + draft PR. No training.
