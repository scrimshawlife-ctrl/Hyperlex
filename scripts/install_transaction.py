"""Staged Hyperlex upgrades with target-keyed backups and recovery.

The two renames have an absent-target window; this is not crash-atomic. Stop
runtime writers during upgrades. A retained recovery directory requires operator
inspection. Locks are never automatically reclaimed. Validation subprocesses
use an isolated temporary home. This helper is Hyperlex-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

KIND = "hyperlex"
CHECKS = {
    KIND: [("hyperlex.py", "check"), ("hyperlex.py", "smoke")],
}
IGNORE = shutil.ignore_patterns(
    ".git",
    "skills",
    "out",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "*.pyc",
    ".worktrees",
    "graft",
    ".env",
    ".env.*",
    ".hermes",
    "*.pem",
    "*.key",
    ".superpowers",
    "superpowers",
)


def _refuse_symlink_target(target: Path, message: str) -> None:
    # Inspect the lexical path before resolve() follows a dangling link.
    if any(part.is_symlink() for part in (target.absolute(), *target.absolute().parents)):
        raise ValueError(message)


def _hermes_home() -> Path:
    raw = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
    return Path(raw).resolve()


def _git(source: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            check=False,
            args=["git", "-C", str(source), *args],
            capture_output=True,
            text=True,
            env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
        )
    except OSError:
        return None  # Git is optional for archive/Python-only installs.
    return result.stdout.strip() if result.returncode == 0 else None


def _assert_layout(source: Path, target: Path, home: Path, kind: str) -> Path:
    if source == target or source in target.parents or target in source.parents:
        raise ValueError("source and target must not overlap")
    if target in (Path("/"), Path.home().resolve(), home, home / "skills"):
        raise ValueError("refusing installation root")
    if target.exists() and not target.is_dir():
        raise ValueError("target must be a directory")
    key = hashlib.sha256(str(target).encode()).hexdigest()[:20]
    backups = home / "backups" / kind / key
    if target == backups or target in backups.parents or backups in target.parents:
        raise ValueError("backup and target must not overlap")
    return backups


def _assert_no_payload_symlinks(source: Path) -> None:
    # Reject payload links rather than shipping aliases into private source state.
    for directory, dirs, files in os.walk(source, followlinks=False):
        ignored = IGNORE(directory, dirs + files)
        dirs[:] = [d for d in dirs if d not in ignored]
        for name in dirs + [f for f in files if f not in ignored]:
            if (Path(directory) / name).is_symlink():
                raise ValueError(f"source payload symlink is not portable: {name}")


def _acquire_lock(target: Path) -> Path:
    lock = target.parent / ("." + target.name + ".install-lock")
    try:
        lock.mkdir()  # exclusive; never remove another installer's lock
    except FileExistsError as exc:
        raise FileExistsError(
            f"Install lock exists: {lock}. Do not reclaim automatically. "
            "Stop launchers and confirm no installer or runtime writer is active; "
            "inspect the target, sibling stage/recovery directories and backups. "
            "Only after resolving recovery, use rmdir on this exact empty lock "
            "(never recursive removal), then retry. See references/source-and-upgrades.md."
        ) from exc
    return lock


def _check_env(workspace: Path, stage: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("HYPERLEX_")}
    check_home = workspace / "check-home"
    check_home.mkdir()
    env.update(
        HOME=str(check_home),
        HERMES_HOME=str(check_home / ".hermes"),
        HERMES_SKILL_DIR=str(stage),
        PYTHONDONTWRITEBYTECODE="1",
    )
    return env


def _run_checks(stage: Path, kind: str, env: dict[str, str], skip_checks: bool) -> None:
    if skip_checks:
        return
    for command in CHECKS[kind]:
        subprocess.run(
            [sys.executable, str(stage / "scripts" / command[0]), *command[1:]],
            cwd=env["HOME"],
            env=env,
            check=True,
        )


def _preserve_legacy_out(target: Path, stage: Path) -> None:
    if (stage / "out").exists():
        shutil.rmtree(stage / "out")  # NEW staging data only
    old_out = target / "out"
    if old_out.is_symlink():
        (stage / "out").symlink_to(os.readlink(old_out), target_is_directory=True)
    elif old_out.exists():
        shutil.copytree(old_out, stage / "out", symlinks=True)


def _checkout_meta(source: Path) -> tuple[Path | None, str | None]:
    top = _git(source, "rev-parse", "--show-toplevel")
    repo_root = Path(top).resolve() if top is not None else None
    if repo_root == source:
        return repo_root, "."
    return None, None


def _write_receipt(
    source: Path,
    target: Path,
    stage: Path,
    kind: str,
    skip_checks: bool,
) -> dict[str, object]:
    repo_root, subtree = _checkout_meta(source)
    own_checkout = repo_root is not None
    dirty = _git(source, "status", "--porcelain") if own_checkout else None
    receipt: dict[str, object] = {
        "source": str(source),
        "source_repository_root": str(repo_root) if own_checkout else None,
        "source_subdirectory": subtree,
        "repository": _git(source, "remote", "get-url", "origin") if own_checkout else None,
        "source_commit": _git(source, "rev-parse", "HEAD") if own_checkout else None,
        "source_dirty": bool(dirty) if dirty is not None else None,
        "version": (source / "VERSION").read_text().strip(),
        "destination": str(target),
        "status": "UNVERIFIED" if skip_checks else "VALIDATED",
        "checks_skipped": list(CHECKS[kind]) if skip_checks else [],
        "validation": "staged runtime; activated contract/version read-back",
    }
    (stage / ".install-provenance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def _publish_backup(target: Path, backups: Path) -> Path | None:
    if not target.exists():
        return None
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / uuid.uuid4().hex
    # Incomplete copies live outside the selectable backup namespace.
    # Publish only after the payload and destination record are complete.
    with tempfile.TemporaryDirectory(prefix=".backup-incomplete-", dir=backups.parent) as tmp:
        pending = Path(tmp) / "backup-payload"
        shutil.copytree(target, pending, symlinks=True)
        marker = pending / ".backup-target.json"
        marker.unlink(missing_ok=True)
        marker.write_text(json.dumps({"destination": str(target)}) + "\n")
        os.replace(pending, backup)
    return backup


def _activate(
    target: Path,
    stage: Path,
    expected: dict[str, bytes],
    workspace: Path,
    backup: Path | None,
) -> None:
    displaced = workspace / "previous"
    try:
        if target.exists():
            os.replace(target, displaced)
        os.replace(stage, target)
        for relative, content in expected.items():
            if (target / relative).read_bytes() != content:
                raise OSError(f"activation read-back mismatch: {relative}")
    except BaseException as original:
        try:
            # Infer completed renames from disk even if replace raised after
            # its side effect. A still-staged package means target is not new.
            if not stage.exists() and target.exists():
                os.replace(target, workspace / "failed-package")
            if displaced.exists():
                os.replace(displaced, target)
        except BaseException as recovery_error:
            raise RuntimeError(
                f"recovery required at {workspace}; backup {backup}; "
                f"activation: {original}; restoration: {recovery_error}"
            ) from recovery_error
        raise


def install(source: Path, target: Path, kind: str, skip_checks: bool = False) -> None:
    if kind not in CHECKS:
        raise ValueError(f"unsupported skill kind: {kind}")
    _refuse_symlink_target(target, "refusing symlink target")
    source, target = source.resolve(), target.resolve()
    home = _hermes_home()
    backups = _assert_layout(source, target, home, kind)
    _assert_no_payload_symlinks(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = _acquire_lock(target)
    workspace = None
    retain_recovery = False
    try:
        workspace = Path(tempfile.mkdtemp(prefix="." + kind + "-stage-", dir=target.parent))
        stage = workspace / "package"
        shutil.copytree(source, stage, ignore=IGNORE)
        if not skip_checks:
            _run_checks(stage, kind, _check_env(workspace, stage), skip_checks)
        _preserve_legacy_out(target, stage)
        receipt = _write_receipt(source, target, stage, kind, skip_checks)
        expected = {
            path: (stage / path).read_bytes()
            for path in ("SKILL.md", "VERSION", ".install-provenance.json")
        }
        backup = _publish_backup(target, backups)
        _refuse_symlink_target(target, "target became a symlink during staging")
        try:
            _activate(target, stage, expected, workspace, backup)
        except RuntimeError:
            retain_recovery = True
            raise
        print(f"Installed {kind}: {target} ({receipt['status']})")
        if backup:
            print(f"Backup: {backup}")
    finally:
        if workspace is not None and not retain_recovery:
            shutil.rmtree(workspace)
        lock.rmdir()


def rollback(target: Path, kind: str, skip_checks: bool = False) -> None:
    if kind not in CHECKS:
        raise ValueError(f"unsupported skill kind: {kind}")
    _refuse_symlink_target(target, "refusing symlink target")
    target = target.resolve()
    home = _hermes_home()
    key = hashlib.sha256(str(target).encode()).hexdigest()[:20]
    backups = home / "backups" / kind / key
    candidates = sorted(
        backups.glob("*"), key=lambda p: p.lstat().st_mtime_ns, reverse=True
    )
    backup = None
    for candidate in candidates:
        marker = candidate / ".backup-target.json"
        if candidate.is_symlink() or not candidate.is_dir() or marker.is_symlink():
            continue
        try:
            record = json.loads(marker.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(record, dict) and record.get("destination") == str(target):
            backup = candidate
            break
    if backup is None:
        raise ValueError(
            f"no target-bound backup for {target}; legacy backups require manual review"
        )
    # Reuse staged runtime checks, backup, activated read-back and failed-rename recovery.
    install(backup, target, kind, skip_checks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target")
    parser.add_argument("kind", choices=CHECKS)
    parser.add_argument("--skip-checks", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    try:
        if not args.target.strip():
            raise ValueError("empty target")
        if args.rollback:
            rollback(Path(args.target), args.kind, args.skip_checks)
        else:
            install(args.source, Path(args.target), args.kind, args.skip_checks)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
