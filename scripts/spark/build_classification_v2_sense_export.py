"""Rebuild the v2 export so fresh rows train on attested definition prose.

The frozen evidence map is unchanged. Rows already admitted as page titles
keep that title only when the stored definition prose is empty or when the
prose identity is already reserved, consumed, or present in the historical
export. New prose identities are routed to training with every reserve
target set to zero. This script does not train and does not move BEST.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.classification_v2_acquire import ACTIVE_TARGETS, evidence_seal  # noqa: E402
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402
from hyperlexical.identity_ledger import (  # noqa: E402
    PLANNING_TARGETS,
    IdentityLedger,
    derived_state,
)

SOURCE = Path("/home/morpheus/hlx-private/classification-v2-acquire-20260929/civilian.v0.1.jsonl")
DEST_DIR = Path("/home/morpheus/hlx-private/classification-v2-sense-20260929")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
BATCH_ID = "HLX-CLASSIFICATION-V2-SENSE-TEXT-20260929"
SEAL = "8b30c98ad8eac7c136e391103450c9d0d20a3499220e9b48f923eab8218581f1"
BLOCKED = {
    "TRAIN_CONSUMED",
    "TRAIN_CANDIDATE",
    "EVAL_RESERVE",
    "EVAL_BOUND",
    "EVAL_SPENT",
    "EVAL_ABANDONED",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path) -> tuple[list[str], list[dict]]:
    base_lines: list[str] = []
    fresh: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            provenance = row.get("provenance")
            if isinstance(provenance, dict) and provenance.get("evidence_seal"):
                fresh.append(row)
            else:
                base_lines.append(line if line.endswith("\n") else line + "\n")
    return base_lines, fresh


def holdout_counts(prose_count: int) -> int:
    """Validation rows from prose text only. At least one prose row stays in train."""
    if prose_count < 2:
        return 0
    if prose_count >= 4:
        return 2
    return 1


def rebuild(base_lines: list[str], fresh: list[dict], ledger: IdentityLedger) -> tuple[list[dict], dict]:
    if evidence_seal() != SEAL:
        raise SystemExit("REFUSE: evidence seal moved")
    used = {normalized_text_sha256(json.loads(line)["text"]) for line in base_lines}
    revised: list[dict] = []
    fallback: dict[str, int] = defaultdict(int)
    for row in fresh:
        provenance = dict(row["provenance"])
        if provenance.get("evidence_seal") != SEAL:
            raise SystemExit("REFUSE: fresh row evidence seal mismatch")
        if row.get("lineage") not in ACTIVE_TARGETS or row.get("class") != "OBSERVED":
            raise SystemExit("REFUSE: fresh row left the frozen target set")
        title = str(row["text"])
        prose = str(provenance.get("definition_prose") or "").strip()
        prose_digest = normalized_text_sha256(prose) if prose else ""
        record = ledger.identity(prose_digest) if prose_digest else None
        state = derived_state(record) if record else "NEW"
        use_prose = bool(prose) and prose_digest not in used and state not in BLOCKED
        if prose and not use_prose:
            fallback["duplicate" if prose_digest in used else state] += 1
        text = prose if use_prose else title
        digest = normalized_text_sha256(text)
        if digest in used:
            raise SystemExit(f"REFUSE: training text collides inside the export ({row['lineage']})")
        used.add(digest)
        if not use_prose:
            title_record = ledger.identity(digest)
            if title_record is None or derived_state(title_record) != "TRAIN_CONSUMED":
                raise SystemExit("REFUSE: title fallback is not already TRAIN_CONSUMED")
        provenance["training_text"] = "definition_prose" if use_prose else "title"
        provenance["definition_prose"] = prose
        revised.append({**row, "provenance": provenance, "text": text, "split": "train"})

    by_family: dict[str, list[dict]] = defaultdict(list)
    for row in revised:
        if row["provenance"]["training_text"] == "definition_prose":
            by_family[row["lineage"]].append(row)
    val_by_family: dict[str, int] = {}
    for family, rows in by_family.items():
        ordered = sorted(rows, key=lambda item: normalized_text_sha256(item["text"]))
        hold = holdout_counts(len(ordered))
        if hold:
            for row in ordered[-hold:]:
                row["split"] = "val"
        val_by_family[family] = hold
    for family in ACTIVE_TARGETS:
        val_by_family.setdefault(family, 0)

    train_by_family = Counter_family(revised, "train")
    missing = [family for family in ACTIVE_TARGETS if train_by_family.get(family, 0) == 0]
    if missing:
        raise SystemExit(f"REFUSE: prose rebuild left families without train support: {missing}")
    report = {
        "fallback_title_rows": sum(1 for row in revised if row["provenance"]["training_text"] == "title"),
        "fresh_rows": len(revised),
        "prose_rows": sum(1 for row in revised if row["provenance"]["training_text"] == "definition_prose"),
        "train_by_family": {family: train_by_family.get(family, 0) for family in ACTIVE_TARGETS},
        "val_by_family": val_by_family,
        "val_rows": sum(1 for row in revised if row["split"] == "val"),
        "blocked_fallbacks": dict(fallback),
    }
    return revised, report


def Counter_family(rows: list[dict], split: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        if row["split"] == split:
            counts[row["lineage"]] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    base_lines, fresh = load_rows(SOURCE)
    if len(fresh) != 113:
        raise SystemExit(f"REFUSE: expected 113 fresh rows, found {len(fresh)}")
    ledger = IdentityLedger.load(LEDGER)
    revised, report = rebuild(base_lines, fresh, ledger)
    to_admit = [row for row in revised if row["provenance"]["training_text"] == "definition_prose"]
    preview = ledger.screen(
        to_admit,
        batch_id=BATCH_ID,
        targets={key: 0 for key in PLANNING_TARGETS},
    )
    if preview["unique_admitted_to_eval_reserve"] != 0:
        raise SystemExit("REFUSE: prose text would enter EVAL_RESERVE")
    if preview["rejected_unique_identities"] != 0:
        raise SystemExit(f"REFUSE: prose text collides with an existing identity: {preview['rejected_existing_identities']}")
    if preview["unique_routed_to_train_candidate"] != len({normalized_text_sha256(row['text']) for row in to_admit}):
        raise SystemExit("REFUSE: prose admission preview did not route every new identity to train")
    print(json.dumps({"preview": {key: preview[key] for key in ("unique_routed_to_train_candidate", "unique_admitted_to_eval_reserve", "rejected_unique_identities")}, **report}, indent=2, sort_keys=True))
    if not args.commit:
        return 0
    if (DEST_DIR / "civilian.v0.1.jsonl").exists():
        raise SystemExit("REFUSE: sense export already exists")
    prior = len(ledger.events)
    export_path = DEST_DIR / "civilian.v0.1.jsonl"
    admitted = ledger.admit(
        to_admit,
        batch_id=BATCH_ID,
        source_artifact=str(export_path),
        targets={key: 0 for key in PLANNING_TARGETS},
    )
    if admitted["unique_admitted_to_eval_reserve"] != 0 or admitted["rejected_unique_identities"] != 0:
        raise SystemExit("REFUSE: admission diverged from the preview")
    for row in to_admit:
        ledger.transition(
            normalized_text_sha256(row["text"]),
            "TRAIN_CONSUMED",
            source_artifact=str(export_path),
            provenance="classification v2 sense-text training",
        )
    DEST_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST_DIR, 0o700)
    body = "".join(base_lines)
    extra = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in revised)
    export_path.write_text(body + extra, encoding="utf-8")
    os.chmod(export_path, 0o600)
    appended = ledger.persist_append(LEDGER, prior)
    receipt = {
        "batch_id": BATCH_ID,
        "evidence_seal": SEAL,
        "export_path": str(export_path),
        "export_rows": len(base_lines) + len(revised),
        "export_sha256": sha256_file(export_path),
        "historical_rows": len(base_lines),
        "jev": "OFF",
        "ledger_events_appended": appended,
        "moves_best": False,
        "schema": "hyperlex.classification.v2.sense_export.v1",
        "source_export": str(SOURCE),
        "source_export_sha256": sha256_file(SOURCE),
        "split_rule": "prose rows sorted by normalized_text_sha256; hold out 2 when at least 4 remain train-eligible, else 1 when at least 2 exist; title fallbacks stay train",
        **report,
        "ledger_report": {
            "rejected_unique_identities": admitted["rejected_unique_identities"],
            "unique_admitted_to_eval_reserve": admitted["unique_admitted_to_eval_reserve"],
            "unique_routed_to_train_candidate": admitted["unique_routed_to_train_candidate"],
        },
    }
    receipt_path = DEST_DIR / "SENSE_EXPORT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(receipt_path, 0o600)
    print(json.dumps({"wrote": str(export_path), "sha256": receipt["export_sha256"], "rows": receipt["export_rows"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
