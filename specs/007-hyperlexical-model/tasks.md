# Tasks 007 — Hyperlexical model (SHADOW)

U1 implemented on branch `007-hyperlexical-model`. Not merged to main.

## Specify cycle

- [x] T0a–T0k specify + A1 + A2
- [ ] T0f Operator merge sentence

## U1 implement

- [x] T1 `scripts/shadow/hyperlexical/packet.py`
- [x] T2 stub infer: offline, no torch, no Hub
- [x] T3 pytest walls (brier, semantic, omit, restricted)
- [x] T3b E6 dialect fixture
- [x] T4 CLI `--offline` on `rizz`
- [x] T5 skipped (spec is the doc)

## U2 / U3 (blocked)

- [ ] T6 Dataset exporter — Hermes prompt in `hermes-dataset-prompt.md`
- [ ] T7 Eval harness vs 004 probe on Spark
- [ ] T8 Hub card upload
- [x] T9 Trunk freeze

## Explicitly not tasks

- Train 149M on Spark
- Push to Hugging Face
- Open 006
- Download ModernBERT in CI
