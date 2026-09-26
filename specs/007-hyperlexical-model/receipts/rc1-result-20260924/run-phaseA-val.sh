#!/usr/bin/env bash
# rc1 phase A (val-only, no test rows read): E2 + corrected soft_ceiling broad eval + val calibration.
# Runs inside lmsysorg/sglang:dev-qwen38-27b-dflash2 with the training mount pattern, via guard.py 0.3.
set -uo pipefail
cd /home/morpheus/Hyperlex
G=/home/morpheus/Hyperlex/scripts/spark/guard.py
O=specs/007-hyperlexical-model/receipts/rc1-result-20260924
M=/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed
H=/home/morpheus/hlx
ENV=scripts/spark/soft_ceiling/rc1-train-env.json
TR="--trained $H/force_train_morph78_expanded.jsonl --trained $H/hard_atoms_train_morph78.jsonl --trained $H/force_train_morph50_expanded.jsonl --trained $H/hard_atoms_train_morph50.jsonl"
FH="--force $H/force_train_morph78_expanded.jsonl --force $H/force_train_morph50_expanded.jsonl --hard $H/hard_atoms_train_morph78.jsonl --hard $H/hard_atoms_train_morph50.jsonl"
step() { echo "=== [$(date -Is)] $*"; "$@"; rc=$?; echo "=== [$(date -Is)] exit=$rc :: $*"; return 0; }
step python $G 0.3 hyperlexical.eval_unbind --trunk-forward --model-dir ${M}-rc1 --out $O/e2-unbind-rc1.json
step python $G 0.3 eval_broad --model ${M}-rc1 $FH --out $O/broad-clean-val-rc1.json
step python $G 0.3 eval_broad --model ${M}-morph78 $FH --out $O/broad-clean-val-morph78.json
for s in rc1 morph78 morph65; do
  step python $G 0.3 calibrate_classify --model ${M}-$s $TR --env $ENV --out $O/calibration-$s.json
done
echo "=== [$(date -Is)] PHASE_A_DONE"
