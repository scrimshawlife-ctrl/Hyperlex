# Plan 007 — Hyperlexical model (SHADOW)

**Status**: PLAN drafted with specify pack. Implement not started.  
**Constitution check**: I–X hold. No API_V1. No Abraxas import. Settled Brier only. Detector over generator. Human gate on Hub / promote.  
**Home box**: NVIDIA DGX Spark (GB10). See `hardware.md`.  
**Alignment**: uncensored base encoder. See `uncensored.md`.  
**T1 trunk**: `answerdotai/ModernBERT-base` (A2). See `trunk.md`.

## Approach

Three implement units, each separately mergeable:

| Unit | Scope | Touches src/? | Operator phrase |
|------|-------|---------------|-----------------|
| U1 | Schema + stub helper + tests | no | implement 007 U1 |
| U2 | Dataset exporter from existing fixtures/receipts (civilian) | no | implement 007 U2 |
| U3 | Training recipe + eval harness vs 004 probe **on Spark** using frozen trunk | no | implement 007 U3 |

U1 is the only unit this plan authorizes without a second operator sentence.
U1 does **not** download ModernBERT. Stub only.
U3 assumes Spark is the train box and the A2 trunk.

## U1 design

```
scripts/shadow/hyperlexical/
  infer.py          # stdlib-first stub; optional torch later
  packet.py         # build + validate inference packet
  __init__.py
tests/test_hyperlexical_shadow.py
specs/007-hyperlexical-model/schemas/hyperlexical_inference.v0.1.schema.json
```

- Default path: stub embeddings (`STATIC_HASH_EMBEDDING`) so CI needs no GPU and no Hub download.
- Packet always `brier: null`, `forecast_eligible: false`, no `semantic`.
- CLI: `python3 scripts/shadow/hyperlexical/infer.py --text "rizz" --offline`
- No chat template. Stub never returns a refusal string.
- Receipt optional, schema `hyperlex.hyperlexical.inference.v0.1`.

## U2 design (later)

Export JSONL from `examples/` + golden receipts + 004 fixtures.

Fields: `text`, `lineage`, `typology`, `stage`, `roles`, `split`, `provenance`.

Lexical split. Hash the export. Do not copy `~/.hyperlex/` ledgers into git.
Include dialect / informal / vulgar civilian atoms. Exclude restricted how-tos.

## U3 design (later)

Training lives outside `src/hyperlex/`. Recipe doc + eval script comparing unbind accuracy to Spec 004 probe on shared fixtures.

- Train home: DGX Spark, aarch64, unified 128 GB.
- Trunk: `answerdotai/ModernBERT-base`. Official tokenizer. Token-state unbind heads.
- MiniLM only as E3 control.
- Weights stay out of git. Hub upload is a named operator action.
- Optional later: NVFP4 export. Not a ship gate.
- ModernBERT-large may sit on Spark as teacher. Not the card.

## Risks

| Risk | Mitigation |
|------|------------|
| Scope creep into chat LM | C1, C6, C24, N1 |
| Safety-tuned trunk sneaks in | C22, C23, C28, E6 |
| Silent trunk swap | C28, trunk.md |
| WordPiece retokenize | C30 |
| Semantic-route claim | C4, schema enum |
| Brier leak | schema const + tests |
| Dual-use generate under "uncensored" | C26, dual-use rows 11–12 |
| API_V1 drift | U1 shadow-only |
| 006 collision | C10 |
| Inflate params because Spark holds 200B | C6, C24 |

## Definition of done for this plan cycle

Specify + plan + tasks + schema + hardware + uncensored + trunk freeze + Notion + draft PR. No training.
