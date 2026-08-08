# Hermes Workflow Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a week-one guided wizard (`$HLX wizard`) powered by a package step engine, with dual mode (interactive / `--auto`) and Hermes `SKILL.md` alignment — offline-first, never auto-settle, open `brier` always null.

**Architecture:** New package `hyperlex.wizard` owns ordered steps (`env_intro` → `doctor` → `demo` → `first_pipeline` → `calibration_coach` → `score_series_hint` → `handoff`) and `run_wizard()`. Thin CLI in `scripts/hyperlex.py` calls the runner and `_emit`s JSON. Docs + SKILL procedure point Hermes at the same step IDs. Wizard composes `run_pipeline` / score-log indexers; it does not call `settle`.

**Tech Stack:** Python 3.10+, existing Hyperlex package (`pipeline`, `calibration.score_log`), argparse CLI, pytest, no new runtime dependencies.

**Spec:** `docs/superpowers/specs/2026-08-08-hermes-workflow-wizard-design.md`

## Global Constraints

- Always open-analysis `brier: null`; never invent numeric Brier.
- Wizard **never** calls `settle` / `settle_and_log`.
- Default route `offline`; `--auto` is offline-safe (`HYPERLEX_OFFLINE=1`, vector off unless already configured).
- Doctor failure is soft-degraded unless `--strict`.
- Non-TTY stdin without `--auto` must still run as `auto` (no prompt hang).
- Step IDs are stable contract for Hermes/docs: `env_intro`, `doctor`, `demo`, `first_pipeline`, `calibration_coach`, `score_series_hint`, `handoff`.
- Schema: `hyperlex.wizard.v1`.
- Do not auto-register Hermes cron; handoff only mentions advisory `risk-schedule`.
- Prefer composing existing APIs; do not rewrite doctor into a second full health system — wizard doctor step is a **lite** skill health check (import + mock analyze + brier null + key files). Full `doctor` CLI remains unchanged.

## File map

| Path | Responsibility |
|------|----------------|
| `src/hyperlex/wizard/__init__.py` | Public exports: `run_wizard`, `WIZARD_STEP_IDS`, `WIZARD_SCHEMA` |
| `src/hyperlex/wizard/steps.py` | Step runners + coach strings |
| `src/hyperlex/wizard/runner.py` | Mode resolution, step loop, aggregate result |
| `scripts/hyperlex.py` | `cmd_wizard` + argparse + `commands` map entry |
| `tests/test_wizard.py` | Unit + CLI offline tests |
| `SKILL.md` | Guided wizard procedure + triggers |
| `docs/hermes-skill.md` | One paragraph + example |
| `docs/operator-loop.md` | Week-one checklist points to wizard |
| `docs/commands.md` | Command table row |
| `QUICKSTART.md` + `docs/start/quickstart.md` | First-success mentions wizard |
| `CHANGELOG.md` | Unreleased / 0.4.x entry when shipping |

---

### Task 1: Wizard package — step IDs, schema, runner skeleton

**Files:**
- Create: `src/hyperlex/wizard/__init__.py`
- Create: `src/hyperlex/wizard/steps.py`
- Create: `src/hyperlex/wizard/runner.py`
- Test: `tests/test_wizard.py`

**Interfaces:**
- Consumes: none yet (stubs)
- Produces:
  - `WIZARD_SCHEMA = "hyperlex.wizard.v1"`
  - `WIZARD_STEP_IDS: Tuple[str, ...] = ("env_intro", "doctor", "demo", "first_pipeline", "calibration_coach", "score_series_hint", "handoff")`
  - `run_wizard(*, mode: str = "auto", query: str = "rizz", skill_root: Optional[Path | str] = None, skip_doctor: bool = False, strict: bool = False, log_path: Optional[Path | str] = None, receipt_dir: Optional[Path | str] = None, out_dir: Optional[Path | str] = None) -> Dict[str, Any]`
  - Return always includes `schema`, `ok`, `mode`, `query`, `route`, `brier`, `steps`, `next`, `note`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_wizard.py`:

```python
"""Hermes workflow wizard — week-one guided path."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_wizard_step_order_and_schema():
    from hyperlex.wizard import WIZARD_SCHEMA, WIZARD_STEP_IDS, run_wizard

    assert WIZARD_SCHEMA == "hyperlex.wizard.v1"
    assert list(WIZARD_STEP_IDS) == [
        "env_intro",
        "doctor",
        "demo",
        "first_pipeline",
        "calibration_coach",
        "score_series_hint",
        "handoff",
    ]
    # skeleton may still return not-fully-wired steps; ids must match
    out = run_wizard(mode="auto", query="rizz")
    assert out["schema"] == WIZARD_SCHEMA
    assert [s["id"] for s in out["steps"]] == list(WIZARD_STEP_IDS)
    assert "brier" in out
    assert out["brier"] is None or out["ok"] is False
    assert isinstance(out.get("next"), list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scrimshawlife/Hyperlex && PYTHONPATH=src python -m pytest tests/test_wizard.py::test_wizard_step_order_and_schema -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'hyperlex.wizard'` (or import error).

- [ ] **Step 3: Write minimal skeleton implementation**

`src/hyperlex/wizard/__init__.py`:

```python
"""Week-one Hermes workflow wizard (guided operator path)."""

from .runner import run_wizard
from .steps import WIZARD_SCHEMA, WIZARD_STEP_IDS

__all__ = ["run_wizard", "WIZARD_SCHEMA", "WIZARD_STEP_IDS"]
```

`src/hyperlex/wizard/steps.py`:

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

WIZARD_SCHEMA = "hyperlex.wizard.v1"
WIZARD_STEP_IDS: Tuple[str, ...] = (
    "env_intro",
    "doctor",
    "demo",
    "first_pipeline",
    "calibration_coach",
    "score_series_hint",
    "handoff",
)


def _step(
    sid: str,
    *,
    ok: bool = True,
    skipped: bool = False,
    degraded: bool = False,
    summary: str = "",
    coach: Optional[List[str]] = None,
    artifacts: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": sid,
        "ok": ok,
        "skipped": skipped,
        "degraded": degraded,
        "summary": summary,
        "coach": list(coach or []),
        "artifacts": dict(artifacts or {}),
        "error": error,
    }


def run_step_env_intro(ctx: Dict[str, Any]) -> Dict[str, Any]:
    root = ctx.get("skill_root")
    return _step(
        "env_intro",
        summary=f"offline-first week-one path; skill_root={root}",
        coach=[
            "export HERMES_SKILL_DIR=\"${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}\"",
            "export HLX=\"python3 $HERMES_SKILL_DIR/scripts/hyperlex.py\"",
            "Data: ~/.hyperlex/ (receipts, score_log, cache)",
        ],
        artifacts={"skill_root": str(root) if root else ""},
    )


def run_step_doctor(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return _step("doctor", ok=True, summary="stub", skipped=False)


def run_step_demo(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return _step("demo", ok=True, summary="stub")


def run_step_first_pipeline(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return _step("first_pipeline", ok=True, summary="stub")


def run_step_calibration_coach(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return _step("calibration_coach", ok=True, summary="stub")


def run_step_score_series_hint(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return _step("score_series_hint", ok=True, summary="stub")


def run_step_handoff(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return _step(
        "handoff",
        summary="week-one handoff",
        coach=[
            "$HLX pending",
            "$HLX settle --forecast-id <id> --decision TRUE",
            "$HLX score-series --mean-shift --verify-chain",
            "$HLX risk-schedule --tier MODERATE --schedule-out /tmp/hlx-cron  # advisory only",
        ],
    )


STEP_RUNNERS = {
    "env_intro": run_step_env_intro,
    "doctor": run_step_doctor,
    "demo": run_step_demo,
    "first_pipeline": run_step_first_pipeline,
    "calibration_coach": run_step_calibration_coach,
    "score_series_hint": run_step_score_series_hint,
    "handoff": run_step_handoff,
}
```

`src/hyperlex/wizard/runner.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_wizard.py::test_wizard_step_order_and_schema -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/hyperlex/wizard tests/test_wizard.py
git commit -m "feat(wizard): skeleton step engine and run_wizard schema"
```

---

### Task 2: Implement real step bodies (doctor lite, demo, pipeline, calibration, score hint)

**Files:**
- Modify: `src/hyperlex/wizard/steps.py`
- Modify: `src/hyperlex/wizard/runner.py` (settlement baseline; env offline)
- Test: `tests/test_wizard.py`

**Interfaces:**
- Consumes: `hyperlex.pipeline.run_pipeline`, `hyperlex.calibration.score_log` (`read_log`, `index_forecasts`, `index_settlements`, `recompute_series`, `default_log_path`)
- Produces: fully working `run_wizard(mode="auto", …)` offline path; no settle side effects

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_wizard.py`:

```python
def test_wizard_auto_offline_null_brier(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_VECTOR", "0")
    from hyperlex.wizard import run_wizard

    out = run_wizard(
        mode="auto",
        query="rizz",
        skill_root=ROOT,
        out_dir=tmp_path / "wiz",
        strict=False,
    )
    assert out["ok"] is True, out
    assert out["schema"] == "hyperlex.wizard.v1"
    assert out["brier"] is None
    assert out["route"] == "offline"
    ids = [s["id"] for s in out["steps"]]
    assert ids == [
        "env_intro",
        "doctor",
        "demo",
        "first_pipeline",
        "calibration_coach",
        "score_series_hint",
        "handoff",
    ]
    by_id = {s["id"]: s for s in out["steps"]}
    assert by_id["demo"]["ok"] is True
    assert by_id["first_pipeline"]["ok"] is True
    assert by_id["calibration_coach"]["ok"] is True
    # open analysis artifacts must not claim brier
    for sid in ("demo", "first_pipeline"):
        art = by_id[sid].get("artifacts") or {}
        assert art.get("brier") in (None, )
    assert any("settle" in c for c in out["next"])


def test_wizard_no_settle_side_effect(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_VECTOR", "0")
    from hyperlex.calibration.score_log import index_settlements, read_log
    from hyperlex.wizard import run_wizard

    log = tmp_path / "wiz" / "wizard_score_log.jsonl"
    out_dir = tmp_path / "wiz"
    # first run creates log
    run_wizard(mode="auto", query="rizz", skill_root=ROOT, out_dir=out_dir)
    before = len(index_settlements(read_log(log)))
    run_wizard(mode="auto", query="rizz", skill_root=ROOT, out_dir=out_dir)
    after = len(index_settlements(read_log(log)))
    assert after == before


def test_wizard_skip_doctor(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_VECTOR", "0")
    from hyperlex.wizard import run_wizard

    out = run_wizard(
        mode="auto",
        query="rizz",
        skill_root=ROOT,
        out_dir=tmp_path / "wiz2",
        skip_doctor=True,
    )
    doc = next(s for s in out["steps"] if s["id"] == "doctor")
    assert doc["skipped"] is True
    assert out["ok"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/test_wizard.py -v -k "auto_offline or no_settle or skip_doctor"`

Expected: FAIL (stubs don't run pipeline / missing artifacts).

- [ ] **Step 3: Implement step bodies**

Replace stubs in `src/hyperlex/wizard/steps.py` with real implementations. Key logic:

```python
def run_step_doctor(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Lite skill health: key files + import + mock analyze brier null."""
    checks = []
    root: Optional[Path] = ctx.get("skill_root")
    if root is not None:
        for rel in ("VERSION", "SKILL.md", "scripts/hyperlex.py", "src/hyperlex/__init__.py"):
            ok = (root / rel).is_file()
            checks.append({"name": f"file:{rel}", "ok": ok})
    try:
        from hyperlex import detect_memetic_patterns

        result = detect_memetic_patterns(query="rizz", ingest_source="mock", validate=False)
        brier_ok = result.get("provenance", {}).get("brier") is None
        checks.append({"name": "analyze_mock", "ok": True})
        checks.append({"name": "brier_null", "ok": brier_ok})
    except Exception as exc:
        checks.append({"name": "analyze_mock", "ok": False, "error": str(exc)})

    failed = [c for c in checks if not c.get("ok")]
    ok = not failed
    degraded = bool(failed)
    if failed and not ctx.get("strict"):
        # soft-fail: report degraded but ok=True for continue
        return _step(
            "doctor",
            ok=True,
            degraded=True,
            summary=f"degraded: {len(failed)} failed checks",
            coach=["Run full health: $HLX doctor", "bash install.sh"],
            artifacts={"checks": checks},
            error="; ".join(c.get("name", "") for c in failed),
        )
    return _step(
        "doctor",
        ok=ok,
        degraded=degraded,
        summary=f"checks={len(checks)} failed={len(failed)}",
        artifacts={"checks": checks},
        error=None if ok else "doctor checks failed",
        coach=[] if ok else ["$HLX doctor", "bash install.sh"],
    )


def run_step_demo(ctx: Dict[str, Any]) -> Dict[str, Any]:
    import os
    from hyperlex.pipeline import run_pipeline

    os.environ.setdefault("HYPERLEX_OFFLINE", "1")
    os.environ.setdefault("HYPERLEX_VECTOR", "0")
    q = ctx.get("query") or "rizz"
    try:
        packet = run_pipeline(
            q,
            route="offline",
            source="mock",
            expand_terms=True,
            receipt=True,
            forecasts=True,
            append_log=True,
            phase5=False,
            log_path=ctx.get("log_path"),
            receipt_dir=ctx.get("receipt_dir"),
            validate=False,
        )
    except Exception as exc:
        return _step("demo", ok=False, summary="demo failed", error=str(exc),
                     coach=["Ensure PYTHONPATH includes src/", "$HLX check"])

    brier = packet.get("brier")
    unit0 = (packet.get("results") or [{}])[0]
    result = unit0.get("result") or {}
    prov = (result.get("provenance") or {}).get("brier")
    lineage = ((result.get("analysis") or {}).get("lineage") or {})
    if not packet.get("ok"):
        return _step("demo", ok=False, summary="pipeline not ok", error=str(packet.get("error")),
                     artifacts={"packet_ok": False})
    if brier is not None or prov is not None:
        return _step(
            "demo",
            ok=False,
            summary="integrity fail: open brier must be null",
            error="open analysis invented brier",
            artifacts={"brier": brier, "provenance_brier": prov},
        )
    return _step(
        "demo",
        ok=True,
        summary=f"offline demo ok atoms={packet.get('n_atoms')} family={lineage.get('family_id')}",
        artifacts={
            "brier": None,
            "n_atoms": packet.get("n_atoms"),
            "lineage_family": lineage.get("family_id"),
            "receipt": unit0.get("receipt"),
            "log_path": str(ctx.get("log_path") or ""),
        },
        coach=["Open analysis keeps brier null until settle."],
    )


def run_step_first_pipeline(ctx: Dict[str, Any]) -> Dict[str, Any]:
    # Same offline pipeline as demo but always uses operator query (may equal demo query).
    # Intentionally second run so forecasts accumulate for calibration_coach.
    import os
    from hyperlex.pipeline import run_pipeline

    os.environ.setdefault("HYPERLEX_OFFLINE", "1")
    os.environ.setdefault("HYPERLEX_VECTOR", "0")
    q = ctx.get("query") or "rizz"
    try:
        packet = run_pipeline(
            q,
            route="offline",
            source="mock",
            expand_terms=True,
            receipt=True,
            forecasts=True,
            append_log=True,
            phase5=True,
            log_path=ctx.get("log_path"),
            receipt_dir=ctx.get("receipt_dir"),
            validate=False,
        )
    except Exception as exc:
        return _step("first_pipeline", ok=False, summary="pipeline failed", error=str(exc))

    brier = packet.get("brier")
    if not packet.get("ok") or brier is not None:
        return _step(
            "first_pipeline",
            ok=False,
            summary="pipeline integrity failed",
            error=packet.get("error") or "brier not null",
            artifacts={"brier": brier},
        )
    ctx["pipeline_ok"] = True
    return _step(
        "first_pipeline",
        ok=True,
        summary=f"pipeline ok n_atoms={packet.get('n_atoms')} n_forecasts={packet.get('n_forecasts')}",
        artifacts={
            "brier": None,
            "n_atoms": packet.get("n_atoms"),
            "n_forecasts": packet.get("n_forecasts"),
            "atoms": packet.get("atoms"),
        },
    )


def run_step_calibration_coach(ctx: Dict[str, Any]) -> Dict[str, Any]:
    from hyperlex.calibration.score_log import (
        index_forecasts,
        index_settlements,
        read_log,
        default_log_path,
    )

    path = ctx.get("log_path") or default_log_path()
    records = read_log(path)
    forecasts = index_forecasts(records)
    settled = set(index_settlements(records).keys())
    open_fcs = []
    for fid, fc in forecasts.items():
        if fid in settled:
            continue
        open_fcs.append({
            "forecast_id": fid,
            "signal_key": fc.get("signal_key"),
            "probability": fc.get("probability") or fc.get("p"),
            "claim": fc.get("claim") or fc.get("statement"),
        })
    ctx["open_forecasts"] = open_fcs
    coach = [
        "Settlement is the only human gate — wizard never auto-settles.",
        "$HLX pending",
        "$HLX settle --forecast-id <id> --decision TRUE|FALSE|VOID",
        "$HLX score-series --mean-shift --verify-chain",
    ]
    if open_fcs:
        sample = open_fcs[0]["forecast_id"]
        coach.insert(1, f"Example open forecast_id: {sample}")
    return _step(
        "calibration_coach",
        ok=True,
        summary=f"open_forecasts={len(open_fcs)} settled={len(settled)}",
        coach=coach,
        artifacts={"open_forecasts": open_fcs[:10], "n_open": len(open_fcs), "log_path": str(path)},
    )


def run_step_score_series_hint(ctx: Dict[str, Any]) -> Dict[str, Any]:
    from hyperlex.calibration.score_log import (
        index_settlements,
        read_log,
        recompute_series,
        default_log_path,
    )

    path = ctx.get("log_path") or default_log_path()
    n_settled = len(index_settlements(read_log(path)))
    if n_settled == 0:
        return _step(
            "score_series_hint",
            ok=True,
            summary="no settlements yet — Brier NOT_COMPUTABLE until settle",
            coach=[
                "Do not invent Brier from demo/pipeline output.",
                "After settle: $HLX score-series --mean-shift --verify-chain",
            ],
            artifacts={"n_settled": 0, "brier": None},
        )
    series = recompute_series(path)
    # series may use NOT_COMPUTABLE; never invent
    return _step(
        "score_series_hint",
        ok=True,
        summary=f"recomputed series from {n_settled} settlements",
        artifacts={"n_settled": n_settled, "series_keys": list(series.keys())[:12]},
        coach=["$HLX score-series --mean-shift --verify-chain"],
    )
```

In `runner.py` `run_wizard`, at start (after building paths):

```python
    import os
    os.environ.setdefault("HYPERLEX_OFFLINE", "1")
    if resolved == "auto":
        os.environ.setdefault("HYPERLEX_VECTOR", "0")
```

Fix overall_ok logic carefully:

```python
    overall_ok = True
    stop = False
    for sid in WIZARD_STEP_IDS:
        if stop:
            steps.append(_step(sid, ok=True, skipped=True, summary="skipped after hard failure"))
            continue
        if sid == "doctor" and skip_doctor:
            steps.append(_step(sid, ok=True, skipped=True, summary="skipped (--skip-doctor)"))
            continue
        result = STEP_RUNNERS[sid](ctx)
        steps.append(result)
        if result.get("degraded"):
            ctx["degraded"] = True
        if result.get("ok") or result.get("skipped"):
            continue
        # hard failure
        if sid == "doctor" and not strict:
            ctx["degraded"] = True
            # rewrite as degraded continue — doctor already returns ok=True when soft
            overall_ok = overall_ok  # no-op
            continue
        overall_ok = False
        if sid in {"demo", "first_pipeline"} or (sid == "doctor" and strict):
            stop = True

    return {
        ...
        "ok": overall_ok,
        "brier": None,
        ...
    }
```

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=src python -m pytest tests/test_wizard.py -v`

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/hyperlex/wizard tests/test_wizard.py
git commit -m "feat(wizard): offline week-one steps without auto-settle"
```

---

### Task 3: CLI `wizard` command + command map

**Files:**
- Modify: `scripts/hyperlex.py` (add `cmd_wizard`, parser, `cmd_commands` daily_ops entry)
- Test: `tests/test_wizard.py` (CLI subprocess)

**Interfaces:**
- Consumes: `hyperlex.wizard.run_wizard`
- Produces: `$HLX wizard [--auto] [--query] [--skip-doctor] [--strict] [--out] [--out-dir]`

- [ ] **Step 1: Write the failing CLI test**

Append to `tests/test_wizard.py`:

```python
def test_wizard_cli_auto(tmp_path):
    out_dir = tmp_path / "cli-wiz"
    env = {
        **dict(os.environ),
        "PYTHONPATH": str(ROOT / "src"),
        "HYPERLEX_OFFLINE": "1",
        "HYPERLEX_VECTOR": "0",
    }
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hyperlex.py"),
            "wizard",
            "--auto",
            "--query",
            "rizz",
            "--out-dir",
            str(out_dir),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["command"] == "wizard"
    assert data["schema"] == "hyperlex.wizard.v1"
    assert data["brier"] is None
    assert len(data["steps"]) == 7
```

- [ ] **Step 2: Run test — expect fail**

Run: `PYTHONPATH=src python -m pytest tests/test_wizard.py::test_wizard_cli_auto -v`

Expected: FAIL (unknown command `wizard` or argparse error).

- [ ] **Step 3: Implement CLI**

Add near other cmds (after `cmd_demo` is fine):

```python
def cmd_wizard(args: argparse.Namespace) -> int:
    """Week-one guided path: doctor → demo → pipeline → calibration coach."""
    import os
    from hyperlex.wizard import run_wizard

    os.environ.setdefault("HYPERLEX_OFFLINE", "1")
    mode = "auto" if getattr(args, "auto", False) else "interactive"
    # resolve skill root = this install
    skill_root = ROOT
    out_dir = getattr(args, "out_dir", None) or None
    if out_dir == "":
        out_dir = None
    result = run_wizard(
        mode=mode,
        query=(getattr(args, "query", None) or "rizz"),
        skill_root=skill_root,
        skip_doctor=bool(getattr(args, "skip_doctor", False)),
        strict=bool(getattr(args, "strict", False)),
        out_dir=out_dir,
        log_path=getattr(args, "log", None) or None,
    )
    out_path = getattr(args, "out", None) or ""
    if out_path:
        Path(out_path).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = {**result, "out": out_path}
    _emit(result)
    return 0 if result.get("ok") else 2
```

In `_build_parser`, after `demo_parser` block:

```python
    wiz = subparsers.add_parser(
        "wizard",
        help="Week-one guided Hermes workflow (doctor→demo→pipeline→calibration coach)",
    )
    wiz.add_argument("--auto", action="store_true", default=False, help="Non-interactive offline path")
    wiz.add_argument("--query", default="rizz", help="Sample query (default: rizz)")
    wiz.add_argument("--skip-doctor", action="store_true", default=False)
    wiz.add_argument("--strict", action="store_true", default=False, help="Abort if doctor fails")
    wiz.add_argument("--out-dir", default="", help="Isolate receipts/score log under DIR")
    wiz.add_argument("--log", default="", help="Score log path override")
    wiz.add_argument("--out", default="", help="Write full wizard JSON to path")
    wiz.set_defaults(func=cmd_wizard)
```

In `cmd_commands` `daily_ops` list, **insert first**:

```python
{"cmd": "wizard --auto", "why": "Week-one guided path (doctor→demo→pipeline→calibration coach)"},
```

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=src python -m pytest tests/test_wizard.py -v`

Expected: PASS

Also smoke:

```bash
PYTHONPATH=src python3 scripts/hyperlex.py wizard --auto --query rizz --out-dir /tmp/hlx-wiz-smoke
```

Expected: exit 0, JSON with `"ok": true`, `"brier": null`.

- [ ] **Step 5: Commit**

```bash
git add scripts/hyperlex.py tests/test_wizard.py
git commit -m "feat(cli): wizard command for week-one Hermes guidance"
```

---

### Task 4: Strict doctor + integrity edge tests

**Files:**
- Test: `tests/test_wizard.py`
- Modify: `src/hyperlex/wizard/steps.py` / `runner.py` only if needed to satisfy tests

**Interfaces:**
- Consumes: `run_wizard(..., strict=True, skill_root=bad_path)`
- Produces: documented failure behavior

- [ ] **Step 1: Write failing tests**

```python
def test_wizard_strict_doctor_missing_skill_root(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERLEX_OFFLINE", "1")
    monkeypatch.setenv("HYPERLEX_VECTOR", "0")
    from hyperlex.wizard import run_wizard

    empty = tmp_path / "empty-skill"
    empty.mkdir()
    out = run_wizard(
        mode="auto",
        query="rizz",
        skill_root=empty,
        out_dir=tmp_path / "wiz-strict",
        strict=True,
    )
    doc = next(s for s in out["steps"] if s["id"] == "doctor")
    assert doc["ok"] is False or out["ok"] is False
    assert out["ok"] is False


def test_wizard_resolve_mode_nontty_forces_auto(monkeypatch):
    from hyperlex.wizard.runner import resolve_mode
    import io

    class FakeStdin(io.StringIO):
        def isatty(self):
            return False

    monkeypatch.setattr(sys, "stdin", FakeStdin())
    assert resolve_mode("interactive") == "auto"
```

- [ ] **Step 2: Run — may fail if doctor soft-returns ok under strict**

Run: `PYTHONPATH=src python -m pytest tests/test_wizard.py::test_wizard_strict_doctor_missing_skill_root tests/test_wizard.py::test_wizard_resolve_mode_nontty_forces_auto -v`

- [ ] **Step 3: Fix doctor strict path**

In `run_step_doctor`, when `ctx.get("strict")` and any check fails, return `ok=False` (do not soft-degrade). Runner already stops on doctor failure when `strict`.

Ensure `resolve_mode` is exported or tested via `hyperlex.wizard.runner`.

- [ ] **Step 4: Run full wizard suite**

Run: `PYTHONPATH=src python -m pytest tests/test_wizard.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/hyperlex/wizard tests/test_wizard.py
git commit -m "test(wizard): strict doctor and non-TTY mode resolution"
```

---

### Task 5: Docs + Hermes SKILL alignment

**Files:**
- Modify: `SKILL.md`
- Modify: `docs/hermes-skill.md`
- Modify: `docs/operator-loop.md`
- Modify: `docs/commands.md`
- Modify: `QUICKSTART.md`
- Modify: `docs/start/quickstart.md`
- Modify: `CHANGELOG.md` (Unreleased bullet)

**Interfaces:**
- Consumes: step IDs and CLI flags from Tasks 1–3
- Produces: Hermes agent procedure + human docs matching engine

- [ ] **Step 1: Update SKILL.md**

In frontmatter `triggers`, add:

```yaml
  - hyperlex wizard
  - get started with hyperlex
  - hyperlex onboarding
```

In **Commands (prefer simplified path)** section, add near top:

```bash
$HLX wizard --auto                 # week-one guided path (offline)
$HLX wizard                        # interactive (TTY)
```

Add section **Guided wizard** after Preferred sequence (or before):

```markdown
## Guided wizard

When the user is new to Hyperlex, asks to get started, or wants a guided
operator path:

1. Ensure skill install (`bash install.sh` if missing).
2. Run `$HLX wizard --auto` (or `$HLX wizard --auto --query "<term>"`).
3. Summarize steps: env → doctor → demo → first pipeline → calibration coach.
4. **Never invent Brier.** Open analysis keeps `brier: null`.
5. Show open forecasts from the wizard output / `$HLX pending`.
6. **Settlement requires operator authority** — ask for TRUE|FALSE|VOID, then:
   `$HLX settle --forecast-id <id> --decision …`
7. `$HLX score-series --mean-shift --verify-chain`
8. Optional advisory only: `$HLX risk-schedule --tier MODERATE --schedule-out /tmp/hlx-cron`
   (never auto-register Hermes cron).

Step IDs (stable): `env_intro`, `doctor`, `demo`, `first_pipeline`,
`calibration_coach`, `score_series_hint`, `handoff`.
```

Update Preferred sequence item 1 to: **`wizard --auto`** then `commands` / `run`.

- [ ] **Step 2: Update operator docs**

`docs/commands.md` — under Daily ops table, first row:

| `wizard [--auto]` | **Week-one guided path** (doctor→demo→pipeline→calibration coach) |

`docs/operator-loop.md` — Week-one checklist item 2 becomes:

```markdown
2. `$HLX wizard --auto` (or interactive `$HLX wizard`) — guided offline path
3. `$HLX doctor` green if wizard degraded
...
```

(renumber subsequent items)

`docs/hermes-skill.md` — after Install:

```bash
$HLX wizard --auto
```

One paragraph: wizard is the preferred first-run Hermes procedure; settle remains human.

`QUICKSTART.md` and `docs/start/quickstart.md` — after install:

```bash
$HLX wizard --auto
```

- [ ] **Step 3: CHANGELOG**

Under Unreleased / next 0.4.x:

```markdown
- CLI `wizard` + package `hyperlex.wizard`: week-one Hermes guided path
  (`--auto` / interactive); never auto-settles; offline-first; SKILL.md procedure
```

- [ ] **Step 4: Verify docs consistency (manual skim)**

```bash
rg -n "wizard" SKILL.md docs/commands.md docs/operator-loop.md docs/hermes-skill.md QUICKSTART.md docs/start/quickstart.md CHANGELOG.md
PYTHONPATH=src python3 scripts/hyperlex.py commands | head -40
```

Expected: wizard appears in command map JSON and docs.

- [ ] **Step 5: Commit**

```bash
git add SKILL.md docs/hermes-skill.md docs/operator-loop.md docs/commands.md QUICKSTART.md docs/start/quickstart.md CHANGELOG.md
git commit -m "docs: Hermes wizard guidance and command map"
```

---

### Task 6: Full verification gate

**Files:** none new (run suite)

- [ ] **Step 1: Run wizard + demo regression**

```bash
cd /home/scrimshawlife/Hyperlex
PYTHONPATH=src python -m pytest tests/test_wizard.py tests/test_demo_offline.py -v
PYTHONPATH=src python3 scripts/hyperlex.py wizard --auto --query rizz --out-dir /tmp/hlx-wiz-final
echo exit:$?
```

Expected: all tests PASS; CLI exit 0; JSON `ok: true`, `brier: null`, 7 steps.

- [ ] **Step 2: Confirm no settle in wizard source**

```bash
rg -n "settle_and_log|settle\(" src/hyperlex/wizard/
```

Expected: no matches (or only string coach text mentioning `$HLX settle`).

- [ ] **Step 3: Final commit only if uncommitted doc/fix fixes**

```bash
git status -sb
# if clean, done; else commit residual fixes
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Week-one operator loop | Task 2 steps |
| Dual mode interactive + `--auto` | Task 1 `resolve_mode`, Task 3 CLI |
| Package step engine | Tasks 1–2 |
| Hermes SKILL procedure | Task 5 |
| Offline first | Tasks 2–3 env defaults |
| Never auto-settle | Task 2 test + Task 6 rg |
| `brier: null` | Task 2 tests |
| Doctor soft vs `--strict` | Tasks 2–4 |
| Command map + docs | Tasks 3, 5 |
| Schema `hyperlex.wizard.v1` | Task 1 |
| Stable step IDs | Task 1 |
| Non-goals (no vector/live/persist) | Not implemented — intentional |

## Self-review notes

- No TBD placeholders in tasks.
- Signatures consistent: `run_wizard(...)` params match CLI flags.
- Doctor is **lite** by design (spec allowed shared health helpers); full `doctor` CLI unchanged.
- Interactive mode in v1: mode resolves and steps run without prompts when auto; interactive may still run steps without blocking prompts in v1 (defaults). Optional prompt for query only if `mode=="interactive"` and TTY — implement in runner if desired:

```python
if resolved == "interactive" and sys.stdin.isatty() and not query_from_cli_explicit:
    # optional: input with default — skip if out of time; --query always wins
    pass
```

For v1, interactive ≡ auto with human-readable coach (no required prompts) is acceptable as long as `--auto` and non-TTY behave identically. Document that in CHANGELOG if prompts are deferred.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-08-hermes-workflow-wizard.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — this session, executing-plans with checkpoints  

Which approach?
