"""Phase 5 scenario runner — compose transmission + multi-agent + risk.

Optional integration from a full analysis result.

Multi-term seeds (e.g. ``sigma rizz locked in``) expand into **separate**
atomic scenarios by default — one per lexicon term — never one blended seed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

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
    expand_terms: bool = True,
) -> Dict[str, Any]:
    """
    Run the Phase 5 research stack for one seed term / optional analysis.

    When ``expand_terms`` is True (default) and the seed splits into multiple
    lexicon atoms (``sigma`` | ``rizz`` | ``locked in``), returns a multi-term
    packet with one full scenario per term.

    All nested packets remain SPECULATIVE; top-level brier is always null.
    """
    raw = (seed_term or "term").strip() or "term"

    if expand_terms:
        from hyperlex.analysis.terms import split_seed_terms

        split = split_seed_terms(raw)
        terms = list(split.get("terms") or [])
        if split.get("multi_term") and len(terms) > 1:
            return run_phase5_multi_term(
                terms,
                original=raw,
                lineage_family=lineage_family,
                virality_hybrid=virality_hybrid,
                memetic_score=memetic_score,
                hyperstition_stage=hyperstition_stage,
                domain=domain,
                n_communities=n_communities,
                transmission_steps=transmission_steps,
                n_agents=n_agents,
                agent_steps=agent_steps,
                include_phylogeny=include_phylogeny,
            )

    term = raw
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
        "multi_term": False,
        "note": (
            "Phase 5 research scenario for a single atomic seed term. "
            "Cultural transmission + multi-agent + hyperstition risk are SPECULATIVE. "
            "Never invents Brier. Pass a multi-term string to expand automatically."
        ),
    }


def run_phase5_multi_term(
    terms: Sequence[str],
    *,
    original: Optional[str] = None,
    lineage_family: Optional[str] = None,
    virality_hybrid: float = 0.5,
    memetic_score: float = 0.5,
    hyperstition_stage: Optional[str] = None,
    domain: str = "general",
    n_communities: int = 6,
    transmission_steps: int = 12,
    n_agents: int = 20,
    agent_steps: int = 15,
    include_phylogeny: bool = True,
) -> Dict[str, Any]:
    """Run one Phase 5 scenario per atomic term; never blend seeds."""
    scenarios: List[Dict[str, Any]] = []
    for t in terms:
        term = str(t).strip()
        if not term:
            continue
        sc = run_phase5_scenario(
            term,
            lineage_family=lineage_family,
            virality_hybrid=virality_hybrid,
            memetic_score=memetic_score,
            hyperstition_stage=hyperstition_stage,
            domain=domain,
            analysis_result=None,
            n_communities=n_communities,
            transmission_steps=transmission_steps,
            n_agents=n_agents,
            agent_steps=agent_steps,
            include_phylogeny=include_phylogeny,
            expand_terms=False,  # already atomic
        )
        scenarios.append(sc)

    # Compact summary for CLI / archive (no full agent dumps)
    summaries = []
    for sc in scenarios:
        risk = sc.get("hyperstition_risk") or {}
        summaries.append({
            "seed_term": sc.get("seed_term"),
            "lineage_family": sc.get("lineage_family"),
            "risk_tier": risk.get("tier"),
            "risk_score": risk.get("risk_score"),
            "transmission_peak": (sc.get("transmission") or {}).get("summary", {}).get("peak_mean_adoption"),
            "cascade_success": (sc.get("multi_agent") or {}).get("summary", {}).get("cascade_success"),
            "brier": None,
        })

    tiers = [s.get("risk_tier") for s in summaries if s.get("risk_tier")]
    # advisory aggregate: highest severity among atoms
    order = {"LOW": 0, "MODERATE": 1, "ELEVATED": 2, "CRITICAL": 3}
    top_tier = None
    if tiers:
        top_tier = max(tiers, key=lambda t: order.get(str(t), 0))

    return {
        "schema": "hyperlex.phase5_multi_term.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "original_seed": original or " ".join(str(t) for t in terms),
        "terms": [s.get("seed_term") for s in scenarios],
        "n_terms": len(scenarios),
        "multi_term": True,
        "scenarios": scenarios,
        "summaries": summaries,
        "aggregate": {
            "top_risk_tier": top_tier,
            "n_terms": len(scenarios),
            "note": "Per-term scenarios only; aggregate tier is max severity, not a blended simulation.",
        },
        "domain": domain,
        "provenance": "SPECULATIVE",
        "brier": None,
        "note": (
            "Each lexicon term is simulated separately. "
            "'sigma rizz locked in' → sigma | rizz | locked in — never one blended seed. "
            "SPECULATIVE; brier always null."
        ),
    }
