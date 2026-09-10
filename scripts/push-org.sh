#!/usr/bin/env bash
set -euo pipefail
# Push current main to the org remote. Personal remains SoT.
if ! git remote get-url org >/dev/null 2>&1; then
  echo "no org remote. add: git remote add org git@github.com:Zero-State-LLC/Hyperlex.git" >&2
  echo "create the org repo first (gh repo create Zero-State-LLC/Hyperlex)" >&2
  exit 2
fi
git push org main
