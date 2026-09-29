"""Fetch and, after a separate decision file, settle a SELECT-006 reserve.

``fetch`` stops at a blind review surface. It does not assign labels.
``settle`` reads operator decisions and binds the ledger only when the
frozen floors are met. It does not train.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(ROOT / "scripts/shadow"))

from hyperlexical.export import _unbind_dual_scheme_rows  # noqa: E402
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402
from hyperlexical.identity_ledger import IdentityLedger  # noqa: E402
from hyperlexical.select_006_reserve_acquisition import (  # noqa: E402
    BATCH_ID,
    DISCOVERY_CATEGORIES,
    DISCOVERY_PER_CATEGORY,
    EXPERIMENT_ID,
    FAILURE_BINDING,
    FAILURE_ISOLATION,
    FAILURE_PROVENANCE,
    FAILURE_QUOTA,
    FAILURE_REPLAY,
    FAILURE_REVIEW,
    FAILURE_RIGHTS,
    FAILURE_ROUTING,
    FAILURE_SETTLEMENT,
    FAILURE_SOURCE,
    FAILURE_SURFACE,
    SELECT_005_ID,
    TRANSITION,
    blind_surface_errors,
    canonical_json,
    exclusion_reason,
    extract_primary_gloss,
    forbidden_training,
    frozen_floors,
    metric_surface,
    review_surface_row,
    sha256_text,
)
from hyperlexical.soft_ceiling import clean_surface  # noqa: E402
from hyperlexical.eval_routing import (  # noqa: E402
    UNBIND_CLEAN_DERIVATION,
    contract_validation,
    derive_batch,
)
from hyperlexical.eval_settlement import commit_settlement, load_logged_ids, settle  # noqa: E402

DEST = Path("/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-001")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
EXPORT = Path("/home/morpheus/hlx-private/d1-spark-tree-20260924T213846Z/morph78-train-export.jsonl")
PRIOR_RAW = Path("/home/morpheus/hlx-private/exp-20260927-select-005/source-fetch-001/RAW_CANDIDATES.jsonl")
SETTLEMENT_LOG = LEDGER / "settlement" / "events.jsonl"
V1_LABELS = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001/RESIDUAL_THRESHOLD_V1_CALIBRATION_LABELS.jsonl"
V2_LABELS = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001/RESIDUAL_THRESHOLD_V2_CALIBRATION_LABELS.jsonl"
V2_MEASURE = LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001/RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl"
EXPOSURE = (
    Path("/home/morpheus/hlx-private/heldout-stream/inbox/box-jev-hashes-20260929T012947Z.txt"),
    Path("/home/morpheus/hlx-private/heldout-stream/state/agent-context-exposed-normtext-sha256.txt"),
)
API = "https://en.wiktionary.org/w/api.php"
UA = "HyperlexSelect006Reserve/1.0 (local evaluation reserve; mediawiki provenance)"
OPERATOR = "Hyperlex Cloud Agent"
SETTLED_AT = "2026-09-29T05:40:00Z"


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)
    return sha256_text(text)


def _jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    text = "".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows)
    return _write(path, text)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _api(params: dict[str, str]) -> dict[str, Any]:
    query = urllib.parse.urlencode({"format": "json", "formatversion": "2", **params})
    request = urllib.request.Request(API + "?" + query, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or "error" in payload:
        raise SystemExit(f"{FAILURE_SOURCE}: mediawiki query failed")
    return payload


_EXCLUSION_PRIORITY = {
    "SELECT_005_EVAL_RESERVE": 0,
    "TRAIN_CONSUMED": 1,
    "EVAL_SPENT": 2,
    "EVAL_ABANDONED": 3,
    "SELECT_001_002_BINDING": 4,
    "THRESHOLD_V1_CALIBRATION": 5,
    "THRESHOLD_V2_CALIBRATION": 6,
    "THRESHOLD_V2_MEASUREMENT": 7,
    "EXPOSURE": 8,
    "PRIOR_FETCH_IDENTITY": 9,
    "LEDGER_IDENTITY": 10,
    "SETTLED_SURFACE": 11,
}


def _blocked() -> dict[str, str]:
    found: dict[str, str] = {}

    def put(digest: str, reason: str) -> None:
        if not digest:
            return
        current = found.get(digest)
        if current is None or _EXCLUSION_PRIORITY[reason] < _EXCLUSION_PRIORITY[current]:
            found[digest] = reason

    for path in EXPOSURE:
        for line in path.read_text(encoding="utf-8").splitlines():
            put(line.strip(), "EXPOSURE")
    for row in _read_jsonl(PRIOR_RAW):
        put(str(row.get("normalized_hash") or ""), "PRIOR_FETCH_IDENTITY")
    for row in _read_jsonl(SETTLEMENT_LOG):
        put(str(row.get("text_hash") or ""), "SETTLED_SURFACE")
    for path, reason in (
        (V1_LABELS, "THRESHOLD_V1_CALIBRATION"),
        (V2_LABELS, "THRESHOLD_V2_CALIBRATION"),
        (V2_MEASURE, "THRESHOLD_V2_MEASUREMENT"),
    ):
        for row in _read_jsonl(path):
            put(str(row.get("normalized_text_sha256") or row.get("text_hash") or ""), reason)
    for line in EXPORT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        put(normalized_text_sha256(str(row.get("text") or "")), "TRAIN_CONSUMED")
    ledger = json.loads((LEDGER / "ledger.json").read_text(encoding="utf-8"))
    for record in ledger["identities"]:
        digest = str(record.get("normalized_text_sha256") or "")
        bindings = [str(item) for item in record.get("experiment_bindings") or []]
        if SELECT_005_ID in bindings and record.get("evaluation_reserved"):
            put(digest, "SELECT_005_EVAL_RESERVE")
        elif record.get("training_consumed"):
            put(digest, "TRAIN_CONSUMED")
        elif record.get("evaluation_spent"):
            put(digest, "EVAL_SPENT")
        elif record.get("evaluation_abandoned"):
            put(digest, "EVAL_ABANDONED")
        elif any("SELECT-001" in item or "SELECT-002" in item for item in bindings):
            put(digest, "SELECT_001_002_BINDING")
        elif digest:
            put(digest, "LEDGER_IDENTITY")
    return found


def _prior_titles() -> set[str]:
    titles = set()
    for row in _read_jsonl(PRIOR_RAW):
        url = str(row.get("page_url") or "")
        if "/wiki/" in url:
            titles.add(urllib.parse.unquote(url.rsplit("/", 1)[-1]).replace("_", " ").casefold())
    return titles


def _discover(prior_titles: set[str]) -> tuple[list[tuple[str, str]], dict[str, int]]:
    chosen: list[tuple[str, str]] = []
    seen: set[str] = set()
    stats: dict[str, int] = {}
    for category in DISCOVERY_CATEGORIES:
        got = 0
        token = ""
        scanned = 0
        while got < DISCOVERY_PER_CATEGORY:
            params = {
                "action": "query",
                "cmlimit": "50",
                "cmtype": "page",
                "cmtitle": category,
                "list": "categorymembers",
            }
            if token:
                params["cmcontinue"] = token
            payload = _api(params)
            members = payload.get("query", {}).get("categorymembers", [])
            if not members and not payload.get("continue"):
                break
            for member in members:
                scanned += 1
                title = str(member.get("title") or "")
                if ":" in title or " " not in title:
                    continue
                key = title.casefold()
                if key in prior_titles or key in seen:
                    continue
                seen.add(key)
                chosen.append((category, title))
                got += 1
                if got >= DISCOVERY_PER_CATEGORY:
                    break
            token = str(payload.get("continue", {}).get("cmcontinue") or "")
            if not token:
                break
        stats[category] = got
        stats[category + " scanned"] = scanned
    if not chosen:
        raise SystemExit(f"{FAILURE_SOURCE}: no new multiword pages")
    return chosen, stats


def _fetch_pages(chosen: list[tuple[str, str]]) -> list[dict[str, Any]]:
    by_title = {title: category for category, title in chosen}
    pages: list[dict[str, Any]] = []
    titles = [title for _, title in chosen]
    for start in range(0, len(titles), 20):
        batch = titles[start : start + 20]
        payload = _api(
            {
                "action": "query",
                "prop": "revisions",
                "rvlimit": "1",
                "rvprop": "ids|timestamp|sha1|content",
                "rvslots": "main",
                "titles": "|".join(batch),
            }
        )
        for page in payload.get("query", {}).get("pages", []):
            title = str(page.get("title") or "")
            if page.get("missing") or title not in by_title:
                continue
            revisions = page.get("revisions") or []
            if not revisions:
                continue
            revision = revisions[0]
            content = ((revision.get("slots") or {}).get("main") or {}).get("content")
            if not isinstance(content, str) or not content.strip():
                continue
            if content.lstrip().lower().startswith("#redirect"):
                continue
            revid = revision.get("revid")
            sha1 = str(revision.get("sha1") or "")
            timestamp = str(revision.get("timestamp") or "")
            if not isinstance(revid, int) or not sha1 or not timestamp:
                continue
            gloss = extract_primary_gloss(content)
            pages.append(
                {
                    "content_has_revision": True,
                    "discovery_category": by_title[title],
                    "exact_gloss": gloss["exact_gloss"],
                    "headword": title,
                    "page_url": "https://en.wiktionary.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
                    "part_of_speech": gloss["part_of_speech"],
                    "revision_id": revid,
                    "revision_sha1": sha1,
                    "revision_timestamp": timestamp,
                }
            )
    if len(pages) != len(chosen):
        missing = len(chosen) - len(pages)
        if missing == len(chosen):
            raise SystemExit(f"{FAILURE_PROVENANCE}: no revision-validated pages")
    return pages


def _candidates(pages: list[dict[str, Any]], blocked: dict[str, str]) -> tuple[list[dict[str, Any]], Counter[str]]:
    train_rows = [json.loads(line) for line in EXPORT.read_text(encoding="utf-8").splitlines() if line.strip()]
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
        tokens = [part for part in title.split(" ") if part]
        gloss = page.get("exact_gloss")
        if not gloss:
            exclusions["FAMILY_A_EVIDENCE_ABSENT"] += 1
        else:
            text = title
            consider(
                {
                    "candidate_id": "s006a-" + sha256_text(page["page_url"])[:16],
                    "discovery_category": page["discovery_category"],
                    "exact_gloss": gloss,
                    "headword": title,
                    "normalized_hash": normalized_text_sha256(text),
                    "normalized_text": text,
                    "page_url": page["page_url"],
                    "part_of_speech": page.get("part_of_speech"),
                    "provenance_status": "COMPLETE",
                    "revision_id": page["revision_id"],
                    "revision_sha1": page["revision_sha1"],
                    "revision_timestamp": page["revision_timestamp"],
                    "rights": "CC-BY-SA",
                    "role_scheme": None,
                    "sense_labels": None,
                    "source_family": "wiktionary_sense_gloss",
                    "source_lemma_tokens": [],
                    "source_url": page["page_url"],
                    "unbind_clean_derivation": None,
                }
            )
        if len(tokens) < 2:
            continue
        built = _unbind_dual_scheme_rows(
            title,
            tokens,
            lineage="none",
            stage="select006",
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
                    "candidate_id": "s006b-" + scheme[:3] + "-" + sha256_text(page["page_url"] + scheme)[:16],
                    "discovery_category": page["discovery_category"],
                    "exact_gloss": None,
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
                    "sense_labels": None,
                    "source_family": "wiktionary_multiword_lemma",
                    "source_lemma_tokens": list(item.get("fillers") or []),
                    "source_url": page["page_url"],
                    "unbind_clean_derivation": UNBIND_CLEAN_DERIVATION,
                }
            )
    return rows, exclusions


def fetch() -> None:
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST, 0o700)
    if (DEST / "RAW_CANDIDATES.jsonl").exists():
        raise SystemExit(f"{FAILURE_SOURCE}: raw candidates already frozen")
    floors = frozen_floors()
    _write(DEST / "FLOORS.json", canonical_json(floors))
    blocked = _blocked()
    chosen, stats = _discover(_prior_titles())
    pages = _fetch_pages(chosen)
    rows, exclusions = _candidates(pages, blocked)
    if not rows:
        raise SystemExit(f"{FAILURE_REVIEW}: no review rows")
    review = [review_surface_row(row) for row in rows]
    errors = blind_surface_errors(review)
    if errors:
        raise SystemExit(f"{FAILURE_REVIEW}: {errors[0]}")
    raw_sha = _jsonl(DEST / "RAW_CANDIDATES.jsonl", rows)
    review_sha = _jsonl(DEST / "REVIEW_SURFACE.jsonl", review)
    summary = {
        "discovered": len(chosen),
        "discovery_stats": stats,
        "exclusion_counts": dict(exclusions),
        "experiment_id": EXPERIMENT_ID,
        "family_a": sum(1 for row in rows if row["source_family"] == "wiktionary_sense_gloss"),
        "family_b": sum(1 for row in rows if row["source_family"] == "wiktionary_multiword_lemma"),
        "fetched_pages": len(pages),
        "firecrawl_labels_assigned": 0,
        "labels_assigned_by_fetch": 0,
        "provenance_authority": "mediawiki action=query prop=revisions rvprop=ids|timestamp|sha1|content",
        "provenance_complete": sum(1 for row in rows if row["provenance_status"] == "COMPLETE"),
        "raw_sha256": raw_sha,
        "review_count": len(review),
        "review_sha256": review_sha,
        "rights_cleared": sum(1 for row in rows if row["rights"] == "CC-BY-SA"),
        "schema": "hyperlex.select_006_fetch_summary.v1",
        **forbidden_training(),
    }
    _write(DEST / "FETCH_SUMMARY.json", canonical_json(summary))
    sys.stdout.write(canonical_json({"fetched_pages": len(pages), "review_count": len(review), "exclusions": dict(exclusions)}))


def _stream(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "family_hint_not_a_label": None,
        "normtext_sha256": raw["normalized_hash"],
        "row_key": raw["candidate_id"],
        "source_type": raw["source_family"],
        "text": raw["normalized_text"],
    }


def _metadata(raw: dict[str, Any]) -> dict[str, Any]:
    task = "classify" if raw["source_family"] == "wiktionary_sense_gloss" else "unbind"
    clean = task == "unbind" and raw.get("unbind_clean_derivation") == UNBIND_CLEAN_DERIVATION
    return {
        "normalized_identity": raw["normalized_hash"],
        "provenance_state": raw["provenance_status"],
        "row_id": raw["candidate_id"],
        "source_identity": raw["source_url"],
        "task": task,
        "unbind_clean": clean,
        "unbind_clean_derivation": raw.get("unbind_clean_derivation"),
    }


def settle_and_bind() -> None:
    decisions_path = DEST / "DECISIONS.jsonl"
    if not decisions_path.is_file():
        raise SystemExit(f"{FAILURE_SETTLEMENT}: decisions are absent")
    if (DEST / "RESERVE_MANIFEST.json").exists() or (DEST / "FAILURE.json").exists():
        raise SystemExit(f"{FAILURE_SETTLEMENT}: reserve outcome already frozen")
    raw_rows = _read_jsonl(DEST / "RAW_CANDIDATES.jsonl")
    review = _read_jsonl(DEST / "REVIEW_SURFACE.jsonl")
    if blind_surface_errors(review):
        raise SystemExit(f"{FAILURE_REVIEW}: review surface is not blind")
    if not review:
        raise SystemExit(f"{FAILURE_REVIEW}: review surface is empty")
    raw_by_id = {row["candidate_id"]: row for row in raw_rows}
    decisions = _read_jsonl(decisions_path)
    if {row["candidate_id"] for row in review} != {row.get("row_id") for row in decisions}:
        raise SystemExit(f"{FAILURE_SETTLEMENT}: decisions do not cover the frozen surface")
    streams = [_stream(raw_by_id[row["candidate_id"]]) for row in review]
    prior = load_logged_ids(SETTLEMENT_LOG)
    try:
        settled = settle(
            streams,
            decisions,
            batch_id=BATCH_ID,
            operator=OPERATOR,
            provenance="Blind review of SELECT-006 reserve-acquisition-001.",
            settled_at=SETTLED_AT,
            prior_ids=prior,
        )
    except SystemExit as exc:
        raise SystemExit(f"{FAILURE_SETTLEMENT}: {exc}") from exc
    records = settled["records"]
    receipt = commit_settlement(
        records,
        settled["receipt"],
        log_path=SETTLEMENT_LOG,
        receipt_path=DEST / "SETTLEMENT_RECEIPT.json",
    )
    pairs = []
    raw_for_record = {row["candidate_id"]: raw_by_id[row["candidate_id"]] for row in review}
    for record in records:
        raw = raw_for_record[record["row_id"]]
        if raw["rights"] != "CC-BY-SA" or record["rights"] != "CC-BY-SA":
            raise SystemExit(f"{FAILURE_RIGHTS}: {record['row_id']}")
        if raw["provenance_status"] != "COMPLETE" or not raw["revision_sha1"] or not raw["revision_id"]:
            raise SystemExit(f"{FAILURE_PROVENANCE}: {record['row_id']}")
        pairs.append((record, _metadata(raw)))
    validation = contract_validation(pairs)
    if validation["state"] != "ROUTING_VALIDATION_COMPLETE" or validation["determinism"] != "IDENTICAL":
        raise SystemExit(f"{FAILURE_ROUTING}: {validation['state']}")
    first = derive_batch(pairs)
    second = derive_batch(pairs)
    if [canonical_json(row) for row in first] != [canonical_json(row) for row in second]:
        raise SystemExit(f"{FAILURE_ROUTING}: replay differed")
    routing_sha = _jsonl(DEST / "ROUTING_RECORDS.jsonl", first)
    surface = metric_surface(first)
    blocked = _blocked()
    overlaps = Counter()
    for record in records:
        reason = exclusion_reason(str(record["text_hash"]), blocked)
        if reason and reason != "SETTLED_SURFACE":
            overlaps[reason] += 1
    isolation_pass = not overlaps
    provenance_pass = all(
        raw["rights"] == "CC-BY-SA" and raw["provenance_status"] == "COMPLETE" for raw in raw_rows
    )
    isolation = {
        "experiment_id": EXPERIMENT_ID,
        "overlaps": dict(overlaps),
        "result": "PASS" if isolation_pass else "FAIL",
        "schema": "hyperlex.select_006_isolation_report.v1",
        "select_005_reserve_reuse": "FORBIDDEN",
    }
    provenance = {
        "experiment_id": EXPERIMENT_ID,
        "provenance_complete": sum(1 for row in raw_rows if row["provenance_status"] == "COMPLETE"),
        "required_fields": [
            "normalized_hash",
            "normalized_text",
            "revision_id",
            "revision_sha1",
            "revision_timestamp",
            "rights",
            "source_url",
        ],
        "result": "PASS" if provenance_pass else "FAIL",
        "rights_cleared": sum(1 for row in raw_rows if row["rights"] == "CC-BY-SA"),
        "schema": "hyperlex.select_006_provenance_report.v1",
    }
    isolation_sha = _write(DEST / "ISOLATION_REPORT.json", canonical_json(isolation))
    provenance_sha = _write(DEST / "PROVENANCE_REPORT.json", canonical_json(provenance))
    failure = None
    if not provenance_pass:
        failure = FAILURE_PROVENANCE
    elif not isolation_pass:
        failure = FAILURE_ISOLATION
    elif not surface["computable"]["classify_macro_f1_nonnone"] or not all(surface["computable"].values()):
        failure = FAILURE_SURFACE
    elif not surface["floors_met"]:
        failure = FAILURE_QUOTA
    if failure:
        _write(
            DEST / "FAILURE.json",
            canonical_json(
                {
                    "failure": failure,
                    "isolation_sha256": isolation_sha,
                    "metric_surface": surface,
                    "provenance_sha256": provenance_sha,
                    "routing_sha256": routing_sha,
                    "schema": "hyperlex.select_006_reserve_failure.v1",
                    "settlement_receipt_sha256": receipt["receipt_sha256"],
                    **forbidden_training(),
                }
            ),
        )
        raise SystemExit(failure)
    eligible = [row for row in first if row["routing_status"] == "ELIGIBLE"]
    manifest_rows = []
    for row in eligible:
        raw = raw_for_record[row["row_id"]]
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
        "rows": manifest_rows,
        "schema": "hyperlex.select_006_reserve_manifest.v1",
        "slice_counts": surface["slice_counts"],
        "head_mapped_non_none": surface["head_mapped_non_none"],
    }
    manifest_sha = _write(DEST / "RESERVE_MANIFEST.json", canonical_json(manifest))
    events_before = _sha_file(LEDGER / "events.jsonl")
    projection_before = _sha_file(LEDGER / "ledger.json")
    ledger = IdentityLedger.load(LEDGER)
    prior_count = len(ledger.events)
    select005_before = len(ledger.active_reserve_records(SELECT_005_ID))
    for row in manifest_rows:
        if exclusion_reason(row["normalized_text_sha256"], _blocked()) not in (None, "SETTLED_SURFACE"):
            raise SystemExit(f"{FAILURE_BINDING}: {row['row_id']}")
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
            provenance="SELECT-006 reserve manifest",
            experiment_id=EXPERIMENT_ID,
        )
        ledger.transition(
            row["normalized_text_sha256"],
            "EVAL_RESERVE",
            source_artifact=str(DEST / "RESERVE_MANIFEST.json"),
            provenance="SELECT-006 reserve binding",
        )
    if ledger.row_id_collisions:
        raise SystemExit(f"{FAILURE_BINDING}: row id collision")
    appended = ledger.persist_append(LEDGER, prior_count)
    replay = IdentityLedger.load(LEDGER)
    replay_projection = json.dumps(replay.project(), indent=2, sort_keys=True) + "\n"
    written = (LEDGER / "ledger.json").read_text(encoding="utf-8")
    if replay_projection != written:
        raise SystemExit(f"{FAILURE_REPLAY}: projection mismatch")
    if len(replay.active_reserve_records(SELECT_005_ID)) != select005_before:
        raise SystemExit(f"{FAILURE_BINDING}: SELECT-005 bindings changed")
    bound = replay.active_reserve_records(EXPERIMENT_ID)
    if len(bound) != len(manifest_rows):
        raise SystemExit(f"{FAILURE_BINDING}: bound {len(bound)} of {len(manifest_rows)}")
    events_after = _sha_file(LEDGER / "events.jsonl")
    projection_after = _sha_file(LEDGER / "ledger.json")
    reserve_receipt = {
        "appended_events": appended,
        "bound_identities": len(bound),
        "experiment_id": EXPERIMENT_ID,
        "isolation_sha256": isolation_sha,
        "ledger_events_sha256_after": events_after,
        "ledger_events_sha256_before": events_before,
        "ledger_projection_sha256_after": projection_after,
        "ledger_projection_sha256_before": projection_before,
        "ledger_replay": "PASS",
        "manifest_sha256": manifest_sha,
        "metric_surface": surface,
        "next_legal_transition": "SELECT_006_ZERO_INIT_LOADER",
        "provenance_sha256": provenance_sha,
        "routing_sha256": routing_sha,
        "schema": "hyperlex.select_006_reserve_receipt.v1",
        "select_005_active_reserve_unchanged": select005_before,
        "settlement_receipt_sha256": receipt["receipt_sha256"],
        "state": "RESERVE_FROZEN",
        "transition": TRANSITION,
        **forbidden_training(),
    }
    _write(DEST / "RESERVE_RECEIPT.json", canonical_json(reserve_receipt))
    sys.stdout.write(canonical_json(reserve_receipt))


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"fetch", "settle"}:
        raise SystemExit("usage: select_006_reserve_acquire.py fetch|settle")
    if sys.argv[1] == "fetch":
        fetch()
    else:
        settle_and_bind()


if __name__ == "__main__":
    main()
