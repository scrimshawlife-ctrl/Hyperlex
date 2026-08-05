#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR" && pwd)"
TARGET="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
DRY_RUN="${1:-}"

if [[ "${DRY_RUN}" == "--dry-run" ]]; then
  echo "[hyperlex] dry-run enabled"
fi

cat <<MSG
[hyperlex] install plan
  source: $ROOT_DIR
  target: $TARGET
  dry-run: $([[ "${DRY_RUN}" == "--dry-run" ]] && echo true || echo false)
MSG

if [[ "${DRY_RUN}" == "--dry-run" ]]; then
  echo "[hyperlex] manifest: $([[ -f "$ROOT_DIR/hyperlex.manifest.yaml" ]] && echo ok || echo missing)"
  echo "[hyperlex] scripts: $([[ -d "$ROOT_DIR/scripts" ]] && echo ok || echo missing)"
  echo "[hyperlex] package: $([[ -d "$ROOT_DIR/src/hyperlex" ]] && echo ok || echo missing)"
  echo "[hyperlex] schemas: $([[ -f "$ROOT_DIR/schemas/ingest.v1.schema.json" && -f "$ROOT_DIR/schemas/result.v1.schema.json" && -f "$ROOT_DIR/schemas/receipt.v1.schema.json" ]] && echo ok || echo missing)"
  echo "[hyperlex] dry-run complete"
  exit 0
fi

mkdir -p "$TARGET"
mkdir -p "$TARGET/.hermes"

if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete --exclude '.git' --exclude '__pycache__' --exclude '.pytest_cache' "$ROOT_DIR/" "$TARGET/"
else
  # Fallback for minimal environments where rsync is not present.
  mkdir -p "$TARGET"
  cp -a "$ROOT_DIR/." "$TARGET/"
  rm -rf "$TARGET/.git"
fi

chmod +x "$TARGET/install.sh" "$TARGET/scripts/hyperlex.py"

echo "[hyperlex] installed to $TARGET"
echo "[hyperlex] quick check: python3 \"$TARGET/scripts/hyperlex.py\" check"
