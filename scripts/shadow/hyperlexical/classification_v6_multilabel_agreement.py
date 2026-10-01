"""Multi-label / set agreement metrics for V6 ontology settlement amendment.

κ alone is not the acceptance metric. Reports three levels:
  1) per-label/axis pos/neg agreement + κ
  2) per-example Jaccard / set-F1
  3) boundary confusion matrices

Also Wilson score CIs and boundary-stratum support checks.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v6_human_ontology_settlement import (
    STABILITY_CRITERIA,
    _cohen_kappa,
    set_jaccard,
)


def wilson_interval(successes: int, n: int, z: float = 1.96) -> dict[str, float | None]:
    if n <= 0:
        return {"p": None, "lo": None, "hi": None, "n": 0}
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return {
        "p": p,
        "lo": max(0.0, center - margin),
        "hi": min(1.0, center + margin),
        "n": n,
    }


def label_set(rater: Mapping[str, Any]) -> set[str]:
    labs = set()
    for d in rater.get("domains") or []:
        labs.add(f"domain:{d}")
    for f in rater.get("functions") or []:
        labs.add(f"function:{f}")
    for m in rater.get("mediation") or []:
        labs.add(f"mediation:{m}")
    # identity as context axis, not Stage-B gold — still tracked for boundary study
    idr = rater.get("identity_relevance")
    if idr == "CLEAR_POSITIVE":
        labs.add("context:identity_positive")
    elif idr == "INSUFFICIENT_CONTEXT":
        labs.add("context:identity_insufficient")
    return labs


def set_f1(a: Sequence[str] | set[str], b: Sequence[str] | set[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    prec = len(sa & sb) / len(sa)
    rec = len(sa & sb) / len(sb)
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


def three_level_agreement(annotated: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Full three-level multi-label agreement report."""
    # Level 1 — per label
    labels_of_interest = [
        ("domain", "gambling_betting"),
        ("domain", "crypto_markets"),
        ("function", "evaluative_stance"),
        ("function", "relational_intimacy"),
        ("mediation", "internet_register"),
    ]
    per_label = {}
    for axis, lab in labels_of_interest:
        key = {"domain": "domains", "function": "functions", "mediation": "mediation"}[axis]
        pa = ["POS" if lab in (r["rater_a"].get(key) or []) else "NEG" for r in annotated]
        pb = ["POS" if lab in (r["rater_b"].get(key) or []) else "NEG" for r in annotated]
        raw_n = sum(x == y for x, y in zip(pa, pb))
        pos_ag = sum(x == "POS" and y == "POS" for x, y in zip(pa, pb))
        pos_either = sum(x == "POS" or y == "POS" for x, y in zip(pa, pb))
        neg_ag = sum(x == "NEG" and y == "NEG" for x, y in zip(pa, pb))
        neg_either = sum(x == "NEG" or y == "NEG" for x, y in zip(pa, pb))
        per_label[f"{axis}:{lab}"] = {
            "raw_agreement": raw_n / max(1, len(pa)),
            "raw_ci": wilson_interval(raw_n, len(pa)),
            "positive_agreement": pos_ag / max(1, pos_either),
            "positive_ci": wilson_interval(pos_ag, pos_either),
            "negative_agreement": neg_ag / max(1, neg_either),
            "cohen_kappa": _cohen_kappa(pa, pb),
            "n_pos_either": pos_either,
            "n": len(pa),
        }

    # identity axis
    id_a = [r["rater_a"]["identity_relevance"] for r in annotated]
    id_b = [r["rater_b"]["identity_relevance"] for r in annotated]
    id_raw = sum(x == y for x, y in zip(id_a, id_b))
    per_label["identity_relevance"] = {
        "raw_agreement": id_raw / max(1, len(id_a)),
        "raw_ci": wilson_interval(id_raw, len(id_a)),
        "cohen_kappa": _cohen_kappa(id_a, id_b),
        "confusion": dict(Counter(f"{a}|{b}" for a, b in zip(id_a, id_b))),
        "n": len(id_a),
    }

    # Level 2 — per example set metrics
    jaccards = []
    f1s = []
    for r in annotated:
        sa, sb = label_set(r["rater_a"]), label_set(r["rater_b"])
        jaccards.append(set_jaccard(sa, sb))
        f1s.append(set_f1(sa, sb))
    mean_j = sum(jaccards) / max(1, len(jaccards))
    mean_f1 = sum(f1s) / max(1, len(f1s))
    # treat "exact set match" as successes for CI
    exact = sum(1 for j in jaccards if j >= 1.0 - 1e-12)
    per_example = {
        "mean_jaccard": mean_j,
        "mean_set_f1": mean_f1,
        "exact_set_match_rate": exact / max(1, len(jaccards)),
        "exact_set_match_ci": wilson_interval(exact, len(jaccards)),
        "jaccard_histogram": dict(
            Counter(
                "1.0"
                if j >= 0.999
                else "0.5-0.99"
                if j >= 0.5
                else "0.01-0.49"
                if j > 0
                else "0.0"
                for j in jaccards
            )
        ),
    }

    # Level 3 — boundary matrices (presence POS/NEG cross)
    def boundary_matrix(lab_a: tuple[str, str], lab_b: tuple[str, str]) -> dict[str, Any]:
        """Confusion of co-presence using adjudicated labels when available."""
        key_a = {"domain": "domains", "function": "functions", "mediation": "mediation", "identity": "identity_relevance"}[
            lab_a[0] if lab_a[0] != "context" else "identity"
        ]
        # Use rater_a vs rater_b joint view via adjudicated for boundary ontology questions
        cells = Counter()
        for r in annotated:
            adj = r["adjudicated"]
            if lab_a[0] == "identity" or lab_a[1] == "identity_positive":
                a_pos = adj.get("identity_relevance") == "CLEAR_POSITIVE"
            else:
                axis = {"domain": "domains", "function": "functions", "mediation": "mediation"}[lab_a[0]]
                a_pos = lab_a[1] in (adj.get(axis) or [])
            if lab_b[0] == "identity" or lab_b[1] == "identity_positive":
                b_pos = adj.get("identity_relevance") == "CLEAR_POSITIVE"
            else:
                axis = {"domain": "domains", "function": "functions", "mediation": "mediation"}[lab_b[0]]
                b_pos = lab_b[1] in (adj.get(axis) or [])
            cells[f"{'POS' if a_pos else 'NEG'}x{'POS' if b_pos else 'NEG'}"] += 1
        return {"cells": dict(cells), "n": sum(cells.values())}

    boundaries = {
        "identity_vs_evaluative": boundary_matrix(
            ("identity", "identity_positive"), ("function", "evaluative_stance")
        ),
        "evaluative_vs_relational": boundary_matrix(
            ("function", "evaluative_stance"), ("function", "relational_intimacy")
        ),
        "gambling_vs_crypto": boundary_matrix(
            ("domain", "gambling_betting"), ("domain", "crypto_markets")
        ),
    }

    # Preserve non-forced uncertainty outcomes from raters (not collapsed)
    uncertainty_dist = Counter()
    for r in annotated:
        uncertainty_dist[r["rater_a"].get("outcome")] += 1
        uncertainty_dist[r["rater_b"].get("outcome")] += 1
        uncertainty_dist["adj:" + str(r["adjudicated"].get("uncertainty"))] += 1

    # Stratum support / inconclusive flags (κ not sole criterion)
    inconclusive = []
    for name, m in per_label.items():
        n_pos = int(m.get("n_pos_either") or 0)
        if name == "identity_relevance":
            # identity uses confusion, not pos_either
            n_pos = sum(
                v
                for k, v in (m.get("confusion") or {}).items()
                if "CLEAR_POSITIVE" in k
            )
        if n_pos < STABILITY_CRITERIA["INSUFFICIENT_SUPPORT"]["positive_cases_lt"]:
            inconclusive.append(
                {
                    "stratum": name,
                    "reason": "INSUFFICIENT_POSITIVE_SUPPORT",
                    "n_pos_either": n_pos,
                    "action": "TOP_UP_BOUNDARY_STRATUM",
                }
            )
        else:
            raw = float(m.get("raw_agreement") or 0)
            kappa = m.get("cohen_kappa")
            kappa_v = float(kappa) if kappa is not None else 0.0
            # acceptance uses raw+pos agreement primary; κ secondary
            pos = float(m.get("positive_agreement") or 0)
            if raw < 0.65 or (n_pos >= 5 and pos < 0.50):
                inconclusive.append(
                    {
                        "stratum": name,
                        "reason": "LOW_PRACTICAL_AGREEMENT",
                        "raw_agreement": raw,
                        "positive_agreement": pos,
                        "cohen_kappa": kappa_v,
                        "action": "TOP_UP_OR_REVISE_BOUNDARY",
                    }
                )

    return {
        "acceptance_policy": {
            "cohen_kappa_sole_metric": False,
            "levels": ["per_label_axis", "per_example_set", "boundary_matrices"],
            "preserve_outcomes": [
                "ONTOLOGY_BOUNDARY_UNCLEAR",
                "INSUFFICIENT_CONTEXT",
                "MULTI_LABEL_POSITIVE",
                "ANNOTATOR_DISAGREEMENT",
            ],
            "do_not_force_all_disagreements_to_single_gold": True,
        },
        "level1_per_label": per_label,
        "level2_per_example": per_example,
        "level3_boundaries": boundaries,
        "uncertainty_outcome_counts": dict(uncertainty_dist),
        "inconclusive_strata": inconclusive,
        "mean_example_jaccard": mean_j,
        "mean_example_set_f1": mean_f1,
        "n_rows": len(annotated),
    }


def stratum_of_row(old_family: str | None, text: str) -> list[str]:
    """Tag rows for boundary-stratified sampling."""
    tags = []
    fam = old_family or ""
    if fam == "identity-affiliation":
        tags.append("identity")
    if fam == "social-evaluation":
        tags.append("evaluative")
    if fam == "relationship-dating":
        tags.append("relational")
    if fam == "betting-sharp":
        tags.append("gambling")
    if fam == "crypto-degen":
        tags.append("crypto")
    low = (text or "").lower()
    if any(x in low for x in ("derogatory", "insult", "pejorative", "slur", "praise")):
        tags.append("evaluative")
    if any(x in low for x in ("dating", "romantic", "boyfriend", "girlfriend", "spouse")):
        tags.append("relational")
    if any(x in low for x in ("bet", "wager", "odds", "casino", "poker", "bookmaker")):
        tags.append("gambling")
    if any(x in low for x in ("crypto", "bitcoin", "ethereum", "blockchain", "nft", "defi")):
        tags.append("crypto")
    if any(x in low for x in ("demonym", "ethnicity", "nationality", "inhabitant of", "native of")):
        tags.append("identity")
    return sorted(set(tags)) or ["other"]
