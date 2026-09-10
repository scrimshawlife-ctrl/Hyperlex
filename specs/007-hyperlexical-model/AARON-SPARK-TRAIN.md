# Aaron — Spark train handoff (007)

Owner of this run: Aaron on the DGX Spark.  
Owner of the spec: Danny.  
Branch: `007-hyperlexical-model` (PR 19).  
Do not train from `main` until this branch is merged or you check it out.

This is a **seed smoke**, not a Hyperlexical card. E2 has not passed. Name-gate is false. Do not upload to Hugging Face. Do not say the model is Hyperlexical.

## 0. What you are doing

Fine-tune frozen-contract trunk `answerdotai/ModernBERT-base` (~149M) with two heads:

- lineage classify (8 families + `none`; `ytd_leaf` unused unless rows exist)
- unbind linear head on last-layer **token** states

Box: NVIDIA DGX Spark, GB10, 128 GB unified, aarch64, compute `sm_121`.

## 1. Preflight (must all pass)

```bash
cd /path/to/Hyperlex
git fetch origin
git checkout 007-hyperlexical-model
git pull --ff-only origin 007-hyperlexical-model || true

uname -m          # expect aarch64
python3 -V        # 3.10+

PYTHONPATH=scripts/shadow python3 -m hyperlexical.preflight
```

`preflight` exit 0 = ready to consider train.  
Exit 2 = gate closed (missing flag, trunk, or jsonl).  
Exit 3 = eval stub still in place; that is normal **before** train.

Also run, and keep the JSON:

```bash
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --out /tmp/hlx-e2-before.json
echo $?
# expect 3  (stub loses to Spec 004)
```

If `eval_unbind` exits 0 on the stub, stop and ping Danny. That means the probe or the stub comparison is wrong.

## 2. Local trunk (once)

Do this on Spark NVMe. Not into git.

```bash
mkdir -p ~/.hyperlex/models/trunks
# Use whatever DGX-OS cache tool you already have.
# Official id: answerdotai/ModernBERT-base
# Resulting directory must contain config.json + tokenizer files + weights.

export HYPERLEX_TRUNK_DIR="$HOME/.hyperlex/models/trunks/ModernBERT-base"
ls "$HYPERLEX_TRUNK_DIR/config.json"
```

Rules:

- `local_files_only=True` in the train loop. If the dir is incomplete, the job aborts.
- Do not swap in an instruct/chat checkpoint.
- Do not use MiniLM as the T1 trunk.
- Do not use ModernBERT-large as the named card. Teacher only, and not this smoke.

## 3. Env

```bash
export HYPERLEX_ALLOW_TRAIN=1
export HYPERLEX_TRUNK_DIR="$HOME/.hyperlex/models/trunks/ModernBERT-base"
export HYPERLEX_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
```

Optional:

```bash
export HYPERLEX_TRAIN_OUT="$HOME/.hyperlex/models/hyperlex-encoder-modernbert-base-seed"
export HYPERLEX_TRAIN_EPOCHS=2
export HYPERLEX_TRAIN_BATCH=8
export HYPERLEX_TRAIN_LR=2e-5
```

## 4. Train smoke

```bash
PYTHONPATH=scripts/shadow python3 -m hyperlexical.train --offline --run
```

Without `--run`, train only prints the gate status.  
Without the two env vars, exit 2.

Writes (outside git):

- `$HYPERLEX_TRAIN_OUT/config-train.json` — hyperparams, data sha256, trunk path
- `$HYPERLEX_TRAIN_OUT/heads.pt` — if torch ran
- `$HYPERLEX_TRAIN_OUT/train-receipt.json` — `brier: null`, `e2_pass: false` unless you re-run eval after load

Do not commit those files.

## 5. After the job

```bash
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --out /tmp/hlx-e2-after.json
```

Send Danny:

1. `preflight` JSON
2. export `MANIFEST.json` sha256 + counts
3. `/tmp/hlx-e2-before.json` and `/tmp/hlx-e2-after.json`
4. `train-receipt.json`
5. uname, `python3 -V`, torch version, whether `sm_121` kernels actually ran
6. One sentence: smoke ok / smoke failed / E2 still false (expected)

## 6. Hard no

- No Hugging Face upload
- No `hyperlex-structure-149m` name
- No chat template
- No refusal head
- No Brier number
- No `semantic` route
- No 7B "because it fits"
- No Orin Nano as this train box
- No Spec 006 IsA labels
- No restricted / wrap / jailbreak rows
- No `~/.hyperlex` ledger copy into the repo

## 7. If Spark torch cannot talk to `sm_121`

Stop. Do not pin an old x86 wheel. Write the error + driver/CUDA/torch versions in the receipt and hand it back. The spec does not authorize a CPU-only "train" as a named encoder.

## 8. What success is for this smoke

- Job starts from a local trunk
- Loss moves on classify rows
- Receipt written with `brier: null`
- E2 still false unless you somehow beat 004 on the TPR fixtures (unlikely on this seed; do not force it)
- Repo dirty state does not include weight binaries
