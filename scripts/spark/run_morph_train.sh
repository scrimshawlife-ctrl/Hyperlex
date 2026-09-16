#!/usr/bin/env bash
# Spark morph train launcher (canonical template for ~/hlx/run_morph_train.sh).
#
# CUDA memory: wraps hyperlexical.train via ~/hlx/guard.py.
# Default morph fraction is 0.3 (~39GB / 130GB) for exclusive-box climbs.
# Co-tenant / beside Qwen: export HYPERLEX_CUDA_MEM_FRACTION=0.03 (or pass
# a lower argv — env wins when set). See scripts/spark/guard.py.
set -euo pipefail
MORPH="${1:?morph number}"
shift
OUT="/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph${MORPH}"
RES="/home/morpheus/hlx/residual-morph${MORPH}.jsonl"
# Exclusive morph default. Override with HYPERLEX_CUDA_MEM_FRACTION for co-tenant.
GUARD_FRAC="${HYPERLEX_CUDA_MEM_FRACTION:-0.3}"
mkdir -p "$OUT"
NAME="hlx-train-morph${MORPH}-$(date +%s)"
echo "$NAME" > /home/morpheus/hlx/last-train-container
# base morph19 envelope; extra -e KEY=VAL from args as KEY=VAL pairs
EXTRA=()
for kv in "$@"; do
  EXTRA+=(-e "$kv")
done
# Pass fraction into the container so guard.py env override matches the launch.
EXTRA+=(-e "HYPERLEX_CUDA_MEM_FRACTION=${GUARD_FRAC}")
docker run -d --name "$NAME" --gpus all \
  -w /home/morpheus/Hyperlex \
  -v /home/morpheus/.cache:/home/morpheus/.cache \
  -v /home/morpheus/hlx:/home/morpheus/hlx \
  -v /home/morpheus/Hyperlex:/home/morpheus/Hyperlex \
  -v /home/morpheus/.hyperlex:/home/morpheus/.hyperlex \
  -e HOME=/home/morpheus \
  -e XDG_CACHE_HOME=/home/morpheus/.cache \
  -e TRITON_CACHE_DIR=/home/morpheus/.cache/triton \
  -e TORCHINDUCTOR_CACHE_DIR=/home/morpheus/.cache/inductor \
  -e PYTHONPATH=scripts/shadow \
  -e TOKENIZERS_PARALLELISM=false \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e PYTHONUNBUFFERED=1 \
  -e HYPERLEX_ALLOW_TRAIN=1 \
  -e HYPERLEX_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e HYPERLEX_INCLUDE_LIVE=1 \
  -e HYPERLEX_TRUNK_DIR=/home/morpheus/.hyperlex/models/trunks/ModernBERT-base \
  -e HYPERLEX_TRAIN_OUT="$OUT" \
  -e HYPERLEX_TRAIN_EPOCHS=6 \
  -e HYPERLEX_TRAIN_BATCH=8 \
  -e HYPERLEX_TRAIN_LR=2e-5 \
  -e HYPERLEX_LAST_TRAINABLE=4 \
  -e HYPERLEX_UNBIND_PRIMARY=slot_ce \
  -e HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=2 \
  -e HYPERLEX_UNBIND_HARD_UPSAMPLE=4 \
  -e HYPERLEX_UNBIND_HARD_ATOMS_PATH=/home/morpheus/hlx/hard_atoms_train.jsonl \
  -e HYPERLEX_UNBIND_FILLER_DENYLIST_PATH=/home/morpheus/hlx/filler-denylist-status.json \
  -e HYPERLEX_UNBIND_INFERRED_WEIGHT=1.0 \
  -e HYPERLEX_UNBIND_INFERRED_CAP=0 \
  -e HYPERLEX_UNBIND_MORPH_MARGIN=0.5 \
  -e HYPERLEX_UNBIND_CURRICULUM=1 \
  -e HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS=1 \
  -e HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS=1 \
  -e HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT=2 \
  -e HYPERLEX_UNBIND_LOSS_WEIGHT=1.0 \
  -e HYPERLEX_UNBIND_RESIDUAL_DUMP="$RES" \
  "${EXTRA[@]}" \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  python /home/morpheus/hlx/guard.py "${GUARD_FRAC}" hyperlexical.train --offline --run --include-live
echo "LAUNCHED $NAME OUT=$OUT GUARD_FRAC=$GUARD_FRAC"
