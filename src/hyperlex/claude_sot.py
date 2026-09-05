"""Local Claude SoT-cleared provenance (no live GitHub fetch)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

PIN_RELATIVE = Path("references") / "claude-sot-cleared.json"


def _git_ok(root: Path, *args: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
            env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
        )
    except OSError:
        return False
    return result.returncode == 0


def _git_text(root: Path, *args: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
            env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip() or None


def load_pin(root: Path) -> Optional[Dict[str, Any]]:
    path = Path(root) / PIN_RELATIVE
    if not path.is_file() or path.is_symlink():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _install_source_commit(root: Path) -> Optional[str]:
    marker = Path(root) / ".install-provenance.json"
    if not marker.is_file() or marker.is_symlink():
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    raw = str(data.get("source_commit") or "").strip()
    return raw or None


def _normalize_sha(raw: Optional[str]) -> Optional[str]:
    sha = str(raw or "").strip().lower()
    if len(sha) < 7 or any(c not in "0123456789abcdef" for c in sha):
        return None
    return sha


def _sha_match(left: str, right: str) -> bool:
    return left == right or left.startswith(right) or right.startswith(left)


def resolve_claude_sot_cleared(root: Path) -> Tuple[bool, str]:
    """Return (cleared, reason) from local pin + git/install provenance.

    Live GitHub fetch is never consulted.
    """
    pin = load_pin(root)
    if pin is None:
        return False, "no local pin file"
    pinned = _normalize_sha(str(pin.get("cleared_sha") or ""))
    if not pinned:
        return False, "pin missing cleared_sha"

    head = _normalize_sha(_git_text(Path(root), "rev-parse", "HEAD"))
    if head and _sha_match(head, pinned):
        return True, f"local HEAD matches pinned {pinned[:12]}"
    pin_present = _git_ok(Path(root), "cat-file", "-e", f"{pinned}^{{commit}}")
    if pin_present and _git_ok(Path(root), "merge-base", "--is-ancestor", pinned, "HEAD"):
        return True, f"local HEAD descends from pinned {pinned[:12]}"

    installed = _normalize_sha(_install_source_commit(root))
    if installed and _sha_match(installed, pinned):
        return True, f"install provenance matches pinned {pinned[:12]}"

    if pin.get("cleared") is True and pinned and not head and not installed:
        return True, f"pin cleared=true sha={pinned[:12]} (no local git)"
    if head and not pin_present:
        shallow = _git_text(Path(root), "rev-parse", "--is-shallow-repository")
        extra = "; shallow clone" if shallow == "true" else ""
        return False, (
            f"pin commit {pinned[:12]} not in local git objects{extra}; "
            f"cannot prove descent (no live GitHub fetch)"
        )
    return False, f"local provenance does not match pinned {pinned[:12]}"


def doctor_sot_should_fail(*, cleared: bool, claimed: bool) -> bool:
    """Prefer fail (not warn-only) when Claude packaging is claimed and uncleared."""
    return bool(claimed) and not bool(cleared)


def claude_packaging_claimed(*, home: Optional[Path] = None) -> bool:
    """True when a Claude personal skill, plugin, or env skill dir is present."""
    base = Path(home) if home is not None else Path.home()
    personal = base / ".claude" / "skills" / "hyperlex"
    plugin = base / ".claude" / "plugins" / "hyperlex"
    if (personal / "SKILL.md").is_file():
        return True
    if (plugin / ".claude-plugin" / "plugin.json").is_file() or (plugin / "SKILL.md").is_file():
        return True
    env_raw = os.environ.get("HYPERLEX_SKILL_DIR") or os.environ.get("CLAUDE_SKILL_DIR") or ""
    if env_raw:
        env_path = Path(env_raw).expanduser()
        if (env_path / "SKILL.md").is_file() or (env_path / "scripts" / "hyperlex.py").is_file():
            return True
    return False
