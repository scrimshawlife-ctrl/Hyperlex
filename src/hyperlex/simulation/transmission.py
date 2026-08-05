"""Cultural transmission simulation (deterministic cascade).

Inspired by cultural-transmission / diffusion literature (arXiv 2203.00715
distillation): discrete communities exchange adoption probability over time
with decay and community-specific resistance.

Pure function. Label: SPECULATIVE. Not Brier-eligible.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# Named community slots (abstract; not real platforms)
DEFAULT_COMMUNITIES = (
    "origin_niche",
    "adjacent_subculture",
    "platform_feed",
    "mainstream_discourse",
    "institutional",
    "archive_residual",
)


def simulate_cultural_transmission(
    seed_term: str,
    *,
    n_communities: int = 6,
    steps: int = 12,
    beta: float = 0.35,
    gamma: float = 0.08,
    seed_community: int = 0,
    seed_adoption: float = 0.85,
    lineage_family: Optional[str] = None,
    virality_hybrid: float = 0.5,
    resistance: Optional[List[float]] = None,
    community_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Discrete-time multi-community transmission cascade.

    Each step: community j receives inflow from neighbors proportional to
    adoption_i * beta * (1 - resistance_j), then decays by gamma.

    Returns trajectories + summary metrics (peak, time-to-peak, reach).
    """
    term = (seed_term or "term").strip() or "term"
    n = max(2, min(12, int(n_communities)))
    t_steps = max(1, min(48, int(steps)))
    b = max(0.0, min(1.0, float(beta)))
    g = max(0.0, min(0.5, float(gamma)))
    sc = max(0, min(n - 1, int(seed_community)))
    vh = max(0.0, min(1.0, float(virality_hybrid)))
    # virality scales effective transmission
    b_eff = min(1.0, b * (0.55 + 0.9 * vh))

    names = list(community_names) if community_names else list(DEFAULT_COMMUNITIES[:n])
    while len(names) < n:
        names.append(f"community_{len(names)}")
    names = names[:n]

    if resistance is None:
        # later communities more resistant (institutional / residual)
        res = [0.05 + 0.12 * i / max(1, n - 1) for i in range(n)]
    else:
        res = [max(0.0, min(0.95, float(r))) for r in resistance[:n]]
        while len(res) < n:
            res.append(0.2)

    state = [0.0] * n
    state[sc] = max(0.0, min(1.0, float(seed_adoption)))
    trajectory: List[Dict[str, Any]] = []
    peak = state[sc]
    peak_step = 0

    for step in range(t_steps + 1):
        snapshot = {
            "step": step,
            "adoptions": {names[i]: round(state[i], 4) for i in range(n)},
            "mean_adoption": round(sum(state) / n, 4),
            "n_above_threshold": sum(1 for x in state if x >= 0.25),
        }
        trajectory.append(snapshot)
        if snapshot["mean_adoption"] > peak:
            peak = snapshot["mean_adoption"]
            peak_step = step

        if step == t_steps:
            break

        nxt = list(state)
        for j in range(n):
            # inflow from adjacent indices (1D chain + weak global)
            inflow = 0.0
            for i in range(n):
                if i == j:
                    continue
                dist = abs(i - j)
                weight = 1.0 / dist if dist <= 2 else 0.08 / dist
                inflow += state[i] * weight
            inflow = inflow / max(1.0, n - 1)
            growth = b_eff * inflow * (1.0 - state[j]) * (1.0 - res[j])
            nxt[j] = max(0.0, min(1.0, state[j] + growth - g * state[j]))
        state = nxt

    final = trajectory[-1]
    reach = final["n_above_threshold"] / n
    # stabilization: last 3 steps variance of mean
    means = [t["mean_adoption"] for t in trajectory[-3:]]
    if len(means) >= 2:
        mu = sum(means) / len(means)
        var = sum((m - mu) ** 2 for m in means) / len(means)
        stabilizing = var < 0.002
    else:
        stabilizing = False

    return {
        "schema": "hyperlex.cultural_transmission.v1",
        "seed_term": term,
        "lineage_family": lineage_family,
        "params": {
            "n_communities": n,
            "steps": t_steps,
            "beta": b,
            "beta_effective": round(b_eff, 4),
            "gamma": g,
            "seed_community": sc,
            "seed_adoption": round(float(seed_adoption), 4),
            "virality_hybrid": vh,
            "resistance": [round(r, 3) for r in res],
            "communities": names,
        },
        "trajectory": trajectory,
        "summary": {
            "peak_mean_adoption": round(peak, 4),
            "time_to_peak": peak_step,
            "final_mean_adoption": final["mean_adoption"],
            "final_reach_fraction": round(reach, 4),
            "stabilizing": stabilizing,
            "dominant_community": max(
                final["adoptions"].items(), key=lambda kv: kv[1]
            )[0]
            if final["adoptions"]
            else names[sc],
        },
        "provenance": "SPECULATIVE",
        "brier": None,
        "note": (
            "Abstract multi-community cascade; not a real-world prediction. "
            "Not Brier-eligible without settlement design."
        ),
    }
