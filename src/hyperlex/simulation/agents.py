"""Multi-agent memetic modeling (lightweight role lattice).

Agents occupy roles with different adoption thresholds and broadcast weights.
Deterministic given seed. Label: SPECULATIVE.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

AGENT_ROLES = (
    "innovator",
    "early_adopter",
    "mainstream",
    "skeptic",
    "amplifier",
)

# threshold to adopt / relative broadcast strength / default count
_ROLE_SPEC = {
    "innovator": {"threshold": 0.15, "broadcast": 0.9, "default_n": 2},
    "early_adopter": {"threshold": 0.35, "broadcast": 0.7, "default_n": 4},
    "mainstream": {"threshold": 0.55, "broadcast": 0.4, "default_n": 8},
    "skeptic": {"threshold": 0.8, "broadcast": 0.2, "default_n": 3},
    "amplifier": {"threshold": 0.4, "broadcast": 1.0, "default_n": 2},
}


def _build_population(
    n_agents: int,
    role_mix: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    agents: List[Dict[str, Any]] = []
    if role_mix:
        for role, count in role_mix.items():
            if role not in _ROLE_SPEC:
                continue
            for _ in range(max(0, int(count))):
                agents.append(_make_agent(role, len(agents)))
    else:
        # proportional defaults scaled to n_agents
        base = sum(s["default_n"] for s in _ROLE_SPEC.values())
        for role, spec in _ROLE_SPEC.items():
            k = max(1, round(n_agents * spec["default_n"] / base))
            for _ in range(k):
                agents.append(_make_agent(role, len(agents)))
        # trim or pad to n_agents
        if len(agents) > n_agents:
            agents = agents[:n_agents]
        while len(agents) < n_agents:
            agents.append(_make_agent("mainstream", len(agents)))
    return agents


def _make_agent(role: str, idx: int) -> Dict[str, Any]:
    spec = _ROLE_SPEC[role]
    return {
        "id": f"a{idx:03d}",
        "role": role,
        "threshold": spec["threshold"],
        "broadcast": spec["broadcast"],
        "adopted": False,
        "exposure": 0.0,
        "adopt_step": None,
    }


def run_multi_agent_memetics(
    seed_term: str,
    *,
    n_agents: int = 20,
    steps: int = 15,
    seed_adopters: int = 2,
    influence: float = 0.22,
    decay: float = 0.05,
    lineage_family: Optional[str] = None,
    memetic_score: float = 0.5,
    role_mix: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Exposure-driven adoption among role-typed agents.

    Seed agents start adopted; each step others accumulate exposure from
    adopted agents' broadcast weights; adopt when exposure ≥ threshold.
    """
    term = (seed_term or "term").strip() or "term"
    n = max(4, min(80, int(n_agents)))
    t_steps = max(1, min(60, int(steps)))
    inf = max(0.0, min(1.0, float(influence)))
    dec = max(0.0, min(0.5, float(decay)))
    ms = max(0.0, min(1.0, float(memetic_score)))
    # memetic score slightly lowers thresholds
    thr_scale = 1.0 - 0.15 * ms

    agents = _build_population(n, role_mix)
    n_seed = max(1, min(len(agents), int(seed_adopters)))
    # innovators first if present
    innovators = [a for a in agents if a["role"] == "innovator"]
    seeds = innovators[:n_seed]
    if len(seeds) < n_seed:
        for a in agents:
            if a not in seeds:
                seeds.append(a)
            if len(seeds) >= n_seed:
                break
    for a in seeds:
        a["adopted"] = True
        a["adopt_step"] = 0
        a["exposure"] = 1.0

    history: List[Dict[str, Any]] = []
    for step in range(t_steps + 1):
        n_adopted = sum(1 for a in agents if a["adopted"])
        by_role: Dict[str, int] = {}
        for a in agents:
            if a["adopted"]:
                by_role[a["role"]] = by_role.get(a["role"], 0) + 1
        history.append({
            "step": step,
            "n_adopted": n_adopted,
            "adoption_rate": round(n_adopted / len(agents), 4),
            "by_role": dict(sorted(by_role.items())),
        })
        if step == t_steps:
            break

        # broadcast field
        field = sum(a["broadcast"] for a in agents if a["adopted"]) / max(1, len(agents))
        for a in agents:
            if a["adopted"]:
                continue
            a["exposure"] = max(0.0, a["exposure"] * (1.0 - dec) + inf * field)
            thr = a["threshold"] * thr_scale
            if a["exposure"] >= thr:
                a["adopted"] = True
                a["adopt_step"] = step + 1

    final_rate = history[-1]["adoption_rate"]
    # cascade success if >50% and amplifier/mainstream involved
    roles_hit = set()
    for a in agents:
        if a["adopted"]:
            roles_hit.add(a["role"])
    cascade = final_rate >= 0.5 and ("mainstream" in roles_hit or "amplifier" in roles_hit)

    agent_rows = [
        {
            "id": a["id"],
            "role": a["role"],
            "adopted": a["adopted"],
            "adopt_step": a["adopt_step"],
            "exposure": round(a["exposure"], 4),
            "threshold": round(a["threshold"] * thr_scale, 4),
        }
        for a in agents
    ]

    return {
        "schema": "hyperlex.multi_agent_memetics.v1",
        "seed_term": term,
        "lineage_family": lineage_family,
        "params": {
            "n_agents": len(agents),
            "steps": t_steps,
            "seed_adopters": n_seed,
            "influence": inf,
            "decay": dec,
            "memetic_score": ms,
            "threshold_scale": round(thr_scale, 4),
        },
        "history": history,
        "agents": agent_rows,
        "summary": {
            "final_adoption_rate": final_rate,
            "cascade_success": cascade,
            "roles_adopted": sorted(roles_hit),
            "time_to_half": next(
                (h["step"] for h in history if h["adoption_rate"] >= 0.5),
                None,
            ),
        },
        "provenance": "SPECULATIVE",
        "brier": None,
        "note": (
            "Abstract role-lattice adoption model; not a prediction of real users. "
            "Not Brier-eligible without settlement design."
        ),
    }
