#!/usr/bin/env bash
set -euo pipefail
OUT="/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph78"
MODEL="$OUT"
if [[ ! -f "$OUT/model.safetensors" && -f "$OUT/best/model.safetensors" ]]; then
  MODEL="$OUT/best"
fi
NAME="hlx-e2-morph78-$(date +%s)"
docker run --rm --name "$NAME" --gpus all \
  -w /home/morpheus/Hyperlex \
  -v /home/morpheus/.cache:/home/morpheus/.cache \
  -v /home/morpheus/hlx:/home/morpheus/hlx \
  -v /home/morpheus/Hyperlex:/home/morpheus/Hyperlex \
  -v /home/morpheus/.hyperlex:/home/morpheus/.hyperlex \
  -e HOME=/home/morpheus -e PYTHONPATH=scripts/shadow \
  -e TOKENIZERS_PARALLELISM=false -e HYPERLEX_OFFLINE=1 -e HF_HUB_OFFLINE=1 \
  -e HYPERLEX_TRUNK_DIR=/home/morpheus/.hyperlex/models/trunks/ModernBERT-base \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  python /home/morpheus/hlx/guard.py 0.3 hyperlexical.eval_unbind --trunk-forward \
    --model-dir "$MODEL" --out /home/morpheus/hlx/e2-unbind-morph78.json
