"""Append atom representations and NONE prose to a new classification export.

Does not rewrite the validation export. Does not admit rows onto the reserve.
Train identities become TRAIN_CONSUMED. Validation identities stay AVAILABLE.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.classification_v2_acquire_run import blocked_identities  # noqa: E402
from hyperlexical.classification_v2_surface import (  # noqa: E402
    SURFACE_ATOM,
    representation_leak,
    surface_census,
    surface_form,
)
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402
from hyperlexical.identity_ledger import IdentityLedger, derived_state  # noqa: E402

SOURCE = Path("/home/morpheus/hlx-private/classification-v2-validation-20260929/civilian.v0.2.jsonl")
NONE_PROSE = Path("/home/morpheus/hlx-private/classification-v2-surface-20260929/NONE_PROSE.jsonl")
DEST = Path("/home/morpheus/hlx-private/classification-v2-surface-20260929")
EXPORT = DEST / "civilian.v0.3.jsonl"
PINS = DEST / "SURFACE_EXPORT.json"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
BATCH = "HLX-CLASSIFICATION-V2-SURFACE-20260929"


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def atom_row(source: dict, blocked: dict[str, str], ledger: IdentityLedger) -> tuple[dict | None, str]:
    provenance = source.get("provenance")
    if not isinstance(provenance, dict):
        return None, "no_provenance"
    prose = str(provenance.get("definition_prose") or "").strip()
    if not prose or str(source.get("text") or "") != prose:
        return None, "not_definition_row"
    if source.get("lineage") in (None, "", "none"):
        return None, "not_family"
    page = str(provenance.get("page") or "").strip()
    if not page or page.startswith("http"):
        return None, "no_headword"
    if surface_form(page) != SURFACE_ATOM:
        return None, "headword_" + surface_form(page).lower()
    digest = normalized_text_sha256(page)
    existing_training = False
    if digest in blocked:
        reason = blocked[digest]
        if reason != "TRAIN_CONSUMED" or source.get("split") != "train":
            return None, "blocked:" + reason
        record = ledger.identity(digest) or {}
        labels = [
            label.get("lineage")
            for label in (record.get("labels") or [])
            if label.get("task") == "classify"
        ]
        if source.get("lineage") not in labels or derived_state(record) != "TRAIN_CONSUMED":
            return None, "consumed_lineage_mismatch"
        existing_training = True
    source_digest = normalized_text_sha256(prose)
    row = {
        "class": source.get("class"),
        "fillers": [],
        "license": source.get("license"),
        "lineage": source.get("lineage"),
        "provenance": {
            "admission": "surface-atom",
            "lineage_rule": "same_source_identity",
            "normalized_text_sha256": digest,
            "page": page,
            "page_url": provenance.get("page_url"),
            "representation": "ATOM",
            "revision_id": provenance.get("revision_id"),
            "source_representation": "PROSE",
            "source_text_sha256": source_digest,
            "source_page": page,
            "split_copied": source.get("split"),
            "ledger_action": "existing_training_identity" if existing_training else "new_identity",
        },
        "role_scheme": None,
        "roles": [],
        "split": source.get("split"),
        "stage": source.get("stage") or "circulating",
        "task": "classify",
        "text": page,
        "typology": [],
    }
    return row, "accepted"


def main() -> int:
    commit = "--commit" in sys.argv
    if EXPORT.exists():
        fail(f"surface export already exists: {EXPORT}")
    if not NONE_PROSE.is_file():
        fail("NONE prose file missing")
    source_bytes = SOURCE.read_bytes()
    source_rows = load_jsonl(SOURCE)
    blocked = blocked_identities()
    ledger = IdentityLedger.load(LEDGER)
    texts = {normalized_text_sha256(str(row.get("text") or "")) for row in source_rows}
    for digest in texts:
        blocked.setdefault(digest, "EXPORT_TEXT")
    atoms = []
    atom_exclusions: dict[str, int] = {}
    for row in source_rows:
        if row.get("task") != "classify":
            continue
        built, reason = atom_row(row, blocked, ledger)
        if built is None:
            atom_exclusions[reason] = atom_exclusions.get(reason, 0) + 1
            continue
        digest = built["provenance"]["normalized_text_sha256"]
        blocked[digest] = "SURFACE_ATOM"
        texts.add(digest)
        atoms.append(built)
    atoms.sort(key=lambda row: row["provenance"]["normalized_text_sha256"])
    none_rows = load_jsonl(NONE_PROSE)
    kept_none = []
    for row in none_rows:
        digest = normalized_text_sha256(str(row.get("text") or ""))
        if digest in blocked:
            fail("NONE prose collides with a blocked identity: " + blocked[digest])
        if row.get("lineage") != "none" or row.get("class") != "INFERRED":
            fail("NONE prose left the none contract")
        if surface_form(str(row.get("text") or "")) != "PROSE":
            fail("NONE prose is not PROSE")
        blocked[digest] = "NONE_PROSE"
        kept_none.append(row)
    combined = source_rows + atoms + kept_none
    leaks = representation_leak(combined)
    if leaks:
        fail(f"representation leak across splits: {len(leaks)}")
    census = surface_census(combined)
    if not census["pass"]:
        fail(f"surface cells incomplete: {census['missing']}")
    summary = {
        "atom_exclusions": atom_exclusions,
        "atom_rows": len(atoms),
        "atom_train": sum(1 for row in atoms if row["split"] == "train"),
        "atom_val": sum(1 for row in atoms if row["split"] == "val"),
        "cells": census["cells"],
        "none_prose": len(kept_none),
        "none_prose_train": sum(1 for row in kept_none if row["split"] == "train"),
        "none_prose_val": sum(1 for row in kept_none if row["split"] == "val"),
        "source_rows": len(source_rows),
    }
    print(json.dumps(summary, sort_keys=True))
    if not commit:
        return 0
    body = source_bytes
    if not body.endswith(b"\n"):
        body += b"\n"
    extra = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in atoms + kept_none)
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST, 0o700)
    EXPORT.write_bytes(body + extra.encode("utf-8"))
    os.chmod(EXPORT, 0o600)
    if not EXPORT.read_bytes().startswith(source_bytes):
        fail("surface export does not keep the validation prefix")
    prior_events = len(ledger.events)
    prior_consumed = sum(1 for record in ledger.identities.values() if record.get("training_consumed"))
    prior_reserve = sum(1 for record in ledger.identities.values() if record.get("evaluation_reserved"))
    new_rows = atoms + kept_none
    fresh_rows = [
        row for row in new_rows
        if row.get("provenance", {}).get("ledger_action") != "existing_training_identity"
    ]
    for row in fresh_rows:
        digest = normalized_text_sha256(str(row.get("text") or ""))
        if ledger.identity(digest) is not None:
            fail("new surface identity already exists in the ledger")
    provenance = "classification v2 surface balance; not evaluation reserve"
    for row in fresh_rows:
        digest = normalized_text_sha256(str(row.get("text") or ""))
        ledger.observe(
            digest,
            source_artifact=str(EXPORT),
            labels=[
                {
                    "task": "classify",
                    "class": row["class"],
                    "lineage": row["lineage"],
                    "split": row["split"],
                }
            ],
            current_source=True,
            catalogued=True,
            provenance=provenance,
        )
        if row["split"] == "train":
            ledger.transition(digest, "TRAIN_CANDIDATE", source_artifact=str(EXPORT), provenance=provenance)
            ledger.transition(digest, "TRAIN_CONSUMED", source_artifact=str(EXPORT), provenance=provenance)
            if derived_state(ledger.identity(digest) or {}) != "TRAIN_CONSUMED":
                fail("train surface identity did not settle TRAIN_CONSUMED")
        elif row["split"] == "val":
            state = derived_state(ledger.identity(digest) or {})
            record = ledger.identity(digest) or {}
            if state != "AVAILABLE" or record.get("training_consumed") or record.get("evaluation_reserved"):
                fail(f"validation surface identity settled as {state}")
        else:
            fail("surface row left train/val")
    ledger.persist_append(LEDGER, prior_events)
    consumed_after = sum(1 for record in ledger.identities.values() if record.get("training_consumed"))
    reserve_after = sum(1 for record in ledger.identities.values() if record.get("evaluation_reserved"))
    expected_consumed = prior_consumed + sum(1 for row in fresh_rows if row["split"] == "train")
    if consumed_after != expected_consumed or reserve_after != prior_reserve:
        fail("ledger census moved outside the surface batch")
    pins = {
        "atom_rows": len(atoms),
        "batch_id": BATCH,
        "export_path": str(EXPORT),
        "export_rows": len(source_rows) + len(new_rows),
        "export_sha256": sha256_file(EXPORT),
        "none_prose_rows": len(kept_none),
        "schema": "hyperlex.classification.v2.surface_export.v1",
        "source_export": str(SOURCE),
        "source_sha256": sha256_file(SOURCE),
        "surface_cells": census["cells"],
    }
    PINS.write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(PINS, 0o600)
    print(json.dumps({"export_sha256": pins["export_sha256"], "export_rows": pins["export_rows"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
