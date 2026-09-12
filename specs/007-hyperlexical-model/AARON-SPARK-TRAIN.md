# Aaron — Spark train handoff (007)

Owner of this run: Aaron on the DGX Spark.  
Owner of the spec: Danny.  
Use current **`main`**. Do not use the old `007-hyperlexical-model` branch.

This is a **seed smoke** for harness wiring, not a Hyperlexical card. E2 has not passed. Name-gate is false. Do not upload to Hugging Face. Do not say the model is Hyperlexical.

**Train data:** T1 / E2 work uses the **local SoT** (`~/.hyperlex/hyperlexical/ingest_candidates.jsonl`). Export it with `PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live`. Train the same rows with an explicit opt-in — default remains the tracked/seed export (smoke-safe):

```bash
export HYPERLEX_INCLUDE_LIVE=1
# or: python3 -m hyperlexical.train --offline --run --include-live
# optional: HYPERLEX_LIVE_STORE=/path/to/ingest_candidates.jsonl
```

If the flag/env is set and the live store is missing, train exits non-zero. Do not train the named path from tracked `exports/civilian.v0.1.jsonl` alone — that file is a seed/snapshot.

The harvest includes the 4333-row dump when `data/hyperlex_4333_dump.jsonl` is present (dump fields only). Shadow stays import-isolated — no `from hyperlex` enrichment. Recent live exports have met the ~2500 classify bar.

Layout (locked): `specs/007-hyperlexical-model/weights.md`

- Freeze encoder except last **2** layers
- `classify`: Linear(768, 9) on token 0
- `role_head` + `filler_head`: Linear(768, vocab) on last-layer token states
- No refusal / Brier / chat tensors

## 0. What you are doing

Fine-tune `answerdotai/ModernBERT-base` (~149M) with the heads above.
Box: NVIDIA DGX Spark, GB10, 128 GB unified, aarch64, `sm_121`.

## 1. Preflight

```bash
cd /path/to/Hyperlex
git fetch origin && git checkout main && git pull --ff-only origin main

uname -m          # expect aarch64
python3 -V        # 3.10+

PYTHONPATH=scripts/shadow python3 -m hyperlexical.preflight
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live
# harvest_4333_dump picks up dump fields if data/hyperlex_4333_dump.jsonl is present.
# omit --include-live only for harness wiring against the tracked seed
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --out /tmp/hlx-e2-before.json
# expect exit 3 (no trained heads yet → stub path)
```

If `eval_unbind` exits 0 on the stub, stop and ping Danny.

## 2. Local trunk (once)

```bash
mkdir -p ~/.hyperlex/models/trunks
export HYPERLEX_TRUNK_DIR="$HOME/.hyperlex/models/trunks/ModernBERT-base"
ls "$HYPERLEX_TRUNK_DIR/config.json"
```

`local_files_only=True`. No instruct/chat. No MiniLM trunk. No ModernBERT-large card.

## 3. Env

```bash
export HYPERLEX_ALLOW_TRAIN=1
export HYPERLEX_TRUNK_DIR="$HOME/.hyperlex/models/trunks/ModernBERT-base"
export HYPERLEX_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export HYPERLEX_TRAIN_OUT="$HOME/.hyperlex/models/hyperlex-encoder-modernbert-base-seed"
export HYPERLEX_TRAIN_EPOCHS=2
export HYPERLEX_TRAIN_BATCH=8
export HYPERLEX_TRAIN_LR=2e-5
# Next train sentence (live SoT). Omit for seed smoke. Fail-closed if the store is missing.
# export HYPERLEX_INCLUDE_LIVE=1
```

## 4. Train smoke

```bash
PYTHONPATH=scripts/shadow python3 -m hyperlexical.train --offline --run
# live SoT: add --include-live (or HYPERLEX_INCLUDE_LIVE=1). Default is seed export.
```

Writes outside git: `heads.pt`, `layout.json`, `train-receipt.json`, `config-train.json`.
Do not commit them.

## 5. After

```bash
# Torch-free digest/stub (CI). Loads head bytes if present; trunk_loaded stays false.
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --out /tmp/hlx-e2-after.json
```

Real E2 on Spark (trained unbind_exact vs the Spec 004 probe). Fail-closed if torch, trunk, or weights are missing. Does not flip `name_gate`. `brier` stays null.

```bash
export HYPERLEX_E2_TRUNK_FORWARD=1
export HYPERLEX_TRUNK_DIR=$HOME/.hyperlex/models/trunks/ModernBERT-base
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --model-dir $HYPERLEX_TRAIN_OUT --out /tmp/hlx-e2-after.json
```

`--model-dir` may be omitted when `HYPERLEX_TRAIN_OUT` is set, or when the default seed-live / seed out dir exists (`~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-live` then `...-seed`). Same as `--trunk-forward` on the CLI.

Send Danny: preflight JSON, MANIFEST sha, e2 before/after, train-receipt.json, layout.json, torch/`sm_121` note. Include any high-signal oversampling notes if used (see 4333/Moltbook sections).

## 6. Hard no

No Hub upload. No `hyperlex-structure-149m`. No chat template. No refusal head. No Brier. No `semantic`. No 7B. No Orin as this box. No 006 labels. No wrap rows. No weight binaries in git. No CPU-only named encoder if `sm_121` fails — stop and return the error.

## High-signal subsets (Moltbook + 4333, not the global SoT)

Moltbook and the 4333 dump (see next section) are first-class **ai-native** sources. They are **subsets**, not the full civilian T1 SoT. Use `--include-live` for the authoritative data; optionally oversample the high-signal files below for memory/provenance signals.

- High-signal file: `exports/moltbook_high_signal.jsonl` (44 rows). Optional oversample for memory/provenance typology.
- Historical tracked-export Moltbook counts (~314–360 ai-native inside the 883-row seed) are **not** current global SoT status.
- Train from local SoT / `--include-live`. Optionally weight rows with moltbook provenance or high memory+provenance efficiency.
- Refresh: `python scripts/curate_moltbook_seeds.py --high-signal`
- Mapping and history: `dataset-harvest.md`

## 4333-row Hyperlex + Vernacular dump (2026-09-11)

Another first-class **ai-native** source (Hyperlex ledger + Vernacular/GrokBot terms from Notion export). Significant volume of memory, provenance, vernacular, and compression signals.

- Source: Notion page attachments (processed 4333 rows NDJSON + CSVs).
- Pipeline: `harvest_4333_dump` (wired in export) copies dump fields only. No `from hyperlex` / `detect_memetic_patterns` import — shadow stays isolated.
- Prepared for training (in `exports/training/`):
  - `training_4333_dump.jsonl` (5019 rows)
  - `training_high_signal.jsonl` (1501 rows, 73%+ ai-native from this dump, avg eff 0.278)
  - `training_ai_native.jsonl`
- High-signal oversampling recommended for memory/provenance typology (parallel to Moltbook).
- To include: Ensure `data/hyperlex_4333_dump.jsonl` is present when running export (or it was already merged into your live ingest).
- Full scoreboard + integration notes: `specs/007-hyperlexical-model/exports/TRAINING_READINESS.md`
- Mapping/history: `dataset-harvest.md` (section "4333-row Hyperlex dump integration")

Train from the live SoT via `--include-live`. Use the high-signal files above for optional weighting/oversampling of strong memory + provenance signals.

## Including the 4333 dump (if not already in live ingest)

If the 4333 data is not yet in your ~/.hyperlex/hyperlexical/ingest_candidates.jsonl:

```bash
# Copy the processed dump (provided separately or from exports/training/training_4333_dump.jsonl)
cp /path/to/training_4333_dump.jsonl data/hyperlex_4333_dump.jsonl

# Then run export (it will pick it up via harvest_4333_dump)
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live
```

The dump is included on export when the file is present (fields as stored; no inline memetic enrichment).

## Recommendations for this T1 run (4333 + high-signal)

- **Primary data**: Always use `--include-live` against the current operator SoT. The tracked `civilian.v0.1.jsonl` is only a seed snapshot.
- **4333 inclusion**: Copy `training_4333_dump.jsonl` (from exports/training/ or provided) to `data/hyperlex_4333_dump.jsonl` before export if not already merged into live ingest. Harvest copies dump fields only.
- **Oversampling**: Strongly recommended for memory/provenance signals. Use `exports/training/training_high_signal.jsonl` (1501 rows, 73%+ from 4333, avg eff 0.278). Prioritize rows with:
  - `memetic_efficiency` >= 0.3
  - `stage` == "hyperstition_ish" or strong "memory"/"provenance" in typology
  - Explicit 4333 provenance
- **Preflight verification**:
  ```bash
  PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live
  # Confirm 4333 rows appear with efficiency/tiers in output or MANIFEST
  PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --out /tmp/hlx-e2-before.json
  ```
- **Post-train**: Re-run eval_unbind. Check train-receipt for 4333 contribution. Send high-signal usage notes.
- **Artifacts to reference**:
  - `exports/training/training_high_signal.jsonl`
  - `exports/training/training_4333_dump.jsonl`
  - `exports/training/training_ai_native.jsonl`
  - `exports/TRAINING_READINESS.md` (full scoreboard)
  - `dataset-harvest.md` (integration history)
- Refresh high-signal locally if needed: `python scripts/curate_moltbook_seeds.py --high-signal` (extend for 4333 if new data).
