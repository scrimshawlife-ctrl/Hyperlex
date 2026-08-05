"""Hyperlex — Hermes skill package for memetic emergence analysis.

Architecture:
  intake → analysis → synthesis → receipt → calibration → relay

Abraxas is **not** a dependency. Relevant Abraxas-shaped capabilities
(Brier ledger/score packets, claim labels, operator review, HLX runes)
are pure Hyperlex modules under ``hyperlex.compat.abraxas`` so hosts may
import them from Hyperlex.

Schemas live under ``hyperlex.schemas`` and repo ``schemas/``.
"""
from pathlib import Path


def _read_version() -> str:
    candidate = Path(__file__).resolve().parents[2] / "VERSION"
    if candidate.exists():
        return candidate.read_text(encoding="utf-8").strip() or "0.1.0"
    return "0.1.0"


PKG_VERSION = _read_version()

from .intake import ingest_signal, fetch_ingest
from .analysis import (
    humanize_slang_output,
    detect_neologisms,
    trace_semantic_variation,
    compute_virality_score,
    predict_virality,
    memetics_protocol_check,
    simulate_hyperstition_loop,
    detect_memetic_patterns,
    match_lineage,
    compute_lineage_confidence,
)
from .analysis.backfill import apply_backfill, inventory_backfill, list_backfill_packs
from .analysis.backprop import backpropagate_lineage
from .synthesis import mock_integrate_with_external_signal
from .receipt import (
    emit_receipt,
    verify_receipt,
    default_ledger_path,
    list_receipts,
    verify_ledger_chain,
    ledger_stats,
)
from . import schemas
from . import calibration
from . import relay
from . import compat
from .relay import (
    relay_from_result,
    relay_forecasts,
    relay_series,
    list_runes,
)
from .calibration import (
    extract_forecasts,
    settle,
    score_pair,
    score_series,
    settle_and_log,
    recompute_series,
    append_forecast,
    default_log_path,
    NOT_COMPUTABLE,
)
from . import connectors
from . import diagrams
from . import archive
from . import simulation
from .diagrams import (
    diagram_from_ledger,
    diagram_from_receipt_files,
    write_diagram_bundle,
)
from .archive import (
    export_analysis_archive,
    export_run_history,
    rebuild_archive_catalog,
)
from .connectors import (
    build_market_signal,
    build_forecast_pipeline,
    hyperstition_feedback_from_series,
)
from .simulation import (
    simulate_cultural_transmission,
    run_multi_agent_memetics,
    forecast_hyperstition_risk,
    risk_from_analysis,
    build_family_phylogeny,
    list_phylogeny_families,
    build_domain_phylogeny,
    list_domain_packs,
    run_phase5_scenario,
    calibrate_transmission_params,
    compare_scenarios,
    list_scenario_presets,
    run_named_scenario,
    export_research_packet,
    plan_scan_from_risk,
    plan_scan_from_term,
    plan_scan_from_tier,
    write_scan_plan,
    aggregate_scan_risk,
    TIER_POLICY,
)
from . import vectordb
from .vectordb import (
    seed_all as vector_seed_all,
    vector_search,
    VectorStore,
    default_vector_db_path,
)

# Stable public API (v0.2 freeze) — see docs/api-v1.md
API_V1 = (
    "ingest_signal",
    "fetch_ingest",
    "detect_memetic_patterns",
    "match_lineage",
    "compute_lineage_confidence",
    "mock_integrate_with_external_signal",
    "emit_receipt",
    "verify_receipt",
    "extract_forecasts",
    "settle",
    "score_pair",
    "score_series",
    "settle_and_log",
    "recompute_series",
    "relay_from_result",
    "relay_forecasts",
    "relay_series",
    "list_runes",
    "NOT_COMPUTABLE",
    "PKG_VERSION",
)

# Extended (0.2.2+) — stable additive surface, not removing API_V1
API_EXTENDED = (
    "build_market_signal",
    "build_forecast_pipeline",
    "hyperstition_feedback_from_series",
    "diagram_from_ledger",
    "diagram_from_receipt_files",
    "write_diagram_bundle",
    "predict_virality",
    "export_analysis_archive",
    "export_run_history",
    "rebuild_archive_catalog",
    "apply_backfill",
    "inventory_backfill",
    "list_backfill_packs",
    "backpropagate_lineage",
    "simulate_cultural_transmission",
    "run_multi_agent_memetics",
    "forecast_hyperstition_risk",
    "risk_from_analysis",
    "build_family_phylogeny",
    "list_phylogeny_families",
    "build_domain_phylogeny",
    "list_domain_packs",
    "run_phase5_scenario",
    "calibrate_transmission_params",
    "compare_scenarios",
    "list_scenario_presets",
    "run_named_scenario",
    "export_research_packet",
    "plan_scan_from_risk",
    "plan_scan_from_term",
    "plan_scan_from_tier",
    "write_scan_plan",
    "aggregate_scan_risk",
    "TIER_POLICY",
    "vector_seed_all",
    "vector_search",
    "VectorStore",
    "default_vector_db_path",
)

__all__ = [
    *API_V1,
    *API_EXTENDED,
    "default_ledger_path",
    "list_receipts",
    "verify_ledger_chain",
    "ledger_stats",
    "humanize_slang_output",
    "compute_virality_score",
    "predict_virality",
    "simulate_hyperstition_loop",
    "detect_neologisms",
    "trace_semantic_variation",
    "memetics_protocol_check",
    "append_forecast",
    "default_log_path",
    "calibration",
    "relay",
    "connectors",
    "compat",
    "archive",
    "schemas",
    "API_V1",
    "diagram_from_ledger",
    "diagram_from_receipt_files",
    "write_diagram_bundle",
    "diagrams",
    "export_analysis_archive",
    "export_run_history",
    "rebuild_archive_catalog",
    "apply_backfill",
    "inventory_backfill",
    "list_backfill_packs",
    "backpropagate_lineage",
    "simulate_cultural_transmission",
    "run_multi_agent_memetics",
    "forecast_hyperstition_risk",
    "risk_from_analysis",
    "build_family_phylogeny",
    "list_phylogeny_families",
    "build_domain_phylogeny",
    "list_domain_packs",
    "run_phase5_scenario",
    "calibrate_transmission_params",
    "compare_scenarios",
    "list_scenario_presets",
    "run_named_scenario",
    "export_research_packet",
    "simulation",
    "vector_seed_all",
    "vector_search",
    "VectorStore",
    "default_vector_db_path",
    "vectordb",
    "API_EXTENDED",
]

__version__ = PKG_VERSION
