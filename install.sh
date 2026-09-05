#!/usr/bin/env bash
# Hyperlex — Hermes skill installer (Claude Code is an additional host)
# Usage:
#   ./install.sh
#   ./install.sh --dry-run
#   ./install.sh --target DIR
#   ./install.sh --rollback
#   ./install.sh --openclaw
#   ./install.sh --claude
#   ./install.sh --claude-plugin
#   ./install.sh --version
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_ROOT="${HERMES_HOME:-$HOME/.hermes}"
DEFAULT_TARGET="${HERMES_ROOT}/skills/hyperlex"
OPENCLAW_TARGET="${HOME}/.openclaw/skills/hyperlex"
CLAUDE_SKILL_TARGET="${HOME}/.claude/skills/hyperlex"
CLAUDE_PLUGIN_TARGET="${HOME}/.claude/plugins/hyperlex"
CLAUDE_HELPERS=(
  hyperlex-demo
  hyperlex-wizard
  hyperlex-scan
  hyperlex-analyze
  hyperlex-pending
  hyperlex-settle
)

VERSION="$(tr -d '[:space:]' < "${ROOT}/VERSION" 2>/dev/null || echo "0.0.0")"

DRY_RUN=0
ROLLBACK=0
ALLOW_OUTSIDE_HOME=0
INSTALL_OPENCLAW=0
INSTALL_CLAUDE=0
INSTALL_CLAUDE_PLUGIN=0
SKIP_SMOKE=0
TARGET="$DEFAULT_TARGET"

usage() {
  cat <<EOF
Hyperlex Hermes skill installer v${VERSION}

Usage: ./install.sh [options]

Hermes remains the default target. Claude flags are additive extra hosts.

Options:
  --dry-run               Show actions without writing
  --target DIR            Install to DIR (default: ${DEFAULT_TARGET})
  --rollback              Restore most recent target-keyed backup
  --openclaw              Also install to ~/.openclaw/skills/hyperlex
  --claude                Also install personal skill to ~/.claude/skills/hyperlex
                          plus slash helpers (hyperlex-demo, …) as sibling skills
  --claude-plugin         Also install plugin tree to ~/.claude/plugins/hyperlex
  --skip-smoke            Skip staged check/smoke (marks UNVERIFIED)
  --allow-outside-home    Permit --target outside \$HOME
  --version               Print version and exit
  -h, --help              Show this help

Claude paths:
  Personal skill:  ~/.claude/skills/hyperlex/   (SKILL.md + scripts/src)
  Local plugin:    ~/.claude/plugins/hyperlex/  (.claude-plugin/ + commands/)
  Project helpers: .claude/skills/ in this repo (when the checkout is the project)
EOF
}

log()  { printf '==> %s\n' "$*"; }
warn() { printf '!!  %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

resolve_path() {
  python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

is_forbidden_prefix() {
  case "$1" in
    /|/etc|/usr|/bin|/sbin|/System|/boot|/dev|/proc|/sys) return 0 ;;
    /etc/*|/usr/*|/bin/*|/sbin/*|/System/*) return 0 ;;
    *) return 1 ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --rollback) ROLLBACK=1; shift ;;
    --openclaw) INSTALL_OPENCLAW=1; shift ;;
    --claude) INSTALL_CLAUDE=1; shift ;;
    --claude-plugin) INSTALL_CLAUDE_PLUGIN=1; shift ;;
    --skip-smoke) SKIP_SMOKE=1; shift ;;
    --allow-outside-home) ALLOW_OUTSIDE_HOME=1; shift ;;
    --version) echo "$VERSION"; exit 0 ;;
    --target)
      [[ $# -ge 2 ]] || die "--target requires a path"
      TARGET="$2"
      shift 2
      ;;
    --target=*) TARGET="${1#--target=}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

validate_target() {
  python3 - "$TARGET" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1]).expanduser().absolute()
if not sys.argv[1].strip() or any(q.is_symlink() for q in (p, *p.parents)):
    raise SystemExit("refusing empty or symlinked target path")
PY

  local parent base resolved home_resolved
  parent="$(dirname "$TARGET")"
  base="$(basename "$TARGET")"
  # Path resolution and dry-run must not create target parents.
  resolved="$(resolve_path "$parent")/${base}"
  TARGET="$resolved"

  [[ -n "$TARGET" ]] || die "empty target"
  [[ "$TARGET" != "/" ]] || die "refusing filesystem root"
  [[ "$TARGET" != "$HOME" ]] || die "refusing \$HOME itself"

  home_resolved="$(resolve_path "$HOME")"
  if [[ "$TARGET" != "$home_resolved" && "$TARGET" != "$home_resolved"/* ]]; then
    if is_forbidden_prefix "$TARGET"; then
      die "refusing system path: ${TARGET}"
    fi
    if [[ $ALLOW_OUTSIDE_HOME -ne 1 ]]; then
      die "target outside \$HOME (${TARGET}); use --allow-outside-home if intentional"
    fi
    warn "installing outside \$HOME: ${TARGET}"
  fi
}

validate_source() {
  log "Validating source at ${ROOT}"
  local required=(
    "SKILL.md"
    "hyperlex.manifest.yaml"
    "VERSION"
    "scripts/hyperlex.py"
    "scripts/hlx-mutation"
    "scripts/claude_hlx.sh"
    "scripts/install_transaction.py"
    ".claude-plugin/plugin.json"
    "src/hyperlex/__init__.py"
    "src/hyperlex/calibration/scoring.py"
    "src/hyperlex/schemas/result.v1.schema.json"
    "schemas/ingest.v1.schema.json"
    "schemas/result.v1.schema.json"
    "schemas/receipt.v1.schema.json"
    "schemas/forecast.v1.schema.json"
    "schemas/settlement.v1.schema.json"
    "schemas/brier_series.v1.schema.json"
    "schemas/lineage.v1.schema.json"
    "schemas/mutation_trace.v0.1.schema.json"
  )
  local f
  for f in "${required[@]}"; do
    [[ -f "${ROOT}/${f}" ]] || die "missing required file: ${f}"
  done
  python3 -c "import ast, pathlib; ast.parse(pathlib.Path(r'''${ROOT}/scripts/hyperlex.py''').read_text())" \
    || die "scripts/hyperlex.py failed syntax check"
  python3 -c "import ast, pathlib; ast.parse(pathlib.Path(r'''${ROOT}/scripts/hlx-mutation''').read_text())" \
    || die "scripts/hlx-mutation failed syntax check"
  python3 -c "import ast, pathlib; ast.parse(pathlib.Path(r'''${ROOT}/scripts/install_transaction.py''').read_text())" \
    || die "scripts/install_transaction.py failed syntax check"
  log "Source validation OK"
}

run_transaction() {
  local dest="$1"
  local check_args=()
  [[ $SKIP_SMOKE -eq 1 ]] && check_args+=(--skip-checks)
  python3 "${ROOT}/scripts/install_transaction.py" "$ROOT" "$dest" hyperlex "${check_args[@]}"
}

install_extra_host() {
  local dest="$1"
  local label="$2"
  local _saved="$TARGET"
  TARGET="$dest"
  validate_target
  if [[ $DRY_RUN -eq 1 ]]; then
    log "DRY RUN: would also install ${label} to ${TARGET}"
    TARGET="$_saved"
    return 0
  fi
  run_transaction "$TARGET"
  TARGET="$_saved"
}

copy_claude_helpers() {
  local dest_root="${HOME}/.claude/skills"
  local name src dest
  for name in "${CLAUDE_HELPERS[@]}"; do
    src="${ROOT}/.claude/skills/${name}/SKILL.md"
    dest="${dest_root}/${name}/SKILL.md"
    if [[ ! -f "$src" ]]; then
      warn "Claude helper missing in source: ${src}"
      continue
    fi
    if [[ $DRY_RUN -eq 1 ]]; then
      log "DRY RUN: would install Claude helper ${name} → ${dest}"
      continue
    fi
    mkdir -p "$(dirname "$dest")"
    cp -f "$src" "$dest"
  done
}

do_rollback() {
  validate_target
  if [[ $DRY_RUN -eq 1 ]]; then
    log "DRY RUN: would validate and restore a backup bound to ${TARGET}"
    log "DRY RUN: locks are never auto-reclaimed; two-rename restore is not crash-atomic"
    return 0
  fi
  local check_args=()
  [[ $SKIP_SMOKE -eq 1 ]] && check_args+=(--skip-checks)
  python3 "${ROOT}/scripts/install_transaction.py" "$ROOT" "$TARGET" hyperlex --rollback "${check_args[@]}"
}

if [[ $ROLLBACK -eq 1 ]]; then
  do_rollback
  exit 0
fi

validate_source
validate_target

if [[ $DRY_RUN -eq 1 ]]; then
  log "DRY RUN: would staged-validate then activate Hyperlex v${VERSION} → ${TARGET}"
  log "DRY RUN: two-rename activation is not crash-atomic; locks are never auto-reclaimed"
  [[ -d "$TARGET" ]] && log "DRY RUN: would publish a target-keyed backup under ${HERMES_ROOT}/backups/hyperlex/"
  [[ $INSTALL_OPENCLAW -eq 1 ]] && log "DRY RUN: would also install to ${OPENCLAW_TARGET}"
  [[ $INSTALL_CLAUDE -eq 1 ]] && log "DRY RUN: would also install Claude personal skill to ${CLAUDE_SKILL_TARGET}"
  [[ $INSTALL_CLAUDE -eq 1 ]] && copy_claude_helpers
  [[ $INSTALL_CLAUDE_PLUGIN -eq 1 ]] && log "DRY RUN: would also install Claude plugin dir to ${CLAUDE_PLUGIN_TARGET}"
  exit 0
fi

run_transaction "$TARGET"

if [[ $INSTALL_OPENCLAW -eq 1 ]]; then
  install_extra_host "$OPENCLAW_TARGET" "OpenClaw"
fi

if [[ $INSTALL_CLAUDE -eq 1 ]]; then
  install_extra_host "$CLAUDE_SKILL_TARGET" "Claude personal skill"
  copy_claude_helpers
fi

if [[ $INSTALL_CLAUDE_PLUGIN -eq 1 ]]; then
  install_extra_host "$CLAUDE_PLUGIN_TARGET" "Claude plugin"
fi

echo ""
if [[ $SKIP_SMOKE -eq 1 ]]; then
  log "Hyperlex v${VERSION} installed — UNVERIFIED (--skip-smoke)"
else
  log "Hyperlex v${VERSION} installed"
fi
echo "  Hermes:  ${TARGET}"
[[ $INSTALL_OPENCLAW -eq 1 ]] && echo "  OpenClaw: ${OPENCLAW_TARGET}"
[[ $INSTALL_CLAUDE -eq 1 ]] && echo "  Claude:   ${CLAUDE_SKILL_TARGET}"
[[ $INSTALL_CLAUDE_PLUGIN -eq 1 ]] && echo "  Plugin:   ${CLAUDE_PLUGIN_TARGET}"
echo ""
echo "Next:"
echo "  export HERMES_SKILL_DIR=\"${TARGET}\""
echo "  python3 \"\$HERMES_SKILL_DIR/scripts/hyperlex.py\" check"
echo "  python3 \"\$HERMES_SKILL_DIR/scripts/hyperlex.py\" pipeline \"rizz\" --route offline"
echo "  python3 \"\$HERMES_SKILL_DIR/scripts/hlx-mutation\" trace \"it's giving mid rizz\""
if [[ $INSTALL_CLAUDE -eq 1 ]]; then
  echo "  export HYPERLEX_SKILL_DIR=\"${CLAUDE_SKILL_TARGET}\""
  echo "  export HLX=\"python3 \$HYPERLEX_SKILL_DIR/scripts/hyperlex.py\""
  echo "  bash \"\$HYPERLEX_SKILL_DIR/scripts/claude_hlx.sh\" check"
  echo "  # Reload Claude Code so it sees ~/.claude/skills/hyperlex"
fi
if [[ $INSTALL_CLAUDE_PLUGIN -eq 1 ]]; then
  echo "  # Enable the local plugin, or: claude plugin add ${CLAUDE_PLUGIN_TARGET}"
fi
echo "  # Reload Hermes skills if the agent is already running"
echo ""
