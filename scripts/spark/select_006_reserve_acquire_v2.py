"""SELECT-006 reserve acquisition v2.

``fetch`` freezes a blind review surface. It does not assign OBSERVED.
``settle`` reads operator decisions and binds a ledger only when every
required metric is computable. It does not train.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(ROOT / "scripts/shadow"))

from hyperlexical.eval_routing import (  # noqa: E402
    UNBIND_CLEAN_DERIVATION,
    contract_validation,
    derive_batch,
)
from hyperlexical.eval_settlement import commit_settlement, load_logged_ids, settle  # noqa: E402
from hyperlexical.export import _unbind_dual_scheme_rows  # noqa: E402
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402
from hyperlexical.identity_ledger import IdentityLedger  # noqa: E402
from hyperlexical.select_006_efficiency_preservation import EPSILON, EXPERIMENT_ID  # noqa: E402
from hyperlexical.select_006_reserve_acquisition import (  # noqa: E402
    SELECT_005_ID,
    exclusion_reason,
    forbidden_training,
    metric_surface,
)
from hyperlexical.select_006_reserve_acquisition_v2 import (  # noqa: E402
    BINDING_CONFLICT,
    DESIGN_PINS,
    FETCH_FAILURE,
    ISOLATION_FAILURE,
    LABEL_AMBIGUOUS,
    LABEL_NOT_AUTHORIZED,
    PIN_MISMATCH,
    PROVENANCE_FAILURE,
    QUOTA_UNFILLED,
    REPLAY_FAILURE,
    REVIEW_EMPTY,
    RIGHTS_FAILURE,
    ROUTING_FAILURE,
    SETTLEMENT_FAILURE,
    SURFACE_INSUFFICIENT,
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
    review_surface_row,
    sha256_text,
)
from hyperlexical.soft_ceiling import clean_surface  # noqa: E402

DEST = Path("/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-002")
DESIGN_DIR = Path("/home/morpheus/hlx-private/exp-20260929-select-006/source-design-v2")
SPENT_RAW = Path("/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-001/RAW_CANDIDATES.jsonl")
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
UA = "HyperlexSelect006ReserveV2/1.0 (local evaluation reserve; mediawiki provenance)"
OPERATOR = "Hyperlex Cloud Agent"
SETTLED_AT = "2026-09-29T06:30:00Z"
BATCH_ID = "HLX-EVAL-RESERVE-SELECT-006-002"
TRANSITION = "SELECT_006_RESERVE_ACQUISITION_V2"
SCAN_CAP = 40

_EXCLUSION_PRIORITY = {
    "SELECT_005_EVAL_RESERVE": 0,
    "SELECT_006_ACQUISITION_001": 1,
    "TRAIN_CONSUMED": 2,
    "EVAL_SPENT": 3,
    "EVAL_ABANDONED": 4,
    "SELECT_001_002_BINDING": 5,
    "THRESHOLD_V1_CALIBRATION": 6,
    "THRESHOLD_V2_CALIBRATION": 7,
    "THRESHOLD_V2_MEASUREMENT": 8,
    "EXPOSURE": 9,
    "PRIOR_FETCH_IDENTITY": 10,
    "LEDGER_IDENTITY": 11,
    "SETTLED_SURFACE": 12,
}


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


def _pins() -> None:
    if EPSILON != 0:
        raise SystemExit(f"{PIN_MISMATCH}: EPSILON")
    for name, digest in DESIGN_PINS.items():
        if _sha_file(DESIGN_DIR / name) != digest:
            raise SystemExit(f"{PIN_MISMATCH}: {name}")
    contract = json.loads((DESIGN_DIR / "FUTURE_ACQUISITION_CONTRACT.json").read_text(encoding="utf-8"))
    if contract.get("direct_labels") != {key: list(DIRECT_LABELS[key]) for key in TARGET_FAMILIES}:
        raise SystemExit(f"{PIN_MISMATCH}: direct labels")
    if contract.get("fetch_authorized") is not False:
        raise SystemExit(f"{PIN_MISMATCH}: fetch flag")


def _api(params: dict[str, str]) -> dict[str, Any]:
    query = urllib.parse.urlencode({"format": "json", "formatversion": "2", **params})
    request = urllib.request.Request(API + "?" + query, headers={"User-Agent": UA})
    delay = 2.0
    payload: Any = None
    for _attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 503}:
                raise SystemExit(f"{FETCH_FAILURE}: mediawiki http {exc.code}") from exc
            time.sleep(delay)
            delay *= 2
    else:
        raise SystemExit(f"{FETCH_FAILURE}: mediawiki rate limit")
    time.sleep(1.0)
    if not isinstance(payload, dict):
        raise SystemExit(f"{FETCH_FAILURE}: mediawiki query failed")
    if "error" in payload:
        code = str(payload.get("error", {}).get("code") or "error")
        raise SystemExit(f"{FETCH_FAILURE}: mediawiki {code}")
    return payload


def _blocked() -> dict[str, str]:
    found: dict[str, str] = {}

    def put(digest: str, reason: str) -> None:
        if not digest:
            return
        current = found.get(digest)
        if current is None or _EXCLUSION_PRIORITY[reason] < _EXCLUSION_PRIORITY[current]:
            found[digest] = reason

    for row in _read_jsonl(SPENT_RAW):
        put(str(row.get("normalized_hash") or ""), "SELECT_006_ACQUISITION_001")
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


def _search(template: str, label: str) -> list[str]:
    titles: list[str] = []
    offset = 0
    while len(titles) < SCAN_CAP:
        payload = _api(
            {
                "action": "query",
                "list": "search",
                "srlimit": "20",
                "srnamespace": "0",
                "sroffset": str(offset),
                "srsearch": search_query(template, label),
            }
        )
        hits = payload.get("query", {}).get("search", [])
        if not hits:
            break
        for hit in hits:
            title = str(hit.get("title") or "")
            if title and ":" not in title and "|" not in title:
                titles.append(title)
            if len(titles) >= SCAN_CAP:
                break
        if not payload.get("continue"):
            break
        offset += 20
    return titles


def _fetch_revisions(titles: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for start in range(0, len(titles), 10):
        batch = titles[start : start + 10]
        payload = _api(
            {
                "action": "query",
                "prop": "revisions",
                "rvprop": "ids|timestamp|sha1|content",
                "rvslots": "main",
                "titles": "|".join(batch),
            }
        )
        for page in payload.get("query", {}).get("pages", []):
            title = str(page.get("title") or "")
            revisions = page.get("revisions") or []
            if page.get("missing") or not revisions:
                continue
            revision = revisions[0]
            content = ((revision.get("slots") or {}).get("main") or {}).get("content")
            revid = revision.get("revid")
            sha1 = str(revision.get("sha1") or "")
            timestamp = str(revision.get("timestamp") or "")
            if not isinstance(content, str) or not isinstance(revid, int) or not sha1 or not timestamp:
                continue
            found[title] = {
                "content": content,
                "revision_id": revid,
                "revision_sha1": sha1,
                "revision_timestamp": timestamp,
                "title": title,
            }
    return found


def _english_text(content: str) -> str:
    parts = content.split("\n==")
    if content.startswith("=="):
        chunks = content.split("\n==")
    else:
        chunks = parts
    for index, chunk in enumerate(chunks):
        text = chunk if index == 0 and content.startswith("==") else ("==" + chunk if index else chunk)
        head = text.strip().splitlines()[:1]
        if head and head[0].strip("= ").casefold() == "english":
            return text if text.startswith("==") else "==" + text
    return ""


def fetch() -> None:
    _pins()
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST, 0o700)
    if (DEST / "RAW_CANDIDATES.jsonl").exists() or (DEST / "FAILURE.json").exists():
        raise SystemExit(f"{FETCH_FAILURE}: acquisition-002 already frozen")
    blocked = _blocked()
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
                titles = _search(template, label)
                queries.append({"family": family, "kept_before": got, "label": label, "query": query, "titles_seen": len(titles)})
                ordered = [title for title in titles if title.casefold() not in kept_titles]
                cursor = 0
                while cursor < len(ordered) and got < DISCOVERY_PER_FAMILY:
                    chunk = ordered[cursor : cursor + 10]
                    cursor += 10
                    missing = [title for title in chunk if title not in revision_cache]
                    found = _fetch_revisions(missing) if missing else {}
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
                        if not label_on_line(label, sense["sense_label_arguments"]):
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
                                "english_entry_text": _english_text(content),
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
    if not rows:
        _write(
            DEST / "FAILURE.json",
            canonical_json(
                {
                    "discovered_pages": len(pages),
                    "exclusion_counts": dict(exclusions),
                    "failure": REVIEW_EMPTY,
                    "fetched_titles": len(revision_cache),
                    "queries": queries,
                    "schema": "hyperlex.select_006_reserve_v2_failure.v1",
                    **forbidden_training(),
                }
            ),
        )
        raise SystemExit(REVIEW_EMPTY)
    review = [review_surface_row(row) for row in rows]
    errors = blind_surface_errors(review)
    if errors:
        raise SystemExit(f"{REVIEW_EMPTY}: {errors[0]}")
    raw_sha = _jsonl(DEST / "RAW_CANDIDATES.jsonl", rows)
    review_sha = _jsonl(DEST / "REVIEW_SURFACE.jsonl", review)
    summary = {
        "discovered_pages": len(pages),
        "exclusion_counts": dict(exclusions),
        "experiment_id": EXPERIMENT_ID,
        "fetched_titles": len(revision_cache),
        "firecrawl_labels_assigned": 0,
        "label_counts": dict(label_counts),
        "labels_assigned_by_fetch": 0,
        "provenance_authority": "mediawiki action=query prop=revisions rvprop=ids|timestamp|sha1|content",
        "provenance_complete": sum(1 for row in rows if row["provenance_status"] == "COMPLETE"),
        "queries": queries,
        "raw_sha256": raw_sha,
        "review_count": len(review),
        "review_sha256": review_sha,
        "rights_cleared": sum(1 for row in rows if row["rights"] == "CC-BY-SA"),
        "schema": "hyperlex.select_006_fetch_summary_v2.v1",
        "source_family": "wiktionary_labeled_sense",
        **forbidden_training(),
    }
    _write(DEST / "FETCH_SUMMARY.json", canonical_json(summary))
    sys.stdout.write(canonical_json({"discovered_pages": len(pages), "review_count": len(review), "label_counts": dict(label_counts)}))


def label_on_line(label: str, arguments: list[str]) -> bool:
    from hyperlexical.select_006_reserve_source_design_v2 import normalize_label

    wanted = normalize_label(label)
    return any(normalize_label(argument) == wanted for argument in arguments)


def _rows(
    pages: list[dict[str, Any]],
    blocked: dict[str, str],
    train_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[str]]:
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
                "candidate_id": "s006v2c-" + sha256_text(page["page_url"])[:16],
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
            stage="select006v2",
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
                    "candidate_id": "s006v2u-" + scheme[:3] + "-" + sha256_text(page["page_url"] + scheme)[:16],
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


def _stream(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "family_hint_not_a_label": None,
        "normtext_sha256": raw["normalized_hash"],
        "row_key": raw["candidate_id"],
        "source_type": "wiktionary_labeled_sense",
        "text": raw["normalized_text"],
    }


def _metadata(raw: dict[str, Any]) -> dict[str, Any]:
    task = "unbind" if raw.get("unbind_clean_derivation") == UNBIND_CLEAN_DERIVATION else "classify"
    return {
        "normalized_identity": raw["normalized_hash"],
        "provenance_state": raw["provenance_status"],
        "row_id": raw["candidate_id"],
        "source_identity": raw["source_url"],
        "task": task,
        "unbind_clean": task == "unbind",
        "unbind_clean_derivation": raw.get("unbind_clean_derivation"),
    }


def _fail(code: str, **extra: Any) -> None:
    _write(
        DEST / "FAILURE.json",
        canonical_json(
            {
                "failure": code,
                "schema": "hyperlex.select_006_reserve_v2_failure.v1",
                **extra,
                **forbidden_training(),
            }
        ),
    )
    raise SystemExit(code)


def settle_and_bind() -> None:
    _pins()
    decisions_path = DEST / "DECISIONS.jsonl"
    if not decisions_path.is_file():
        raise SystemExit(f"{SETTLEMENT_FAILURE}: decisions are absent")
    if (DEST / "RESERVE_MANIFEST.json").exists() or (DEST / "FAILURE.json").exists():
        raise SystemExit(f"{SETTLEMENT_FAILURE}: reserve outcome already frozen")
    raw_rows = _read_jsonl(DEST / "RAW_CANDIDATES.jsonl")
    review = _read_jsonl(DEST / "REVIEW_SURFACE.jsonl")
    if blind_surface_errors(review):
        raise SystemExit(f"{REVIEW_EMPTY}: review surface is not blind")
    if not review:
        _fail(REVIEW_EMPTY)
    raw_by_id = {row["candidate_id"]: row for row in raw_rows}
    decisions = _read_jsonl(decisions_path)
    if {row["candidate_id"] for row in review} != {row.get("row_id") for row in decisions}:
        raise SystemExit(f"{SETTLEMENT_FAILURE}: decisions do not cover the frozen surface")
    streams = [_stream(raw_by_id[row["candidate_id"]]) for row in review]
    try:
        settled = settle(
            streams,
            decisions,
            batch_id=BATCH_ID,
            operator=OPERATOR,
            provenance="Blind review of SELECT-006 reserve-acquisition-002.",
            settled_at=SETTLED_AT,
            prior_ids=load_logged_ids(SETTLEMENT_LOG),
        )
    except SystemExit as exc:
        raise SystemExit(f"{SETTLEMENT_FAILURE}: {exc}") from exc
    records = settled["records"]
    receipt = commit_settlement(
        records,
        settled["receipt"],
        log_path=SETTLEMENT_LOG,
        receipt_path=DEST / "SETTLEMENT_RECEIPT.json",
    )
    pairs = []
    for record in records:
        raw = raw_by_id[record["row_id"]]
        if raw["rights"] != "CC-BY-SA" or record["rights"] != "CC-BY-SA":
            _fail(RIGHTS_FAILURE, settlement_receipt_sha256=receipt["receipt_sha256"])
        if raw["provenance_status"] != "COMPLETE" or not raw["revision_sha1"] or not raw["revision_id"]:
            _fail(PROVENANCE_FAILURE, settlement_receipt_sha256=receipt["receipt_sha256"])
        pairs.append((record, _metadata(raw)))
    validation = contract_validation(pairs)
    if validation["state"] != "ROUTING_VALIDATION_COMPLETE" or validation["determinism"] != "IDENTICAL":
        _fail(ROUTING_FAILURE, routing_state=validation["state"])
    first = derive_batch(pairs)
    second = derive_batch(pairs)
    if [canonical_json(row) for row in first] != [canonical_json(row) for row in second]:
        _fail(ROUTING_FAILURE, routing_state="replay differed")
    routing_sha = _jsonl(DEST / "ROUTING_RECORDS.jsonl", first)
    surface = metric_surface(first)
    computability = {
        "computable": surface["computable"],
        "experiment_id": EXPERIMENT_ID,
        "floors_met": surface["floors_met"],
        "head_mapped_non_none": surface["head_mapped_non_none"],
        "schema": "hyperlex.select_006_metric_computability.v1",
        "slice_counts": surface["slice_counts"],
    }
    computability_sha = _write(DEST / "METRIC_COMPUTABILITY.json", canonical_json(computability))
    blocked = _blocked()
    overlaps: Counter[str] = Counter()
    for record in records:
        reason = exclusion_reason(str(record["text_hash"]), blocked)
        if reason and reason != "SETTLED_SURFACE":
            overlaps[reason] += 1
    isolation_pass = not overlaps
    provenance_pass = all(row["rights"] == "CC-BY-SA" and row["provenance_status"] == "COMPLETE" for row in raw_rows)
    isolation = {
        "acquisition_001_reuse": "FORBIDDEN",
        "experiment_id": EXPERIMENT_ID,
        "overlaps": dict(overlaps),
        "result": "PASS" if isolation_pass else "FAIL",
        "schema": "hyperlex.select_006_isolation_report_v2.v1",
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
        "schema": "hyperlex.select_006_provenance_report_v2.v1",
    }
    isolation_sha = _write(DEST / "ISOLATION_REPORT.json", canonical_json(isolation))
    provenance_sha = _write(DEST / "PROVENANCE_REPORT.json", canonical_json(provenance))
    failure = None
    if not provenance_pass:
        failure = PROVENANCE_FAILURE
    elif not isolation_pass:
        failure = ISOLATION_FAILURE
    elif not all(surface["computable"].values()):
        failure = SURFACE_INSUFFICIENT
    elif not surface["floors_met"]:
        failure = QUOTA_UNFILLED
    if failure:
        _fail(
            failure,
            computability_sha256=computability_sha,
            isolation_sha256=isolation_sha,
            metric_surface=surface,
            provenance_sha256=provenance_sha,
            routing_sha256=routing_sha,
            settlement_receipt_sha256=receipt["receipt_sha256"],
        )
    eligible = [row for row in first if row["routing_status"] == "ELIGIBLE"]
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
        "schema": "hyperlex.select_006_reserve_manifest.v1",
        "slice_counts": surface["slice_counts"],
    }
    manifest_sha = _write(DEST / "RESERVE_MANIFEST.json", canonical_json(manifest))
    events_before = _sha_file(LEDGER / "events.jsonl")
    projection_before = _sha_file(LEDGER / "ledger.json")
    ledger = IdentityLedger.load(LEDGER)
    prior_count = len(ledger.events)
    select005_before = len(ledger.active_reserve_records(SELECT_005_ID))
    fresh_blocked = _blocked()
    for row in manifest_rows:
        if exclusion_reason(row["normalized_text_sha256"], fresh_blocked) not in (None, "SETTLED_SURFACE"):
            _fail(BINDING_CONFLICT, row_id=row["row_id"])
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
            provenance="SELECT-006 reserve manifest v2",
            experiment_id=EXPERIMENT_ID,
        )
        ledger.transition(
            row["normalized_text_sha256"],
            "EVAL_RESERVE",
            source_artifact=str(DEST / "RESERVE_MANIFEST.json"),
            provenance="SELECT-006 reserve binding v2",
        )
    if ledger.row_id_collisions:
        _fail(BINDING_CONFLICT, detail="row id collision")
    appended = ledger.persist_append(LEDGER, prior_count)
    replay = IdentityLedger.load(LEDGER)
    replay_projection = json.dumps(replay.project(), indent=2, sort_keys=True) + "\n"
    written = (LEDGER / "ledger.json").read_text(encoding="utf-8")
    if replay_projection != written:
        _fail(REPLAY_FAILURE, detail="projection mismatch")
    if len(replay.active_reserve_records(SELECT_005_ID)) != select005_before:
        _fail(BINDING_CONFLICT, detail="SELECT-005 bindings changed")
    bound = replay.active_reserve_records(EXPERIMENT_ID)
    if len(bound) != len(manifest_rows):
        _fail(BINDING_CONFLICT, detail=f"bound {len(bound)} of {len(manifest_rows)}")
    events_after = _sha_file(LEDGER / "events.jsonl")
    projection_after = _sha_file(LEDGER / "ledger.json")
    reserve_receipt = {
        "appended_events": appended,
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
        raise SystemExit("usage: select_006_reserve_acquire_v2.py fetch|settle")
    if sys.argv[1] == "fetch":
        fetch()
    else:
        settle_and_bind()


if __name__ == "__main__":
    main()
