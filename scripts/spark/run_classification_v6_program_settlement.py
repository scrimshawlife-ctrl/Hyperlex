"""SETTLE_HYPERLEX_PROGRAM_END_STATE — write settlement artifacts (CPU, no train)."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(os.environ.get("HLX_REPO") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.classification_v6_program_settlement import (  # noqa: E402
    EXPERIMENT_ID,
    PHASE_RULE,
    build_program_settlement_receipt,
    program_settlement_contract,
    settled_audit_from_evidence,
)

REPO_ART = REPO / "artifacts" / "experiments" / EXPERIMENT_ID
SPEC = REPO / "specs" / "007-hyperlexical-model"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    sealed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    audit = settled_audit_from_evidence()
    receipt = build_program_settlement_receipt(audit, sealed_at=sealed_at)
    contract = program_settlement_contract()
    summary = {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PRIMARY_DISPOSITION": receipt["disposition"]["PRIMARY_DISPOSITION"],
        "RELEASE_STATUS": receipt["disposition"]["RELEASE_STATUS"],
        "HUB_PUBLISH_AUTHORIZED": False,
        "CLASSIFIER_RELEASE_ELIGIBLE": False,
        "classifier_candidate_result": receipt["disposition"][
            "classifier_candidate_result"
        ],
        "NEXT_ACTION": receipt["disposition"]["NEXT_ACTION"],
        "RECEIPT": receipt["SYSTEM_PROGRAM_SETTLEMENT_RECEIPT_SHA256"],
        "sealed_at": sealed_at,
        "grade_summary_counts": {
            k: len(v) for k, v in receipt["grade_summary"].items()
        },
    }
    write_json(REPO_ART / "contract.json", contract)
    write_json(REPO_ART / "audit.json", audit)
    write_json(REPO_ART / "receipt.json", receipt)
    write_json(REPO_ART / "RECEIPT.json", receipt)
    write_json(REPO_ART / "summary.json", summary)
    write_json(REPO_ART / "SUMMARY.json", summary)
    write_json(
        SPEC / "classification-v6-program-settlement-receipt-20261002.json",
        {
            "EXPERIMENT_ID": EXPERIMENT_ID,
            "PHASE_RULE": PHASE_RULE,
            "PRIMARY_DISPOSITION": summary["PRIMARY_DISPOSITION"],
            "RELEASE_STATUS": summary["RELEASE_STATUS"],
            "RECEIPT": summary["RECEIPT"],
            "sealed_at": sealed_at,
            "artifacts": str(REPO_ART),
        },
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
