#!/usr/bin/env bash
set -euo pipefail
MODEL=${HLX_FAIR_MODEL:-/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65}
OUT=${HLX_BROAD_OUT:-/home/morpheus/hlx/broad-eval-observed.json}
PRIV=${HLX_BROAD_PRIV:-}
NAME=${HLX_BROAD_NAME:-hlx-broad-$(date +%s)}
if docker ps --format "{{.Names}}" | grep -qE "^hlx-(train|fair|broad)-"; then
  echo "REFUSE: GPU job already running"
  docker ps --format "{{.Names}}"
  exit 9
fi
ARGS=(
  --rm --name "$NAME" --gpus all
  -w /home/morpheus/Hyperlex
  -v /home/morpheus/.cache:/home/morpheus/.cache
  -v /home/morpheus/hlx:/home/morpheus/hlx
  -v /home/morpheus/Hyperlex:/home/morpheus/Hyperlex
  -v /home/morpheus/.hyperlex:/home/morpheus/.hyperlex
  -e HOME=/home/morpheus
  -e PYTHONPATH=scripts/shadow
  -e TOKENIZERS_PARALLELISM=false
  -e HYPERLEX_OFFLINE=1
  -e HF_HUB_OFFLINE=1
  -e HYPERLEX_TRUNK_DIR=/home/morpheus/.hyperlex/models/trunks/ModernBERT-base
  -e HYPERLEX_CUDA_MEM_FRACTION=0.3
  -e HLX_FAIR_MODEL="$MODEL"
  -e HLX_BROAD_OUT="$OUT"
)
if [[ -n "$PRIV" ]]; then ARGS+=(-e HLX_BROAD_PRIV="$PRIV"); fi
ARGS+=(lmsysorg/sglang:dev-qwen38-27b-dflash2 python /home/morpheus/hlx/eval_broad_observed.py)
echo "running broad eval $NAME model=$MODEL out=$OUT"
docker run "${ARGS[@]}"
echo "$NAME" > /home/morpheus/hlx/last-broad-container
