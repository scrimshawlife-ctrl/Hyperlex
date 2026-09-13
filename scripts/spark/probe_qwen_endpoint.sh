#!/usr/bin/env bash
# Smoke the Hermes/Spark OpenAI-compatible Qwen gateway.
# Uses SPARK_OPENAI_API_KEY or OPENAI_API_KEY from the environment.
# Does not print the key.
set -euo pipefail

BASE="${OPENAI_BASE_URL:-https://qwen.zer0state.com/v1}"
BASE="${BASE%/}"
KEY="${SPARK_OPENAI_API_KEY:-${OPENAI_API_KEY:-}}"
MODEL="${OPENAI_MODEL:-/model}"

if [[ -z "$KEY" ]]; then
  echo "Set SPARK_OPENAI_API_KEY (or OPENAI_API_KEY). Refusing to probe." >&2
  exit 2
fi

echo "GET $BASE/models"
code=$(curl -sS -o /tmp/hlx-qwen-models.json -w "%{http_code}" \
  "$BASE/models" -H "Authorization: Bearer $KEY")
echo "HTTP $code"
python3 - <<'PY'
import json
from pathlib import Path
raw = Path("/tmp/hlx-qwen-models.json").read_text(encoding="utf-8")
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print(raw[:300])
    raise SystemExit(1)
ids = [m.get("id") for m in data.get("data", [])] if isinstance(data, dict) else []
print("models:", ids[:20] or data)
PY

echo "POST $BASE/chat/completions model=$MODEL"
code=$(curl -sS -o /tmp/hlx-qwen-chat.json -w "%{http_code}" \
  "$BASE/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":8}")
echo "HTTP $code"
python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("/tmp/hlx-qwen-chat.json").read_text(encoding="utf-8"))
choice = (data.get("choices") or [{}])[0]
msg = (choice.get("message") or {}).get("content") or choice.get("text")
print("reply:", (msg or str(data)[:200])[:200])
PY
