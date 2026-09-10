#!/usr/bin/env bash
# Hyperlex install script (modeled on Abraxas-Orchestra)
set -euo pipefail

TARGET="${HOME}/.hermes/skills/hyperlex"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "[dry-run] Would install to $TARGET"
fi

echo "Hyperlex symbolic integration install"
echo "Source: $(pwd)"
echo "Target: $TARGET"

if $DRY_RUN; then
  echo "[dry-run] Skipping actual copy"
  exit 0
fi

mkdir -p "$TARGET"
rsync -a --delete src/ "$TARGET/src/" 2>/dev/null || cp -r src/ "$TARGET/"
cp -r symbolic/ "$TARGET/symbolic/" 2>/dev/null || true
cp SKILL.md pyproject.toml README.md install.sh "$TARGET/" 2>/dev/null || true

echo "Installed. To use as skill: pip install -e . in the skill dir or activate via Hermes."
echo "Symbolic architecture applied."
