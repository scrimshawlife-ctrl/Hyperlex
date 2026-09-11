# Aaron — Spark train handoff (007)

Owner of this run: Aaron on the DGX Spark.  
Owner of the spec: Danny.  
Use current **`main`**. Do not use the old `007-hyperlexical-model` branch.

This is a **seed smoke**, not a Hyperlexical card. E2 has not passed. Name-gate is false. Do not upload to Hugging Face. Do not say the model is Hyperlexical.

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
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export
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

## Moltbook high-signal prep (agent memory hyperstitions)
- Moltbook data (agent discourse on memory, provenance, KDR, rented cognition, episodic/rubric tiers) is integrated as first-class ai-native source.
- Dedicated high-signal subset: `data/moltbook_hyperlexical_high_signal.jsonl` (44 rows, 15 hyperstition_ish, strong provenance/memory).
- In civilian export (via harvest_moltbook): ~314 high-signal-ish ai-native rows.
- For this train: oversample the high-signal file or filter civilian for "memory" + "provenance" + high eff to strengthen memory typology and hyperstition signals.
- Eval on high-signal: avg eff 0.593, hyperstition_rate 0.295, provenance_density 0.682 (strong lift).
- After export: `python scripts/curate_moltbook_seeds.py --high-signal` to refresh if needed.
- MANIFEST has moltbook_integration.high_signal_subset details.

## Moltbook high-signal for this train
- High-signal file now in exports/: `moltbook_high_signal.jsonl` (44 rows, 15 hyperstition_ish, strong agent memory/provenance from Moltbook).
- Civilian export already merges Moltbook data (314+ ai-native rows with memory typology).
- For training: the civilian.v0.1.jsonl has the data; oversample or weight rows matching "moltbook" provenance or "memory" + "provenance" typology + high efficiency to boost the memory architecture signals in the model.
- Run `python scripts/curate_moltbook_seeds.py --high-signal` post-export if refreshing.
- See dataset-harvest.md for full Moltbook integration details.
- Eval on high-signal shows strong lift: avg eff 0.593, hyperstition rate 0.295, provenance density 0.682.
