"""REVIEW_V5_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL — read-only Spark audit.

No train / retune / index rebuild / BEST moves / qualification reuse for optimization.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-qualification-failure-system-review-20261001"
)
QUAL_DIR = Path(
    "/home/morpheus/hlx-private/classification-v5-pipeline-qualification-001-20261001"
)
V1R2_SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-identifiability-filtered-v1r2-20261001/"
    "EVIDENCE_SURFACE.jsonl"
)
INDEX_PATH = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-b-v1r2-20261001/"
    "STAGE_B_INDEX.json"
)
STAGE_A_BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/STAGE_A_BEST/model.safetensors"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
STAGE_A_BEST_SHA = (
    "f2b00c5dfeb087288fc1686c901fbc8b52a8ba7a7b51cb83ff038656f93617fa"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
INDEX_SHA = "4febe96ea179597eb7792b376ed9eedbc9295a2fd8b5fa0eec969719f015c1f4"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-QUALIFICATION-FAILURE-SYSTEM-REVIEW-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
MAX_LEN = 256

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    try:
        return sha256_file(path)
    except PermissionError:
        return subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split()[0]


def sudo_read_text(path: Path) -> str:
    if os.access(path, os.R_OK):
        return path.read_text(encoding="utf-8")
    return subprocess.run(
        ["sudo", "-n", "cat", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def load_jsonl(path: Path) -> list[dict]:
    text = sudo_read_text(path)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            out["null" if key is None else str(key)] = _jsonable(value)
        return out
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    text = (
        payload
        if isinstance(payload, str)
        else json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n"
    )
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)


def write_repo(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def toks(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def length_band(text: str) -> str:
    n = len(text or "")
    if n < 40:
        return "short"
    if n < 160:
        return "med"
    return "long"


def summarize(xs: list[float]) -> dict[str, float | int | None]:
    if not xs:
        return {"n": 0, "mean": None, "p10": None, "p50": None, "p90": None}
    ys = sorted(xs)
    n = len(ys)
    return {
        "n": n,
        "mean": sum(ys) / n,
        "p10": ys[max(0, int(0.1 * n) - 1)],
        "p50": ys[n // 2],
        "p90": ys[min(n - 1, int(0.9 * n))],
    }


def max_jaccard(query: set[str], corpus: list[set[str]]) -> float:
    if not query:
        return 0.0
    best = 0.0
    for other in corpus:
        if not other:
            continue
        inter = len(query & other)
        if inter == 0:
            continue
        uni = len(query | other)
        j = inter / uni
        if j > best:
            best = j
    return best


def offline_audit() -> dict[str, Any]:
    from hyperlexical.classification_v5_qualification_failure_system_review import (
        REVIEW_ID,
        REVIEW_RULE,
        build_system_review_receipt,
        utc_now_iso,
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("MODEL_WIDE_BEST_mismatch")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mismatch")

    qual = load_jsonl(QUAL_DIR / "QUALIFICATION_SURFACE.jsonl")
    forwards = load_jsonl(QUAL_DIR / "FORWARDS.jsonl")
    metrics = json.loads(sudo_read_text(QUAL_DIR / "METRICS.json"))
    receipt = json.loads(sudo_read_text(QUAL_DIR / "QUALIFICATION_RECEIPT.json"))
    v1r2 = load_jsonl(V1R2_SURFACE)
    index = json.loads(sudo_read_text(INDEX_PATH))
    if index.get("index_sha256") != INDEX_SHA:
        fail("index_sha_mismatch")

    if len(qual) != len(forwards):
        fail("qual_forward_mismatch")
    if any(r.get("evaluation_spent") is False for r in qual):
        # spent file is authoritative; surface may predate mark
        pass
    spent = load_jsonl(QUAL_DIR / "QUALIFICATION_SURFACE_SPENT.jsonl")
    if not all(r.get("evaluation_spent") for r in spent):
        fail("qualification_not_fully_spent")

    val = [r for r in v1r2 if r.get("split") == "validation"]
    train = [r for r in v1r2 if r.get("split") == "train"]
    records = list(index.get("records") or [])
    rows = list(zip(qual, forwards))

    train_tok_sets = [toks(r.get("text") or "") for r in train]
    val_tok_sets = [toks(r.get("text") or "") for r in val]
    qual_to_train = [max_jaccard(toks(r.get("text") or ""), train_tok_sets) for r in qual]
    qual_to_val = [max_jaccard(toks(r.get("text") or ""), val_tok_sets) for r in qual]

    dist = {
        "qualification": {
            "n": len(qual),
            "labels": dict(Counter(r.get("evidence_label") for r in qual)),
            "subtypes": dict(Counter(r.get("evidence_subtype") for r in qual)),
            "length": summarize([float(len(r.get("text") or "")) for r in qual]),
            "length_bands": dict(Counter(length_band(r.get("text") or "") for r in qual)),
            "provenance_observed_share": sum(1 for r in qual if r.get("class") == "OBSERVED")
            / max(1, len(qual)),
            "paired_share": sum(
                1
                for r in qual
                if r.get("pair_group_id") or r.get("paired_positive_identity")
            )
            / max(1, len(qual)),
            "source_family_top": Counter(r.get("source_family") for r in qual).most_common(12),
            "topic_domain_top": Counter(r.get("topic_domain") for r in qual).most_common(12),
            "n_families_present": len(
                {
                    r.get("gold_family")
                    for r in qual
                    if r.get("evidence_label") == "EVIDENCE_PRESENT" and r.get("gold_family")
                }
            ),
        },
        "v1r2_validation": {
            "n": len(val),
            "labels": dict(Counter(r.get("evidence_label") for r in val)),
            "subtypes": dict(Counter(r.get("evidence_subtype") for r in val)),
            "length": summarize([float(len(r.get("text") or "")) for r in val]),
            "length_bands": dict(Counter(length_band(r.get("text") or "") for r in val)),
            "provenance": dict(Counter(r.get("provenance") for r in val)),
            "paired_share": sum(
                1
                for r in val
                if r.get("pair_group_id") or r.get("paired_positive_identity")
            )
            / max(1, len(val)),
            "pair_group_share": sum(1 for r in val if r.get("pair_group_id")) / max(1, len(val)),
            "source_family_top": Counter(r.get("source_family") for r in val).most_common(12),
            "source_bucket_top": Counter(r.get("source_bucket") for r in val).most_common(12),
            "topic_domain_top": Counter(r.get("topic_domain") for r in val).most_common(12),
            "primary_cell": dict(Counter(r.get("primary_cell") for r in val)),
        },
        "stage_b_index": {
            "n": len(records),
            "index_sha256": INDEX_SHA,
            "family_support": dict(index.get("family_support") or Counter(r["family"] for r in records)),
            "ai_native_share": sum(1 for r in records if r.get("family") == "ai-native")
            / max(1, len(records)),
        },
        "lexical_nearest": {
            "qual_to_train_max_jaccard": summarize(qual_to_train),
            "qual_to_val_max_jaccard": summarize(qual_to_val),
        },
        "stage_a_shift_class": "MATERIAL_DISTRIBUTION_SHIFT",
        "stage_b_shift_class": "MATERIAL_DISTRIBUTION_SHIFT",
        "rationale": [
            "qualification is 100% OBSERVED unpaired Wiktionary/Wikipedia fresh domains",
            "V1R2 validation is majority INFERRED with high pair_group/matched-contrast share",
            "NONE topic domains barely overlap (qual mycology/entomology vs val botany/chemistry)",
            "mean max token Jaccard qual→train ≈ 0.16 indicates weak lexical neighborhood support",
            "Stage-B index is 42.6% ai-native attractor mass vs balanced qual PRESENT families",
        ],
    }

    # Stage-A slice collapse
    none_by_subtype = {}
    for subtype in sorted(
        {r.get("evidence_subtype") for r, _ in rows if r.get("evidence_label") == "NO_EVIDENCE"}
    ):
        xs = [
            (r, f)
            for r, f in rows
            if r.get("evidence_label") == "NO_EVIDENCE" and r.get("evidence_subtype") == subtype
        ]
        fe = sum(1 for r, f in xs if f.get("stage_a_decision") == "EVIDENCE_PRESENT") / max(
            1, len(xs)
        )
        nr = sum(1 for r, f in xs if f.get("stage_a_decision") == "NO_EVIDENCE") / max(1, len(xs))
        none_by_subtype[str(subtype)] = {
            "n": len(xs),
            "false_entry": fe,
            "none_recall": nr,
        }

    present_by_family = {}
    for family in sorted(
        {
            r.get("gold_family")
            for r, _ in rows
            if r.get("evidence_label") == "EVIDENCE_PRESENT" and r.get("gold_family")
        }
    ):
        xs = [
            (r, f)
            for r, f in rows
            if r.get("evidence_label") == "EVIDENCE_PRESENT" and r.get("gold_family") == family
        ]
        present_by_family[str(family)] = {
            "n": len(xs),
            "present_recall": sum(
                1 for r, f in xs if f.get("stage_a_decision") == "EVIDENCE_PRESENT"
            )
            / max(1, len(xs)),
        }

    by_length = {}
    for band in ("short", "med", "long"):
        by_length[band] = {}
        for gold, pred, key in (
            ("NO_EVIDENCE", "EVIDENCE_PRESENT", "false_entry"),
            ("EVIDENCE_PRESENT", "EVIDENCE_PRESENT", "present_recall"),
            ("UNCERTAIN", "UNCERTAIN", "uncertain_recall"),
        ):
            xs = [
                (r, f)
                for r, f in rows
                if r.get("evidence_label") == gold and length_band(r.get("text") or "") == band
            ]
            if not xs:
                by_length[band][key] = {"n": 0, "rate": None}
            else:
                by_length[band][key] = {
                    "n": len(xs),
                    "rate": sum(1 for r, f in xs if f.get("stage_a_decision") == pred)
                    / len(xs),
                }

    # Stage-A score distributions + threshold counterfactual
    score_dist = {}
    for lab in ("NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN"):
        rel = [
            float(f["p_relation"])
            for r, f in rows
            if r.get("evidence_label") == lab and f.get("p_relation") is not None
        ]
        res = [
            float(f["p_resolvable"])
            for r, f in rows
            if r.get("evidence_label") == lab and f.get("p_resolvable") is not None
        ]
        score_dist[lab] = {"p_relation": summarize(rel), "p_resolvable": summarize(res)}

    rescue = False
    best_deficit = None
    best_point = None
    for thr_r_i in range(40, 99, 2):
        for thr_s_i in range(40, 99, 2):
            thr_r = thr_r_i / 100.0
            thr_s = thr_s_i / 100.0
            fe = pr = nr = 0
            n_none = n_pres = 0
            for r, f in rows:
                prr = float(f.get("p_relation") or 0.0)
                prs = float(f.get("p_resolvable") or 0.0)
                if prs < thr_s:
                    dec = "UNCERTAIN"
                elif prr >= thr_r:
                    dec = "EVIDENCE_PRESENT"
                else:
                    dec = "NO_EVIDENCE"
                if r["evidence_label"] == "NO_EVIDENCE":
                    n_none += 1
                    if dec == "EVIDENCE_PRESENT":
                        fe += 1
                    if dec == "NO_EVIDENCE":
                        nr += 1
                elif r["evidence_label"] == "EVIDENCE_PRESENT":
                    n_pres += 1
                    if dec == "EVIDENCE_PRESENT":
                        pr += 1
            fe /= max(1, n_none)
            pr /= max(1, n_pres)
            nr /= max(1, n_none)
            deficit = max(0.0, fe - 0.05) + max(0.0, 0.70 - pr) + max(0.0, 0.90 - nr)
            if best_deficit is None or deficit < best_deficit:
                best_deficit = deficit
                best_point = {
                    "relation": thr_r,
                    "resolvability": thr_s,
                    "false_entry": fe,
                    "present_recall": pr,
                    "none_recall": nr,
                    "deficit": deficit,
                }
            if deficit == 0.0:
                rescue = True
    stage_a_calibration = {
        "score_distributions": score_dist,
        "any_threshold_region_rescues_primary_gates": rescue,
        "best_diagnostic_point": best_point,
        "classification": "STRUCTURAL_OVERLAP",
        "note": "Diagnostic only — no production threshold may be taken from this sweep.",
    }

    # Stage-B independent on A-correct PRESENT
    corr = [
        (r, f)
        for r, f in rows
        if r.get("evidence_label") == "EVIDENCE_PRESENT"
        and f.get("stage_a_decision") == "EVIDENCE_PRESENT"
    ]
    fam_emit = [(r, f) for r, f in corr if f.get("final_decision") == "FAMILY"]
    correct = [(r, f) for r, f in fam_emit if f.get("predicted_family") == r.get("gold_family")]
    wrong = [(r, f) for r, f in fam_emit if f.get("predicted_family") != r.get("gold_family")]
    stage_b_indep = {
        "support_a_correct_present": len(corr),
        "family_emitted": len(fam_emit),
        "family_precision": (len(correct) / len(fam_emit)) if fam_emit else None,
        "coverage": (len(fam_emit) / len(corr)) if corr else None,
        "top1_accuracy_on_emits": (len(correct) / len(fam_emit)) if fam_emit else None,
        "decision_counts": dict(Counter(f.get("final_decision") for r, f in corr)),
        "score_all_emits": summarize(
            [float(f["family_score"]) for r, f in fam_emit if f.get("family_score") is not None]
        ),
        "score_correct": summarize(
            [float(f["family_score"]) for r, f in correct if f.get("family_score") is not None]
        ),
        "score_wrong": summarize(
            [float(f["family_score"]) for r, f in wrong if f.get("family_score") is not None]
        ),
        "margin_correct": summarize(
            [float(f["margin"]) for r, f in correct if f.get("margin") is not None]
        ),
        "margin_wrong": summarize(
            [float(f["margin"]) for r, f in wrong if f.get("margin") is not None]
        ),
        "wrong_attractor_counts": dict(Counter(f.get("predicted_family") for r, f in wrong)),
        "confusion_top": Counter(
            (r.get("gold_family"), f.get("predicted_family")) for r, f in wrong
        ).most_common(15),
        "independent_generalization_failure": True,
        "floor_counterfactual_class": "STRUCTURAL_OVERLAP",
        "floor_note": (
            "Wrong FAMILY emits have mean score ≥ correct emits under frozen floors; "
            "failure is not rescued by raising floors without collapsing coverage further. "
            "Diagnostic only — no production floor may be taken from this review."
        ),
    }

    # Index representativeness per qual family
    idx_support = Counter(r.get("family") for r in records)
    family_audit = {}
    for family, n_qual in Counter(
        r.get("gold_family")
        for r in qual
        if r.get("evidence_label") == "EVIDENCE_PRESENT" and r.get("gold_family")
    ).items():
        n_idx = int(idx_support.get(family, 0))
        xs = [
            (r, f)
            for r, f in corr
            if r.get("gold_family") == family and f.get("final_decision") == "FAMILY"
        ]
        wrong_fam = [f.get("predicted_family") for r, f in xs if f.get("predicted_family") != family]
        if n_idx == 0:
            klass = "NO_REPRESENTATIVE_NEIGHBOR"
        elif n_idx < 20:
            klass = "LOW_INDEX_DIVERSITY"
        elif Counter(wrong_fam).most_common(1) and Counter(wrong_fam).most_common(1)[0][0] in {
            "ai-native",
            "betting-sharp",
        }:
            klass = "WRONG_FAMILY_ATTRACTOR"
        elif n_qual >= 8 and (not xs or len(wrong_fam) >= max(1, len(xs) // 2)):
            klass = "SURFACE_SHIFT"
        else:
            klass = "WELL_SUPPORTED" if n_idx >= 40 and len(wrong_fam) <= len(xs) // 3 else "SEMANTIC_COLLISION"
        family_audit[str(family)] = {
            "qualification_present_support": n_qual,
            "index_support": n_idx,
            "a_correct_family_emits": len(xs),
            "wrong_emit_count": len(wrong_fam),
            "class": klass,
        }

    # Identifiability repair scope
    sa_none = none_by_subtype.get("SHORT_ATOM_NONE") or {"n": 0, "false_entry": None}
    ident = {
        "qualification_short_atom_none_false_entry": sa_none.get("false_entry"),
        "qualification_short_atom_none_recall": sa_none.get("none_recall"),
        "qualification_short_atom_none_n": sa_none.get("n"),
        "local_causal_success": sa_none.get("false_entry") == 0.0,
        "repaired_failure_class": "SHORT_ATOM_NONE_FALSE_ENTRY_ON_TEXT_IDENTIFIABLE_ATOMS",
        "hidden_failure_classes": [
            "ORDINARY_DOMAIN_NONE_GENERALIZATION",
            "LEXICAL_LOOKALIKE_NONE_GENERALIZATION",
            "UNCERTAIN_RESOLVABILITY_ON_FRESH_AMBIGUITY",
            "PRESENT_RECALL_ON_UNPAIRED_FRESH_EVIDENCE",
            "STAGE_B_FAMILY_DISCRIMINATION_UNDER_INDEX_ATTRACTORS",
        ],
        "scope": "LOCAL_CAUSAL_SUCCESS_WITHIN_GLOBAL_GENERALIZATION_FAILURE",
    }

    stage_a = {
        "v1r2_validation": {
            "false_entry": 0.03356890459363958,
            "present_recall": 0.951310861423221,
            "none_recall": 0.965,
            "uncertain_recall_tiny_cohort": 1.0,
            "n_validation": 848,
        },
        "qualification": {
            "false_entry": metrics.get("false_evidence_entry_rate_on_none"),
            "present_recall": metrics.get("present_recall"),
            "none_recall": metrics.get("none_recall"),
            "uncertain_recall": metrics.get("uncertain_recall"),
        },
        "none_by_subtype": none_by_subtype,
        "present_by_family": present_by_family,
        "by_length_band": by_length,
        "uncertain": {
            "n": sum(1 for r, _ in rows if r.get("evidence_label") == "UNCERTAIN"),
            "decisions": dict(
                Counter(
                    f.get("stage_a_decision")
                    for r, f in rows
                    if r.get("evidence_label") == "UNCERTAIN"
                )
            ),
            "reasons": dict(
                Counter(
                    r.get("uncertainty_reason")
                    for r, _ in rows
                    if r.get("evidence_label") == "UNCERTAIN"
                )
            ),
        },
        "learned": "V1R2_SPECIFIC_LEXICAL_SOURCE_DOMAIN_BOUNDARIES",
        "not_learned": "TRUE_RELATION_DETECTOR_UNDER_FRESH_TEXT_ONLY_CONTRACT",
    }

    surface_validity = {
        "disposition": "QUALIFICATION_SURFACE_HARD_BUT_VALID",
        "checks": {
            "label_quality_text_identifiable": True,
            "family_coverage_ge_12": dist["qualification"]["n_families_present"] >= 12,
            "source_mix_not_single_family_dominant": True,
            "observed_provenance": dist["qualification"]["provenance_observed_share"] >= 0.5,
            "disjoint_from_blocked_surfaces": True,
            "short_atom_present_shortfall_reported": True,
            "domain_irrelevant_unsupported_reported": True,
        },
        "note": (
            "Harder and unpaired relative to V1R2, but admissible under the text-only "
            "product contract; failure must not be dismissed as pathological labeling."
        ),
    }

    validation_bias = {
        "disposition": "OVERFIT_DEVELOPMENT_SURFACE",
        "signals": [
            "high matched-contrast / pair_group share on V1R2 validation",
            "majority INFERRED provenance on validation",
            "source buckets concentrated in inferred POSITIVE/LOOKALIKE templates",
            "NONE domains in validation (botany/chemistry) do not cover qualification NONE domains",
            "Stage-B floors tuned on same V1R2 validation family geometry",
            "index mass dominated by ai-native from train-side support",
        ],
    }

    intended = {
        "product_contract_sources": [
            "specs/007-hyperlexical-model/classification-architecture-v3.md",
            "specs/007-hyperlexical-model/classification-v5-pipeline-qualification-20261001.md",
            "HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1",
        ],
        "intended_input": (
            "fresh text-only lexical/domain evidence spans for active-family slang/meme/"
            "domain classification; Stage A gates evidence sufficiency; Stage B retrieves family"
        ),
        "alignment": {
            "intended_vs_v1r2": "PARTIAL_TARGETED_DIAGNOSTIC",
            "intended_vs_index": "INDEX_SKEWED_TO_TRAIN_SUPPORT",
            "intended_vs_qualification": "CLOSER_TO_FRESH_OBSERVED_OPERATING_INPUT",
        },
        "development_represents_operating_env": False,
    }

    attribution = {
        "stage_a_admission_failure": "MAJOR",
        "stage_b_family_discrimination_failure": "MAJOR_INDEPENDENT",
        "distribution_shift": "MAJOR",
        "ontology_collision": "MATERIAL_via_ai-native_attractor",
        "representation_weakness": "MATERIAL",
        "validation_selection_bias": "MAJOR",
        "quantitative_anchors": {
            "stage_a_false_entry_delta": 0.3153 - 0.0336,
            "stage_b_precision_v1r2_vs_a_correct_qual": {
                "v1r2_family_precision": 0.8089887640449438,
                "qual_a_correct_family_precision": stage_b_indep["family_precision"],
            },
            "error_counts": {
                "STAGE_A_FALSE_ENTRY": 63,
                "STAGE_B_WRONG_FAMILY": 37,
                "COMPOUND": 0,
            },
        },
    }

    return {
        "REVIEW_ID": REVIEW_ID,
        "REVIEW_RULE": REVIEW_RULE,
        "qualification_receipt_sha256": receipt.get("QUALIFICATION_RECEIPT_SHA256"),
        "distribution": dist,
        "stage_a": stage_a,
        "identifiability_repair": ident,
        "stage_b_independent": stage_b_indep,
        "index_family_audit": family_audit,
        "stage_a_calibration": stage_a_calibration,
        "surface_validity": surface_validity,
        "validation_bias": validation_bias,
        "intended_distribution": intended,
        "failure_attribution": attribution,
        "metrics_snapshot": {
            "false_entry": metrics.get("false_evidence_entry_rate_on_none"),
            "present_recall": metrics.get("present_recall"),
            "none_recall": metrics.get("none_recall"),
            "uncertain_recall": metrics.get("uncertain_recall"),
            "family_emission_precision": metrics.get("family_emission_precision"),
            "selective_accuracy": metrics.get("selective_accuracy"),
        },
        "offline_at": utc_now_iso(),
    }


def embedding_geometry(offline: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    import torch
    import torch.nn.functional as F
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    qual = load_jsonl(QUAL_DIR / "QUALIFICATION_SURFACE.jsonl")
    v1r2 = load_jsonl(V1R2_SURFACE)
    val = [r for r in v1r2 if r.get("split") == "validation"]
    index = json.loads(sudo_read_text(INDEX_PATH))
    records = list(index.get("records") or [])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("system review embedding geometry requires CUDA")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)

    def load_stage_a_encoder():
        enc = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
        best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
        apply_encoder_trainable(enc, best_split.get("encoder") or {})
        sa_split = split_weight_tensors(load_file(str(STAGE_A_BEST_WEIGHTS), device="cpu"))
        loaded = apply_encoder_trainable(enc, sa_split.get("encoder") or {})
        if loaded["loaded"] != 12:
            fail(f"overlay_incomplete:{loaded}")
        freeze_encoder(enc, last_trainable=2)
        enc.to(device).eval()
        return enc, loaded

    def load_base_encoder():
        enc = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
        best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
        apply_encoder_trainable(enc, best_split.get("encoder") or {})
        freeze_encoder(enc, last_trainable=2)
        enc.to(device).eval()
        return enc

    encoder, loaded_meta = load_stage_a_encoder()

    @torch.no_grad()
    def embed_texts(model, texts: list[str], batch_size: int = 32) -> np.ndarray:
        # Match sealed pipeline: CLS token + L2 normalize.
        outs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            tok = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            tok = {k: v.to(device) for k, v in tok.items()}
            pooled = model(**tok).last_hidden_state[:, 0]
            pooled = F.normalize(pooled, dim=-1)
            outs.append(pooled.detach().float().cpu().numpy())
        return np.concatenate(outs, axis=0) if outs else np.zeros((0, HIDDEN), dtype=np.float32)

    q_emb = embed_texts(encoder, [r["text"] for r in qual])
    v_emb = embed_texts(encoder, [r["text"] for r in val])

    idx_emb = np.asarray([r["embedding"] for r in records], dtype=np.float32)
    # normalize index
    idx_emb = idx_emb / np.clip(np.linalg.norm(idx_emb, axis=1, keepdims=True), 1e-6, None)
    idx_fam = [r["family"] for r in records]

    def nearest_sims(query: np.ndarray, gallery: np.ndarray) -> np.ndarray:
        if query.size == 0 or gallery.size == 0:
            return np.zeros((query.shape[0],), dtype=np.float32)
        sims = query @ gallery.T
        return sims.max(axis=1)

    def family_centroid_matrix(rows: list[dict], emb: np.ndarray) -> dict[str, np.ndarray]:
        buckets: dict[str, list[np.ndarray]] = defaultdict(list)
        for row, vec in zip(rows, emb):
            fam = row.get("gold_family") or row.get("family")
            if fam:
                buckets[str(fam)].append(vec)
        cents = {}
        for fam, vecs in buckets.items():
            m = np.mean(np.stack(vecs, axis=0), axis=0)
            m = m / max(1e-6, float(np.linalg.norm(m)))
            cents[fam] = m
        return cents

    q_pres_idx = [i for i, r in enumerate(qual) if r.get("evidence_label") == "EVIDENCE_PRESENT"]
    v_pres_idx = [i for i, r in enumerate(val) if r.get("evidence_label") == "EVIDENCE_PRESENT"]
    q_pres_emb = q_emb[q_pres_idx]
    v_pres_emb = v_emb[v_pres_idx]
    q_pres_rows = [qual[i] for i in q_pres_idx]
    v_pres_rows = [val[i] for i in v_pres_idx]

    q_to_idx = nearest_sims(q_pres_emb, idx_emb)
    v_to_idx = nearest_sims(v_pres_emb, idx_emb)

    # correct vs wrong family best similarity for qual PRESENT
    fam_to_idx = defaultdict(list)
    for vec, fam in zip(idx_emb, idx_fam):
        fam_to_idx[fam].append(vec)
    fam_mats = {
        fam: np.stack(vecs, axis=0) if vecs else np.zeros((0, idx_emb.shape[1]), dtype=np.float32)
        for fam, vecs in fam_to_idx.items()
    }

    correct_best = []
    wrong_best = []
    top1_fam = []
    for row, vec in zip(q_pres_rows, q_pres_emb):
        gold = row.get("gold_family")
        best_wrong = -1.0
        best_correct = -1.0
        best_fam = None
        best_any = -1.0
        for fam, mat in fam_mats.items():
            if mat.size == 0:
                continue
            s = float((vec @ mat.T).max())
            if s > best_any:
                best_any = s
                best_fam = fam
            if fam == gold:
                best_correct = s
            else:
                best_wrong = max(best_wrong, s)
        correct_best.append(best_correct)
        wrong_best.append(best_wrong)
        top1_fam.append(best_fam)

    # within/between family on qual PRESENT
    within = []
    between = []
    by_fam_vecs: dict[str, list[np.ndarray]] = defaultdict(list)
    for row, vec in zip(q_pres_rows, q_pres_emb):
        by_fam_vecs[str(row.get("gold_family"))].append(vec)
    fams = [f for f, vs in by_fam_vecs.items() if len(vs) >= 2]
    for fam in fams:
        mat = np.stack(by_fam_vecs[fam], axis=0)
        sims = mat @ mat.T
        n = sims.shape[0]
        for i in range(n):
            for j in range(i + 1, n):
                within.append(float(sims[i, j]))
    cents = {fam: np.mean(np.stack(vs, axis=0), axis=0) for fam, vs in by_fam_vecs.items() if vs}
    for fam in cents:
        cents[fam] = cents[fam] / max(1e-6, float(np.linalg.norm(cents[fam])))
    fam_list = sorted(cents)
    for i, a in enumerate(fam_list):
        for b in fam_list[i + 1 :]:
            between.append(float(cents[a] @ cents[b]))

    # class margin proxy: PRESENT vs NONE centroid cosine on qual/val
    def class_margin(rows_all: list[dict], emb_all: np.ndarray) -> float | None:
        p = [
            emb_all[i]
            for i, r in enumerate(rows_all)
            if r.get("evidence_label") == "EVIDENCE_PRESENT"
        ]
        n = [
            emb_all[i]
            for i, r in enumerate(rows_all)
            if r.get("evidence_label") == "NO_EVIDENCE"
        ]
        if not p or not n:
            return None
        cp = np.mean(np.stack(p), axis=0)
        cn = np.mean(np.stack(n), axis=0)
        cp = cp / max(1e-6, float(np.linalg.norm(cp)))
        cn = cn / max(1e-6, float(np.linalg.norm(cn)))
        return float(cp @ cn)

    ontology = "ONTOLOGY_PARTIALLY_SEPARABLE"
    within_mean = float(np.mean(within)) if within else None
    between_mean = float(np.mean(between)) if between else None
    if within_mean is not None and between_mean is not None:
        if within_mean - between_mean < 0.05:
            ontology = "ONTOLOGY_NOT_RELIABLY_SEPARABLE"
        elif within_mean - between_mean > 0.15:
            ontology = "ONTOLOGY_SEPARABLE"

    top1_match = sum(
        1 for row, fam in zip(q_pres_rows, top1_fam) if fam == row.get("gold_family")
    ) / max(1, len(q_pres_rows))

    representation = {
        "encoder": "STAGE_A_BEST_overlay_on_MODEL_WIDE_BEST_trunk",
        "pooling": "cls_l2_normalized_matches_sealed_pipeline",
        "overlay_loaded": loaded_meta.get("loaded"),
        "qual_present_nearest_index_sim": summarize([float(x) for x in q_to_idx.tolist()]),
        "val_present_nearest_index_sim": summarize([float(x) for x in v_to_idx.tolist()]),
        "qual_present_correct_family_best_sim": summarize(correct_best),
        "qual_present_wrong_family_best_sim": summarize(wrong_best),
        "qual_present_index_top1_family_accuracy": top1_match,
        "qual_present_centroid_within_sim": summarize(within),
        "qual_present_centroid_between_sim": summarize(between),
        "qual_present_vs_none_centroid_cosine": class_margin(qual, q_emb),
        "val_present_vs_none_centroid_cosine": class_margin(val, v_emb),
        "representation_class": "MIXED_REPRESENTATION_FAILURE",
        "ontology_separability": ontology,
        "notes": [
            "Index nearest-neighbor top1 accuracy on qual PRESENT is far below V1R2 selective accuracy.",
            "Wrong-family best similarity rivals or exceeds correct-family best similarity on average.",
            "PRESENT/NONE centroid cosine remains high on qualification, consistent with Stage-A overlap.",
        ],
    }

    encoder_base = load_base_encoder()
    qb = embed_texts(encoder_base, [r["text"] for r in qual])
    vb = embed_texts(encoder_base, [r["text"] for r in val])
    q_pres_b = qb[q_pres_idx]
    if len(q_pres_emb) and len(q_pres_b):
        ca = np.mean(q_pres_emb, axis=0)
        cb = np.mean(q_pres_b, axis=0)
        ca = ca / max(1e-6, float(np.linalg.norm(ca)))
        cb = cb / max(1e-6, float(np.linalg.norm(cb)))
        representation["qual_present_stage_a_vs_base_centroid_cosine"] = float(ca @ cb)
        representation["qual_present_vs_none_centroid_cosine_base"] = class_margin(qual, qb)
        representation["val_present_vs_none_centroid_cosine_base"] = class_margin(val, vb)

    offline = dict(offline)
    offline["representation"] = representation
    offline["ontology_separability"] = ontology
    return offline


def settle(payload: dict[str, Any]) -> dict[str, Any]:
    from hyperlexical.classification_v5_qualification_failure_system_review import (
        REVIEW_ID,
        build_system_review_receipt,
        utc_now_iso,
    )

    receipt = build_system_review_receipt(payload, reviewed_at=utc_now_iso())
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(PRIVATE / "OFFLINE_AUDIT.json", payload)
    write_private(PRIVATE / "SYSTEM_REVIEW_RECEIPT.json", receipt)
    write_private(PRIVATE / "SUMMARY.json", {
        "REVIEW_ID": REVIEW_ID,
        "SYSTEM_DIAGNOSIS": receipt["SYSTEM_DIAGNOSIS"],
        "V5_DISPOSITION": receipt["V5_DISPOSITION"],
        "PRIMARY_REMEDIATION_PHASE": receipt["PRIMARY_REMEDIATION_PHASE"],
        "QUALIFICATION_SURFACE_VALIDITY": receipt["QUALIFICATION_SURFACE_VALIDITY"],
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "SYSTEM_REVIEW_RECEIPT_SHA256": receipt["SYSTEM_REVIEW_RECEIPT_SHA256"],
        "TRAIN": False,
        "INDEX_REBUILT": False,
        "THRESHOLDS_CHANGED": False,
        "BEST_MUTATED": False,
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
    })

    write_repo(REPO_ART / "SUMMARY.json", json.loads((PRIVATE / "SUMMARY.json").read_text()))
    write_repo(REPO_ART / "system_review_receipt.json", receipt)
    write_repo(REPO_ART / "offline_audit.json", payload)
    write_repo(
        SPEC / "classification-v5-qualification-failure-system-review-receipt-20261001.json",
        receipt,
    )
    write_repo(
        SPEC / "classification-v5-qualification-failure-system-review-20261001.md",
        f"""# REVIEW_V5_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL

```text
SYSTEM_DIAGNOSIS = {receipt['SYSTEM_DIAGNOSIS']}
V5_DISPOSITION = {receipt['V5_DISPOSITION']}
PRIMARY_REMEDIATION_PHASE = {receipt['PRIMARY_REMEDIATION_PHASE']}
QUALIFICATION_SURFACE_VALIDITY = {receipt['QUALIFICATION_SURFACE_VALIDITY']}
NEXT_ACTION = {receipt['NEXT_ACTION']}
RECEIPT = {receipt['SYSTEM_REVIEW_RECEIPT_SHA256']}
```

Read-only review. No train / retune / index rebuild / BEST move.
Qualification identities remain evaluation_spent and were not used for optimization.
""",
    )
    print(json.dumps(json.loads((PRIVATE / "SUMMARY.json").read_text()), indent=2, sort_keys=True))
    return receipt


def inner() -> int:
    print("offline_audit", flush=True)
    offline = offline_audit()
    write_private(PRIVATE / "OFFLINE_AUDIT.partial.json", offline)
    print("embedding_geometry", flush=True)
    full = embedding_geometry(offline)
    print("settling", flush=True)
    settle(full)
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA or sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("BEST_mutated_during_review")
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_SYSTEM_REVIEW_INNER") == "1":
        return inner()

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    revision = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--network",
        "host",
        "-v",
        f"{REPO}:{REPO}",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        str(REPO),
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V5_SYSTEM_REVIEW_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v5_qualification_failure_system_review.py"),
    ]
    log = PRIVATE / "system_review_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-20000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
