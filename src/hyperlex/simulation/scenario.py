"""Phase 5 scenario runner — compose transmission + multi-agent + risk.

Optional integration from a full analysis result.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .transmission import simulate_cultural_transmission
from .agents import run_multi_agent_memetics
from .risk import forecast_hyperstition_risk, risk_from_analysis
from .phylogeny import build_family_phylogeny


def run_phase5_scenario(
    seed_term: str,
    *,
    lineage_family: Optional[str] = None,
    virality_hybrid: float = 0.5,
    memetic_score: float = 0.5,
    hyperstition_stage: Optional[str] = None,
    domain: str = "general",
    analysis_result: Optional[Dict[str, Any]] = None,
    n_communities: int = 6,
    transmission_steps: int = 12,
    n_agents: int = 20,
    agent_steps: int = 15,
    include_phylogeny: bool = True,
) -> Dict[str, Any]:
    """
    Run the Phase 5 research stack for one seed term / optional analysis.

    All nested packets remain SPECULATIVE; top-level brier is always null.
    """
    term = (seed_term or "term").strip() or "term"
    fam = lineage_family
    vh = float(virality_hybrid)
    ms = float(memetic_score)
    stage = hyperstition_stage

    if analysis_result:
        analysis = analysis_result.get("analysis") or {}
        lin = analysis.get("lineage") or {}
        vir = analysis.get("virality") or {}
        mem = analysis.get("memetics") or {}
        hyper = analysis.get("hyperstition") or {}
        fam = fam or lin.get("family_id")
        vh = float(vir.get("hybrid_score") or vh)
        ms = float(mem.get("score") or ms)
        stage = stage or hyper.get("loop_stage")
        if not term or term == "term":
            term = str(analysis_result.get("query") or term)

    transmission = simulate_cultural_transmission(
        term,
        n_communities=n_communities,
        steps=transmission_steps,
        lineage_family=fam,
        virality_hybrid=vh,
    )
    multi_agent = run_multi_agent_memetics(
        term,
        n_agents=n_agents,
        steps=agent_steps,
        lineage_family=fam,
        memetic_score=ms,
    )

    if analysis_result:
        risk = risk_from_analysis(
            analysis_result,
            transmission=transmission,
            multi_agent=multi_agent,
            domain=domain,
        )
    else:
        risk = forecast_hyperstition_risk(
            hyperstition_stage=stage,
            virality_hybrid=vh,
            memetic_score=ms,
            transmission_peak=transmission["summary"]["peak_mean_adoption"],
            transmission_reach=transmission["summary"]["final_reach_fraction"],
            agent_cascade_success=multi_agent["summary"]["cascade_success"],
            agent_adoption_rate=multi_agent["summary"]["final_adoption_rate"],
            domain=domain,
            seed_term=term,
            lineage_family=fam,
        )

    phylo = None
    if include_phylogeny and fam:
        phylo = build_family_phylogeny(fam)

    return {
        "schema": "hyperlex.phase5_scenario.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed_term": term,
        "lineage_family": fam,
        "domain": domain,
        "transmission": transmission,
        "multi_agent": multi_agent,
        "hyperstition_risk": risk,
        "phylogeny": phylo,
        "provenance": "SPECULATIVE",
        "brier": None,
        "note": (
            "Phase 5 research scenario. Cultural transmission + multi-agent + "
            "hyperstition risk are SPECULATIVE. Never invents Brier."
        ),
    }
