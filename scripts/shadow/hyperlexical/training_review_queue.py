"""Human review queue for legacy rows. Does not invent rights or label approval.

Builds digest-keyed worksheets from legacy JSONL and materializes an intake
metadata sidecar only from decisions with confirm_rights=true and
confirm_labels=true. OBSERVED class, license strings, and filenames never
auto-approve.

Provenance: Hyperlex Spec 007 WF-002 review queue helper.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from .layout import FAMILIES
from .training_contracts import digest, validate_dataset
from .training_intake import convert, parse_json

PARTITION_MAP = {"train": "train", "val": "dev", "dev": "dev", "test": "test"}


def _text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _preview(text: str, limit: int = 160) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def _suggest_source_kind(row: dict) -> str:
    prov = json.dumps(row.get("provenance") or {}, sort_keys=True).lower()
    if "wiktionary" in prov or "wikipedia" in prov:
        return "citation"
    typology = row.get("typology") or []
    if isinstance(typology, list) and "vernacular" in typology:
        return "term"
    return "context"


def _suggest_partition(row: dict) -> str:
    return PARTITION_MAP.get(str(row.get("split") or "").strip(), "dev")


def _draft_family(row: dict) -> dict:
    lineage = row.get("lineage")
    if lineage in FAMILIES and lineage != "none":
        return {
            "status": "unreviewed",
            "values": [lineage],
            "loss_mask": False,
            "method": "legacy_lineage_suggestion_only",
            "reviewer": None,
        }
    return {
        "status": "unreviewed",
        "values": [],
        "loss_mask": False,
        "method": "unreviewed",
        "reviewer": None,
    }


def _draft_structure(row: dict) -> tuple[dict, list]:
    roles = row.get("roles") or []
    fillers = row.get("fillers") or []
    text = row.get("text") or ""
    spans: list[dict] = []
    if (
        isinstance(roles, list)
        and isinstance(fillers, list)
        and roles
        and len(roles) == len(fillers)
        and all(isinstance(x, str) and x for x in fillers)
    ):
        cursor = 0
        for i, (role, filler) in enumerate(zip(roles, fillers, strict=True)):
            start = text.find(filler, cursor)
            if start < 0:
                spans = []
                break
            end = start + len(filler)
            spans.append(
                {
                    "occurrence_id": f"sug-{i}",
                    "start": start,
                    "end": end,
                    "text": filler,
                    "role": role if isinstance(role, str) and role.strip() else f"pos_{i}",
                }
            )
            cursor = end
    label = {
        "status": "unreviewed",
        "values": [s["role"] for s in spans] if spans else [],
        "loss_mask": False,
        "method": "legacy_span_suggestion_only" if spans else "unreviewed",
        "reviewer": None,
    }
    return label, spans


def build_queue_item(row: dict, *, line: int, record_sha256: str) -> dict:
    if not isinstance(row, dict) or not isinstance(row.get("text"), str) or not row["text"].strip():
        raise ValueError("INVALID_ROW")
    text = row["text"]
    key = digest(row)
    family = _draft_family(row)
    structure, spans = _draft_structure(row)
    source_id = f"src-{key[:12]}"
    example_id = f"ex-{key[:12]}"
    draft = {
        "source": {
            "version": "source.v1",
            "source_id": source_id,
            "raw_text": text,
            "text_sha256": _text_sha(text),
            "source_kind": _suggest_source_kind(row),
            "rights_status": "unreviewed",
            "rights_reference": str(row.get("license") or "MISSING_RIGHTS_REFERENCE"),
            "provenance_reference": json.dumps(row.get("provenance") or {}, sort_keys=True),
        },
        "annotation": {
            "version": "annotation.v1",
            "example_id": example_id,
            "source_id": source_id,
            "group_ids": [f"grp-{key[:12]}"],
            "offset_unit": "unicode_codepoint",
            "ontology_version": "proposal-v1",
            "spans": spans,
            "labels": {"family": family, "structure": structure},
        },
        "partition": _suggest_partition(row),
    }
    return {
        "line": line,
        "record_sha256": record_sha256,
        "canonical_row_sha256": key,
        "legacy_class": row.get("class"),
        "legacy_license": row.get("license"),
        "legacy_task": row.get("task"),
        "legacy_split": row.get("split"),
        "legacy_lineage": row.get("lineage"),
        "text_preview": _preview(text),
        "text_sha256": _text_sha(text),
        "required_actions": [
            "Replace rights_reference with authoritative source-use evidence.",
            "Set rights_status=approved only after that evidence is real.",
            "Per-head review family/structure; set status=reviewed with reviewer id.",
            "Correct spans/occurrence_ids; suggestions are not final.",
            "Confirm partition under a frozen group-aware split policy.",
            "Set confirm_rights=true and confirm_labels=true only after human review.",
        ],
        "auto_approve_forbidden": True,
        "observed_is_not_rights": True,
        "draft": draft,
        "confirm_rights": False,
        "confirm_labels": False,
        "decision": "PENDING_REVIEW",
    }


def build_review_queue(payload: bytes) -> dict:
    text = payload.decode("utf-8-sig")
    items: list[dict] = []
    quarantine: list[dict] = []
    seen: set[str] = set()
    reasons: Counter = Counter()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        record_sha = hashlib.sha256(line.encode("utf-8")).hexdigest()
        try:
            row = parse_json(line)
            if not isinstance(row, dict):
                raise ValueError("NOT_AN_OBJECT")
            key = digest(row)
            if key in seen:
                raise ValueError("DUPLICATE_ROW")
            seen.add(key)
            items.append(build_queue_item(row, line=number, record_sha256=record_sha))
        except Exception as exc:
            reason = str(exc)
            allowed = {"NOT_AN_OBJECT", "DUPLICATE_ROW", "INVALID_ROW"}
            if reason not in allowed:
                reason = "MALFORMED_JSON"
            quarantine.append({"line": number, "record_sha256": record_sha, "reason": reason})
            reasons[reason] += 1
    triage = Counter(str(item.get("legacy_license") or "unknown") for item in items)
    report = {
        "version": "training_review_queue.v1",
        "status": "QUEUE_BUILT",
        "input_sha256": hashlib.sha256(payload).hexdigest(),
        "n_records": len(items) + len(quarantine),
        "n_queue": len(items),
        "n_quarantined": len(quarantine),
        "triage_by_license": dict(triage),
        "quarantine_reasons": dict(reasons),
        "training_ready": False,
        "name_gate": False,
        "note": (
            "Worksheet only. No rights or label approvals are granted. "
            "Apply confirmed decisions to build a sidecar; never invent approvals."
        ),
    }
    return {"report": report, "queue": items, "quarantine": quarantine}


def materialize_sidecar_entry(item: dict) -> dict:
    if not isinstance(item, dict):
        raise TypeError("decision item must be an object")
    if item.get("confirm_rights") is not True or item.get("confirm_labels") is not True:
        raise ValueError("unconfirmed decision cannot enter sidecar")
    draft = item.get("draft")
    if not isinstance(draft, dict) or set(draft) != {"source", "annotation", "partition"}:
        raise ValueError("decision draft malformed")
    source = draft["source"]
    if source.get("rights_status") != "approved":
        raise ValueError("confirmed rights require rights_status=approved")
    ref = source.get("rights_reference")
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError("approved rights require non-empty rights_reference")
    banned = {
        "MISSING_RIGHTS_REFERENCE",
        "operator-local",
        "operator-attested",
        "operator-attested; labels OBSERVED",
        "operator-local; labels INFERRED",
        "operator-local; labels OBSERVED",
    }
    if ref.strip() in banned or ref.strip().startswith("operator-local"):
        raise ValueError("rights_reference is not authoritative")
    labels = draft["annotation"].get("labels") or {}
    active = False
    for head, label in labels.items():
        if label.get("loss_mask"):
            active = True
            if label.get("status") != "reviewed":
                raise ValueError(f"active {head} label must be reviewed")
            if not isinstance(label.get("reviewer"), str) or not label["reviewer"].strip():
                raise ValueError(f"active {head} label requires reviewer id")
    if not active:
        raise ValueError("confirmed labels require at least one active reviewed head")
    ann = draft["annotation"]
    if ann.get("source_id") != source.get("source_id"):
        raise ValueError("annotation source_id mismatch")
    raw = source.get("raw_text")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("source raw_text required")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != source.get("text_sha256"):
        raise ValueError("source text hash mismatch")
    partition = draft["partition"]
    if partition not in {"train", "dev", "test"}:
        raise ValueError("partition must be train|dev|test")
    candidate = {
        "sources": [source],
        "annotations": [ann],
        "split": {
            "version": "split.v1",
            "split_id": "intake-review-v1",
            "assignments": [{"example_id": ann["example_id"], "partition": partition}],
        },
    }
    try:
        validate_dataset(candidate)
    except ValueError as exc:
        raise ValueError(f"dataset validation failed: {exc}") from exc
    return {"source": source, "annotation": ann, "partition": partition}


def apply_confirmed_decisions(queue_items: list, decisions: list) -> dict:
    by_key = {
        item["canonical_row_sha256"]: item
        for item in queue_items
        if isinstance(item, dict) and "canonical_row_sha256" in item
    }
    sidecar: dict = {}
    skipped: list[dict] = []
    for decision in decisions:
        if not isinstance(decision, dict):
            skipped.append({"reason": "NOT_AN_OBJECT"})
            continue
        key = decision.get("canonical_row_sha256")
        if key not in by_key:
            skipped.append({"canonical_row_sha256": key, "reason": "UNKNOWN_DIGEST"})
            continue
        merged = json.loads(json.dumps(by_key[key]))
        if "draft" in decision:
            merged["draft"] = decision["draft"]
        merged["confirm_rights"] = decision.get("confirm_rights", False)
        merged["confirm_labels"] = decision.get("confirm_labels", False)
        try:
            sidecar[key] = materialize_sidecar_entry(merged)
        except (TypeError, ValueError) as exc:
            skipped.append({"canonical_row_sha256": key, "reason": str(exc)})
    report = {
        "version": "training_review_apply.v1",
        "status": "SIDECAR_PARTIAL" if skipped or not sidecar else "SIDECAR_READY_FOR_INTAKE",
        "n_decisions": len(decisions),
        "n_sidecar_entries": len(sidecar),
        "n_skipped": len(skipped),
        "training_ready": False,
        "name_gate": False,
        "note": "Sidecar entries are intake evidence only; preparation/verify still required.",
    }
    return {"report": report, "metadata": sidecar, "skipped": skipped}


def _priority_cohort(item: dict) -> str:
    """Human review order only. Never grants rights or label approval."""
    legacy_class = str(item.get("legacy_class") or "")
    license_ = str(item.get("legacy_license") or "")
    observed = legacy_class == "OBSERVED"
    attested = license_.startswith("operator-attested")
    local = license_.startswith("operator-local")
    if observed and attested:
        return "P1_observed_attested"
    if observed and not local:
        return "P2_observed_non_local"
    if observed and local:
        return "P3_observed_operator_local"
    if attested:
        return "P4_inferred_attested"
    return "P5_inferred_operator_local"


def _write_triage_artifacts(directory: Path, result: dict) -> dict:
    queue = result["queue"]
    by_class = Counter(str(i.get("legacy_class") or "unknown") for i in queue)
    by_split = Counter(str(i.get("legacy_split") or "unknown") for i in queue)
    by_task = Counter(str(i.get("legacy_task") or "unknown") for i in queue)
    by_lineage = Counter(str(i.get("legacy_lineage") or "unknown") for i in queue)
    by_cohort: Counter = Counter()
    cohorts: dict[str, list] = {}
    for item in queue:
        cohort = _priority_cohort(item)
        by_cohort[cohort] += 1
        cohorts.setdefault(cohort, []).append(item)

    worksheets = directory / "worksheets"
    worksheets.mkdir(exist_ok=False)
    for name, items in sorted(cohorts.items()):
        slim = [
            {
                "canonical_row_sha256": it["canonical_row_sha256"],
                "line": it["line"],
                "legacy_class": it.get("legacy_class"),
                "legacy_license": it.get("legacy_license"),
                "legacy_lineage": it.get("legacy_lineage"),
                "legacy_split": it.get("legacy_split"),
                "legacy_task": it.get("legacy_task"),
                "text_preview": it.get("text_preview"),
                "priority_cohort": name,
                "confirm_rights": False,
                "confirm_labels": False,
                "decision": "PENDING_REVIEW",
            }
            for it in items
        ]
        (worksheets / f"{name}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in slim),
            encoding="utf-8",
        )

    for name in ("P1_observed_attested", "P2_observed_non_local", "P3_observed_operator_local"):
        items = cohorts.get(name) or []
        if not items:
            continue
        template = [
            {
                "canonical_row_sha256": item["canonical_row_sha256"],
                "confirm_rights": False,
                "confirm_labels": False,
                "priority_cohort": name,
                "draft": item["draft"],
                "decision": "PENDING_REVIEW",
                "reviewer_notes": "",
            }
            for item in items[:25]
        ]
        (directory / f"decisions_template_{name}_first25.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in template),
            encoding="utf-8",
        )

    triage = {
        "version": "training_review_triage.v1",
        "training_ready": False,
        "name_gate": False,
        "n_queue": len(queue),
        "by_license": dict(result["report"].get("triage_by_license") or {}),
        "by_class": dict(by_class),
        "by_split": dict(by_split),
        "by_task": dict(by_task),
        "by_lineage": dict(by_lineage),
        "by_priority_cohort": dict(sorted(by_cohort.items())),
        "recommended_review_order": [
            "P1_observed_attested",
            "P2_observed_non_local",
            "P3_observed_operator_local",
            "P4_inferred_attested",
            "P5_inferred_operator_local",
        ],
        "note": (
            "Priority cohorts order human attention only. "
            "No cohort grants rights or label approval. "
            "operator-local / OBSERVED never auto-approve."
        ),
    }
    (directory / "triage_summary.json").write_text(
        json.dumps(triage, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return triage


def export_queue_package(directory: Path, result: dict, payload: bytes) -> None:
    directory.mkdir(exist_ok=False)
    (directory / "original.jsonl").write_bytes(payload)
    (directory / "report.json").write_text(
        json.dumps(result["report"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directory / "queue.json").write_text(
        json.dumps(result["queue"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directory / "quarantine.json").write_text(
        json.dumps(result["quarantine"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    template = [
        {
            "canonical_row_sha256": item["canonical_row_sha256"],
            "confirm_rights": False,
            "confirm_labels": False,
            "draft": item["draft"],
            "decision": "PENDING_REVIEW",
        }
        for item in result["queue"][: min(20, len(result["queue"]))]
    ]
    (directory / "decisions_template_first20.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in template),
        encoding="utf-8",
    )
    triage = _write_triage_artifacts(directory, result)
    (directory / "README.txt").write_text(
        "\n".join(
            [
                "Hyperlex review queue package",
                "",
                "Status: QUEUE_BUILT only. training_ready=false. No approvals granted.",
                "",
                "Suggested human order (see triage_summary.json / worksheets/):",
                "  P1_observed_attested -> P2 -> P3 -> P4 -> P5",
                "Priority is attention order only; OBSERVED/operator-local never auto-approve.",
                "",
                "1. Skim triage_summary.json.",
                "2. Open worksheets/<cohort>.jsonl for the next cohort.",
                "3. Fill decisions_template_<cohort>_first25.jsonl or write your own decisions JSONL.",
                "4. Replace rights_reference with authoritative source-use evidence.",
                "5. Set rights_status=approved and per-head reviewed labels with reviewer ids.",
                "6. Set confirm_rights=true and confirm_labels=true only after real review.",
                "7. python -m scripts.shadow.hyperlexical.training_review_queue apply \\",
                "     --queue queue.json --decisions decisions.jsonl --out-metadata metadata.json",
                "8. python -m scripts.shadow.hyperlexical.training_intake --input original.jsonl \\",
                "     --metadata metadata.json --out-dir ../intake-NEW",
                "9. Then training_prepare + verify_preparation into a fresh directory.",
                "",
                "This package does not approve training.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    worksheet_names = sorted(p.name for p in (directory / "worksheets").glob("*.jsonl"))
    file_names = sorted(p.name for p in directory.iterdir() if p.is_file())
    manifest = {
        "version": "training_review_package.v1",
        "input_sha256": result["report"].get("input_sha256"),
        "n_queue": result["report"].get("n_queue"),
        "n_quarantined": result["report"].get("n_quarantined"),
        "training_ready": False,
        "name_gate": False,
        "triage_by_priority_cohort": triage.get("by_priority_cohort"),
        "files": file_names + [f"worksheets/{name}" for name in worksheet_names],
    }
    (directory / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )



def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build", help="Build a review queue from legacy JSONL")
    build.add_argument("--input", type=Path, required=True)
    build.add_argument("--out-dir", type=Path, required=True)

    apply = sub.add_parser("apply", help="Apply confirmed decisions into a metadata sidecar")
    apply.add_argument("--queue", type=Path, required=True)
    apply.add_argument("--decisions", type=Path, required=True)
    apply.add_argument("--out-metadata", type=Path, required=True)

    preview = sub.add_parser("intake-preview", help="Preview intake convert with a sidecar")
    preview.add_argument("--input", type=Path, required=True)
    preview.add_argument("--metadata", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.cmd == "build":
        payload = args.input.read_bytes()
        result = build_review_queue(payload)
        export_queue_package(args.out_dir, result, payload)
        print(json.dumps(result["report"], indent=2, sort_keys=True))
        return 0
    if args.cmd == "apply":
        queue = parse_json(args.queue.read_text(encoding="utf-8"))
        if not isinstance(queue, list):
            raise SystemExit("queue.json must be a list")
        decisions = []
        for line in args.decisions.read_text(encoding="utf-8").splitlines():
            if line.strip():
                decisions.append(parse_json(line))
        result = apply_confirmed_decisions(queue, decisions)
        args.out_metadata.write_text(
            json.dumps(result["metadata"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps({"report": result["report"], "skipped": result["skipped"]}, indent=2, sort_keys=True))
        return 0 if result["metadata"] and not result["skipped"] else 2
    if args.cmd == "intake-preview":
        result = convert(args.input.read_bytes(), args.metadata.read_bytes())
        print(json.dumps(result["report"], indent=2, sort_keys=True))
        return 0 if result["report"].get("n_quarantined", 1) == 0 else 2
    raise SystemExit(2)


if __name__ == "__main__":
    raise SystemExit(main())
