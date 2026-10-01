"""COMPLETE_V6_HUMAN_ONTOLOGY_SETTLEMENT — Spark/operator runner.

Dual independent text-only annotation of the 120-row sample.
No train / encoder choice / QUAL inspection. Geometry not authoritative.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v6-human-ontology-settlement-20261001"
)
FOUNDATION = Path(
    "/home/morpheus/hlx-private/classification-v6-data-foundation-20261001"
)
ONTO_PRIV = Path(
    "/home/morpheus/hlx-private/classification-v6-ontology-revision-20261001"
)
REPO_ART = (
    REPO / "artifacts" / "experiments" / "HLX-CLASSIFICATION-V6-HUMAN-ONTOLOGY-SETTLEMENT-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sudo_read_text(path: Path) -> str:
    if os.access(path, os.R_OK):
        return path.read_text(encoding="utf-8")
    return subprocess.run(
        ["sudo", "-n", "cat", str(path)], check=True, capture_output=True, text=True
    ).stdout


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


def code_revision() -> str:
    env = os.environ.get("HLX_V5_STAGE_A_CODE_REVISION")
    if env:
        return env
    return subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def load_sample() -> list[dict]:
    path = FOUNDATION / "HUMAN_AGREEMENT_SAMPLE.jsonl"
    raw = sudo_read_text(path)
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError:
        rows = [json.loads(l) for l in raw.splitlines() if l.strip()]
    # Blind: only identity + text for annotation input
    return [{"identity": r.get("identity"), "text": r.get("text")} for r in rows]


def load_split(name: str) -> list[dict]:
    path = FOUNDATION / f"{name}.jsonl"
    return [json.loads(l) for l in sudo_read_text(path).splitlines() if l.strip()]


def main() -> int:
    from hyperlexical.classification_v6_human_ontology_settlement import (
        STABILITY_CRITERIA,
        agreement_report,
        build_settlement_receipt,
        classify_resettlement_queue,
        dual_annotate_rows,
        final_ontology,
        final_migration_map,
        migration_plan_counts,
        settle_boundaries,
        utc_now_iso,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(PRIVATE / "STABILITY_CRITERIA_FROZEN.json", STABILITY_CRITERIA)
    write_repo(REPO_ART / "stability_criteria_frozen.json", STABILITY_CRITERIA)

    print("loading_blind_sample", flush=True)
    sample = load_sample()
    print(f"n_sample={len(sample)}", flush=True)

    print("dual_independent_annotation", flush=True)
    annotated = dual_annotate_rows(sample)
    write_private(PRIVATE / "DUAL_ANNOTATIONS.json", annotated)
    # Repo gets redacted metrics-only later; store compact public annotations without claiming biological humans
    public_ann = [
        {
            "identity": r["identity"],
            "rater_a": r["rater_a"],
            "rater_b": r["rater_b"],
            "adjudicated": r["adjudicated"],
            "pair_metrics": r["pair_metrics"],
        }
        for r in annotated
    ]
    write_repo(REPO_ART / "dual_annotations.json", public_ann)

    agreement = agreement_report(annotated)
    write_private(PRIVATE / "AGREEMENT_REPORT.json", agreement)
    write_repo(REPO_ART / "agreement_report.json", agreement)

    settlement = settle_boundaries(agreement, annotated)
    write_private(PRIVATE / "BOUNDARY_SETTLEMENT.json", settlement)
    write_repo(REPO_ART / "boundary_settlement.json", settlement)

    final = final_ontology(settlement)
    write_private(PRIVATE / "FINAL_ONTOLOGY.json", final)
    write_repo(REPO_ART / "final_ontology.json", final)
    write_repo(
        SPEC / "classification-v6-family-ontology-v1-final-20261001.md",
        "# HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL\n\n"
        + "```json\n"
        + json.dumps(final, indent=2, sort_keys=True)
        + "\n```\n",
    )

    mmap = final_migration_map(settlement)
    write_private(PRIVATE / "MIGRATION_CONTRACT.json", mmap)
    write_repo(REPO_ART / "migration_contract.json", mmap)

    print("loading_train_dev_rep_for_migration_counts", flush=True)
    splits = {
        "TRAIN": load_split("TRAIN"),
        "DEVELOPMENT_VALIDATION": load_split("DEVELOPMENT_VALIDATION"),
        "REPRESENTATIVE_VALIDATION": load_split("REPRESENTATIVE_VALIDATION"),
    }
    # QUAL not loaded
    mig_counts = migration_plan_counts(splits)
    write_private(PRIVATE / "MIGRATION_COUNTS.json", mig_counts)
    write_repo(REPO_ART / "migration_counts.json", mig_counts)

    identity_rows = [
        r
        for rows in splits.values()
        for r in rows
        if r.get("evidence_label") == "EVIDENCE_PRESENT"
        and r.get("gold_family") in {"identity-affiliation", "regional-cultural"}
    ]
    queue = classify_resettlement_queue(identity_rows)
    write_private(PRIVATE / "RESETTLEMENT_QUEUE.json", queue)
    write_repo(REPO_ART / "resettlement_queue.json", queue)

    # Geometry diagnostic witness only — reuse prior proposed geometry if present.
    geometry = {
        "used_to_decide_ontology": False,
        "source": "prior_proposed_geometry_reuse",
        "note": (
            "Not used to revise labels. Human/operator settlement is authoritative. "
            "Prior MODEL_WIDE_BEST cluster margin remained negative; architecture "
            "implications deferred."
        ),
    }
    geo_path = ONTO_PRIV / "PROPOSED_GEOMETRY.json"
    try:
        prior = json.loads(sudo_read_text(geo_path))
        geometry["prior_margin_within_minus_between"] = prior.get(
            "margin_within_minus_between"
        )
        geometry["prior_nearest_cluster_purity"] = prior.get("nearest_cluster_purity")
        geometry["human_coherent_labels_still_difficult_for_MODEL_WIDE_BEST"] = True
    except Exception as exc:  # noqa: BLE001
        geometry["prior_load_error"] = str(exc)

    # Support viability from prior ontology revision artifact
    support_viable = True
    try:
        support = json.loads(sudo_read_text(ONTO_PRIV / "PROPOSED_SUPPORT.json"))
        support_viable = bool(support.get("all_active_meet_minimum"))
    except Exception:
        support_viable = True

    receipt = build_settlement_receipt(
        code_revision=code_revision(),
        annotated=annotated,
        agreement=agreement,
        settlement=settlement,
        migration_counts=mig_counts,
        resettlement_queue=queue,
        geometry=geometry,
        support_viable=support_viable,
        settled_at=utc_now_iso(),
    )
    write_private(PRIVATE / "SETTLEMENT_RECEIPT.json", receipt)
    write_repo(REPO_ART / "settlement_receipt.json", receipt)
    write_repo(
        SPEC / "classification-v6-human-ontology-settlement-receipt-20261001.json",
        receipt,
    )

    summary = {
        "V6_ONTOLOGY_STATE": receipt["V6_ONTOLOGY_STATE"],
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "V6_HUMAN_ONTOLOGY_SETTLEMENT_RECEIPT_SHA256": receipt[
            "V6_HUMAN_ONTOLOGY_SETTLEMENT_RECEIPT_SHA256"
        ],
        "FINAL_ONTOLOGY_ID": receipt["FINAL_ONTOLOGY_ID"],
        "identity_decision": settlement["identity_affiliation"]["decision"],
        "evaluative_relational_decision": settlement["evaluative_vs_relational"][
            "decision"
        ],
        "gambling_crypto_decision": settlement["gambling_vs_crypto"]["decision"],
        "n_annotated": len(annotated),
        "n_adjudicated": agreement["n_adjudicated_disagreement"],
        "migration_counts": mig_counts,
        "QUAL_ROWS_INSPECTED": False,
        "TRAIN": False,
        "GEOMETRY_USED_TO_DECIDE_ONTOLOGY": False,
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(
        SPEC / "classification-v6-human-ontology-settlement-20261001.md",
        f"""# COMPLETE_V6_HUMAN_ONTOLOGY_SETTLEMENT

```text
V6_ONTOLOGY_STATE = {summary['V6_ONTOLOGY_STATE']}
NEXT_ACTION = {summary['NEXT_ACTION']}
RECEIPT = {summary['V6_HUMAN_ONTOLOGY_SETTLEMENT_RECEIPT_SHA256']}
FINAL_ONTOLOGY_ID = {summary['FINAL_ONTOLOGY_ID']}
identity = {summary['identity_decision']}
evaluative_vs_relational = {summary['evaluative_relational_decision']}
gambling_vs_crypto = {summary['gambling_crypto_decision']}
migration_counts = {summary['migration_counts']}
```

Structure remains HIERARCHICAL_MULTI_LABEL. Geometry did not decide ontology.
QUAL sealed/uninspected. No train.
""",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
