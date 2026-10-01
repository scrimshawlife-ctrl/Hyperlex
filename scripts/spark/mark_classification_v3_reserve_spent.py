"""Mark sealed v3 reserve identities as evaluation_spent in the ledger.

The v3 reserve was sealed from AVAILABLE without ledger transitions. This pass
records the historical spend only. It does not train, score, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
LEDGER_DIR = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
PRIVATE = Path("/home/morpheus/hlx-private/classification-v3-reserve-20260930")
ROWS = PRIVATE / "reserve-rows.jsonl"
ROWS_SHA = "abb8bf22012bb450dba05ce3129e32c2f28fabe9911030b28c68c5b99d39b937"
MANIFEST = PRIVATE / "RESERVE_MANIFEST.json"
MANIFEST_FILE_SHA = (
    "81cd8666f555943ea4591bb5ffd62789ac14095caeab72fbe63147cac9cdc1b6"
)
MANIFEST_INNER_SHA = (
    "4a13d7a76352fd0e0008a0b3f36ca2976876c945896e28c945be00f4cabc2ef5"
)
DEST = Path("/home/morpheus/hlx-private/classification-v4-balanced-reserve-acquire-20260930")
EXPERIMENT = "HLX-CLASSIFICATION-V3-RESERVE-20260930"

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def main() -> int:
    from hyperlexical.identity_ledger import IdentityLedger, derived_state

    if sha256_file(ROWS) != ROWS_SHA:
        fail("spent v3 rows digest mismatch")
    if sha256_file(MANIFEST) != MANIFEST_FILE_SHA:
        fail("spent v3 manifest file digest mismatch")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("manifest_sha256") != MANIFEST_INNER_SHA:
        fail("spent v3 manifest inner digest mismatch")
    identities = []
    for line in ROWS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        identities.append(str(row.get("identity") or row["normalized_text_sha256"]))
    if len(identities) != len(set(identities)):
        fail("duplicate identities in spent v3 rows")
    ledger = IdentityLedger.load(LEDGER_DIR)
    prior_events = len(ledger.events)
    already = 0
    marked = 0
    missing = 0
    for digest in identities:
        record = ledger.identities.get(digest)
        if record is None:
            missing += 1
            continue
        state = derived_state(record)
        if record.get("evaluation_spent") or state == "EVAL_SPENT":
            already += 1
            continue
        ledger.mark_historical(
            digest,
            "evaluation_spent",
            source_artifact=str(ROWS),
            provenance="classification-v3-reserve-20260930 one-shot score; permanent exclusion",
            experiment_id=EXPERIMENT,
        )
        marked += 1
    appended = ledger.persist_append(LEDGER_DIR, prior_events)
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST, 0o700)
    summary = {
        "already_spent": already,
        "appended_events": appended,
        "experiment_id": EXPERIMENT,
        "ledger_path": str(LEDGER_DIR / "ledger.json"),
        "marked": marked,
        "missing": missing,
        "n": len(identities),
        "prior_events": prior_events,
        "rows_sha256": ROWS_SHA,
        "rule": "HYPERLEX_CLASSIFICATION_V4_BALANCED_RESERVE_ACQUIRE_V1",
    }
    out = DEST / "SPENT_V3_LEDGER_MARK.json"
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(out, 0o600)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if missing:
        fail(f"missing ledger identities: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
