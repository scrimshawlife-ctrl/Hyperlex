"""Validate sealed residual-threshold artifacts against the retrospective schemas.

This module only reads private evidence. A conformance gap is reported.
Frozen bytes are not rewritten.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO / "specs/007-hyperlexical-model/schemas/residual-threshold"
SOURCE = Path("/home/morpheus/hlx-private/eval-reserve-20260926/operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
TRACKER = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001/HYPOTHESIS.json"
REPORT_PATH = SCHEMA_DIR / "CONFORMANCE.json"

SCHEMA_FILES = {
    "manifest": "residual-threshold-surface-manifest.schema.json",
    "receipt": "residual-threshold-receipt.schema.json",
    "join": "residual-threshold-support-join.schema.json",
    "direction": "residual-threshold-direction-analysis.schema.json",
    "confound": "residual-threshold-confound-analysis.schema.json",
    "search": "residual-threshold-threshold-search.schema.json",
    "decision": "residual-threshold-decision.schema.json",
    "completion": "residual-threshold-completion-receipt.schema.json",
}

EXPECTED_MEASUREMENT = "78ca09ab14912681d028e8b9b1c77a8daf1d0c8c81561434eb9b6ade45a753e5"
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_LEDGER = "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0"
EXPECTED_TRACKER = "e674c207d9eb160159a673c23f7e2a2e8262b5bfc963ccf81b216d8291dc4b0f"
GAP = "SCHEMA_CONFORMANCE_GAP"
PASS = "PASS"
OPERATOR_LABELS = {"HIGH", "SECONDARY", "REJECT", "QUARANTINE", "UNRESOLVED"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_schemas() -> dict[str, dict]:
    loaded = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        loaded[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def schema_registry(schemas: dict[str, dict]) -> Registry:
    registry = Registry()
    for schema in schemas.values():
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


def _errors(schema: dict, instance: object, registry: Registry) -> list[str]:
    validator = Draft202012Validator(schema, registry=registry)
    found = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path)):
        location = "/" + "/".join(str(part) for part in error.path)
        found.append(f"{location}: {error.validator}")
    return found


def classify(name: str) -> str | None:
    if name.endswith("_MANIFEST.jsonl"):
        return "manifest"
    if name.endswith("_SUPPORT_JOIN.jsonl"):
        return "join"
    if name.endswith("_COMPLETION_RECEIPT.json"):
        return "completion"
    if name.endswith("_RECEIPT.json"):
        return "receipt"
    if name.endswith("_DIRECTION_ANALYSIS.json"):
        return "direction"
    if name.endswith("_CONFOUND_ANALYSIS.json"):
        return "confound"
    if name.endswith("_THRESHOLD_SEARCH.json"):
        return "search"
    if name.endswith("_DIRECTION_DECISION.json") or name.endswith("_CONFOUND_DECISION.json"):
        return "decision"
    if name.endswith("_FAILURE.json") or name.endswith("_DESIGN_CLOSURE.json"):
        return "decision"
    if name.endswith("_SUPPORT_REASSESSMENT.json"):
        return "decision"
    return None


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_artifact(path: Path, kind: str, schemas: dict[str, dict], registry: Registry) -> dict:
    schema = schemas[SCHEMA_FILES[kind]]
    errors: list[str] = []
    if path.suffix == ".jsonl":
        for index, row in enumerate(_jsonl(path), start=1):
            for error in _errors(schema, row, registry):
                errors.append(f"line {index} {error}")
    else:
        errors.extend(_errors(schema, json.loads(path.read_text(encoding="utf-8")), registry))
    return {
        "artifact": path.name,
        "errors": errors,
        "schema": SCHEMA_FILES[kind],
        "status": PASS if not errors else GAP,
    }


def _semantic(source: Path) -> list[dict]:
    checks = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "detail": detail, "status": PASS if ok else GAP})

    manifest = _jsonl(source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl")
    labels = _jsonl(source / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELS.jsonl")
    join = _jsonl(source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN.jsonl")
    measurement = _jsonl(source / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl")
    manifest_ids = {row["row_id"] for row in manifest}
    label_ids = {row["row_id"] for row in labels}
    join_ids = {row["row_id"] for row in join}
    measurement_ids = {row["row_id"] for row in measurement}
    ready = sum(row["row_resolution_status"] == "RESIDUAL_READY" for row in join)
    unknown = sum(row["row_resolution_status"] == "UNKNOWN" for row in join)
    add("support_join_rows", len(join) == 200, f"rows={len(join)}")
    add("ready_plus_unknown", ready + unknown == 200, f"ready={ready} unknown={unknown}")
    add(
        "row_id_sets",
        manifest_ids == label_ids == join_ids and len(manifest_ids) == 200,
        f"manifest={len(manifest_ids)} labels={len(label_ids)} join={len(join_ids)}",
    )
    add(
        "measurement_disjoint",
        measurement_ids.isdisjoint(manifest_ids) and len(measurement_ids) == 200,
        f"measurement_rows={len(measurement_ids)}",
    )
    measurement_hash = sha256_file(source / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl")
    manifest_hash = sha256_file(source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl")
    add("measurement_manifest_unchanged", measurement_hash == EXPECTED_MEASUREMENT, measurement_hash)
    receipt = json.loads((source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN_RECEIPT.json").read_text(encoding="utf-8"))
    add("join_receipt_manifest_hash", receipt["manifest_hash"] == manifest_hash, receipt["manifest_hash"])
    add(
        "join_receipt_label_hash",
        receipt["operator_label_hash"] == sha256_file(source / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELS.jsonl"),
        receipt["operator_label_hash"],
    )
    add(
        "join_receipt_score_hash",
        receipt["score_hash"] == sha256_file(source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SCORES.jsonl"),
        receipt["score_hash"],
    )
    direction = json.loads((source / "RESIDUAL_THRESHOLD_V2_DIRECTION_ANALYSIS.json").read_text(encoding="utf-8"))
    add(
        "direction_join_hash",
        direction["source_support_join_hash"] == sha256_file(source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN.jsonl"),
        direction["source_support_join_hash"],
    )
    label_values = {row["operator_label"] for row in labels}
    add("operator_labels_closed", label_values <= OPERATOR_LABELS, "labels stay inside the emitted enum")
    v1_labels = _jsonl(source / "RESIDUAL_THRESHOLD_V1_CALIBRATION_LABELS.jsonl")
    unlabeled = all(row["operator_bucket"] is None and row["operator_label_present"] is False for row in v1_labels)
    add("v1_labels_unlabeled", unlabeled and len(v1_labels) == 27, f"rows={len(v1_labels)}")
    v1_manifest = _jsonl(source / "RESIDUAL_THRESHOLD_V1_CALIBRATION_MANIFEST.jsonl")
    v1_identity = all(row["calibration_row_id"] == row["normalized_text_sha256"] for row in v1_manifest)
    add("v1_manifest_identity", v1_identity and len(v1_manifest) == 27, f"rows={len(v1_manifest)}")
    v2_identity = all(row["row_id"] == row["normalized_text_sha256"] for row in manifest)
    add("v2_manifest_identity", v2_identity, "row_id matches normalized_text_sha256")
    draw = json.loads((source / "RESIDUAL_THRESHOLD_V2_SURFACE_DRAW_RECEIPT.json").read_text(encoding="utf-8"))
    add("draw_receipt_measurement_hash", draw["measurement_manifest_sha256"] == EXPECTED_MEASUREMENT, draw["measurement_manifest_sha256"])
    add("draw_receipt_manifest_hash", draw["calibration_manifest_sha256"] == manifest_hash, draw["calibration_manifest_sha256"])
    add("events_unchanged", sha256_file(LEDGER / "events.jsonl") == EXPECTED_EVENTS, EXPECTED_EVENTS)
    add("ledger_unchanged", sha256_file(LEDGER / "ledger.json") == EXPECTED_LEDGER, EXPECTED_LEDGER)
    add("tracker_unchanged", sha256_file(TRACKER) == EXPECTED_TRACKER, EXPECTED_TRACKER)
    return checks


def evidence_hashes(source: Path) -> dict[str, str]:
    return {path.name: sha256_file(path) for path in sorted(source.iterdir()) if path.is_file() and path.name.startswith("RESIDUAL_THRESHOLD_")}


def conformance_report() -> dict:
    schemas = load_schemas()
    registry = schema_registry(schemas)
    before = evidence_hashes(SOURCE) if SOURCE.is_dir() else {}
    results = []
    skipped = []
    if SOURCE.is_dir():
        for path in sorted(SOURCE.iterdir()):
            if not path.is_file() or not path.name.startswith("RESIDUAL_THRESHOLD_"):
                continue
            kind = classify(path.name)
            if kind is None:
                skipped.append(path.name)
                continue
            results.append(validate_artifact(path, kind, schemas, registry))
        semantic = _semantic(SOURCE)
    else:
        semantic = [{"check": "private_reserve", "detail": "reserve is absent", "status": GAP}]
    after = evidence_hashes(SOURCE) if SOURCE.is_dir() else {}
    changed = sorted(name for name, digest in before.items() if after.get(name) != digest)
    schema_gaps = [row["artifact"] for row in results if row["status"] == GAP]
    semantic_gaps = [row["check"] for row in semantic if row["status"] == GAP]
    return {
        "authorization": "THRESHOLD_ARTIFACT_SCHEMA_HARDENING_AUTHORIZATION",
        "calibration_evidence_modified": bool(changed),
        "calibration_state": "NO_THRESHOLD_PASSES_PRECISION_GATE",
        "changed_artifacts": changed,
        "json_schema_family": sorted(SCHEMA_FILES.values()) + ["residual-threshold-common.schema.json"],
        "outcome": GAP if schema_gaps or semantic_gaps or changed else PASS,
        "results": results,
        "schema_conformance_gaps": schema_gaps,
        "scientific_remediation": False,
        "semantic": semantic,
        "semantic_conformance_gaps": semantic_gaps,
        "skipped_not_applicable": skipped,
        "threshold_redesign": False,
        "training_authorized": False,
    }


def render_report(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def write_public_report(report: dict) -> None:
    if "hlx-private" in str(REPORT_PATH) or not str(REPORT_PATH).endswith("/schemas/residual-threshold/CONFORMANCE.json"):
        raise RuntimeError("conformance report path is not the public schema directory")
    REPORT_PATH.write_text(render_report(report), encoding="utf-8")


def main() -> None:
    report = conformance_report()
    text = render_report(report)
    if "--write" in sys.argv:
        write_public_report(report)
    print(text)


if __name__ == "__main__":
    main()
