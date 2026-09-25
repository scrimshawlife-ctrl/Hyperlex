#!/usr/bin/env bash
# rc1 phase B: the ONE pre-registered test-split score (D7). rc1 + morph78 + morph65 together,
# each with its clean-val calibration from phase A. score_holdout.py refuses on manifest/slice drift
# and refuses to overwrite its output.
set -uo pipefail
cd /home/morpheus/Hyperlex
G=/home/morpheus/Hyperlex/scripts/spark/guard.py
R=specs/007-hyperlexical-model/receipts
O=$R/rc1-result-20260924
M=/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed
echo "=== [$(date -Is)] weight sha256 (manifest pins morph78 fc53676b..., morph65 96838b96...)"
sha256sum ${M}-rc1/model.safetensors ${M}-rc1/best/model.safetensors ${M}-morph78/model.safetensors ${M}-morph65/model.safetensors
echo "=== [$(date -Is)] score_holdout"
python $G 0.3 score_holdout --manifest $R/rc1-prereg-20260924/holdout-manifest-rc1.json \
  --model hyperlex-encoder-modernbert-base-seed-rc1=${M}-rc1=$O/calibration-rc1.json \
  --model hyperlex-encoder-modernbert-base-seed-morph78=${M}-morph78=$O/calibration-morph78.json \
  --model hyperlex-encoder-modernbert-base-seed-morph65=${M}-morph65=$O/calibration-morph65.json \
  --env scripts/spark/soft_ceiling/rc1-train-env.json --out $O/holdout-scores-rc1.json
echo "=== [$(date -Is)] exit=$? PHASE_B_DONE"
