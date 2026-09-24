#!/usr/bin/env bash
set -euo pipefail
NAME=$(cat /home/morpheus/hlx/last-train-container)
PRIV=/home/morpheus/hlx-private/p1-spark-morph78-40ep-val-settle-20260924
OUT=/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph78
LOG=$PRIV/poll.log
mkdir -p "$PRIV"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) poll start $NAME" | tee -a "$LOG"
while docker inspect -f "{{.State.Running}}" "$NAME" 2>/dev/null | grep -q true; do
  case "$NAME" in
  hlx-train-morph78-*) ;;
  *) echo "REFUSE unexpected container $NAME" | tee -a "$LOG"; exit 9 ;;
  esac
  if [[ -f "$OUT/train-receipt.json" ]]; then
    python3 - <<'PY' | tee -a "$LOG" || true
import json
from pathlib import Path
d=json.loads(Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph78/train-receipt.json").read_text())
print("best ep", d.get("best_epoch") or d.get("val",{}).get("epoch"),
      "ue", d.get("best_unbind_exact") or d.get("val",{}).get("unbind_exact"),
      "fair", 1.0)
PY
  fi
  sleep 120
done
EC=$(docker inspect -f "{{.State.ExitCode}}" "$NAME" 2>/dev/null || echo missing)
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DONE ec=$EC" | tee -a "$LOG"
docker logs "$NAME" 2>&1 | tail -120 | tee -a "$PRIV/nohup.out" || true
if [[ -f "$OUT/train-receipt.json" ]]; then
  sudo chown -R morpheus:morpheus "$OUT" "$PRIV" 2>/dev/null || true
  /home/morpheus/hlx/run_e2_morph78.sh 2>&1 | tee -a "$LOG" || true
  HLX_FAIR_MODEL=/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65 \
    HLX_BROAD_OUT=/home/morpheus/hlx/broad-eval-prior-morph65.json \
    HLX_BROAD_PRIV=$PRIV \
    HLX_BROAD_NAME=hlx-broad-prior65-morph78-$(date +%s) \
    bash /home/morpheus/hlx/run_broad_eval.sh 2>&1 | tee -a "$LOG" || true
  HLX_FAIR_MODEL=$OUT \
    HLX_BROAD_OUT=/home/morpheus/hlx/broad-eval-morph78.json \
    HLX_BROAD_PRIV=$PRIV \
    HLX_BROAD_NAME=hlx-broad-morph78-$(date +%s) \
    bash /home/morpheus/hlx/run_broad_eval.sh 2>&1 | tee -a "$LOG" || true
  python3 - <<'PY' || true
import json
from pathlib import Path
lock=Path("/home/morpheus/hlx-private/p1-spark-morph78-40ep-val-settle-20260924/GATE_LOCK.json")
if lock.is_file():
    d=json.loads(lock.read_text())
    if d.get("status") == "done":
        raise SystemExit(0)
GATE_OWNER=morph78-val-settle python3 /home/morpheus/hlx/finish_morph78.py 2>&1 | tee -a "$LOG" || true
PY
else
  echo "NO_RECEIPT" | tee -a "$LOG"
fi
