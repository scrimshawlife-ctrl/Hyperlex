# Tasks 007 — Hyperlexical model (SHADOW)

Do not start T1 until operator says **implement 007 U1**.

## Specify cycle (this PR)

- [x] T0a Freeze spec.md, clarify C1–C32, plan, dual-use-gate, checklist
- [x] T0b Packet schema `hyperlex.hyperlexical.inference.v0.1`
- [x] T0c Notion operator pages under 02 Operator
- [x] T0d Branch `007-hyperlexical-model` + draft PR (specs only)
- [x] T0e Constitution I–X written check (`constitution-check.md`)
- [x] T0g Research fold + data-model
- [x] T0h Spark hardware + uncensored contract
- [x] T0i Analyze pass + example packets + model-card draft
- [x] T0j A1 ceiling 150M
- [x] T0k A2 trunk freeze ModernBERT-base
- [ ] T0f Operator sentence: implement U1 / hold / open 006 IsA

## U1 implement (blocked)

- [ ] T1 `scripts/shadow/hyperlexical/packet.py` builds schema-valid packets
- [ ] T2 stub infer: offline, no torch required, no chat template, no ModernBERT download
- [ ] T3 pytest: brier null, no semantic route, omit-on-empty, restricted redaction wall
- [ ] T3b E6: dialect fixture yields packet, never a refusal string
- [ ] T4 CLI `--offline` on civilian fixture `rizz`
- [ ] T5 Docs one-pager under `docs/` only if operator asks (default: spec is enough)

## U2 / U3 (blocked on later sentences)

- [ ] T6 Dataset exporter (include dialect civilian atoms)
- [ ] T7 Eval harness vs 004 probe on Spark against frozen trunk
- [ ] T8 Hub card from `model-card.draft.md` — still no upload
- [x] T9 Freeze trunk id (`trunk.md`, C28)

## Explicitly not tasks

- Train T1 149M weights
- Push to Hugging Face
- Import Abraxas
- Open 006 IsA
- Mutate API_V1
- Add generate / wrap verbs
- Swap trunk to MiniLM or Qwen
- Download ModernBERT in U1 CI
