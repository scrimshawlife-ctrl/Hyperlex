"""Wire Hyperlex into agent skill trees the way graft init does.

pip install hyperlex
hyperlex init
# writes a thin SKILL.md that tells the agent to call `hyperlex` on PATH
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Dict, List


TARGETS = {
    "hermes": Path.home() / ".hermes" / "skills" / "hyperlex",
    "openclaw": Path.home() / ".openclaw" / "skills" / "hyperlex",
    "grok": Path.home() / ".grok" / "skills" / "hyperlex",
    "claude": Path.home() / ".claude" / "skills" / "hyperlex",
}

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


def _write_skill(dest: Path, *, dry_run: bool) -> str:
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "SKILL.md"
    body = skill_template()
    if not dry_run:
        path.write_text(body, encoding="utf-8")
    return str(path)


def run_init(names: List[str], *, dry_run: bool) -> Dict:
    written = []
    for name in names:
        dest = TARGETS[name]
        written.append({"target": name, "path": _write_skill(dest, dry_run=dry_run)})
    return {"ok": True, "command": "init", "dry_run": dry_run, "written": written}


def run_uninstall(names: List[str], *, dry_run: bool) -> Dict:
    removed = []
    for name in names:
        dest = TARGETS[name]
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
    ini.add_argument("--target", action="append", choices=sorted(TARGETS), dest="targets")
    ini.add_argument("--all", action="store_true")
    ini.add_argument("--dry-run", action="store_true")
    un = sub.add_parser("uninstall-skill")
    un.add_argument("--target", action="append", choices=sorted(TARGETS), dest="targets")
    un.add_argument("--all", action="store_true")
    un.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    names = list(args.targets or [])
    if args.all or not names:
        names = ["hermes", "openclaw", "grok"]
    if args.cmd == "init":
        out = run_init(names, dry_run=bool(args.dry_run))
    else:
        out = run_uninstall(names, dry_run=bool(args.dry_run))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0
