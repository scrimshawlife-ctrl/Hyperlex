#!/usr/bin/env bash
# Hyperlex operator burn-in — atomic offline runs + pending list.
# Never invents Brier. Never settles automatically.
set -euo pipefail

HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
HLX="${HLX:-python3 $HERMES_SKILL_DIR/scripts/hyperlex.py}"
export HYPERLEX_OFFLINE="${HYPERLEX_OFFLINE:-1}"

# Prefer skill tree; fall back to repo checkout
if [[ ! -f "$HERMES_SKILL_DIR/scripts/hyperlex.py" ]]; then
  ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
  HLX="python3 $ROOT/scripts/hyperlex.py"
  export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"
fi

echo "==> doctor"
$HLX doctor >/tmp/hlx-burn-doctor.json || true
python3 -c "import json;d=json.load(open('/tmp/hlx-burn-doctor.json'));print('ok',d.get('ok'),'version',d.get('version'))"

echo "==> terms-split demo"
$HLX terms-split "sigma rizz locked in" --no-lineage | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print('atoms', d['split']['terms'])"

# Automatic backend: one pipeline call can expand multi-term bags
echo "==> pipeline multi-term (auto expand → atoms → full results)"
$HLX pipeline "sigma rizz locked in" --route offline --no-phase5 >/tmp/hlx-burn-multi.json
python3 -c "import json;d=json.load(open('/tmp/hlx-burn-multi.json'));print('  atoms',d.get('atoms'),'n_forecasts',d.get('n_forecasts'),'brier',d.get('brier'))"

# Single-atom automatic runs
ATOMS=(rizz "locked in" "sharp money" "agentic slop")
for term in "${ATOMS[@]}"; do
  echo "==> pipeline atom: $term"
  $HLX pipeline "$term" --route offline >/tmp/hlx-burn-last.json
  python3 -c "import json;d=json.load(open('/tmp/hlx-burn-last.json'));r=d.get('result') or {};a=r.get('analysis') or {};print('  family',(a.get('lineage') or {}).get('family_id'),'risk',(d.get('phase5') or {}).get('risk_tier'),'n_fc',d.get('n_forecasts'),'brier',d.get('brier'))"
done

echo "==> pending (open forecasts — settle manually)"
$HLX pending --limit 20 | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print('n_open', d.get('n_open')); [print(' ',x.get('forecast_id'), x.get('signal_key')) for x in (d.get('open') or [])[:8]]"

echo "==> next"
echo "  settle:  \$HLX settle --forecast-id <id> --decision TRUE|FALSE|VOID"
echo "  series:  \$HLX score-series --mean-shift --verify-chain"
echo "  cron:    \$HLX risk-schedule --tier MODERATE --schedule-out /tmp/hlx-cron"
echo "  demos:   docs/demos/atomic-terms.md"
echo "done."
