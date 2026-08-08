from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .steps import STEP_RUNNERS, WIZARD_SCHEMA, WIZARD_STEP_IDS, _step


def resolve_mode(mode: str, *, force_auto: bool = False) -> str:
    m = (mode or "auto").strip().lower()
    if force_auto or m == "auto":
        return "auto"
    if m == "interactive":
        # Non-TTY must not hang
        if not sys.stdin.isatty():
            return "auto"
        return "interactive"
    return "auto"


def run_wizard(
    *,
    mode: str = "auto",
    query: str = "rizz",
    skill_root: Optional[Path | str] = None,
    skip_doctor: bool = False,
    strict: bool = False,
    log_path: Optional[Path | str] = None,
    receipt_dir: Optional[Path | str] = None,
    out_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    resolved = resolve_mode(mode)
    q = (query or "rizz").strip() or "rizz"
    root = Path(skill_root).resolve() if skill_root else None

    # Isolate wizard artifacts when out_dir/log provided (tests)
    if out_dir:
        out_p = Path(out_dir)
        out_p.mkdir(parents=True, exist_ok=True)
        log_path = log_path or (out_p / "wizard_score_log.jsonl")
        receipt_dir = receipt_dir or (out_p / "receipts")

    ctx: Dict[str, Any] = {
        "mode": resolved,
        "query": q,
        "skill_root": root,
        "skip_doctor": skip_doctor,
        "strict": strict,
        "log_path": Path(log_path) if log_path else None,
        "receipt_dir": Path(receipt_dir) if receipt_dir else None,
        "out_dir": Path(out_dir) if out_dir else None,
        "settlement_count_before": 0,
        "open_forecasts": [],
        "pipeline_ok": False,
        "degraded": False,
    }

    steps: List[Dict[str, Any]] = []
    overall_ok = True
    stop = False

    for sid in WIZARD_STEP_IDS:
        if stop:
            steps.append(_step(sid, ok=False, skipped=True, summary="skipped after failure"))
            continue
        if sid == "doctor" and skip_doctor:
            steps.append(_step(sid, ok=True, skipped=True, summary="skipped (--skip-doctor)"))
            continue
        runner = STEP_RUNNERS[sid]
        result = runner(ctx)
        steps.append(result)
        if result.get("degraded"):
            ctx["degraded"] = True
        if not result.get("ok") and not result.get("skipped"):
            overall_ok = False
            if sid in {"demo", "first_pipeline"} or (sid == "doctor" and strict):
                stop = True
            elif sid == "doctor" and not strict:
                # soft continue
                overall_ok = True if all(
                    s.get("ok") or s.get("skipped") or s.get("id") == "doctor"
                    for s in steps
                ) else overall_ok
                # keep overall_ok true for soft doctor fail; mark degraded
                overall_ok = True
                ctx["degraded"] = True
                result["degraded"] = True

    next_cmds = [
        'python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}/scripts/hyperlex.py" pending',
        'python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}/scripts/hyperlex.py" settle --forecast-id <id> --decision TRUE',
        'python3 "${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}/scripts/hyperlex.py" score-series --mean-shift --verify-chain',
    ]

    return {
        "schema": WIZARD_SCHEMA,
        "ok": overall_ok and not stop,
        "mode": resolved,
        "query": q,
        "route": "offline",
        "brier": None,
        "degraded": bool(ctx.get("degraded")),
        "steps": steps,
        "next": next_cmds,
        "note": "Week-one guided path. Never invent Brier. Never auto-settle.",
        "command": "wizard",
    }
