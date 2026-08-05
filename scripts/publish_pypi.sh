#!/usr/bin/env bash
# Build and optionally publish hyperlex to PyPI.
# Usage:
#   ./scripts/publish_pypi.sh              # build only
#   ./scripts/publish_pypi.sh --test       # upload to TestPyPI
#   ./scripts/publish_pypi.sh --prod       # upload to PyPI
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null; then
  PY=python3
else
  echo "python3 required" >&2; exit 1
fi
MODE="${1:-build}"
echo "==> using $PY"
rm -rf dist/ build/ src/*.egg-info src/hyperlex.egg-info 2>/dev/null || true
"$PY" -m pip install -q --upgrade build twine
echo "==> building sdist + wheel"
"$PY" -m build
echo "==> checking"
"$PY" -m twine check dist/*
ls -la dist/
case "$MODE" in
  build)
    echo "Build only. Publish with:"
    echo "  TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-... $0 --test|--prod"
    ;;
  --test|test)
    : "${TWINE_PASSWORD:?set TWINE_PASSWORD to API token}"
    export TWINE_USERNAME="${TWINE_USERNAME:-__token__}"
    "$PY" -m twine upload --repository testpypi dist/*
    ;;
  --prod|prod|publish)
    : "${TWINE_PASSWORD:?set TWINE_PASSWORD to API token}"
    export TWINE_USERNAME="${TWINE_USERNAME:-__token__}"
    "$PY" -m twine upload dist/*
    ;;
  *) echo "unknown mode: $MODE" >&2; exit 2 ;;
esac
