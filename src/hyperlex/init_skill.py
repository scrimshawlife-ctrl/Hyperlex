"""Wire Hyperlex into agent skill trees the way graft init does.

pip install hyperlex
hyperlex init
# writes a thin SKILL.md that tells the agent to call `hyperlex` on PATH
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional


def skill_targets() -> Dict[str, Path]:
    home = Path.home()
    return {
        "hermes": home / ".hermes" / "skills" / "hyperlex",
        "openclaw": home / ".openclaw" / "skills" / "hyperlex",
        "grok": home / ".grok" / "skills" / "hyperlex",
        "claude": home / ".claude" / "skills" / "hyperlex",
    }


# Import-time snapshot for existing tests; run_* recomputes via skill_targets().
TARGETS = skill_targets()

MARKER = "<!-- hyperlex-init -->"


def skill_template() -> str:
    packaged = Path(__file__).resolve().parent / "data" / "SKILL.agent.md"
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")
    return _FALLBACK_SKILL


_FALLBACK_SKILL = """---
name: hyperlex
description: Use when the user wants slang, memetics, lineage, mutation trace, Brier settlement, or cultural-signal receipts. Not for jailbreak wraps.
version: 0.4.0
---

<!-- hyperlex-init -->
# Hyperlex

CLI is on PATH after `pip install hyperlex`. Run the command. Do not copy the repo.

```bash
hyperlex pipeline \"<term>\" --route offline
hyperlex mutation trace \"<attested sentence>\"
hyperlex mutation predict <atom>
hyperlex pending
hyperlex settle --forecast-id <id> --decision TRUE
hyperlex commands
```

Never invent Brier. Mutation packets are forecast_eligible false.
"""


def _refuse_symlink_dest(dest: Path) -> None:
    # Inspect the lexical path before resolve() follows a dangling link.
    absolute = dest.expanduser().absolute()
    if any(part.is_symlink() for part in (absolute, *absolute.parents)):
        raise ValueError("refusing symlink dest")


def _backup_root() -> Path:
    raw = os.environ.get("HYPERLEX_HOME") or str(Path.home() / ".hyperlex")
    return Path(raw).expanduser()


def _publish_target_backup(dest: Path) -> Optional[Path]:
    if not dest.exists():
        return None
    key = hashlib.sha256(str(dest.resolve()).encode()).hexdigest()[:20]
    backups = _backup_root() / "backups" / "init" / key
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / uuid.uuid4().hex
    if dest.is_file():
        backup.mkdir(parents=True)
        shutil.copy2(dest, backup / dest.name)
    else:
        shutil.copytree(dest, backup, symlinks=True)
    marker = backup / ".backup-target.json"
    marker.write_text(json.dumps({"destination": str(dest.resolve())}) + "\n", encoding="utf-8")
    return backup


def _stage_write_skill(dest: Path, body: str, *, skip_smoke: bool) -> Dict[str, object]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=".hyperlex-init-", dir=str(dest.parent)))
    stage = workspace / "SKILL.md"
    try:
        stage.write_text(body, encoding="utf-8")
        status = "UNVERIFIED"
        if skip_smoke:
            status = "UNVERIFIED"
        else:
            staged = stage.read_text(encoding="utf-8")
            if MARKER not in staged or "hyperlex" not in staged.lower():
                raise ValueError("staged SKILL.md failed smoke (marker/cli missing)")
            status = "VALIDATED"
        final = dest / "SKILL.md"
        if dest.exists() and dest.is_file():
            # dest itself is a file (unexpected); replace via parent
            os.replace(stage, dest)
            return {"path": str(dest), "status": status}
        dest.mkdir(parents=True, exist_ok=True)
        os.replace(stage, final)
        return {"path": str(final), "status": status}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _write_skill(dest: Path, *, dry_run: bool, skip_smoke: bool) -> Dict[str, object]:
    _refuse_symlink_dest(dest)
    path = dest / "SKILL.md"
    body = skill_template()
    if dry_run:
        return {"target_path": str(path), "path": str(path), "status": "DRY_RUN", "dry_run": True}
    backup = _publish_target_backup(dest)
    written = _stage_write_skill(dest, body, skip_smoke=skip_smoke)
    if backup is not None:
        written["backup"] = str(backup)
    return written


def run_init(names: List[str], *, dry_run: bool, skip_smoke: bool = False) -> Dict:
    written = []
    for name in names:
        dest = skill_targets()[name]
        row = _write_skill(dest, dry_run=dry_run, skip_smoke=skip_smoke)
        row["target"] = name
        written.append(row)
    return {"ok": True, "command": "init", "dry_run": dry_run, "written": written}


def run_uninstall(names: List[str], *, dry_run: bool) -> Dict:
    removed = []
    for name in names:
        dest = skill_targets()[name]
        skill = dest / "SKILL.md"
        if skill.is_file() and MARKER in skill.read_text(encoding="utf-8", errors="ignore"):
            if not dry_run:
                skill.unlink()
                if dest.exists() and not any(dest.iterdir()):
                    dest.rmdir()
            removed.append(str(skill))
    return {"ok": True, "command": "uninstall-skill", "dry_run": dry_run, "removed": removed}


def dispatch(argv: List[str]) -> int:
    p = argparse.ArgumentParser(prog="hyperlex")
    sub = p.add_subparsers(dest="cmd", required=True)
    ini = sub.add_parser("init")
    ini.add_argument("--target", action="append", choices=sorted(skill_targets()), dest="targets")
    ini.add_argument("--all", action="store_true")
    ini.add_argument("--dry-run", action="store_true")
    ini.add_argument("--skip-smoke", action="store_true", help="Skip staged smoke (marks UNVERIFIED)")
    un = sub.add_parser("uninstall-skill")
    un.add_argument("--target", action="append", choices=sorted(skill_targets()), dest="targets")
    un.add_argument("--all", action="store_true")
    un.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    names = list(args.targets or [])
    if args.all or not names:
        names = ["hermes", "openclaw", "grok"]
    try:
        if args.cmd == "init":
            out = run_init(names, dry_run=bool(args.dry_run), skip_smoke=bool(getattr(args, "skip_smoke", False)))
        else:
            out = run_uninstall(names, dry_run=bool(args.dry_run))
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0
