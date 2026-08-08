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
