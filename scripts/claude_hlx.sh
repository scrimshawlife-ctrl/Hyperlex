#!/usr/bin/env bash
# Claude Code operator entry — set skill dir + HLX, then exec hyperlex.py.
# Mirrors the Hermes operator path. Offline. No network. No secrets.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_root="$(cd "${_here}/.." && pwd)"

_resolve_skill_dir() {
  local candidate
  for candidate in \
    "${HYPERLEX_SKILL_DIR:-}" \
    "${CLAUDE_SKILL_DIR:-}" \
    "${HERMES_SKILL_DIR:-}" \
    "${_root}" \
    "${HOME}/.claude/skills/hyperlex" \
    "${HOME}/.claude/plugins/hyperlex" \
    "${HOME}/.hermes/skills/hyperlex"
  do
    [[ -n "${candidate}" ]] || continue
    if [[ -f "${candidate}/scripts/hyperlex.py" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

SKILL_DIR="$(_resolve_skill_dir)" || {
  printf 'error: Hyperlex CLI not found. Run: bash install.sh --claude\n' >&2
  exit 1
}

export HYPERLEX_SKILL_DIR="${SKILL_DIR}"
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-${SKILL_DIR}}"
export HLX="${HLX:-python3 ${SKILL_DIR}/scripts/hyperlex.py}"

exec python3 "${SKILL_DIR}/scripts/hyperlex.py" "$@"
