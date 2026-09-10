# SHADOW — Spec 007 model path

The Hermes skill is the **current operator surface**. This page is the **model path**: a learned encoder that starts as T0 and may become T1 after E2.

Not on Hyperlex `API_V1`. Not a Hugging Face model. Not named **Hyperlexical** until eval gate E2 passes on Spark.

Specify is locked C1–C52 plus A5 milestones. Implement on `main` is the stub, harvest, eval harness, and gated Spark loop.

## Trajectory (T0 → T1)

| Tier | Meaning | Name allowed | State today |
|------|---------|--------------|-------------|
| Skill | Hermes CLI + package | Hyperlex (the skill) | Shipping v0.4.0 |
| T0 | Base encoder + classify heads | `hyperlex-encoder-*` only | Specified. Not Hyperlexical. |
| T1 | Encoder + unbind heads; E2 vs Spec 004 | `hyperlex-structure-*` / Hyperlexical | **Not earned.** E2 Spark-blocked. |
| T2 | Separate generative LoRA | out of this cycle | Not an implement target |

`name_gate` stays **false** until E2. Classify volume ready ≠ T1.

## Honest gates (2026-09-10)

| Gate | State |
|------|--------|
| Classify volume | **Ready** — operator harvest with `--include-live` reached export family classify **2437**. Store family-labeled **1789**. See [blanket-yes receipt](receipts/blanket-yes-unlock-2026-09-10.md). |
| `name_gate` | **false**. Volume does not name the model. Gate stays false until E2 passes on Spark. |
| E2 vs Spec 004 | **FAIL** on the stub (expected). A trained E2 is Spark-blocked. Seed smoke is not a pass. |
| Hub | No upload. Skeleton only. Weights stay on Spark. |
| Families | **8**. No ninth family. |
| Brier | `null` on every packet. |

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

Bring-up is procedure, not a product card. A seed smoke that ends with E2 failing and a receipt written is a successful harness check — not a Hyperlexical name.

| Doc | Role |
|-----|------|
| [SPARK-BRINGUP.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/SPARK-BRINGUP.md) | Box procedure (#28) |
| [AARON-SPARK-TRAIN.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/AARON-SPARK-TRAIN.md) | Train spec (Danny) |
| [HERMES-SPARK-RUN.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/HERMES-SPARK-RUN.md) | Hermes run order |
| [milestones.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/milestones.md) | A5 name-gate / tier table (#33) |

Trunk: `answerdotai/ModernBERT-base`. Local snapshot only. Last 2 layers trainable. Span aligner + val metrics. HF-shaped dump (`config.json`, `model.safetensors` or `heads.pt`). No Hub upload from the recipe. Card name stays `hyperlex-encoder-modernbert-base-seed` until E2.

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

`pipeline_tag` is `text-classification`.

## Live ingest tap

Current slang atoms from `pipeline` / `analyze` / `scan` / inbox write INFERRED rows to `~/.hyperlex/hyperlexical/ingest_candidates.jsonl`.
They do not become OBSERVED and do not mint Brier. Spec: [ingest-tap.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/ingest-tap.md).

Live rows with an invalid split are coerced to a lexical train/val/test assignment (#38). That is export hygiene, not an E2 pass.
