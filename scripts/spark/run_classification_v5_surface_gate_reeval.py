"""Re-evaluate sealed v5 surface under exact SURFACE_READINESS_GATES_V1.

Does not rebuild the dataset, does not train, does not score reserves, and does
not move BEST. Writes GATE_EVAL.json and supersedes readiness under exact gates.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
PRIVATE = Path(
    os.environ.get(
        "HLX_V5_SURFACE_DIR",
        "/home/morpheus/hlx-private/"
        "classification-v5-stage-a-negative-evidence-surface-20260930",
    )
)
DATASET = PRIVATE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = os.environ.get(
    "HLX_V5_SURFACE_SHA",
    "3add3aa624bab8e578d461574ea8344f3e2c4b7eec30ddbb9faffbe2c0bea3eb",
).strip()
PAIR_RECORDS = PRIVATE / "PAIR_RECORDS.json"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")
SPENT_V2 = Path(
    "/home/morpheus/hlx-private/classification-v2-train-ready-20260929/reserve-eval-rows.jsonl"
)
SPENT_V3 = Path(
    "/home/morpheus/hlx-private/classification-v3-reserve-20260930/reserve-rows.jsonl"
)
SPENT_V4 = Path(
    "/home/morpheus/hlx-private/classification-v4-reserve-20260930/reserve-rows.jsonl"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
EMBEDDING_REPORT = PRIVATE / "EMBEDDING_HARDNESS.json"

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
        completed = subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.split()[0]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def blocked_reasons() -> dict[str, str]:
    from hyperlexical.holdout_guard import normalized_text_sha256

    blocked: dict[str, str] = {}
    for path, reason in ((SPENT_V2, "spent_v2"), (SPENT_V3, "spent_v3"), (SPENT_V4, "spent_v4")):
        for row in load_jsonl(path):
            for key in ("identity", "normalized_text_sha256"):
                value = row.get(key)
                if isinstance(value, str) and len(value) == 64:
                    blocked.setdefault(value, reason)
            text = row.get("text")
            if isinstance(text, str) and text.strip():
                blocked.setdefault(normalized_text_sha256(text), reason)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    for record in ledger.get("identities") or []:
        digest = record.get("normalized_text_sha256")
        state = str(record.get("state") or "")
        if not digest:
            continue
        if record.get("evaluation_spent") or state == "EVAL_SPENT":
            # already spent reserves covered above; keep ledger spent as v2-class
            blocked.setdefault(str(digest), blocked.get(str(digest), "spent_v2"))
    return blocked


def main() -> int:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        BEST_SHA as MODULE_BEST,
        STAGE_A_TRAIN_CONTRACT,
        SURFACE_RULE as LEGACY_SURFACE_RULE,
        canonical_json,
        sha256_text,
    )
    from hyperlexical.classification_v5_surface_readiness_gates import (
        GATE_RULE,
        evaluate_surface_readiness,
        frozen_readiness_gates,
    )

    try:
        from hyperlexical.classification_v5_stage_a_mixed_remediate import (
            SURFACE_RULE_V1R8 as REMEDIATED_SURFACE_RULE,
        )
    except Exception:
        try:
            from hyperlexical.classification_v5_stage_a_surface_remediate import (
                SURFACE_RULE_V1R7 as REMEDIATED_SURFACE_RULE,
            )
        except Exception:
            REMEDIATED_SURFACE_RULE = LEGACY_SURFACE_RULE
    surface_rule = os.environ.get("HLX_V5_SURFACE_RULE", "").strip() or (
        REMEDIATED_SURFACE_RULE
        if "v1r" in str(PRIVATE)
        else LEGACY_SURFACE_RULE
    )

    if MODULE_BEST != BEST_SHA:
        fail("module BEST pin drift")
    observed_sha = sha256_file(DATASET)
    if DATASET_SHA and observed_sha != DATASET_SHA:
        fail(f"sealed dataset digest mismatch:{observed_sha}!={DATASET_SHA}")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")

    rows = load_jsonl(DATASET)
    pair_records = json.loads(PAIR_RECORDS.read_text(encoding="utf-8"))
    embedding_report = None
    if EMBEDDING_REPORT.exists():
        embedding_report = json.loads(EMBEDDING_REPORT.read_text(encoding="utf-8"))

    evaluated = evaluate_surface_readiness(
        rows,
        pair_records=pair_records,
        ontology=ACTIVE_FAMILY_VOCABULARY,
        blocked=blocked_reasons(),
        embedding_report=embedding_report,
    )
    detail_key = {
        "acquisition_floors_pass": "acquisition",
        "validation_floors_pass": "validation",
        "all_disjointness_pass": "disjointness",
        "duplicate_quality_pass": "duplicate_quality",
        "pairing_pass": "pairing",
        "surface_balance_pass": "surface_balance",
        "lexical_overlap_pass": "lexical_overlap",
        "embedding_hardness_pass": "embedding_hardness",
        "shallow_shortcut_pass": "shallow_shortcut",
        "topic_balance_pass": "topic_balance",
        "provenance_pass": "provenance",
        "schema_integrity_pass": "schema_integrity",
    }
    missing = {
        name: evaluated["details"][detail_key[name]]
        for name in evaluated["missing_evidence"]
    }

    gate_eval = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "dataset_sha256": observed_sha,
        "gate_pass": evaluated["gate_pass"],
        "gate_rule": GATE_RULE,
        "gates": frozen_readiness_gates(),
        "missing_evidence": missing,
        "model_acceptance_gates_separate": {
            **STAGE_A_TRAIN_CONTRACT,
            "note": "model gates; not dataset-readiness gates",
        },
        "n": len(rows),
        "prior_readiness_superseded": True,
        "schema": "hyperlex.classification.v5.surface_gate_eval.v1",
        "state": evaluated["state"],
        "surface_rule": surface_rule,
        "train": False,
    }
    gate_eval["gate_eval_sha256"] = sha256_text(
        canonical_json({k: v for k, v in gate_eval.items() if k != "gate_eval_sha256"})
    )
    write_private(PRIVATE / "GATE_EVAL.json", gate_eval)

    # Supersede READINESS under exact gates (dataset body unchanged).
    readiness = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "dataset_sha256": observed_sha,
        "design_rule": "DESIGN_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE",
        "gate_eval_sha256": gate_eval["gate_eval_sha256"],
        "gate_rule": GATE_RULE,
        "gate_pass": evaluated["gate_pass"],
        "missing_evidence": missing,
        "model_acceptance_gates_separate": gate_eval["model_acceptance_gates_separate"],
        "prior_ready_under_legacy_gates_superseded": True,
        "readiness": {
            "blockers": [{"failed_gate": name} for name in missing],
            "missing_evidence": missing,
            "state": evaluated["state"],
            "surface_rule": surface_rule,
        },
        "readiness_details": evaluated.get("details"),
        "remediate_rule": "REMEDIATE_V5_STAGE_A_SURFACE_V1",
        "schema": "hyperlex.classification.v5.evidence_surface_readiness.v1r7",
        "state": evaluated["state"],
        "surface_rule": surface_rule,
        "train": False,
    }
    readiness["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in readiness.items() if k != "receipt_sha256"})
    )
    write_private(PRIVATE / "READINESS.json", readiness)

    summary = json.loads((PRIVATE / "SUMMARY.json").read_text(encoding="utf-8"))
    summary["readiness_state"] = evaluated["state"]
    summary["gate_rule"] = GATE_RULE
    summary["gate_eval_sha256"] = gate_eval["gate_eval_sha256"]
    summary["missing_evidence_gates"] = sorted(missing)
    summary["prior_ready_under_legacy_gates_superseded"] = True
    write_private(PRIVATE / "SUMMARY.json", summary)

    print(
        json.dumps(
            {
                "dataset_sha256": observed_sha,
                "gate_eval_sha256": gate_eval["gate_eval_sha256"],
                "missing_evidence_gates": sorted(missing),
                "receipt_sha256": readiness["receipt_sha256"],
                "state": evaluated["state"],
                "surface_rule": surface_rule,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
