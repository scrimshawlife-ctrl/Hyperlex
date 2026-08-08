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
        return _step(
            "demo",
            ok=False,
            summary="demo failed",
            error=str(exc),
            coach=["Ensure PYTHONPATH includes src/", "$HLX check"],
        )

    brier = packet.get("brier")
    unit0 = (packet.get("results") or [{}])[0]
    result = unit0.get("result") or {}
    prov = (result.get("provenance") or {}).get("brier")
    lineage = ((result.get("analysis") or {}).get("lineage") or {})
    if not packet.get("ok"):
        return _step(
            "demo",
            ok=False,
            summary="pipeline not ok",
            error=str(packet.get("error")),
            artifacts={"packet_ok": False},
        )
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
