# Spark run order — seed-rc2 (post-rc1)

Operator / Hermes on a host that can `ssh spark` → `spark-bf46` as `morpheus`.  
Pre-reg: `receipts/20260926-rc2-preregistration.md`. Env: `scripts/spark/soft_ceiling/rc2-train-env.json`.

## 0. Sync code

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
cd ~/Hyperlex
git fetch origin
git checkout main
git pull --ff-only origin main
# or the PR branch that carries rc2 prep
hostname; git rev-parse --short HEAD
REMOTE
```

## 1. Census + flag (read-only)

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
cd ~/Hyperlex
export PYTHONPATH=scripts/shadow:scripts/spark/soft_ceiling
export HYPERLEX_OFFLINE=1 HYPERLEX_INCLUDE_LIVE=1 HYPERLEX_RELEASE_SET=1
export HYPERLEX_FILLER_FILTER=strict HYPERLEX_TASK_ROUTING=legacy_split
mkdir -p specs/007-hyperlexical-model/receipts/rc2-prereg-20260926
python scripts/spark/soft_ceiling/flag_rows.py \
  --trained /home/morpheus/hlx/force_train_morph78_expanded.jsonl \
  --trained /home/morpheus/hlx/hard_atoms_train_morph78.jsonl \
  --trained /home/morpheus/hlx/force_train_morph50_expanded.jsonl \
  --trained /home/morpheus/hlx/hard_atoms_train_morph50.jsonl \
  --out-dir specs/007-hyperlexical-model/receipts/rc2-prereg-20260926/flags
python scripts/spark/soft_ceiling/heldout_census.py \
  --holdout-manifest specs/007-hyperlexical-model/receipts/rc1-prereg-20260924/holdout-manifest-rc1.json \
  --trained /home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph78/train-receipt.json \
  --out-dir specs/007-hyperlexical-model/receipts/rc2-prereg-20260926/census
REMOTE
```

Census must report a drawable pool (`DRAW_READY` / non-exhausted). Do not train if `POOL_EXHAUSTED`.

## 2. Freeze new holdout (before any train)

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
cd ~/Hyperlex
export PYTHONPATH=scripts/shadow:scripts/spark/soft_ceiling
export HYPERLEX_OFFLINE=1 HYPERLEX_INCLUDE_LIVE=1 HYPERLEX_RELEASE_SET=1
export HYPERLEX_FILLER_FILTER=strict HYPERLEX_TASK_ROUTING=legacy_split
python scripts/spark/soft_ceiling/holdout_manifest.py \
  --model /home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph78 \
  --model /home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65 \
  --trained /home/morpheus/hlx/force_train_morph78_expanded.jsonl \
  --trained /home/morpheus/hlx/hard_atoms_train_morph78.jsonl \
  --trained /home/morpheus/hlx/force_train_morph50_expanded.jsonl \
  --trained /home/morpheus/hlx/hard_atoms_train_morph50.jsonl \
  --out specs/007-hyperlexical-model/receipts/rc2-prereg-20260926/holdout-manifest-rc2.json
python - <<'PY'
import json
from pathlib import Path
m = json.loads(Path("specs/007-hyperlexical-model/receipts/rc2-prereg-20260926/holdout-manifest-rc2.json").read_text())
assert m["status"] == "FROZEN_NOT_SCORED", m["status"]
print("frozen ok", {k: v.get("n") for k, v in m.get("slices", {}).items()})
PY
REMOTE
```

Commit the manifest + census/flags before launch (separate docs commit on the train host or PR).

## 3. Launch train

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
cd ~/Hyperlex
test ! -f /home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-rc2/train-receipt.json
python scripts/spark/soft_ceiling/launch_train.py \
  --env scripts/spark/soft_ceiling/rc2-train-env.json \
  --tag rc2
cat /home/morpheus/hlx/last-train-container
REMOTE
```

Poll until container exits 0. Refuse if GPU already busy (`hlx-*` running).

## 4. Score once (val then test)

Copy pattern from `receipts/rc1-result-20260924/run-phaseA-val.sh` and `run-phaseB-test.sh`, swapping:

- model dir → `...-seed-rc2`
- manifest → `holdout-manifest-rc2.json`
- env → `rc2-train-env.json`
- out dir → `receipts/rc2-result-20260926/`

Do **not** pass `--apply-best` unless the decision rule PASSes and Danny says so.

## 5. Record

Write `receipts/rc2-result-YYYYMMDD/OPERATOR-CARD.md` with the five-rule table. Update `NEXT_MOVES_007.md`. BEST moves only on explicit promote.
