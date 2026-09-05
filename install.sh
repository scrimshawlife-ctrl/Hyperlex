#!/usr/bin/env bash
# Hyperlex — Hermes skill installer
# Usage:
#   ./install.sh
#   ./install.sh --dry-run
#   ./install.sh --target DIR
#   ./install.sh --rollback
#   ./install.sh --openclaw
#   ./install.sh --version
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_ROOT="${HERMES_HOME:-$HOME/.hermes}"
DEFAULT_TARGET="${HERMES_ROOT}/skills/hyperlex"
BACKUP_ROOT="${HERMES_ROOT}/receipts/hyperlex-backups"
OPENCLAW_TARGET="${HOME}/.openclaw/skills/hyperlex"

VERSION="$(tr -d '[:space:]' < "${ROOT}/VERSION" 2>/dev/null || echo "0.0.0")"

DRY_RUN=0
ROLLBACK=0
ALLOW_OUTSIDE_HOME=0
INSTALL_OPENCLAW=0
SKIP_SMOKE=0
TARGET="$DEFAULT_TARGET"

usage() {
  cat <<EOF
Hyperlex Hermes skill installer v${VERSION}

Usage: ./install.sh [options]

Options:
  --dry-run               Show actions without writing
  --target DIR            Install to DIR (default: ${DEFAULT_TARGET})
  --rollback              Restore most recent backup
  --openclaw              Also install to ~/.openclaw/skills/hyperlex
  --skip-smoke            Skip post-install smoke check
  --allow-outside-home    Permit --target outside \$HOME
  --version               Print version and exit
  -h, --help              Show this help
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
  )
  local f
  for f in "${required[@]}"; do
    [[ -f "${ROOT}/${f}" ]] || die "missing required file: ${f}"
  done
  python3 -c "import ast, pathlib; ast.parse(pathlib.Path(r'''${ROOT}/scripts/hyperlex.py''').read_text())" \
    || die "scripts/hyperlex.py failed syntax check"
  log "Source validation OK"
}

backup_existing() {
  if [[ ! -d "$TARGET" ]]; then
    return 0
  fi
  local stamp dest
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  dest="${BACKUP_ROOT}/${stamp}"
  log "Backing up existing install to ${dest}"
  if [[ $DRY_RUN -eq 1 ]]; then
    printf '[dry-run] cp -a %q %q\n' "$TARGET" "$dest"
  else
    mkdir -p "${BACKUP_ROOT}"
    cp -a "${TARGET}" "${dest}"
  fi
}

sync_tree() {
  local dest="$1"
  log "Installing to ${dest}"
  if [[ $DRY_RUN -eq 1 ]]; then
    printf '[dry-run] rsync/copy %q → %q\n' "$ROOT" "$dest"
    return 0
  fi
  mkdir -p "$dest"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete \
      --exclude '.git' \
      --exclude '.venv' \
      --exclude '__pycache__' \
      --exclude '.pytest_cache' \
      --exclude 'out/' \
      --exclude '*.pyc' \
      "${ROOT}/" "${dest}/"
  else
    tar -C "${ROOT}" \
      --exclude '.git' \
      --exclude '.venv' \
      --exclude '__pycache__' \
      --exclude '.pytest_cache' \
      --exclude 'out' \
      -cf - . | tar -C "${dest}" -xf -
  fi
  chmod +x "${dest}/install.sh" "${dest}/scripts/hyperlex.py" 2>/dev/null || true
  # rsync --exclude '.git' also skips deleting a leftover dest .git; drop it so the
  # skill install is never a nested half-repo from a prior manual checkout.
  if [[ -e "${dest}/.git" ]]; then
    rm -rf "${dest}/.git"
  fi
  mkdir -p "${dest}/.hermes"
  cat > "${dest}/.hermes/install-receipt.json" <<EOF
{
  "skill": "hyperlex",
  "version": "${VERSION}",
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source": "${ROOT}",
  "destination": "${dest}"
}
EOF
}

post_check() {
  local dest="$1"
  [[ $SKIP_SMOKE -eq 1 ]] && return 0
  [[ $DRY_RUN -eq 1 ]] && return 0
  log "Post-install check"
  if ! python3 "${dest}/scripts/hyperlex.py" check >/dev/null; then
    warn "check failed — run: python3 ${dest}/scripts/hyperlex.py check"
    return 1
  fi
  if ! python3 "${dest}/scripts/hyperlex.py" smoke >/dev/null; then
    warn "smoke failed — run: python3 ${dest}/scripts/hyperlex.py smoke"
    return 1
  fi
  log "Post-install check OK"
}

do_rollback() {
  validate_target
  if [[ $DRY_RUN -eq 1 ]]; then
    log "DRY RUN: would validate and restore a backup bound to ${TARGET}"
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
  log "DRY RUN: would install Hyperlex v${VERSION} → ${TARGET}"
  [[ -d "$TARGET" ]] && log "DRY RUN: would backup existing install under ${BACKUP_ROOT}"
  [[ $INSTALL_OPENCLAW -eq 1 ]] && log "DRY RUN: would also install to ${OPENCLAW_TARGET}"
  exit 0
fi

CHECK_ARGS=()
[[ $SKIP_SMOKE -eq 1 ]] && CHECK_ARGS+=(--skip-checks)
python3 "${ROOT}/scripts/install_transaction.py" "$ROOT" "$TARGET" hyperlex "${CHECK_ARGS[@]}"

if [[ $INSTALL_OPENCLAW -eq 1 ]]; then
  mkdir -p "$(dirname "$OPENCLAW_TARGET")"
  # reuse TARGET temporarily for openclaw path
  _saved="$TARGET"
  TARGET="$OPENCLAW_TARGET"
  validate_target
  python3 "${ROOT}/scripts/install_transaction.py" "$ROOT" "$TARGET" hyperlex "${CHECK_ARGS[@]}"
  TARGET="$_saved"
fi

echo ""
if [[ $SKIP_SMOKE -eq 1 ]]; then
  log "Hyperlex v${VERSION} installed — UNVERIFIED (--skip-smoke)"
else
  log "Hyperlex v${VERSION} installed"
fi
echo "  Hermes:  ${TARGET}"
[[ $INSTALL_OPENCLAW -eq 1 ]] && echo "  OpenClaw: ${OPENCLAW_TARGET}"
echo ""
echo "Next:"
echo "  export HERMES_SKILL_DIR=\"${TARGET}\""
echo "  python3 \"\$HERMES_SKILL_DIR/scripts/hyperlex.py\" check"
echo "  python3 \"\$HERMES_SKILL_DIR/scripts/hyperlex.py\" analyze --query \"sharp steam\" --source mock --forecasts"
echo "  # Reload Hermes skills if the agent is already running"
echo ""
