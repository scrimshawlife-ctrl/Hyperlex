"""Multi-agent scenario library + comparative runs.

Named presets over role mix / influence / seed adopters for comparative
research. All outputs SPECULATIVE; brier always null.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .agents import run_multi_agent_memetics

# Named research presets
SCENARIO_LIBRARY: Dict[str, Dict[str, Any]] = {
    "baseline": {
        "label": "Default role lattice",
        "n_agents": 20,
        "steps": 15,
        "seed_adopters": 2,
        "influence": 0.22,
        "decay": 0.05,
        "role_mix": None,
    },
    "viral_cascade": {
        "label": "Amplifier-heavy viral cascade",
        "n_agents": 24,
        "steps": 18,
        "seed_adopters": 3,
        "influence": 0.32,
        "decay": 0.03,
        "role_mix": {
            "innovator": 2,
            "early_adopter": 4,
            "mainstream": 8,
            "skeptic": 2,
            "amplifier": 8,
        },
    },
    "skeptic_wall": {
        "label": "Skeptic-dominated resistance",
        "n_agents": 24,
        "steps": 18,
        "seed_adopters": 2,
        "influence": 0.18,
        "decay": 0.08,
        "role_mix": {
            "innovator": 1,
            "early_adopter": 3,
            "mainstream": 6,
            "skeptic": 12,
            "amplifier": 2,
        },
    },
    "elite_innovators": {
        "label": "Innovator core, thin mainstream",
        "n_agents": 18,
        "steps": 16,
        "seed_adopters": 4,
        "influence": 0.28,
        "decay": 0.04,
        "role_mix": {
            "innovator": 6,
            "early_adopter": 4,
            "mainstream": 4,
            "skeptic": 2,
            "amplifier": 2,
        },
    },
    "slow_burn": {
        "label": "Low influence, long horizon",
        "n_agents": 20,
        "steps": 28,
        "seed_adopters": 1,
        "influence": 0.12,
        "decay": 0.02,
        "role_mix": None,
    },
}


def list_scenario_presets() -> List[Dict[str, Any]]:
    return [
        {"id": k, "label": v.get("label"), "n_agents": v.get("n_agents"), "steps": v.get("steps")}
        for k, v in SCENARIO_LIBRARY.items()
    ]


def run_named_scenario(
    scenario_id: str,
    seed_term: str,
    *,
    lineage_family: Optional[str] = None,
    memetic_score: float = 0.5,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if scenario_id not in SCENARIO_LIBRARY:
        return {
            "schema": "hyperlex.multi_agent_scenario.v1",
            "ok": False,
            "error": "unknown_scenario",
            "scenario_id": scenario_id,
            "available": list(SCENARIO_LIBRARY.keys()),
            "brier": None,
        }
    cfg = dict(SCENARIO_LIBRARY[scenario_id])
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if k in cfg or k in {
            "n_agents", "steps", "seed_adopters", "influence", "decay", "role_mix", "memetic_score"
        }})
    label = cfg.pop("label", scenario_id)
    result = run_multi_agent_memetics(
        seed_term,
        n_agents=int(cfg.get("n_agents") or 20),
        steps=int(cfg.get("steps") or 15),
        seed_adopters=int(cfg.get("seed_adopters") or 2),
        influence=float(cfg.get("influence") or 0.22),
        decay=float(cfg.get("decay") or 0.05),
        lineage_family=lineage_family,
        memetic_score=float(cfg.get("memetic_score") or memetic_score),
        role_mix=cfg.get("role_mix"),
    )
    return {
        "schema": "hyperlex.multi_agent_scenario.v1",
        "ok": True,
        "scenario_id": scenario_id,
        "label": label,
        "params": {
            "n_agents": cfg.get("n_agents"),
            "steps": cfg.get("steps"),
            "seed_adopters": cfg.get("seed_adopters"),
            "influence": cfg.get("influence"),
            "decay": cfg.get("decay"),
            "role_mix": cfg.get("role_mix"),
        },
        "summary": result.get("summary"),
        "history_tail": (result.get("history") or [])[-3:],
        "provenance": "SPECULATIVE",
        "brier": None,
        "full": result,
    }


def compare_scenarios(
    seed_term: str,
    *,
    scenario_ids: Optional[Sequence[str]] = None,
    lineage_family: Optional[str] = None,
    memetic_score: float = 0.5,
) -> Dict[str, Any]:
    ids = list(scenario_ids) if scenario_ids else list(SCENARIO_LIBRARY.keys())
    runs = []
    for sid in ids:
        r = run_named_scenario(
            sid,
            seed_term,
            lineage_family=lineage_family,
            memetic_score=memetic_score,
        )
        if not r.get("ok"):
            continue
        # drop full agent dump for comparison packet
        compact = {k: v for k, v in r.items() if k != "full"}
        runs.append(compact)

    # rank by final adoption rate
    ranked = sorted(
        runs,
        key=lambda r: float((r.get("summary") or {}).get("final_adoption_rate") or 0.0),
        reverse=True,
    )
    return {
        "schema": "hyperlex.multi_agent_compare.v1",
        "ok": True,
        "seed_term": seed_term,
        "lineage_family": lineage_family,
        "n_scenarios": len(runs),
        "ranking": [
            {
                "scenario_id": r["scenario_id"],
                "label": r.get("label"),
                "final_adoption_rate": (r.get("summary") or {}).get("final_adoption_rate"),
                "cascade_success": (r.get("summary") or {}).get("cascade_success"),
                "time_to_half": (r.get("summary") or {}).get("time_to_half"),
            }
            for r in ranked
        ],
        "runs": ranked,
        "provenance": "SPECULATIVE",
        "brier": None,
        "note": "Comparative multi-agent presets; not a real-user forecast.",
    }
