"""Code provenance for train/eval receipts. No git binary needed.

``code_commit`` is read from ``.git`` files (the training container may not
ship git). ``code_tree_sha256`` hashes the shadow package source, so an
uncommitted edit changes it even when the commit does not.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
ENV_PREFIX = "HYPERLEX_"


def _git_dir(root: Path) -> Path | None:
    dot = root / ".git"
    if dot.is_dir():
        return dot
    if dot.is_file():
        text = dot.read_text(encoding="utf-8").strip()
        if text.startswith("gitdir:"):
            path = Path(text.split(":", 1)[1].strip())
            return path if path.is_absolute() else (root / path).resolve()
    return None


def code_commit(root: Path) -> str | None:
    """HEAD commit, or None if unreadable (e.g. worktree gitdir not mounted)."""
    try:
        git = _git_dir(root)
        if git is None:
            return None
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
        if not head.startswith("ref:"):
            return head or None
        ref = head.split(":", 1)[1].strip()
        dirs = [git]
        common = git / "commondir"
        if common.is_file():
            c = Path(common.read_text(encoding="utf-8").strip())
            dirs.append(c if c.is_absolute() else (git / c).resolve())
        for d in dirs:
            loose = d / ref
            if loose.is_file():
                return loose.read_text(encoding="utf-8").strip()
        for d in dirs:
            packed = d / "packed-refs"
            if packed.is_file():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line.endswith(" " + ref):
                        return line.split(" ", 1)[0]
    except OSError:
        return None
    return None


def code_tree_sha256(package: Path = PACKAGE) -> str:
    h = hashlib.sha256()
    for path in sorted(package.glob("*.py")):
        h.update(path.name.encode("utf-8") + b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def env_snapshot(environ: dict | None = None) -> dict[str, str]:
    env = os.environ if environ is None else environ
    return {k: env[k] for k in sorted(env) if k.startswith(ENV_PREFIX)}


def provenance(root: Path) -> dict:
    return {
        "code_commit": code_commit(root),
        "code_tree_sha256": code_tree_sha256(),
        "hyperlex_env": env_snapshot(),
    }
