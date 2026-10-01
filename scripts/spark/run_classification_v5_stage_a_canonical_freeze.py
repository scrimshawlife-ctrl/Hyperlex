"""FREEZE_V5_STAGE_A_CANONICAL_AND_UPDATE_DOWNSTREAM_PROVENANCE — offline seal.

No GPU required. No training. No index rebuild. No reserve scoring.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("HLX_REPO") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(REPO / "scripts" / "shadow"))
os.environ.setdefault("HLX_V2_FORWARD_ONTOLOGY", "1")

ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-CANONICAL-V1"
)
PIPE_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-B-PIPELINE-V1"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
STAGE_B_ART = (
    REPO / "artifacts" / "experiments" / "HLX-CLASSIFICATION-V5-STAGE-B-001"
)


def code_revision() -> str:
    override = (os.environ.get("HLX_V5_STAGE_A_CODE_REVISION") or "").strip()
    if override:
        return override
    try:
        return subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    from hyperlexical.classification_v5_stage_a_b_pipeline import (
        PIPELINE_ID,
        build_pipeline_freeze_receipt,
        integrate_text_probabilities,
        pipeline_contract,
        verify_entry_gating,
        verify_stage_b_parent_and_floors,
    )
    from hyperlexical.classification_v5_stage_a_canonical import (
        CANONICAL_ID,
        KNOWN_LIMITATIONS,
        STAGE_A_BEST_SHA256,
        assert_canonical_factorized_flat,
        build_canonical_freeze_receipt,
        stage_a_canonical_contract,
        utc_now_iso,
        verify_canonical_checkpoint_keys,
    )
    from hyperlexical.classification_v5_stage_b import stage_b_contract
    from hyperlexical.classification_v5_stale_reference_audit import (
        audit_tree,
        seal_audit_receipt,
    )
    from hyperlexical.save_pretrained import FACTORIZED_HEAD_NAMES

    revision = code_revision()
    frozen_at = utc_now_iso()

    # Serialization regression: incomplete flat must fail closed.
    incomplete = {f"encoder.layers.20.attn.Wqkv.weight": [0.0]}
    try:
        assert_canonical_factorized_flat(incomplete)
        raise SystemExit("expected_factorized_assert_to_fail")
    except ValueError:
        serialization_fail_closed = True

    complete_keys = [
        f"encoder.layers.{i}.x"
        for i in range(12)
    ] + [
        f"{name}.{suffix}"
        for name in FACTORIZED_HEAD_NAMES
        for suffix in ("weight", "bias")
    ]
    head_ok = verify_canonical_checkpoint_keys(complete_keys)
    if not head_ok["pass"]:
        print(json.dumps(head_ok, indent=2, sort_keys=True))
        return 2

    audit = audit_tree(REPO)
    if not audit["pass"]:
        write_json(ART / "STALE_REFERENCE_AUDIT_FAIL.json", audit)
        print(json.dumps({"stale_active": audit["active_needs_fix"]}, indent=2))
        return 2
    audit_receipt = seal_audit_receipt(audit)

    entry = verify_entry_gating()
    parent = verify_stage_b_parent_and_floors()
    if not entry["pass"] or not parent["pass"]:
        write_json(
            ART / "INTEGRATION_FAIL.json",
            {"entry": entry, "parent": parent},
        )
        print(json.dumps({"entry": entry, "parent": parent}, indent=2, sort_keys=True))
        return 2

    # Probability → decision → Stage-B entry smoke (read-only).
    samples = [
        integrate_text_probabilities(p_relation=0.9, p_resolvable=0.5),
        integrate_text_probabilities(p_relation=0.9, p_resolvable=0.8),
        integrate_text_probabilities(p_relation=0.4, p_resolvable=0.8),
    ]
    sample_checks = {
        "uncertain_abstains": samples[0]["stage_a_decision"] == "UNCERTAIN"
        and samples[0]["invokes_stage_b"] is False,
        "present_enters": samples[1]["stage_a_decision"] == "EVIDENCE_PRESENT"
        and samples[1]["invokes_stage_b"] is True,
        "none_stops": samples[2]["stage_a_decision"] == "NO_EVIDENCE"
        and samples[2]["invokes_stage_b"] is False,
    }
    if not all(sample_checks.values()):
        print(json.dumps(sample_checks, indent=2))
        return 2

    integration = {
        "entry_gating": entry,
        "stage_b_parent_and_floors": parent,
        "probability_smoke": {"samples": samples, "checks": sample_checks},
        "serialization_fail_closed": serialization_fail_closed,
        "checkpoint_key_contract": head_ok,
        "pass": True,
    }

    stage_a_receipt = build_canonical_freeze_receipt(
        code_revision=revision,
        stale_reference_audit=audit_receipt,
        frozen_at=frozen_at,
    )
    pipeline_receipt = build_pipeline_freeze_receipt(
        code_revision=revision,
        integration=integration,
        frozen_at=frozen_at,
    )
    stage_b_active = stage_b_contract()

    ART.mkdir(parents=True, exist_ok=True)
    PIPE_ART.mkdir(parents=True, exist_ok=True)
    write_json(ART / "stage_a_canonical_contract.json", stage_a_canonical_contract())
    write_json(ART / "stage_a_canonical_receipt.json", stage_a_receipt)
    write_json(ART / "stale_reference_audit.json", audit_receipt)
    write_json(ART / "integration_verification.json", integration)
    write_json(PIPE_ART / "pipeline_contract.json", pipeline_contract())
    write_json(PIPE_ART / "pipeline_receipt.json", pipeline_receipt)
    write_json(STAGE_B_ART / "stage_b_active_contract.json", stage_b_active)

    write_json(
        SPEC / "classification-v5-stage-a-canonical-receipt-20261001.json",
        stage_a_receipt,
    )
    write_json(
        SPEC / "classification-v5-stage-a-b-pipeline-receipt-20261001.json",
        pipeline_receipt,
    )
    write_json(
        SPEC / "classification-v5-stage-b-active-contract-20261001.json",
        stage_b_active,
    )
    write_json(
        SPEC / "classification-v5-stale-reference-audit-20261001.json",
        audit_receipt,
    )

    md_a = f"""# HYPERLEX_V5_STAGE_A_CANONICAL_V1

Frozen after REPRO promotion of complete factorized Stage-A.

```text
CANONICAL_ID = {CANONICAL_ID}
STAGE_A_BEST = {STAGE_A_BEST_SHA256}
MODEL_WIDE_BEST = 9fba0f66…
V5_STAGE_A_STATE = CANONICAL_FROZEN
STAGE_A_RESEARCH_LOOP = CLOSED_FOR_CURRENT_FAILURE_CLASS
STAGE_A_CANONICAL_RECEIPT_SHA256 = {stage_a_receipt['STAGE_A_CANONICAL_RECEIPT_SHA256']}
```

## Decision

```text
p_resolvable < 0.75 -> UNCERTAIN
else p_relation >= 0.60 -> EVIDENCE_PRESENT
else -> NO_EVIDENCE
```

Outputs: `NO_EVIDENCE` | `EVIDENCE_PRESENT` | `UNCERTAIN`.
Input: `text`. `AUTO_RELABEL=false`.

## Limitations

- DOMAIN_IRRELEVANT_GENERALIZATION = {KNOWN_LIMITATIONS['DOMAIN_IRRELEVANT_GENERALIZATION']}
- SHORT_ATOM_POSITIVE_GENERALIZATION = {KNOWN_LIMITATIONS['SHORT_ATOM_POSITIVE_GENERALIZATION']}
- CONTEXT_DEPENDENT_GOLD = {KNOWN_LIMITATIONS['CONTEXT_DEPENDENT_GOLD']}
"""
    md_p = f"""# HYPERLEX_V5_STAGE_A_B_PIPELINE_V1

```text
PIPELINE_ID = {PIPELINE_ID}
PIPELINE_RECEIPT_SHA256 = {pipeline_receipt['PIPELINE_RECEIPT_SHA256']}
flow = text -> Stage A -> stop|abstain|Stage B retrieval
```

Stage-B index/floors frozen (`index_rebuilt=false`, `floors_retuned=false`).
Parent pin: `STAGE_A_BEST=f2b00c5d…`, `STAGE_A_CANONICAL={CANONICAL_ID}`.
"""
    write_text(SPEC / "classification-v5-stage-a-canonical-20261001.md", md_a)
    write_text(SPEC / "classification-v5-stage-a-b-pipeline-20261001.md", md_p)

    summary = {
        "CANONICAL_ID": CANONICAL_ID,
        "PIPELINE_ID": PIPELINE_ID,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_CANONICAL_RECEIPT_SHA256": stage_a_receipt[
            "STAGE_A_CANONICAL_RECEIPT_SHA256"
        ],
        "PIPELINE_RECEIPT_SHA256": pipeline_receipt["PIPELINE_RECEIPT_SHA256"],
        "STALE_AUDIT_RECEIPT_SHA256": audit_receipt["receipt_sha256"],
        "V5_STAGE_A_STATE": "CANONICAL_FROZEN",
        "STAGE_A_RESEARCH_LOOP": "CLOSED_FOR_CURRENT_FAILURE_CLASS",
        "integration_pass": True,
        "serialization_fail_closed": True,
        "NEXT_ACTION": "EVALUATE_FULL_V5_PIPELINE_OR_PRODUCTION_PACKAGING",
        "TRAIN": False,
        "code_revision": revision,
    }
    write_json(ART / "SUMMARY.json", summary)
    write_json(PIPE_ART / "SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
