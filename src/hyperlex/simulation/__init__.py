"""Phase 5 — simulation, multi-agent memetics, hyperstition risk, phylogeny scaffold.

All outputs are **SPECULATIVE** research tooling. They do not emit Brier scores,
do not auto-settle, and never rewrite historical receipt integrity.

Submodules:
  transmission — cultural transmission cascade across communities
  agents       — multi-agent role model (innovator → amplifier)
  risk         — hyperstition risk forecast for real-world systems
  phylogeny    — lightweight family tree from registry + backfill timeline
"""

from .transmission import simulate_cultural_transmission
from .agents import run_multi_agent_memetics, AGENT_ROLES
from .risk import forecast_hyperstition_risk, risk_from_analysis
from .phylogeny import (
    build_domain_phylogeny,
    build_family_phylogeny,
    list_domain_packs,
    list_phylogeny_families,
)
from .scenario import run_phase5_scenario
from .calibrate import calibrate_transmission_params, load_calibration_pairs
from .library import (
    SCENARIO_LIBRARY,
    compare_scenarios,
    list_scenario_presets,
    run_named_scenario,
)
from .research_export import export_research_packet
from .schedule import (
    TIER_POLICY,
    aggregate_scan_risk,
    plan_scan_from_risk,
    plan_scan_from_term,
    plan_scan_from_tier,
    policy_for_tier,
    write_scan_plan,
)

__all__ = [
    "simulate_cultural_transmission",
    "run_multi_agent_memetics",
    "AGENT_ROLES",
    "forecast_hyperstition_risk",
    "risk_from_analysis",
    "build_family_phylogeny",
    "list_phylogeny_families",
    "build_domain_phylogeny",
    "list_domain_packs",
    "run_phase5_scenario",
    "calibrate_transmission_params",
    "load_calibration_pairs",
    "SCENARIO_LIBRARY",
    "compare_scenarios",
    "list_scenario_presets",
    "run_named_scenario",
    "export_research_packet",
    "TIER_POLICY",
    "aggregate_scan_risk",
    "plan_scan_from_risk",
    "plan_scan_from_term",
    "plan_scan_from_tier",
    "policy_for_tier",
    "write_scan_plan",
]
