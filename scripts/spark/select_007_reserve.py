"""Fresh SELECT-007 reserve from the sealed Wiktionary sense-label recipe.

One readiness pass. It does not create a source-design, admission, loader,
or launch-authorization state, and it does not train.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(ROOT / "scripts/shadow"))
sys.path.insert(0, str(ROOT / "scripts/spark"))

import select_006_reserve_acquire_v2 as acq  # noqa: E402
from hyperlexical.eval_routing import (  # noqa: E402
    UNBIND_CLEAN_DERIVATION,
    contract_validation,
    derive_batch,
)
from hyperlexical.eval_settlement import commit_settlement, load_logged_ids, settle  # noqa: E402
from hyperlexical.export import _unbind_dual_scheme_rows  # noqa: E402
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402
from hyperlexical.identity_ledger import IdentityLedger  # noqa: E402
from hyperlexical.select_006_reserve_acquisition import (  # noqa: E402
    exclusion_reason,
    forbidden_training,
    metric_surface,
)
from hyperlexical.select_006_reserve_acquisition_v2 import (  # noqa: E402
    LABEL_AMBIGUOUS,
    LABEL_NOT_AUTHORIZED,
    TEMPLATE_NAMES,
    qualifying_sense,
    search_query,
)
from hyperlexical.select_006_reserve_source_design_v2 import (  # noqa: E402
    DIRECT_LABELS,
    DISCOVERY_PER_FAMILY,
    TARGET_FAMILIES,
    blind_surface_errors,
    canonical_json,
    named_target_family,
    review_surface_row,
    sha256_text,
)
from hyperlexical.select_007 import (  # noqa: E402
    EXPERIMENT_ID,
    LEDGER_EVENTS_BEFORE,
    LEDGER_PROJECTION_BEFORE,
    SELECT_006_ID,
)
from hyperlexical.soft_ceiling import clean_surface  # noqa: E402

DEST = Path("/home/morpheus/hlx-private/exp-20260929-select-007/reserve-001")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
EXPORT = Path("/home/morpheus/hlx-private/d1-spark-tree-20260924T213846Z/morph78-train-export.jsonl")
SELECT_006_RAW = Path(
    "/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-002/RAW_CANDIDATES.jsonl"
)
SELECT_006_DECISIONS = Path(
    "/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-002/DECISIONS.jsonl"
)
SETTLEMENT_LOG = LEDGER / "settlement" / "events.jsonl"
SCAN_CAP = 240
BATCH_ID = "HLX-EVAL-RESERVE-SELECT-007-001"
OPERATOR = "Hyperlex Cloud Agent"
SETTLED_AT = "2026-09-29T09:30:00Z"
SELECT_005_ID = "HLX-EXP-2026-09-27-SELECT-005"


def decision_for(raw: dict[str, Any]) -> dict[str, Any]:
    """The sealed label rule. A score is not an input."""
    if raw.get("unbind_clean_derivation"):
        family = "none"
        decision = "NONE"
        attest = "INFERRED"
    else:
        family = named_target_family(list(raw.get("sense_label_arguments") or []))
        if family not in TARGET_FAMILIES:
            raise SystemExit(f"{LABEL_NOT_AUTHORIZED}: {raw.get('candidate_id')}")
        decision = "ACCEPT"
        attest = "OBSERVED"
    return {
        "attest": attest,
        "decision": decision,
        "function": None,
        "register": None,
        "row_id": raw["candidate_id"],
        "semantic_family": family,
        "text_hash": raw["normalized_hash"],
    }


def replay_select_006_decisions() -> None:
    """The rule must reproduce the sealed SELECT-006 decisions before a new fetch."""
    raw_rows = acq._read_jsonl(SELECT_006_RAW)
    decisions = acq._read_jsonl(SELECT_006_DECISIONS)
    produced = [decision_for(row) for row in raw_rows]
    if produced != decisions:
        raise SystemExit("SELECT-006 decision replay failed")


def _rows(pages: list[dict[str, Any]], blocked: dict[str, str], train_rows: list[dict[str, Any]]):
    exclusions: Counter[str] = Counter()
    emitted: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    def consider(row: dict[str, Any]) -> None:
        digest = row["normalized_hash"]
        reason = exclusion_reason(digest, blocked)
        if reason is None and digest in emitted:
            reason = "DUPLICATE_IDENTITY"
        if reason:
            exclusions[reason] += 1
            return
        emitted[digest] = row
        rows.append(row)

    for page in pages:
        title = str(page["headword"])
        consider(
            {
                "candidate_id": "s007c-" + sha256_text(page["page_url"])[:16],
                "discovery_label": page["discovery_label"],
                "english_entry_text": page["english_entry_text"],
                "exact_definition_line": page["exact_definition_line"],
                "exact_definition_prose": page["exact_definition_prose"],
                "headword": title,
                "normalized_hash": normalized_text_sha256(title),
                "normalized_text": title,
                "page_url": page["page_url"],
                "part_of_speech": page.get("part_of_speech"),
                "provenance_status": "COMPLETE",
                "revision_id": page["revision_id"],
                "revision_sha1": page["revision_sha1"],
                "revision_timestamp": page["revision_timestamp"],
                "rights": "CC-BY-SA",
                "role_scheme": None,
                "sense_label_arguments": list(page["sense_label_arguments"]),
                "source_family": "wiktionary_labeled_sense",
                "source_lemma_tokens": [],
                "source_url": page["source_url"],
                "unbind_clean_derivation": None,
            }
        )
        tokens = [part for part in title.split(" ") if part]
        if len(tokens) < 2:
            continue
        built = _unbind_dual_scheme_rows(
            title,
            tokens,
            lineage="none",
            stage="select007",
            epistemic="INFERRED",
            pos_provenance="source_lemma_tokens",
            type_provenance="source_lemma_tokens",
            license="CC-BY-SA",
        )
        kept, _accounting = clean_surface(built, train_rows=train_rows)
        kept_ids = {id(item) for item in kept}
        for item in built:
            if id(item) not in kept_ids:
                exclusions["UNBIND_NOT_CLEAN"] += 1
                continue
            text = str(item.get("text") or "")
            scheme = str(item.get("role_scheme") or "")
            consider(
                {
                    "candidate_id": "s007u-" + scheme[:3] + "-" + sha256_text(page["page_url"] + scheme)[:16],
                    "discovery_label": page["discovery_label"],
                    "english_entry_text": page["english_entry_text"],
                    "exact_definition_line": None,
                    "exact_definition_prose": None,
                    "headword": title,
                    "normalized_hash": normalized_text_sha256(text),
                    "normalized_text": text,
                    "page_url": page["page_url"],
                    "part_of_speech": None,
                    "provenance_status": "COMPLETE",
                    "revision_id": page["revision_id"],
                    "revision_sha1": page["revision_sha1"],
                    "revision_timestamp": page["revision_timestamp"],
                    "rights": "CC-BY-SA",
                    "role_scheme": scheme,
                    "sense_label_arguments": [],
                    "source_family": "wiktionary_labeled_sense",
                    "source_lemma_tokens": list(item.get("fillers") or []),
                    "source_url": page["source_url"],
                    "unbind_clean_derivation": UNBIND_CLEAN_DERIVATION,
                }
            )
    return rows, exclusions


def fetch() -> None:
    replay_select_006_decisions()
    if acq._sha_file(LEDGER / "events.jsonl") != LEDGER_EVENTS_BEFORE:
        raise SystemExit("ledger events drifted before SELECT-007 acquisition")
    if acq._sha_file(LEDGER / "ledger.json") != LEDGER_PROJECTION_BEFORE:
        raise SystemExit("ledger projection drifted before SELECT-007 acquisition")
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST, 0o700)
    if (DEST / "RAW_CANDIDATES.jsonl").exists():
        raise SystemExit("SELECT-007 reserve fetch is already frozen")
    acq.SCAN_CAP = SCAN_CAP
    blocked = acq._blocked()
    train_rows = [json.loads(line) for line in EXPORT.read_text(encoding="utf-8").splitlines() if line.strip()]
    queries: list[dict[str, Any]] = []
    kept_titles: dict[str, str] = {}
    pages: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    revision_cache: dict[str, dict[str, Any] | None] = {}
    for family in TARGET_FAMILIES:
        got = 0
        for label in DIRECT_LABELS[family]:
            if got >= DISCOVERY_PER_FAMILY:
                break
            for template in TEMPLATE_NAMES:
                if got >= DISCOVERY_PER_FAMILY:
                    break
                query = search_query(template, label)
                titles = acq._search(template, label)
                queries.append(
                    {
                        "family": family,
                        "kept_before": got,
                        "label": label,
                        "query": query,
                        "titles_seen": len(titles),
                    }
                )
                ordered = [title for title in titles if title.casefold() not in kept_titles]
                cursor = 0
                while cursor < len(ordered) and got < DISCOVERY_PER_FAMILY:
                    chunk = ordered[cursor : cursor + 10]
                    cursor += 10
                    missing = [title for title in chunk if title not in revision_cache]
                    found = acq._fetch_revisions(missing) if missing else {}
                    for title in missing:
                        revision_cache[title] = found.get(title)
                    for title in chunk:
                        if got >= DISCOVERY_PER_FAMILY:
                            break
                        if title.casefold() in kept_titles:
                            continue
                        page = revision_cache.get(title)
                        if page is None:
                            continue
                        content = str(page["content"])
                        if content.lstrip().lower().startswith("#redirect"):
                            exclusions["REDIRECT"] += 1
                            continue
                        sense = qualifying_sense(content)
                        if sense["status"] == "ambiguous":
                            exclusions[LABEL_AMBIGUOUS] += 1
                            continue
                        if sense["status"] != "unique" or sense["target_family"] != family:
                            exclusions[LABEL_NOT_AUTHORIZED] += 1
                            continue
                        if not acq.label_on_line(label, sense["sense_label_arguments"]):
                            exclusions[LABEL_NOT_AUTHORIZED] += 1
                            continue
                        prose = sense["exact_definition_prose"]
                        if not prose:
                            exclusions[LABEL_NOT_AUTHORIZED] += 1
                            continue
                        digest = normalized_text_sha256(title)
                        reason = exclusion_reason(digest, blocked)
                        if reason:
                            exclusions[reason] += 1
                            continue
                        url = "https://en.wiktionary.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
                        pages.append(
                            {
                                "discovery_label": label,
                                "english_entry_text": acq._english_text(content),
                                "exact_definition_line": sense["exact_definition_line"],
                                "exact_definition_prose": prose,
                                "headword": title,
                                "page_url": url,
                                "part_of_speech": sense["part_of_speech"],
                                "revision_id": page["revision_id"],
                                "revision_sha1": page["revision_sha1"],
                                "revision_timestamp": page["revision_timestamp"],
                                "sense_label_arguments": list(sense["sense_label_arguments"]),
                                "source_url": url,
                            }
                        )
                        kept_titles[title.casefold()] = family
                        label_counts[label] += 1
                        got += 1
    rows, more = _rows(pages, blocked, train_rows)
    exclusions.update(more)
    if not any(row.get("unbind_clean_derivation") for row in rows):
        for family in TARGET_FAMILIES:
            if any(row.get("unbind_clean_derivation") for row in rows):
                break
            extra = 0
            for label in DIRECT_LABELS[family]:
                if any(row.get("unbind_clean_derivation") for row in rows) or extra >= DISCOVERY_PER_FAMILY:
                    break
                for template in TEMPLATE_NAMES:
                    if any(row.get("unbind_clean_derivation") for row in rows) or extra >= DISCOVERY_PER_FAMILY:
                        break
                    titles = acq._search(template, label)
                    queries.append(
                        {
                            "continuation": True,
                            "family": family,
                            "label": label,
                            "query": search_query(template, label),
                            "titles_seen": len(titles),
                        }
                    )
                    ordered = [title for title in titles if title.casefold() not in kept_titles]
                    cursor = 0
                    while cursor < len(ordered) and extra < DISCOVERY_PER_FAMILY:
                        if any(row.get("unbind_clean_derivation") for row in rows):
                            break
                        chunk = ordered[cursor : cursor + 10]
                        cursor += 10
                        missing = [title for title in chunk if title not in revision_cache]
                        found = acq._fetch_revisions(missing) if missing else {}
                        for title in missing:
                            revision_cache[title] = found.get(title)
                        for title in chunk:
                            if extra >= DISCOVERY_PER_FAMILY or any(
                                row.get("unbind_clean_derivation") for row in rows
                            ):
                                break
                            page = revision_cache.get(title)
                            if page is None or title.casefold() in kept_titles:
                                continue
                            content = str(page["content"])
                            if content.lstrip().lower().startswith("#redirect"):
                                continue
                            sense = qualifying_sense(content)
                            if sense["status"] != "unique" or sense["target_family"] != family:
                                continue
                            if not acq.label_on_line(label, sense["sense_label_arguments"]):
                                continue
                            prose = sense["exact_definition_prose"]
                            if not prose or exclusion_reason(normalized_text_sha256(title), blocked):
                                continue
                            url = "https://en.wiktionary.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
                            pages.append(
                                {
                                    "discovery_label": label,
                                    "english_entry_text": acq._english_text(content),
                                    "exact_definition_line": sense["exact_definition_line"],
                                    "exact_definition_prose": prose,
                                    "headword": title,
                                    "page_url": url,
                                    "part_of_speech": sense["part_of_speech"],
                                    "revision_id": page["revision_id"],
                                    "revision_sha1": page["revision_sha1"],
                                    "revision_timestamp": page["revision_timestamp"],
                                    "sense_label_arguments": list(sense["sense_label_arguments"]),
                                    "source_url": url,
                                }
                            )
                            kept_titles[title.casefold()] = family
                            label_counts[label] += 1
                            extra += 1
                            rows, added = _rows(pages, blocked, train_rows)
                            exclusions.update(added)
    rows, more = _rows(pages, blocked, train_rows)
    exclusions.update(more)
    if not rows:
        raise SystemExit("REVIEW_SURFACE_EMPTY")
    review = [review_surface_row(row) for row in rows]
    errors = blind_surface_errors(review)
    if errors:
        raise SystemExit(f"REVIEW_SURFACE_EMPTY: {errors[0]}")
    decisions = [decision_for(row) for row in rows]
    raw_sha = acq._jsonl(DEST / "RAW_CANDIDATES.jsonl", rows)
    review_sha = acq._jsonl(DEST / "REVIEW_SURFACE.jsonl", review)
    decisions_sha = acq._jsonl(DEST / "DECISIONS.jsonl", decisions)
    summary = {
        "decisions_sha256": decisions_sha,
        "discovered_pages": len(pages),
        "discovery_per_family": DISCOVERY_PER_FAMILY,
        "exclusion_counts": dict(exclusions),
        "experiment_id": EXPERIMENT_ID,
        "fetched_titles": len(revision_cache),
        "label_counts": dict(label_counts),
        "provenance_authority": "mediawiki action=query prop=revisions rvprop=ids|timestamp|sha1|content",
        "queries": queries,
        "raw_sha256": raw_sha,
        "review_count": len(review),
        "review_sha256": review_sha,
        "rights_cleared": sum(1 for row in rows if row["rights"] == "CC-BY-SA"),
        "scan_cap_per_query": SCAN_CAP,
        "schema": "hyperlex.select_007_fetch_summary.v1",
        "select_006_decision_replay": "PASS",
        "select_006_reserve_reused": False,
        "source_family": "wiktionary_labeled_sense",
        **forbidden_training(),
    }
    acq._write(DEST / "FETCH_SUMMARY.json", canonical_json(summary))
    sys.stdout.write(canonical_json({"discovered_pages": len(pages), "label_counts": dict(label_counts)}) + "\n")


def settle_and_bind() -> None:
    if not (DEST / "DECISIONS.jsonl").is_file():
        raise SystemExit("SETTLEMENT_FAILURE: decisions are absent")
    if (DEST / "RESERVE_MANIFEST.json").exists():
        raise SystemExit("SETTLEMENT_FAILURE: reserve outcome already frozen")
    raw_rows = acq._read_jsonl(DEST / "RAW_CANDIDATES.jsonl")
    review = acq._read_jsonl(DEST / "REVIEW_SURFACE.jsonl")
    decisions = acq._read_jsonl(DEST / "DECISIONS.jsonl")
    if blind_surface_errors(review):
        raise SystemExit("REVIEW_SURFACE_EMPTY: review surface is not blind")
    if [decision_for(row) for row in raw_rows] != decisions:
        raise SystemExit("SETTLEMENT_FAILURE: decisions drifted from the label rule")
    raw_by_id = {row["candidate_id"]: row for row in raw_rows}
    streams = [
        {
            "family_hint_not_a_label": None,
            "normtext_sha256": raw_by_id[row["candidate_id"]]["normalized_hash"],
            "row_key": row["candidate_id"],
            "source_type": "wiktionary_labeled_sense",
            "text": raw_by_id[row["candidate_id"]]["normalized_text"],
        }
        for row in review
    ]
    settled = settle(
        streams,
        decisions,
        batch_id=BATCH_ID,
        operator=OPERATOR,
        provenance="SELECT-007 labeled-sense reserve.",
        settled_at=SETTLED_AT,
        prior_ids=load_logged_ids(SETTLEMENT_LOG),
    )
    records = settled["records"]
    pairs = []
    for record in records:
        raw = raw_by_id[record["row_id"]]
        if raw["rights"] != "CC-BY-SA" or not raw["revision_sha1"] or not raw["revision_id"]:
            raise SystemExit("PROVENANCE_FAILURE")
        task = "unbind" if raw.get("unbind_clean_derivation") == UNBIND_CLEAN_DERIVATION else "classify"
        pairs.append(
            (
                record,
                {
                    "normalized_identity": raw["normalized_hash"],
                    "provenance_state": raw["provenance_status"],
                    "row_id": raw["candidate_id"],
                    "source_identity": raw["source_url"],
                    "task": task,
                    "unbind_clean": task == "unbind",
                    "unbind_clean_derivation": raw.get("unbind_clean_derivation"),
                },
            )
        )
    validation = contract_validation(pairs)
    if validation["state"] != "ROUTING_VALIDATION_COMPLETE" or validation["determinism"] != "IDENTICAL":
        raise SystemExit(f"ROUTING_FAILURE: {validation['state']}")
    routed = derive_batch(pairs)
    routing_sha = acq._jsonl(DEST / "ROUTING_RECORDS.jsonl", routed)
    surface = metric_surface(routed)
    if not all(surface["computable"].values()) or not surface["floors_met"]:
        acq._write(
            DEST / "METRIC_COMPUTABILITY.json",
            canonical_json(
                {
                    "computable": surface["computable"],
                    "experiment_id": EXPERIMENT_ID,
                    "floors_met": surface["floors_met"],
                    "schema": "hyperlex.select_007_metric_computability.v1",
                    "slice_counts": surface["slice_counts"],
                }
            ),
        )
        raise SystemExit("RESERVE_METRIC_SURFACE_INSUFFICIENT")
    computability = {
        "computable": {**surface["computable"], "predicted_none_rate": surface["slice_counts"]["classify"] >= 1},
        "experiment_id": EXPERIMENT_ID,
        "floors_met": surface["floors_met"],
        "head_mapped_non_none": surface["head_mapped_non_none"],
        "schema": "hyperlex.select_007_metric_computability.v1",
        "slice_counts": surface["slice_counts"],
    }
    if not computability["computable"]["predicted_none_rate"]:
        raise SystemExit("METRIC_NONCOMPUTABLE: predicted_none_rate")
    receipt = commit_settlement(
        records,
        settled["receipt"],
        log_path=SETTLEMENT_LOG,
        receipt_path=DEST / "SETTLEMENT_RECEIPT.json",
    )
    computability_sha = acq._write(DEST / "METRIC_COMPUTABILITY.json", canonical_json(computability))
    blocked = acq._blocked()
    overlaps: Counter[str] = Counter()
    for record in records:
        reason = exclusion_reason(str(record["text_hash"]), blocked)
        if reason and reason != "SETTLED_SURFACE":
            overlaps[reason] += 1
    if overlaps:
        raise SystemExit(f"EVALUATION_LEAKAGE: {dict(overlaps)}")
    isolation = {
        "experiment_id": EXPERIMENT_ID,
        "overlaps": {},
        "result": "PASS",
        "schema": "hyperlex.select_007_isolation_report.v1",
        "select_006_reserve_reuse": "FORBIDDEN",
    }
    provenance = {
        "experiment_id": EXPERIMENT_ID,
        "provenance_complete": len(raw_rows),
        "result": "PASS",
        "rights": "CC-BY-SA",
        "schema": "hyperlex.select_007_provenance_report.v1",
    }
    isolation_sha = acq._write(DEST / "ISOLATION_REPORT.json", canonical_json(isolation))
    provenance_sha = acq._write(DEST / "PROVENANCE_REPORT.json", canonical_json(provenance))
    eligible = [row for row in routed if row["routing_status"] == "ELIGIBLE"]
    manifest_rows = []
    for row in eligible:
        raw = raw_by_id[row["row_id"]]
        manifest_rows.append(
            {
                "class": row["class"],
                "lineage": row["lineage"],
                "normalized_text_sha256": row["normalized_identity"],
                "rights": row["rights_state"],
                "row_id": row["row_id"],
                "slices": row["slices"],
                "source_identity": row["source_identity"],
                "source_revision_id": raw["revision_id"],
                "source_revision_sha1": raw["revision_sha1"],
                "task": row["task"],
                "unbind_clean": row["unbind_clean"],
            }
        )
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "head_mapped_non_none": surface["head_mapped_non_none"],
        "rows": manifest_rows,
        "schema": "hyperlex.select_007_reserve_manifest.v1",
        "slice_counts": surface["slice_counts"],
    }
    manifest_sha = acq._write(DEST / "RESERVE_MANIFEST.json", canonical_json(manifest))
    events_before = acq._sha_file(LEDGER / "events.jsonl")
    projection_before = acq._sha_file(LEDGER / "ledger.json")
    ledger = IdentityLedger.load(LEDGER)
    prior_count = len(ledger.events)
    select005_before = len(ledger.active_reserve_records(SELECT_005_ID))
    select006_before = len(ledger.active_reserve_records(SELECT_006_ID))
    for row in manifest_rows:
        if exclusion_reason(row["normalized_text_sha256"], acq._blocked()) not in (None, "SETTLED_SURFACE"):
            raise SystemExit(f"LEDGER_BINDING_CONFLICT: {row['row_id']}")
        ledger.observe(
            row["normalized_text_sha256"],
            source_artifact=str(DEST / "RESERVE_MANIFEST.json"),
            row_ids=[row["row_id"]],
            labels=[
                {
                    "class": row["class"],
                    "lineage": row["lineage"],
                    "task": row["task"],
                    **({"unbind_clean": True} if row["unbind_clean"] else {}),
                }
            ],
            provenance="SELECT-007 reserve manifest",
            experiment_id=EXPERIMENT_ID,
        )
        ledger.transition(
            row["normalized_text_sha256"],
            "EVAL_RESERVE",
            source_artifact=str(DEST / "RESERVE_MANIFEST.json"),
            provenance="SELECT-007 reserve binding",
        )
    if ledger.row_id_collisions:
        raise SystemExit("LEDGER_BINDING_CONFLICT: row id collision")
    ledger.persist_append(LEDGER, prior_count)
    replay = IdentityLedger.load(LEDGER)
    if len(replay.active_reserve_records(SELECT_005_ID)) != select005_before:
        raise SystemExit("LEDGER_BINDING_CONFLICT: SELECT-005 bindings changed")
    if len(replay.active_reserve_records(SELECT_006_ID)) != select006_before:
        raise SystemExit("LEDGER_BINDING_CONFLICT: SELECT-006 bindings changed")
    bound = replay.active_reserve_records(EXPERIMENT_ID)
    if len(bound) != len(manifest_rows):
        raise SystemExit(f"LEDGER_BINDING_CONFLICT: bound {len(bound)} of {len(manifest_rows)}")
    counts = replay.active_reserve_counts(EXPERIMENT_ID)
    events_after = acq._sha_file(LEDGER / "events.jsonl")
    projection_after = acq._sha_file(LEDGER / "ledger.json")
    binding = {
        "counts": counts,
        "experiment_id": EXPERIMENT_ID,
        "identities": len(bound),
        "ledger_dir": str(LEDGER),
        "ledger_events_sha256": events_after,
        "ledger_projection_sha256": projection_after,
        "lifecycle": "EVAL_RESERVE",
        "schema": "hyperlex.reserve_binding.v1",
        "scored": False,
    }
    binding_sha = acq._write(DEST / "RESERVE_BINDING.json", canonical_json(binding))
    reserve_receipt = {
        "binding_sha256": binding_sha,
        "bound_identities": len(bound),
        "computability_sha256": computability_sha,
        "experiment_id": EXPERIMENT_ID,
        "isolation_sha256": isolation_sha,
        "ledger_events_sha256_after": events_after,
        "ledger_events_sha256_before": events_before,
        "ledger_projection_sha256_after": projection_after,
        "ledger_projection_sha256_before": projection_before,
        "ledger_replay": "PASS",
        "manifest_sha256": manifest_sha,
        "metric_surface": surface,
        "provenance_sha256": provenance_sha,
        "routing_sha256": routing_sha,
        "schema": "hyperlex.select_007_reserve_receipt.v1",
        "select_005_active_reserve_unchanged": select005_before,
        "select_006_active_reserve_unchanged": select006_before,
        "settlement_receipt_sha256": receipt["receipt_sha256"],
        "state": "RESERVE_FROZEN",
        **forbidden_training(),
    }
    acq._write(DEST / "RESERVE_RECEIPT.json", canonical_json(reserve_receipt))
    sys.stdout.write(canonical_json(reserve_receipt) + "\n")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"fetch", "settle"}:
        raise SystemExit("usage: select_007_reserve.py fetch|settle")
    if sys.argv[1] == "fetch":
        fetch()
    else:
        settle_and_bind()


if __name__ == "__main__":
    main()
