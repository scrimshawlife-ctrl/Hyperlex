#!/usr/bin/env bash
# morph15 civilian unbind climb — Spark operator card (Spec 007).
# Pin BEST seed-morph14 (unbind_exact≈0.3857). Ladder target 0.45.
# name_gate stays false. Do not Hub. Do not invent OBSERVED gold.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

: "${HYPERLEX_ALLOW_TRAIN:=1}"
: "${HYPERLEX_TRUNK_DIR:=$HOME/.hyperlex/models/trunks/ModernBERT-base}"
: "${HYPERLEX_OFFLINE:=1}"
: "${HYPERLEX_INCLUDE_LIVE:=1}"
: "${HYPERLEX_TRAIN_OUT:=$HOME/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph15}"
: "${HYPERLEX_TRAIN_EPOCHS:=6}"
: "${HYPERLEX_TRAIN_BATCH:=8}"
: "${HYPERLEX_TRAIN_LR:=2e-5}"

# Already-landed levers — do not search aux λ
export HYPERLEX_UNBIND_PRIMARY="${HYPERLEX_UNBIND_PRIMARY:-slot_ce}"
export HYPERLEX_UNBIND_OBSERVED_UPSAMPLE="${HYPERLEX_UNBIND_OBSERVED_UPSAMPLE:-2}"
export HYPERLEX_UNBIND_INFERRED_WEIGHT="${HYPERLEX_UNBIND_INFERRED_WEIGHT:-0.5}"
export HYPERLEX_UNBIND_CURRICULUM="${HYPERLEX_UNBIND_CURRICULUM:-1}"
export HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS="${HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS:-2}"
export HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS="${HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS:-1}"
export HYPERLEX_UNBIND_HARD_ATOMS_PATH="${HYPERLEX_UNBIND_HARD_ATOMS_PATH:-/home/morpheus/hlx/hard_atoms_train.jsonl}"
export HYPERLEX_UNBIND_HARD_UPSAMPLE="${HYPERLEX_UNBIND_HARD_UPSAMPLE:-3}"
export HYPERLEX_UNBIND_RESIDUAL_DUMP="${HYPERLEX_UNBIND_RESIDUAL_DUMP:-/tmp/hlx-morph15-residual.jsonl}"

export HYPERLEX_ALLOW_TRAIN HYPERLEX_TRUNK_DIR HYPERLEX_OFFLINE HYPERLEX_INCLUDE_LIVE
export HYPERLEX_TRAIN_OUT HYPERLEX_TRAIN_EPOCHS HYPERLEX_TRAIN_BATCH HYPERLEX_TRAIN_LR
export TOKENIZERS_PARALLELISM=false

echo "== morph15 preflight =="
test -f "$HYPERLEX_TRUNK_DIR/config.json" || {
  echo "missing trunk at $HYPERLEX_TRUNK_DIR" >&2
  exit 2
}
test -f "$HYPERLEX_UNBIND_HARD_ATOMS_PATH" || {
  echo "missing hard atoms JSONL at $HYPERLEX_UNBIND_HARD_ATOMS_PATH (fail closed)" >&2
  exit 2
}

PYTHONPATH=scripts/shadow python3 -m hyperlexical.preflight
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live

echo "== morph15 train =="
PYTHONPATH=scripts/shadow python3 -m hyperlexical.train --offline --run --include-live

echo "== morph15 residual summary =="
if [[ -f "${HYPERLEX_UNBIND_RESIDUAL_DUMP%.jsonl}.summary.json" ]]; then
  cat "${HYPERLEX_UNBIND_RESIDUAL_DUMP%.jsonl}.summary.json"
elif [[ -f "${HYPERLEX_UNBIND_RESIDUAL_DUMP}.summary.json" ]]; then
  cat "${HYPERLEX_UNBIND_RESIDUAL_DUMP}.summary.json"
fi

echo "== morph15 done =="
echo "OUT=$HYPERLEX_TRAIN_OUT"
echo "Send Danny: train-receipt.json + residual summary + e2 before/after."
echo "name_gate stays false."
