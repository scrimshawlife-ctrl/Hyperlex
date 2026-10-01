"""Freeze Hyperlex V5 as HYPERLEX_V5_RESEARCH_BASELINE.

V5 is not release-qualified. Artifacts are preserved for historical
comparison, failure taxonomy, measurement design, and regression baselines.
Do not retune V5, move BEST, or reuse spent qualification identities.
"""

from __future__ import annotations

from typing import Any

from .classification_v5_pipeline_qualification import (
    DEPENDENCY_MANIFEST_SHA256_PIN,
    QUALIFICATION_ID,
    SEAL_PACKAGE_RECEIPT_SHA256_PIN,
)
from .classification_v5_qualification_failure_system_review import (
    PRIMARY_REMEDIATION_PHASE as V5_NEXT_PHASE,
    SYSTEM_DIAGNOSIS as V5_SYSTEM_DIAGNOSIS,
    V5_DISPOSITION,
)
from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import (
    MODEL_WIDE_BEST_SHA256,
    STAGE_A_BEST_SHA256,
)
from .classification_v5_stage_b import FROZEN_INDEX_SHA256

BASELINE_ID = "HYPERLEX_V5_RESEARCH_BASELINE"
BASELINE_RULE = "FREEZE_HYPERLEX_V5_AS_RESEARCH_BASELINE"
SCHEMA = "hyperlex.classification.v6.v5_research_baseline.v1"

RELEASE_QUALIFIED = False
HUB_PUBLISH_AUTHORIZED = False

ALLOWED_USES = (
    "historical_comparison",
    "failure_taxonomy",
    "measurement_design",
    "regression_baselines",
)
FORBIDDEN_USES = (
    "production_release",
    "threshold_retune",
    "index_reuse_as_v6_production",
    "optimization_on_spent_qualification_rows",
    "automatic_weight_transfer_into_v6",
)

PRESERVED_LOCAL_FINDINGS = (
    "gold_identifiability_repair",
    "serialization_repair",
    "factorized_checkpoint_packaging",
    "SHORT_ATOM_NONE_repair",
    "Stage_B_V1R2_validation_behavior",
)

SYSTEM_LEVEL_FAILURES = (
    "Stage_A_admission_generalization",
    "Stage_B_family_discrimination_generalization",
    "distribution_shift",
    "validation_selection_bias",
    "ontology_separability",
    "representation_generalization",
)


def v5_research_baseline() -> dict[str, Any]:
    return {
        "BASELINE_ID": BASELINE_ID,
        "BASELINE_RULE": BASELINE_RULE,
        "RELEASE_QUALIFIED": RELEASE_QUALIFIED,
        "HUB_PUBLISH_AUTHORIZED": HUB_PUBLISH_AUTHORIZED,
        "V5_DISPOSITION": V5_DISPOSITION,
        "PRIMARY_SYSTEM_DIAGNOSIS": V5_SYSTEM_DIAGNOSIS,
        "NEXT_PHASE_AT_FREEZE": V5_NEXT_PHASE,
        "statement": "V5 is not release-qualified.",
        "pins": {
            "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
            "STAGE_A_BEST": STAGE_A_BEST_SHA256,
            "STAGE_B_INDEX": FROZEN_INDEX_SHA256,
            "PIPELINE_DEPENDENCY_MANIFEST_SHA256": DEPENDENCY_MANIFEST_SHA256_PIN,
            "SEAL_PACKAGE_RECEIPT_SHA256": SEAL_PACKAGE_RECEIPT_SHA256_PIN,
            "QUALIFICATION_ID": QUALIFICATION_ID,
        },
        "allowed_uses": list(ALLOWED_USES),
        "forbidden_uses": list(FORBIDDEN_USES),
        "preserved_local_findings": list(PRESERVED_LOCAL_FINDINGS),
        "system_level_failures": list(SYSTEM_LEVEL_FAILURES),
        "qualification_rows_evaluation_spent": True,
        "artifacts_mutable": False,
        "schema": SCHEMA,
    }


def baseline_receipt(*, code_revision: str, frozen_at: str) -> dict[str, Any]:
    payload = {
        **v5_research_baseline(),
        "code_revision": code_revision,
        "frozen_at": frozen_at,
    }
    payload["V5_RESEARCH_BASELINE_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "V5_RESEARCH_BASELINE_RECEIPT_SHA256"
            }
        )
    )
    return payload
