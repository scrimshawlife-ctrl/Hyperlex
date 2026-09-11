# Aaron — Spark train handoff (007)

Owner of this run: Aaron on the DGX Spark.  
Owner of the spec: Danny.  
Use current **`main`**. Do not use the old `007-hyperlexical-model` branch.

This is a **seed smoke** for harness wiring, not a Hyperlexical card. E2 has not passed. Name-gate is false. Do not upload to Hugging Face. Do not say the model is Hyperlexical.

**Train data:** T1 / E2 work uses the **local SoT** (`~/.hyperlex/hyperlexical/ingest_candidates.jsonl`) via `PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live`. Do not train the named path from tracked `exports/civilian.v0.1.jsonl` alone — that file is an 883-row **seed/snapshot**. Operator `--include-live` (2026-09-10 PT evening): n=6506 · classify **2437** · unbind **1345** · negatives **208** · gaps 0/0/0 · `name_gate` false. Danny ~2500 bar: **met**.

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
# omit --include-live only for harness wiring against the tracked seed
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --out /tmp/hlx-e2-before.json
# expect exit 3
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
```

## 4. Train smoke

```bash
PYTHONPATH=scripts/shadow python3 -m hyperlexical.train --offline --run
```

Writes outside git: `heads.pt`, `layout.json`, `train-receipt.json`, `config-train.json`.
Do not commit them.

## 5. After

```bash
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --out /tmp/hlx-e2-after.json
```

Send Danny: preflight JSON, MANIFEST sha, e2 before/after, train-receipt.json, layout.json, torch/`sm_121` note.

## 6. Hard no

No Hub upload. No `hyperlex-structure-149m`. No chat template. No refusal head. No Brier. No `semantic`. No 7B. No Orin as this box. No 006 labels. No wrap rows. No weight binaries in git. No CPU-only named encoder if `sm_121` fails — stop and return the error.

## Moltbook subset (not the global SoT)

Moltbook is a first-class **ai-native** source (memory, provenance, KDR, rented cognition). It is a **subset**, not the civilian T1 SoT.

- High-signal file: `exports/moltbook_high_signal.jsonl` (44 rows). Optional oversample for memory/provenance typology.
- Historical tracked-export Moltbook counts (~314–360 ai-native inside the 883-row seed) are **not** current global SoT status.
- Train from local SoT / `--include-live`. Optionally weight rows with moltbook provenance or high memory+provenance efficiency.
- Refresh: `python scripts/curate_moltbook_seeds.py --high-signal`
- Mapping and history: `dataset-harvest.md`
