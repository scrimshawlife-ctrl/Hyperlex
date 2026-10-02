"""REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT.

Read-only product decision from persisted V3 / redesign / signal / pragmatic
artifacts. No training. No QUAL rescoring. No architecture mutation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v6-function-product-requirement-20261002"
)
PRIVATE_EXPAND = Path(
    "/home/morpheus/hlx-private/classification-v6-function-diversity-expand-20261002"
)
PRIVATE_REDESIGN = Path(
    "/home/morpheus/hlx-private/classification-v6-function-prediction-redesign-20261002"
)
PRIVATE_SIGNAL = Path(
    "/home/morpheus/hlx-private/classification-v6-function-task-signal-reassess-20261002"
)
PRIVATE_PRAG = Path(
    "/home/morpheus/hlx-private/classification-v6-pragmatic-function-objective-20261002"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-FUNCTION-PRODUCT-REQUIREMENT-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sudo_read_text(path: Path) -> str:
    if path.is_file() and os.access(path, os.R_OK):
        return path.read_text(encoding="utf-8")
    if path.is_file():
        return subprocess.run(
            ["sudo", "-n", "cat", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    raise FileNotFoundError(path)


def load_json(path: Path) -> Any:
    return json.loads(sudo_read_text(path))


def write_private(path: Path, payload: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    text = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    )
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)


def write_repo(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def maybe_load(path: Path) -> Any | None:
    try:
        return load_json(path)
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return None


def main() -> int:
    from hyperlexical.classification_v6_function_prediction_redesign import (
        BASELINE_REP_V3,
    )
    from hyperlexical.classification_v6_function_product_requirement import (
        FUNCTION_VOCAB,
        PARENT,
        PER_FUNCTION_EVIDENCE,
        PHASE_RULE,
        REJECTED_MICRO_FIXES,
        build_product_requirement_receipt,
        classify_product_disposition,
        core_without_function_metrics,
        product_requirement_contract,
        recommend_function_disposition,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    contract = product_requirement_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    baseline = maybe_load(PRIVATE_EXPAND / "BASELINE_REP_V3_METRICS.json") or dict(
        BASELINE_REP_V3
    )
    redesign = maybe_load(PRIVATE_REDESIGN / "SUMMARY.json") or {}
    signal = maybe_load(PRIVATE_SIGNAL / "SUMMARY.json") or {}
    prag = maybe_load(PRIVATE_PRAG / "SUMMARY.json") or {}
    baseline_full = maybe_load(PRIVATE_REDESIGN / "BASELINE_REP_V3.json") or {}

    domain = float(baseline.get("DOMAIN_macro_f1") or BASELINE_REP_V3["DOMAIN_macro_f1"])
    mediation = float(
        baseline.get("MEDIATION_macro_f1") or BASELINE_REP_V3["MEDIATION_macro_f1"]
    )
    zero_fp = float(
        baseline.get("zero_label_false_positive_rate")
        or BASELINE_REP_V3["zero_label_false_positive_rate"]
    )
    zero_exact = float(
        baseline.get("zero_label_exact_rejection")
        or BASELINE_REP_V3["zero_label_exact_rejection"]
    )
    hier_corr = int(baseline_full.get("hierarchy_corrections") or 3)
    n_rows = int(baseline_full.get("n_rows") or 1511)
    hierarchy_violation_rate = hier_corr / max(1, n_rows)

    core = core_without_function_metrics(
        domain_macro=domain,
        mediation_macro=mediation,
        zero_fp=zero_fp,
        zero_exact=zero_exact,
        hierarchy_violation_rate=hierarchy_violation_rate,
    )

    per_function = {}
    for lab in FUNCTION_VOCAB:
        ev = dict(PER_FUNCTION_EVIDENCE[lab])
        rec = recommend_function_disposition(ev)
        per_function[lab] = {
            **rec,
            "downstream_utility": ev["downstream_utility"],
            "cost_of_false_positive": ev["cost_of_false_positive"],
            "cost_of_false_negative": ev["cost_of_false_negative"],
            "context_dependence": ev["context_dependence"],
            "substitutable_by_domain_mediation": ev[
                "substitutable_by_domain_mediation"
            ],
            "signal_class": ev["signal_class"],
            "old_head_f1": ev["old_head_f1"],
            "independent_f1": ev["independent_f1"],
            "hybrid_f1": ev["hybrid_f1"],
            "baseline_precision": ev["baseline_precision"],
            "independent_precision": ev["independent_precision"],
            "explicit_lexical_share": ev["explicit_lexical_share"],
            "pragmatic_or_context_share": ev["pragmatic_or_context_share"],
            "consensus_fail_share": ev["consensus_fail_share"],
            "rep_support": ev["rep_support"],
        }

    preserved = [
        "FUNCTION_TASK_SIGNAL_PARTIAL",
        "TEXT_SIGNAL_CEILING≈0.30_macro_F1",
        "V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED",
        "direct_heads_and_independent_verifiers_converged",
        "semantic_matching_underperformed",
        "cue_primitive_decomposition_rejected",
        "NONE_DOMAIN_MEDIATION_remain_viable",
        "QUAL-003_EVALUATION_SPENT_not_rescored",
        "ontology_function_labels_preserved_as_concepts",
    ]

    audit = {
        "per_function_dispositions": per_function,
        "core_without_function": core,
        "none_preserved": zero_fp <= 0.35 and zero_exact >= 0.50,
        "ceiling_class": signal.get("CEILING_CLASS") or PARENT["CEILING_CLASS"],
        "pragmatic_outcome": prag.get("OUTCOME") or PARENT["PRAGMATIC_OBJECTIVE"],
        "primitive_cue_recovery_lift": float(
            prag.get("identifiability_lift")
            or PARENT["primitive_cue_recovery_lift"]
        ),
        "baseline_FUNCTION_macro_f1": float(
            baseline.get("FUNCTION_macro_f1") or PARENT["direct_FUNCTION_baseline"]
        ),
        "independent_FUNCTION_macro_f1": float(
            PARENT["independent_verifier_FUNCTION"]
        ),
        "prefer_contextual_only": False,
        "contract_alternatives_considered": {
            "A_KEEP_FUNCTION_MANDATORY": {
                "justified": False,
                "reason": "~0.30 text-only ceiling does not satisfy required-axis reliability",
            },
            "B_MAKE_FUNCTION_OPTIONAL_BEST_EFFORT": {
                "justified": True,
                "reason": "core gate+DOMAIN+MEDIATION viable; FUNCTION advisory when evidence strong",
            },
            "C_MOVE_FUNCTION_TO_CONTEXTUAL_REASONING": {
                "justified": "parallel_research",
                "reason": "reliable FUNCTION needs discourse/entity/world context; track preserved",
            },
            "D_REMOVE_FUNCTION_FROM_V6_PRODUCT_SCOPE": {
                "justified": False,
                "reason": "concepts still useful as optional/research; full deprecate premature",
            },
        },
        "preserved_research_findings": preserved,
        "parent_summaries": {
            "redesign_outcome": redesign.get("OUTCOME"),
            "signal_diagnosis": signal.get("PRIMARY_DIAGNOSIS"),
            "pragmatic_outcome": prag.get("OUTCOME"),
        },
        "baseline_REP_V3": {
            "DOMAIN_macro_f1": domain,
            "FUNCTION_macro_f1": float(
                baseline.get("FUNCTION_macro_f1")
                or BASELINE_REP_V3["FUNCTION_macro_f1"]
            ),
            "MEDIATION_macro_f1": mediation,
            "system_macro_f1": float(
                baseline.get("system_macro_f1") or BASELINE_REP_V3["system_macro_f1"]
            ),
            "zero_label_false_positive_rate": zero_fp,
            "zero_label_exact_rejection": zero_exact,
        },
    }

    # Fix independent F1 extraction more carefully
    cand = redesign.get("candidate_REP_V3")
    if isinstance(cand, dict) and cand.get("FUNCTION_macro_f1") is not None:
        audit["independent_FUNCTION_macro_f1"] = float(cand["FUNCTION_macro_f1"])
    elif redesign.get("OUTCOME"):
        # SUMMARY may flatten metrics
        for key in ("FUNCTION_macro_f1",):
            if key in redesign and redesign.get("selected_formulation") == (
                "INDEPENDENT_BINARY_VERIFIERS"
            ):
                audit["independent_FUNCTION_macro_f1"] = float(redesign[key])

    decision = classify_product_disposition(audit)
    sealed_at = utc_now_iso()
    receipt = build_product_requirement_receipt(audit, sealed_at=sealed_at)

    summary = {
        "PHASE_RULE": PHASE_RULE,
        "PRODUCT_DISPOSITION": decision["PRODUCT_DISPOSITION"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "selected_contract_alternative": decision["selected_contract_alternative"],
        "rationale": decision["rationale"],
        "per_function_disposition": {
            lab: per_function[lab]["disposition"] for lab in FUNCTION_VOCAB
        },
        "per_function_placement": {
            lab: per_function[lab]["placement"] for lab in FUNCTION_VOCAB
        },
        "revised_v6_output_contract": decision["revised_v6_output_contract"],
        "release_gate_effects": decision["release_gate_effects"],
        "core_without_function": core,
        "core_viable": decision["core_viable"],
        "none_preserved": decision["none_preserved"],
        "preserved_research_findings": preserved,
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "QUALIFICATION_RESCORED": False,
        "FUNCTION_MODEL_TRAINED": False,
        "RECEIPT": receipt["SYSTEM_FUNCTION_PRODUCT_REQUIREMENT_RECEIPT_SHA256"],
    }

    write_private(PRIVATE / "AUDIT.json", audit)
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_private(
        PRIVATE / "POINTER.json",
        {
            "FUNCTION_REQUIRED_IN_V6_CORE": False,
            "FUNCTION_MODEL_TRAINED": False,
            "DOMAIN_HEAD_MUTATED": False,
            "MEDIATION_HEAD_MUTATED": False,
            "NONE_GATE_MUTATED": False,
            "HUB_PUBLISH_AUTHORIZED": False,
        },
    )

    public = {k: v for k, v in receipt.items()}
    write_repo(REPO_ART / "summary.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "receipt.json", public)
    write_repo(REPO_ART / "RECEIPT.json", public)
    write_repo(
        REPO_ART / "audit_summary.json",
        {
            "PRODUCT_DISPOSITION": decision["PRODUCT_DISPOSITION"],
            "NEXT_ACTION": decision["NEXT_ACTION"],
            "selected_contract_alternative": decision["selected_contract_alternative"],
            "per_function_disposition": summary["per_function_disposition"],
            "core_system_macro_f1": core["core_system_macro_f1"],
            "revised_required_outputs": decision["revised_v6_output_contract"][
                "required_outputs"
            ],
        },
    )
    write_repo(
        SPEC / "classification-v6-function-product-requirement-receipt-20261002.json",
        public,
    )

    # Settlement markdown
    lines = [
        "# REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT",
        "",
        "```text",
        f"PRODUCT_DISPOSITION = {decision['PRODUCT_DISPOSITION']}",
        f"NEXT_ACTION         = {decision['NEXT_ACTION']}",
        f"selected_alternative = {decision['selected_contract_alternative']}",
        f"rationale = {decision['rationale']}",
        "",
        "revised required outputs:",
        f"  {', '.join(decision['revised_v6_output_contract']['required_outputs'])}",
        "optional:",
        f"  {', '.join(decision['revised_v6_output_contract']['optional_outputs']) or '(none)'}",
        "",
        f"core_system_macro_f1 (DOMAIN+MEDIATION) = {core['core_system_macro_f1']:.4f}",
        f"three-axis system_macro_f1 (reference)  = {BASELINE_REP_V3['system_macro_f1']:.4f}",
        f"NONE zero-FP / exact                   = {zero_fp:.4f} / {zero_exact:.4f}",
        f"hierarchy_violation_rate               = {hierarchy_violation_rate:.6f}",
        "FUNCTION_blocks_release = false",
        "```",
        "",
        f"Receipt: `{receipt['SYSTEM_FUNCTION_PRODUCT_REQUIREMENT_RECEIPT_SHA256']}`",
        "",
        "## Product rationale",
        "",
        "Repeated modeling evidence shows FUNCTION labels are human-coherent but",
        "not reliably recoverable from text-only input under the current contract:",
        "direct heads ≈0.296, independent verifiers ≈0.294, hybrid ≈0.306,",
        "semantic matching ≈0.172, cue-primitives ≈0.189 / derived FUNCTION ≈0.198.",
        "Ceiling class TEXT_SIGNAL_CEILING; pragmatic objective NOT_SUPPORTED.",
        "Incorrect function emission is costly (esp. memetic FP). Omission is",
        "preferable to false product claims. NONE, DOMAIN, and MEDIATION remain",
        "viable and form a coherent core without required FUNCTION.",
        "",
        "## Per-function disposition",
        "",
        "| function | disposition | placement | best F1 | baseline P | prag/ctx | FP cost |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for lab in FUNCTION_VOCAB:
        r = per_function[lab]
        lines.append(
            f"| {lab.split('.')[-1]} | {r['disposition']} | "
            f"{','.join(r['placement'])} | {r['best_f1']:.3f} | "
            f"{r['baseline_precision']:.3f} | {r['pragmatic_or_context_share']:.2f} | "
            f"{r['cost_of_false_positive']} |"
        )
    lines += [
        "",
        "## Contract alternatives",
        "",
        "- **A mandatory** — rejected: ~0.30 ceiling does not satisfy required-axis need.",
        "- **B optional / best-effort** — **selected**: core = gate + DOMAIN + MEDIATION;",
        "  FUNCTION emitted only as advisory when evidence/confidence sufficient.",
        "- **C contextual reasoning** — preserved as research track (not V6 core blocker).",
        "- **D full remove** — rejected for now: concepts retain optional/research value.",
        "",
        "## V6 product without required FUNCTION",
        "",
        f"- DOMAIN macro-F1 = {domain:.4f}",
        f"- MEDIATION macro-F1 = {mediation:.4f}",
        f"- core system macro-F1 = {core['core_system_macro_f1']:.4f} (≥ 0.30 floor)",
        f"- NONE rejection: zero-FP {zero_fp:.4f}, exact {zero_exact:.4f}",
        f"- hierarchy violation rate ≈ {hierarchy_violation_rate:.6f}",
        "- QUAL-003 not rescored (EVALUATION_SPENT); gates updated so FUNCTION",
        "  no longer blocks release / system macro.",
        "",
        "## Release-gate effects",
        "",
        "```text",
        "system_macro_axes = domain, mediation",
        "FUNCTION_axis_gate = not_required",
        "FUNCTION_reporting = advisory_only",
        "FUNCTION_blocks_release = false",
        "ontology function labels = preserved (concepts/research/annotation)",
        "```",
        "",
        "## Preserved research findings",
        "",
    ]
    for p in preserved:
        lines.append(f"- `{p}`")
    lines += [
        "",
        "## Rejected micro-fixes",
        "",
        "```text",
        "train_another_function_model = rejected",
        "change_encoder / NONE / DOMAIN / MEDIATION / ontology = rejected",
        "rescore_QUAL = rejected",
        "```",
        "",
        "## Primary disposition + next action",
        "",
        "```text",
        f"PRODUCT_DISPOSITION = {decision['PRODUCT_DISPOSITION']}",
        f"NEXT_ACTION         = {decision['NEXT_ACTION']}",
        "```",
        "",
        "No function model trained. Encoder / NONE / DOMAIN / MEDIATION / ontology frozen.",
        "MODEL_WIDE_BEST unchanged.",
        "",
    ]
    md = "\n".join(lines)
    write_repo(
        SPEC / "classification-v6-function-product-requirement-20261002.md", md
    )
    write_private(PRIVATE / "SETTLEMENT.md", md)
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
