"""Risk-tier → scan/cron schedule coupling (advisory).

Maps hyperstition risk tiers to recommended LIVE_EMERGENCE_SCAN cadence,
query budget, and Hermes cron job envelopes. Operator must still register
jobs; this module does not auto-mutate Hermes cron state.

SPECULATIVE / advisory. Never invents Brier.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .risk import forecast_hyperstition_risk, risk_from_analysis
from .scenario import run_phase5_scenario

# Advisory schedule policy per risk tier
TIER_POLICY: Dict[str, Dict[str, Any]] = {
    "LOW": {
        "cron": "0 */12 * * *",
        "interval_hours": 12,
        "max_queries": 3,
        "source_recommend": "mock",
        "receipt": True,
        "forecasts": True,
        "append_log": True,
        "vector_seed": False,
        "archive_export": False,
        "operator_note": "Monitor only; niche circulation likely.",
    },
    "MODERATE": {
        "cron": "0 */6 * * *",
        "interval_hours": 6,
        "max_queries": 5,
        "source_recommend": "mock",
        "receipt": True,
        "forecasts": True,
        "append_log": True,
        "vector_seed": False,
        "archive_export": False,
        "operator_note": "Default LIVE_EMERGENCE_SCAN cadence.",
    },
    "ELEVATED": {
        "cron": "0 */2 * * *",
        "interval_hours": 2,
        "max_queries": 8,
        "source_recommend": "combined",
        "receipt": True,
        "forecasts": True,
        "append_log": True,
        "vector_seed": True,
        "archive_export": True,
        "operator_note": "Increase scan frequency; archive + reseed vectors after runs.",
    },
    "CRITICAL": {
        "cron": "0 * * * *",
        "interval_hours": 1,
        "max_queries": 12,
        "source_recommend": "combined",
        "receipt": True,
        "forecasts": True,
        "append_log": True,
        "vector_seed": True,
        "archive_export": True,
        "operator_note": "Hourly scan; prepare settlement criteria; verify evidence for ACTUALIZING loops.",
    },
}

# Atomic lexicon items / true multi-word phrases only — never bag independent atoms.
DEFAULT_QUERIES = [
    "sharp money",
    "steam",
    "revenge",
    "diamond hands",
    "rizz",
    "locked in",
    "crash out",
    "agentic slop",
    "skill issue",
    "vibe coding",
    "based",
    "quiet quitting",
    "act your wage",
    "touch grass",
]


def _atomic_queries(text: Optional[str]) -> List[str]:
    """Expand free text into scan queries (one atom each)."""
    if not text:
        return []
    try:
        from hyperlex.analysis.terms import split_seed_terms

        split = split_seed_terms(str(text))
        terms = [str(t).strip() for t in (split.get("terms") or []) if str(t).strip()]
        if terms:
            return terms
    except Exception:
        pass
    s = str(text).strip()
    return [s] if s else []


def policy_for_tier(tier: str) -> Dict[str, Any]:
    t = str(tier or "MODERATE").upper()
    return dict(TIER_POLICY.get(t) or TIER_POLICY["MODERATE"])


def plan_scan_from_risk(
    risk: Dict[str, Any],
    *,
    queries: Optional[Sequence[str]] = None,
    job_name: Optional[str] = None,
    seed_term: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an advisory scan plan from a hyperstition risk packet."""
    tier = str(risk.get("tier") or "MODERATE").upper()
    policy = policy_for_tier(tier)
    # Expand any bag queries into atomic lexicon items
    raw_q = list(queries) if queries is not None else list(DEFAULT_QUERIES)
    expanded: List[str] = []
    seen_q: set = set()
    for item in raw_q:
        for atom in _atomic_queries(str(item)):
            key = atom.lower()
            if key not in seen_q:
                seen_q.add(key)
                expanded.append(atom)
    if not expanded:
        expanded = list(DEFAULT_QUERIES)

    max_q = int(policy.get("max_queries") or 5)
    selected = expanded[:max_q]
    # Prefer risk seed atoms first (split multi-term bags)
    st = seed_term or risk.get("seed_term")
    seed_atoms = _atomic_queries(str(st) if st else "")
    if seed_atoms:
        head = [a for a in seed_atoms if a.lower() not in {x.lower() for x in selected}]
        selected = (head + selected)[:max_q]

    name = job_name or f"hyperlex-scan-{tier.lower()}"
    cron = policy["cron"]
    source = policy["source_recommend"]

    scan_flags = []
    if policy.get("receipt"):
        scan_flags.append("--receipt")
    if policy.get("forecasts"):
        scan_flags.append("--forecasts")
    if policy.get("append_log"):
        scan_flags.append("--append-log")
    flags = " ".join(scan_flags)

    script = (
        'export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"; '
        f'python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" scan '
        f'--queries "{",".join(selected)}" '
        f'--source {source} {flags} --json'
    )

    post_hooks = []
    if policy.get("vector_seed"):
        post_hooks.append(
            'python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" vector-seed --include-home --no-registry 2>/dev/null || true'
        )
    if policy.get("archive_export"):
        post_hooks.append(
            'python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" archive-export --include-home-receipts --history '
            '--snapshot-id "scan-$(date -u +%Y%m%dT%H%M%SZ)" 2>/dev/null || true'
        )
    if post_hooks:
        script = script + "; " + "; ".join(post_hooks)

    job = {
        "name": name,
        "description": (
            f"Advisory LIVE_EMERGENCE_SCAN for risk tier {tier}. "
            "Generated by hyperlex.simulation.schedule — operator must register."
        ),
        "skills": ["hyperlex"],
        "skill": "hyperlex",
        "script": script,
        "no_agent": True,
        "model": None,
        "provider": None,
        "schedule": {
            "kind": "cron",
            "expr": cron,
            "display": f"{cron} (every {policy['interval_hours']}h · tier {tier})",
        },
        "schedule_display": cron,
        "state": "proposed",
        "risk_tier": tier,
        "risk_score": risk.get("risk_score"),
        "queries": selected,
        "source_recommend": source,
        "notes": [
            "ADVISORY only — does not auto-register with Hermes cron.",
            policy.get("operator_note") or "",
            "Scan never invents Brier; settle forecasts via settle / score-series.",
            f"source_recommend={source}; offline force: HYPERLEX_OFFLINE=1 + --source mock",
        ],
    }

    return {
        "schema": "hyperlex.risk_scan_plan.v1",
        "ok": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tier": tier,
        "risk_score": risk.get("risk_score"),
        "policy": policy,
        "queries": selected,
        "job": job,
        "hermes_cron_hint": (
            f'hermes cron add --name "{name}" --cron "{cron}" --skill hyperlex --no-agent '
            f"--script '{script}'"
        ),
        "provenance": "SPECULATIVE",
        "brier": None,
        "note": (
            "Risk→schedule coupling is advisory. Operator registers cron. "
            "Not market advice; not auto-settlement."
        ),
    }


def plan_scan_from_term(
    term: str,
    *,
    domain: str = "general",
    analysis_result: Optional[Dict[str, Any]] = None,
    queries: Optional[Sequence[str]] = None,
    use_phase5: bool = True,
) -> Dict[str, Any]:
    """Compute risk (optionally full Phase 5) then emit scan plan."""
    if analysis_result is not None:
        if use_phase5:
            sc = run_phase5_scenario(term, analysis_result=analysis_result, domain=domain)
            risk = sc.get("hyperstition_risk") or risk_from_analysis(analysis_result, domain=domain)
            plan = plan_scan_from_risk(risk, queries=queries, seed_term=term)
            plan["phase5_summary"] = {
                "transmission_peak": (sc.get("transmission") or {}).get("summary", {}).get("peak_mean_adoption"),
                "cascade_success": (sc.get("multi_agent") or {}).get("summary", {}).get("cascade_success"),
            }
            return plan
        risk = risk_from_analysis(analysis_result, domain=domain)
        return plan_scan_from_risk(risk, queries=queries, seed_term=term)

    # term-only risk (minimal features)
    risk = forecast_hyperstition_risk(
        hyperstition_stage="EMERGENT",
        virality_hybrid=0.45,
        seed_term=term,
        domain=domain,
    )
    if use_phase5:
        sc = run_phase5_scenario(term, domain=domain)
        risk = sc.get("hyperstition_risk") or risk
        plan = plan_scan_from_risk(risk, queries=queries, seed_term=term)
        plan["phase5_summary"] = {
            "transmission_peak": (sc.get("transmission") or {}).get("summary", {}).get("peak_mean_adoption"),
            "cascade_success": (sc.get("multi_agent") or {}).get("summary", {}).get("cascade_success"),
        }
        return plan
    return plan_scan_from_risk(risk, queries=queries, seed_term=term)


def plan_scan_from_tier(
    tier: str,
    *,
    queries: Optional[Sequence[str]] = None,
    job_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Direct tier → plan without re-running simulation."""
    policy = policy_for_tier(tier)
    risk = {
        "tier": str(tier).upper(),
        "risk_score": {"LOW": 0.2, "MODERATE": 0.4, "ELEVATED": 0.6, "CRITICAL": 0.85}.get(
            str(tier).upper(), 0.4
        ),
        "seed_term": None,
    }
    return plan_scan_from_risk(risk, queries=queries, job_name=job_name)


def write_scan_plan(
    plan: Dict[str, Any],
    *,
    out_dir: Path | str,
    write_queries: bool = True,
    write_job: bool = True,
) -> Dict[str, Any]:
    """Write job JSON + queries JSON for Hermes cron registration."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tier = str(plan.get("tier") or "MODERATE").lower()
    written = []
    job_path = None
    queries_path = None
    if write_job and plan.get("job"):
        job_path = out / f"hyperlex-scan-{tier}.job.json"
        job_path.write_text(json.dumps(plan["job"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(str(job_path))
    if write_queries:
        queries_path = out / f"scan-queries-{tier}.json"
        packet = {
            "schema": "hyperlex.scan_queries.v1",
            "description": f"Risk-tier {plan.get('tier')} query pack (advisory)",
            "risk_tier": plan.get("tier"),
            "queries": plan.get("queries") or [],
        }
        queries_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(str(queries_path))
    plan_path = out / f"risk-scan-plan-{tier}.json"
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written.append(str(plan_path))
    return {
        "ok": True,
        "written": written,
        "job_path": str(job_path) if job_path else None,
        "queries_path": str(queries_path) if queries_path else None,
        "plan_path": str(plan_path),
        "tier": plan.get("tier"),
        "brier": None,
    }


def aggregate_scan_risk(scan_results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """
    From a LIVE_EMERGENCE_SCAN results list, derive a coarse tier recommendation.

    Uses lineage presence + mock brier-null results only as weak features.
    """
    n = len(scan_results)
    n_lineage = 0
    families = set()
    for row in scan_results:
        # scan rows are summaries; full result may be nested
        fam = row.get("lineage_family")
        if not fam and isinstance(row.get("result"), dict):
            fam = ((row["result"].get("analysis") or {}).get("lineage") or {}).get("family_id")
        if fam:
            n_lineage += 1
            families.add(fam)
    coverage = n_lineage / n if n else 0.0
    # crude tiering for post-scan advisory
    if coverage >= 0.85 and len(families) >= 4:
        tier = "ELEVATED"
    elif coverage >= 0.5:
        tier = "MODERATE"
    elif coverage > 0:
        tier = "LOW"
    else:
        tier = "LOW"
    plan = plan_scan_from_tier(tier)
    return {
        "schema": "hyperlex.scan_risk_aggregate.v1",
        "n_results": n,
        "n_with_lineage": n_lineage,
        "families": sorted(families),
        "coverage": round(coverage, 3),
        "recommended_tier": tier,
        "next_plan": {
            "cron": plan["policy"]["cron"],
            "interval_hours": plan["policy"]["interval_hours"],
            "max_queries": plan["policy"]["max_queries"],
            "source_recommend": plan["policy"]["source_recommend"],
        },
        "provenance": "SPECULATIVE",
        "brier": None,
        "note": "Post-scan advisory only; re-run risk-schedule for full Phase 5 risk.",
    }
