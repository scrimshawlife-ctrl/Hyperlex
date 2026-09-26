"""Build the GEN-0 text-identity ledger from receipt-backed artifacts.

Does not train, score, draw a holdout, or write raw text. Exits 2 when the
eligible-universe census does not reproduce the sealed exhaustion result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from hyperlexical.holdout_eligibility import census
from hyperlexical.holdout_guard import operational_status, _file_sha256, _read_manifest
from hyperlexical.identity_ledger import (
    GENERATION,
    POLICY_ID,
    IdentityLedger,
    acquisition_gap,
    normalized_text_sha256,
)
from hyperlexical.selection_surface import row_id
from hyperlexical.soft_ceiling import clean_surface

EXPECTED = {
    "source_rows": 5005,
    "excluded_by_split_test": 440,
    "excluded_by_training_row_id": 3247,
    "excluded_by_training_normalized_text_hash": 608,
    "excluded_by_spent_or_abandoned": 710,
    "eligible_rows": 0,
    "classify_observed_eligible": 0,
    "classify_non_none_eligible": 0,
}


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _require_status(path: Path, expected: str) -> dict:
    record, ids, hashes = _read_manifest(str(path))
    status = operational_status(record)
    if status != expected:
        raise SystemExit(f"STOP: {path} operational status {status} != {expected}")
    return {"record": record, "ids": ids, "hashes": hashes, "status": status}


def _clean_hashes(rows: list[dict], train_rows: list[dict]) -> set[str]:
    unbind = [row for row in rows if row.get("task") == "unbind"]
    train = [row for row in train_rows if row.get("split") == "train"]
    kept, _account = clean_surface(unbind, train_rows=train)
    return {normalized_text_sha256(str(row.get("text") or "")) for row in kept}


def _receipt_shas(models: Path) -> list[str]:
    found: set[str] = set()
    for path in models.rglob("train-receipt.json"):
        text = str(path)
        if "/src-" in text or "/stepB/" in text or "/wt-" in text:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sha = payload.get("data_sha256")
        if isinstance(sha, str) and len(sha) == 64:
            found.add(sha)
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", required=True)
    parser.add_argument("--pin-sha256", required=True)
    parser.add_argument("--pin-rows", type=int, required=True)
    parser.add_argument("--store", required=True)
    parser.add_argument("--store-sha256", required=True)
    parser.add_argument("--store-rows", type=int, required=True)
    parser.add_argument("--v2", required=True)
    parser.add_argument("--rc1-scored", required=True)
    parser.add_argument("--rc1-unbind-rows", required=True)
    parser.add_argument("--select-001", required=True)
    parser.add_argument("--select-002", required=True)
    parser.add_argument("--train-aux", action="append", default=[], help="path|provenance")
    parser.add_argument("--models", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    pin_path = Path(args.pin)
    store_path = Path(args.store)
    pin_sha = _file_sha(pin_path)
    store_sha = _file_sha(store_path)
    if pin_sha != args.pin_sha256:
        raise SystemExit("STOP: pinned export sha256 mismatch")
    if store_sha != args.store_sha256:
        raise SystemExit("STOP: live store sha256 mismatch")
    pin_rows = _jsonl(pin_path)
    store_rows = _jsonl(store_path)
    if len(pin_rows) != args.pin_rows or len(store_rows) != args.store_rows:
        raise SystemExit("STOP: row count mismatch")

    v2 = _require_status(Path(args.v2), "SCORED_SPENT")
    v2_payload = json.loads(Path(args.v2).read_text(encoding="utf-8"))
    definition = str(v2_payload.get("text_hash_definition") or "")
    if "normalize_group_text" not in definition:
        raise SystemExit("STOP: v2 text hash definition is not the canonical normalizer")
    select_001 = _require_status(Path(args.select_001), "UNSCORED_ABANDONED")
    select_002 = _require_status(Path(args.select_002), "UNSCORED_ABANDONED")
    rc1_payload = json.loads(Path(args.rc1_scored).read_text(encoding="utf-8"))
    rc1_record = {
        "path": args.rc1_scored,
        "sha256": _file_sha256(Path(args.rc1_scored)),
        "status": rc1_payload.get("status"),
    }
    if operational_status(rc1_record) != "SCORED_SPENT":
        raise SystemExit("STOP: rc1 scored manifest is not SCORED_SPENT")
    rc1_rows = _jsonl(Path(args.rc1_unbind_rows))

    joined = 0
    mismatch = 0
    v2_by_id = dict(zip(v2_payload["row_ids"], v2_payload["normalized_text_sha256"]))
    for row in store_rows:
        ident = row_id(row)
        if ident in v2_by_id:
            joined += 1
            if normalized_text_sha256(str(row.get("text") or "")) != v2_by_id[ident]:
                mismatch += 1
    if mismatch:
        raise SystemExit(f"STOP: v2 manifest hashes diverge from canonical text identity ({mismatch})")

    report = census(
        store_rows,
        pin_rows,
        extra_rows=rc1_rows,
        extra_manifests=[args.v2, args.select_001, args.select_002],
    )
    discrepancy = {key: [report.get(key), EXPECTED[key]] for key in EXPECTED if report.get(key) != EXPECTED[key]}
    if discrepancy or not report.get("waterfall_sums_to_source"):
        sys.stdout.write(json.dumps({"STOP": True, "discrepancy": discrepancy}, indent=2) + "\n")
        return 2

    clean = _clean_hashes(store_rows, pin_rows)
    clean |= _clean_hashes(rc1_rows, pin_rows)
    ledger = IdentityLedger()
    pin_artifact = str(pin_path)
    consumed: set[str] = set()
    for row in pin_rows:
        digest = ledger.observe_row(
            row,
            source_artifact=pin_artifact,
            provenance="morph78 train receipt data_sha256 matches this export",
            catalogued=True,
        )
        if digest not in consumed:
            ledger.mark_historical(
                digest,
                "training_consumed",
                source_artifact=pin_artifact,
                provenance="pinned morph78 training export consumed by seed-morph78",
            )
            consumed.add(digest)
    for item in args.train_aux:
        path_text, _sep, reason = item.partition("|")
        aux = Path(path_text)
        for row in _jsonl(aux):
            digest = ledger.observe_row(
                row,
                source_artifact=str(aux),
                provenance=reason,
                catalogued=True,
            )
            if digest not in consumed:
                ledger.mark_historical(
                    digest,
                    "training_consumed",
                    source_artifact=str(aux),
                    provenance=reason,
                )
                consumed.add(digest)
    v2_artifact = str(Path(args.v2))
    spent: set[str] = set()
    for digest, ident in zip(v2_payload["normalized_text_sha256"], v2_payload["row_ids"]):
        ledger.observe(
            digest,
            source_artifact=v2_artifact,
            row_ids=[ident],
            catalogued=True,
            provenance="holdout-manifest-v2 status SCORED_SPENT; hash definition is normalize_group_text",
        )
        if digest not in spent:
            ledger.mark_historical(
                digest,
                "evaluation_spent",
                source_artifact=v2_artifact,
                provenance="v2 holdout scored and spent",
            )
            spent.add(digest)
    rc1_artifact = str(Path(args.rc1_unbind_rows))
    for row in rc1_rows:
        digest = ledger.observe_row(
            row,
            source_artifact=rc1_artifact,
            provenance="rc1 scored manifest SCORED_SPENT; unbind row file matched slice n=312",
            catalogued=True,
            unbind_clean=normalized_text_sha256(str(row.get("text") or "")) in clean,
        )
        if digest not in spent:
            ledger.mark_historical(
                digest,
                "evaluation_spent",
                source_artifact=str(Path(args.rc1_scored)),
                provenance="rc1 evaluation material scored; test burned for selection",
            )
            spent.add(digest)
    for manifest, bundle, experiment in (
        (Path(args.select_001), select_001, "HLX-EXP-2026-09-26-SELECT-001"),
        (Path(args.select_002), select_002, "HLX-EXP-2026-09-26-SELECT-002"),
    ):
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        abandoned: set[str] = set()
        for digest, ident in zip(payload["normalized_text_sha256"], payload["row_ids"]):
            ledger.observe(
                digest,
                source_artifact=str(manifest),
                row_ids=[ident],
                catalogued=True,
                provenance="lifecycle receipt UNSCORED_ABANDONED; manifest bytes left sealed",
                experiment_id=experiment,
            )
            if digest not in abandoned:
                ledger.mark_historical(
                    digest,
                    "evaluation_abandoned",
                    source_artifact=str(manifest),
                    provenance="holdout closed before a valid scored execution",
                    experiment_id=experiment,
                )
                abandoned.add(digest)
        _ = bundle
    store_artifact = str(store_path)
    for row in store_rows:
        digest = normalized_text_sha256(str(row.get("text") or ""))
        ledger.observe_row(
            row,
            source_artifact=store_artifact,
            provenance="current live store; labels joined, text not stored",
            current_source=True,
            catalogued=True,
            unbind_clean=digest in clean,
        )

    live_hashes = {normalized_text_sha256(str(row.get("text") or "")) for row in store_rows}
    summary = ledger.census(live_hashes)
    if summary["live_available_hashes"] != 0 or summary["currently_available_hashes"] != 0:
        sys.stdout.write(json.dumps({"STOP": True, "ledger_census": summary}, indent=2) + "\n")
        return 2
    screen = ledger.screen(store_rows, batch_id="live-store-rescreen")
    if screen["unique_admitted_to_eval_reserve"] != 0:
        raise SystemExit("STOP: live store admitted reserve identities")

    train_hashes = {normalized_text_sha256(str(row.get("text") or "")) for row in pin_rows}
    gate = ledger.select_003_gate(train_hashes)
    if gate["eligible"]:
        raise SystemExit("STOP: SELECT-003 gate must stay closed while the reserve is empty")

    test_rows = [row for row in store_rows if str(row.get("split") or "") == "test"]
    test_in_train = 0
    for row in test_rows:
        digest = normalized_text_sha256(str(row.get("text") or ""))
        record = ledger.identity(digest)
        if record and record["training_consumed"]:
            test_in_train += 1
    receipt_shas = _receipt_shas(Path(args.models))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ledger.save(out)
    proof = {
        "schema": "hyperlex.eval_reserve_proof.v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "generation": GENERATION,
        "policy_id": POLICY_ID,
        "authorizes_training": False,
        "authorizes_select_003": False,
        "select_003": "NOT_DRAFTED",
        "identity_function": "hyperlexical.holdout_guard.normalized_text_sha256",
        "pin_sha256": pin_sha,
        "pin_rows": len(pin_rows),
        "store_sha256": store_sha,
        "store_rows": len(store_rows),
        "census_eligible_rows": report["eligible_rows"],
        "census_reproduced": True,
        "waterfall_sums_to_source": True,
        "v2_store_joined": joined,
        "v2_hash_mismatch": mismatch,
        "v2_status": "SCORED_SPENT",
        "rc1_scored_status": "SCORED_SPENT",
        "rc1_unbind_rows": len(rc1_rows),
        "rc1_classify_row_identities": "NOT_IN_MANIFEST",
        "select_001_operational_status": "UNSCORED_ABANDONED",
        "select_002_operational_status": "UNSCORED_ABANDONED",
        "split_test_rows": len(test_rows),
        "split_test_training_consumed": test_in_train,
        "ledger_census": summary,
        "live_store_admission_screen": screen,
        "acquisition_gap": acquisition_gap(ledger.reserve_counts()),
        "select_003_gate": gate,
        "training_receipt_data_sha256_count": len(receipt_shas),
        "pinned_export_sha_in_train_receipts": pin_sha in receipt_shas,
        "training_receipt_text_extracted_only_for_bytes_read": True,
        "unresolved_training_artifact_shas": [sha for sha in receipt_shas if sha != pin_sha],
        "model_outcomes_consulted": False,
        "generation_analysis": {
            "chosen": "GEN-0",
            "gen_1_created": False,
            "continue_gen_0": "Acquire evaluation-only text disjoint from TRAIN_CONSUMED, EVAL_SPENT, and EVAL_ABANDONED. Keep the pinned morph78 export and seed-morph78.",
            "gen_1_not_chosen_because": "convenience is not a reset condition; the baseline is still the system under test",
            "gen_0_impractical_if": [
                "new classify evidence cannot represent OBSERVED and non-none",
                "new text keeps colliding with the pinned export or spent/abandoned hashes",
                "train-candidate growth continues while reserve slices stay empty",
                "the reserve cannot hold the four required slices",
                "the historical baseline is no longer the system under test",
            ],
        },
    }
    proof_path = out / "exhaustion-proof.json"
    proof_path.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Projection must not contain raw text keys.
    blob = (out / "ledger.json").read_text(encoding="utf-8")
    if '"text":' in blob:
        raise SystemExit("STOP: ledger projection contains a text field")
    sys.stdout.write(
        json.dumps(
            {
                "out": str(out),
                "identities": summary["identities"],
                "live_available": summary["live_available_hashes"],
                "reserve": summary["reserve_counts"],
                "screen_raw_rows": screen["raw_rows"],
                "screen_unique": screen["unique_canonical_text_identities"],
                "screen_reserved": screen["unique_admitted_to_eval_reserve"],
            },
            indent=2,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
