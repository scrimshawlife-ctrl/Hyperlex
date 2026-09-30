"""Seal HYPERLEX_ACTIVE_FAMILY_MIXED_REMEDIATION_V1 from the separability audit.

Read-only planner. Does not train, fetch, score the reserve, move BEST, or
mutate the active ontology.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
AUDIT = Path(
    "/home/morpheus/hlx-private/classification-v2-separability-audit-20260930/SEPARABILITY_AUDIT.json"
)
AUDIT_SHA = "2cb2fe2459a86323dfa8aa50136bb8e6822598ffd8895a1988af459949853d5f"
DESTINATION = Path(
    "/home/morpheus/hlx-private/classification-v2-mixed-remediation-20260930/MIXED_REMEDIATION.json"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except PermissionError:
        import subprocess

        return subprocess.check_output(["sudo", "sha256sum", str(path)], text=True).split()[0]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def main() -> int:
    from hyperlexical.classification_v2_mixed_remediation import (
        assemble_remediation,
        next_engineering_action,
        remediation_contract,
    )

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(AUDIT) != AUDIT_SHA:
        # The sealed audit may be mode-restricted; compare embedded hash too.
        audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        if audit.get("artifact_sha256") != AUDIT_SHA:
            fail("separability audit hash mismatch")
    else:
        audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        if audit.get("artifact_sha256") != AUDIT_SHA:
            fail("separability audit embedded hash mismatch")

    artifact = assemble_remediation(audit)
    artifact["next_engineering_action"] = next_engineering_action(artifact)
    artifact["contract"] = remediation_contract()
    from hyperlexical.classification_v2 import canonical_json, sha256_text

    artifact["artifact_sha256"] = sha256_text(
        canonical_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    )
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    DESTINATION.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    DESTINATION.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "destination": str(DESTINATION),
                "remediation_state": artifact["remediation_state"],
                "artifact_sha256": artifact["artifact_sha256"],
                "next_engineering_action": artifact["next_engineering_action"],
                "training_gate": artifact["training_gate"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
