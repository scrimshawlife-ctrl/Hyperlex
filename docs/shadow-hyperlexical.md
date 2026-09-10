# SHADOW — Spec 007 Hyperlexical encoder

Not on Hyperlex API_V1. Not a Hugging Face model. Not named **Hyperlexical** until eval gate E2 passes.

Specify is locked C1–C52. Implement on `main` is the stub + harvest + eval harness + gated Spark loop.

## Commands

```bash
PYTHONPATH=scripts/shadow python3 -m hyperlexical.infer --text rizz --offline
PYTHONPATH=scripts/shadow python3 -m hyperlexical.ingest_tap --dry-run
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind
PYTHONPATH=scripts/shadow python3 -m hyperlexical.preflight
PYTHONPATH=scripts/shadow python3 -m hyperlexical.train --offline
```

`eval_unbind` exit 3 on the stub is expected (E2 fail).
`train` without Spark env exits 2.

## Spark

Aaron runbook: [`specs/007-hyperlexical-model/AARON-SPARK-TRAIN.md`](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/AARON-SPARK-TRAIN.md)

Trunk: `answerdotai/ModernBERT-base`. Local snapshot only. Last 2 layers trainable. Span aligner + val metrics. HF-shaped dump (`config.json`, `model.safetensors` or `heads.pt`). No Hub upload from the recipe.

## Eval table (stub)

| Gate | Status |
|------|--------|
| E0 packet | PASS |
| E1 classify | NOT RUN |
| E2 vs Spec 004 | FAIL |
| E3 MiniLM control | NOT RUN |
| E4 restricted | PASS |
| E5 schema walls | PASS |
| E6 dialect | PASS |

Brier stays null. `pipeline_tag` is `text-classification`.

## Live ingest tap

Current slang atoms from `pipeline` / `analyze` / `scan` / inbox write INFERRED rows to `~/.hyperlex/hyperlexical/ingest_candidates.jsonl`.
They do not become OBSERVED and do not mint Brier. Spec: `specs/007-hyperlexical-model/ingest-tap.md`.
