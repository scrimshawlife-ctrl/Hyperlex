"""Validate sealed residual-threshold artifacts against the contract schema family.

VALIDATE_ONLY. A conformance gap is reported. Frozen bytes are not rewritten.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO / "specs/007-hyperlexical-model/schemas/hyperlex/residual-threshold"
SOURCE = Path("/home/morpheus/hlx-private/eval-reserve-20260926/operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
TRACKER = LEDGER / "operator-review/HLX-EVAL-UNBIND-SENSE-SCREEN-V1-HYPOTHESIS-001/HYPOTHESIS.json"
REPORT_PATH = SCHEMA_DIR / "CONTRACT_VALIDATION.json"

EXPECTED_MEASUREMENT = "78ca09ab14912681d028e8b9b1c77a8daf1d0c8c81561434eb9b6ade45a753e5"
EXPECTED_EVENTS = "96b74a92d44f1cf9fe152b18e5207176f161ba3bfce528dac38aa4571a742f9c"
EXPECTED_LEDGER = "77e22433203879b252f7a9e309d2013d7550101d1c4a014b494d2c96df87d0e0"
EXPECTED_TRACKER = "e674c207d9eb160159a673c23f7e2a2e8262b5bfc963ccf81b216d8291dc4b0f"
GAP = "SCHEMA_CONFORMANCE_GAP"
SEMANTIC_GAP = "SCHEMA_SEMANTIC_VALIDATION_FAILURE"
PASS = "PASS"
AUTHORIZATION = "THRESHOLD_ARTIFACT_SCHEMA_HARDENING_AUTHORIZATION"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_schemas(schema_dir: Path | None = None) -> dict[str, dict]:
    directory = schema_dir or SCHEMA_DIR
    loaded = {}
    for path in sorted(directory.glob("*.schema.json")):
        loaded[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def schema_registry(schemas: dict[str, dict]) -> Registry:
    registry = Registry()
    for schema in schemas.values():
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


def classify(name: str) -> str | None:
    if name.endswith("_MANIFEST.jsonl"):
        return "surface-manifest-row.schema.json"
    if name.endswith("_SUPPORT_JOIN.jsonl"):
        return "support-join-row.schema.json"
    if name.endswith("_RESOLUTION.jsonl"):
        return "resolution-row.schema.json"
    if name.endswith("_SCORES.jsonl"):
        return "score-row.schema.json"
    if name.endswith("_OPERATOR_LABELS.jsonl") or name.endswith("_CALIBRATION_LABELS.jsonl"):
        return "operator-label-row.schema.json"
    if name.endswith("_COMPLETION_RECEIPT.json"):
        return "completion-receipt.schema.json"
    if name.endswith("_OPERATOR_LABELING_RECEIPT.json"):
        return "operator-labeling-receipt.schema.json"
    if name.endswith("_RESOLUTION_RECEIPT.json"):
        return "resolution-receipt.schema.json"
    if name.endswith("_SCORE_RECEIPT.json"):
        return "score-receipt.schema.json"
    if name.endswith("_DRAW_RECEIPT.json"):
        return "surface-draw-receipt.schema.json"
    if name.endswith("_SUPPORT_REASSESSMENT.json"):
        return "support-reassessment.schema.json"
    if name.endswith("_DIRECTION_ANALYSIS.json"):
        return "direction-analysis.schema.json"
    if name.endswith("_DIRECTION_DECISION.json"):
        return "direction-decision.schema.json"
    if name.endswith("_CONFOUND_ANALYSIS.json"):
        return "confound-analysis.schema.json"
    if name.endswith("_CONFOUND_DECISION.json"):
        return "confound-decision.schema.json"
    if name.endswith("_THRESHOLD_SEARCH.json"):
        return "threshold-search.schema.json"
    if name.endswith("_THRESHOLD_DECISION.json") or name.endswith("_THRESHOLD_FROZEN.json"):
        return "threshold-decision.schema.json"
    if name.endswith("_FAILURE.json"):
        return "calibration-failure.schema.json"
    return None


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _redact(value: object) -> object:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, str) and " " not in value and len(value) <= 64:
        return value
    return {"redacted": type(value).__name__}


def public_errors(schema: dict, instance: object, registry: Registry) -> list[dict]:
    validator = Draft202012Validator(schema, registry=registry)
    found = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path)):
        location = "/" + "/".join(str(part) for part in error.path)
        found.append(
            {
                "expected_contract": error.validator,
                "field_path": location,
                "observed_value": _redact(error.instance),
            }
        )
    return found


def validate_artifact(path: Path, schema_name: str, schemas: dict[str, dict], registry: Registry) -> dict:
    schema = schemas[schema_name]
    errors: list[dict] = []
    if path.suffix == ".jsonl":
        for index, row in enumerate(_jsonl(path), start=1):
            for error in public_errors(schema, row, registry):
                error["field_path"] = f"line {index} {error['field_path']}"
                errors.append(error)
    else:
        errors.extend(public_errors(schema, json.loads(path.read_text(encoding="utf-8")), registry))
    return {
        "artifact": path.name,
        "errors": errors,
        "historical_artifact_mutated": False,
        "schema": schema_name,
        "status": PASS if not errors else GAP,
    }


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"check": name, "detail": detail, "status": PASS if ok else SEMANTIC_GAP}


def semantic_checks(source: Path, measurement_hash: str = EXPECTED_MEASUREMENT) -> list[dict]:
    checks = []
    manifest_path = source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_MANIFEST.jsonl"
    label_path = source / "RESIDUAL_THRESHOLD_V2_OPERATOR_LABELS.jsonl"
    join_path = source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN.jsonl"
    measurement_path = source / "RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl"
    if manifest_path.is_file() and label_path.is_file() and join_path.is_file():
        manifest = _jsonl(manifest_path)
        labels = _jsonl(label_path)
        join = _jsonl(join_path)
        manifest_ids = [row["row_id"] for row in manifest]
        label_ids = [row["row_id"] for row in labels]
        join_ids = [row["row_id"] for row in join]
        ready = sum(row["row_resolution_status"] == "RESIDUAL_READY" for row in join)
        unknown = sum(row["row_resolution_status"] == "UNKNOWN" for row in join)
        checks.append(_check("calibration_manifest_rows", len(manifest) == 200, f"rows={len(manifest)}"))
        checks.append(_check("operator_label_rows", len(labels) == 200, f"rows={len(labels)}"))
        checks.append(_check("support_join_rows", len(join) == 200, f"rows={len(join)}"))
        checks.append(_check("ready_plus_unknown", ready + unknown == 200, f"ready={ready} unknown={unknown}"))
        checks.append(_check(
            "row_set_equality",
            manifest_ids == label_ids == join_ids and len(set(manifest_ids)) == 200,
            f"manifest={len(set(manifest_ids))} labels={len(set(label_ids))} join={len(set(join_ids))}",
        ))
        checks.append(_check(
            "manifest_order",
            [row["global_draw_order"] for row in manifest] == list(range(1, 201)),
            "calibration global_draw_order",
        ))
        synsets = [row["pwn30_synset"] for row in manifest]
        checks.append(_check("calibration_synset_unique", len(synsets) == len(set(synsets)), f"synsets={len(set(synsets))}"))
        inventory: dict[str, int] = {}
        for row in labels:
            inventory[row["operator_label"]] = inventory.get(row["operator_label"], 0) + 1
        checks.append(_check("label_inventory_total", sum(inventory.values()) == 200, f"total={sum(inventory.values())}"))
    if measurement_path.is_file() and manifest_path.is_file():
        measurement = _jsonl(measurement_path)
        manifest = _jsonl(manifest_path)
        measurement_ids = {row["row_id"] for row in measurement}
        manifest_ids = {row["row_id"] for row in manifest}
        measurement_synsets = {row["pwn30_synset"] for row in measurement}
        manifest_synsets = {row["pwn30_synset"] for row in manifest}
        digest = sha256_file(measurement_path)
        checks.append(_check("measurement_rows", len(measurement) == 200, f"rows={len(measurement)}"))
        checks.append(_check("measurement_synset_unique", len(measurement_synsets) == len(measurement), f"synsets={len(measurement_synsets)}"))
        checks.append(_check("synset_set_isolation", measurement_synsets.isdisjoint(manifest_synsets), "calibration and measurement synsets"))
        checks.append(_check("measurement_row_isolation", measurement_ids.isdisjoint(manifest_ids), "calibration and measurement row ids"))
        checks.append(_check("measurement_manifest_unchanged", digest == measurement_hash, digest))
        checks.append(_check(
            "measurement_order",
            [row["global_draw_order"] for row in measurement] == list(range(201, 401)),
            "measurement global_draw_order",
        ))
    join_receipt_path = source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SUPPORT_JOIN_RECEIPT.json"
    if join_receipt_path.is_file():
        receipt = json.loads(join_receipt_path.read_text(encoding="utf-8"))
        pairs = {
            "join_receipt_manifest_hash": (receipt.get("manifest_hash"), manifest_path),
            "join_receipt_label_hash": (receipt.get("operator_label_hash"), label_path),
            "join_receipt_score_hash": (receipt.get("score_hash"), source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_SCORES.jsonl"),
            "join_receipt_resolution_hash": (receipt.get("resolution_hash"), source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION.jsonl"),
        }
        for name, (claimed, target) in pairs.items():
            actual = sha256_file(target) if target.is_file() else ""
            checks.append(_check(name, claimed == actual and actual != "", claimed or ""))
    draw_path = source / "RESIDUAL_THRESHOLD_V2_SURFACE_DRAW_RECEIPT.json"
    if draw_path.is_file() and manifest_path.is_file():
        draw = json.loads(draw_path.read_text(encoding="utf-8"))
        checks.append(_check(
            "draw_receipt_measurement_hash",
            draw.get("measurement_manifest_sha256") == measurement_hash,
            draw.get("measurement_manifest_sha256", ""),
        ))
        checks.append(_check(
            "draw_receipt_manifest_hash",
            draw.get("calibration_manifest_sha256") == sha256_file(manifest_path),
            draw.get("calibration_manifest_sha256", ""),
        ))
    direction_path = source / "RESIDUAL_THRESHOLD_V2_DIRECTION_ANALYSIS.json"
    if direction_path.is_file() and join_path.is_file():
        direction = json.loads(direction_path.read_text(encoding="utf-8"))
        checks.append(_check(
            "direction_join_hash",
            direction.get("source_support_join_hash") == sha256_file(join_path),
            direction.get("source_support_join_hash", ""),
        ))
    resolution_receipt = source / "RESIDUAL_THRESHOLD_V2_CALIBRATION_RESOLUTION_RECEIPT.json"
    if resolution_receipt.is_file():
        payload = json.loads(resolution_receipt.read_text(encoding="utf-8"))
        parents = payload.get("parent_rows")
        ready = payload.get("residual_ready_rows")
        unknown = payload.get("unknown_rows")
        checks.append(_check(
            "resolution_parent_totals",
            isinstance(parents, list) and len(parents) == 200 and ready + unknown == 200,
            f"parents={len(parents) if isinstance(parents, list) else 'invalid'} ready={ready} unknown={unknown}",
        ))
    return checks


def evidence_hashes(source: Path) -> dict[str, str]:
    if not source.is_dir():
        return {}
    return {
        path.name: sha256_file(path)
        for path in sorted(source.iterdir())
        if path.is_file() and path.name.startswith("RESIDUAL_THRESHOLD_")
    }


def validate_directory(source: Path, schemas: dict[str, dict] | None = None) -> dict:
    loaded = schemas or load_schemas()
    registry = schema_registry(loaded)
    before = evidence_hashes(source)
    results = []
    skipped = []
    if source.is_dir():
        for path in sorted(source.iterdir()):
            if not path.is_file() or not path.name.startswith("RESIDUAL_THRESHOLD_"):
                continue
            schema_name = classify(path.name)
            if schema_name is None:
                skipped.append(path.name)
                continue
            results.append(validate_artifact(path, schema_name, loaded, registry))
        semantic = semantic_checks(source)
    else:
        semantic = [_check("private_reserve", False, "reserve is absent")]
    after = evidence_hashes(source)
    changed = sorted(name for name, digest in before.items() if after.get(name) != digest)
    schema_gaps = [row["artifact"] for row in results if row["status"] != PASS]
    semantic_gaps = [row["check"] for row in semantic if row["status"] != PASS]
    if changed:
        outcome = SEMANTIC_GAP
    elif schema_gaps:
        outcome = GAP
    elif semantic_gaps:
        outcome = SEMANTIC_GAP
    else:
        outcome = "HISTORICAL_VALIDATION_COMPLETE"
    return {
        "authorization": AUTHORIZATION,
        "calibration_evidence_modified": bool(changed),
        "changed_artifacts": changed,
        "historical_artifact_mutated": False,
        "mode": "VALIDATE_ONLY",
        "outcome": outcome,
        "results": results,
        "schema_conformance_gaps": schema_gaps,
        "scientific_remediation": False,
        "semantic": semantic,
        "semantic_conformance_gaps": semantic_gaps,
        "skipped_not_applicable": skipped,
        "threshold_decision_emitted": any(row["schema"] == "threshold-decision.schema.json" for row in results),
        "threshold_redesign": False,
        "training_authorized": False,
    }


def render_report(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def write_public_report(report: dict) -> None:
    if "hlx-private" in str(REPORT_PATH) or REPORT_PATH.name != "CONTRACT_VALIDATION.json":
        raise RuntimeError("contract report path is not the public schema directory")
    REPORT_PATH.write_text(render_report(report), encoding="utf-8")


def main() -> None:
    report = validate_directory(SOURCE)
    if "--write" in sys.argv:
        write_public_report(report)
    print(render_report(report))


if __name__ == "__main__":
    main()
