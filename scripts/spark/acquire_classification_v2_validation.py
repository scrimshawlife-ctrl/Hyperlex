"""Acquire disjoint Wiktionary validation rows for two Classification v2 families.

Discovery may use MediaWiki search. Settlement uses the frozen evidence map
in classification_v2_acquire. Admitted rows are validation-side only: split
val, catalogued, and not routed to training or the evaluation reserve.

This script does not train, does not move BEST, and does not rewrite the
sense-text export.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from hyperlexical.classification_v2_acquire import (
    classify_wikitext,
    evidence_seal,
    training_row,
)
from hyperlexical.classification_v2_acquire_run import blocked_identities
from hyperlexical.classification_v2_prototype import validation_family_support
from hyperlexical.holdout_guard import normalized_text_sha256
from hyperlexical.identity_ledger import IdentityLedger, derived_state

API = "https://en.wiktionary.org/w/api.php"
UA = "HyperlexClassificationV2Validation/1.0 (validation acquisition; mediawiki provenance)"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
SENSE_EXPORT = Path(
    "/home/morpheus/hlx-private/classification-v2-sense-20260929/civilian.v0.1.jsonl"
)
SENSE_EXPORT_SHA256 = "a1332bce1dcf8a3e2646243990e1c9104e191019dae9324ffb9bbce91a28c1cc"
DEST = Path("/home/morpheus/hlx-private/classification-v2-validation-20260929")
EXPORT_PATH = DEST / "civilian.v0.2.jsonl"
BATCH_ID = "HLX-CLASSIFICATION-V2-VALIDATION-20260929"
EVIDENCE_SEAL = "8b30c98ad8eac7c136e391103450c9d0d20a3499220e9b48f923eab8218581f1"
TARGETS = ("internet-slang", "memetic")
MAX_TITLES = 160
PAUSE = 2.5
EXPECTED_SEAL = EVIDENCE_SEAL

# Search strings only. They do not widen the frozen label or gloss map.
DISCOVERY: dict[str, tuple[str, ...]] = {
    "internet-slang": (
        'insource:"{{lb|en|Internet slang"',
        'insource:"{{lb|en|internet slang"',
        'insource:"{{lbl|en|Internet slang"',
        'insource:"{{tlb|en|Internet slang"',
        'insource:"{{lb|en|Reddit slang"',
        'insource:"{{lb|en|reddit slang"',
        'insource:"{{lb|en|2channel slang"',
        'insource:"{{lb|en|internet|slang"',
    ),
    "memetic": (
        'insource:"{{lb|en|meme}}"',
        'insource:"{{lb|en|meme|"',
        'insource:"{{lb|en|Internet|meme"',
        'insource:"{{lbl|en|meme"',
        'insource:"{{tlb|en|meme"',
        'insource:"internet meme"',
        'insource:"image macro"',
        'insource:"copypasta"',
    ),
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _api(params: dict[str, str]) -> dict[str, Any]:
    query = dict(params)
    query["format"] = "json"
    query["formatversion"] = "2"
    url = API + "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 5:
                time.sleep(30 + attempt * 15)
                continue
            raise
        finally:
            time.sleep(PAUSE)


def _search(query: str) -> list[str]:
    titles: list[str] = []
    offset = 0
    while len(titles) < MAX_TITLES:
        payload = _api(
            {
                "action": "query",
                "list": "search",
                "srlimit": "40",
                "srnamespace": "0",
                "sroffset": str(offset),
                "srsearch": query,
            }
        )
        hits = payload.get("query", {}).get("search", [])
        if not hits:
            break
        for hit in hits:
            title = str(hit.get("title") or "")
            if title and ":" not in title:
                titles.append(title)
            if len(titles) >= MAX_TITLES:
                break
        if not payload.get("continue"):
            break
        offset += 40
    return titles


def _fetch(titles: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for start in range(0, len(titles), 8):
        batch = titles[start : start + 8]
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
            }
        print(f"fetched {min(start + 8, len(titles))}/{len(titles)}", flush=True)
    return found


def _page_url(title: str) -> str:
    slug = urllib.parse.quote(title.replace(" ", "_"), safe="()!'*_,")
    return "https://en.wiktionary.org/wiki/" + slug


def _load_sense_rows() -> list[dict[str, Any]]:
    if _sha256_file(SENSE_EXPORT) != SENSE_EXPORT_SHA256:
        raise SystemExit("REFUSE: sense export hash moved")
    rows = []
    with SENSE_EXPORT.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG = re.compile(r"<[^>]+>")


def _usable_definition(prose: str) -> bool:
    """Reject editor comments and markup left after the frozen prose extractor."""
    visible = _TAG.sub(" ", _COMMENT.sub(" ", prose))
    visible = re.sub(r"\s+", " ", visible).strip(" .;")
    return bool(re.search(r"[A-Za-z]{2,}", visible))


def _extend_blocked(blocked: dict[str, str], rows: list[dict[str, Any]]) -> set[str]:
    pages: set[str] = set()
    for row in rows:
        text = row.get("text")
        if isinstance(text, str) and text:
            digest = normalized_text_sha256(text)
            blocked.setdefault(digest, "SENSE_EXPORT_TEXT")
        provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        prose = str(provenance.get("definition_prose") or "").strip()
        if prose:
            blocked.setdefault(normalized_text_sha256(prose), "SENSE_EXPORT_PROSE")
        page = provenance.get("page")
        if isinstance(page, str) and page:
            pages.add(page.casefold())
            blocked.setdefault(normalized_text_sha256(page), "SENSE_EXPORT_PAGE")
    return pages


def discover(dest: Path) -> dict[str, Any]:
    dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(dest, 0o700)
    by_family: dict[str, list[str]] = {}
    query_counts: dict[str, list[dict[str, Any]]] = {}
    ordered: list[str] = []
    seen: set[str] = set()
    for family in TARGETS:
        found: list[str] = []
        query_counts[family] = []
        for query in DISCOVERY[family]:
            titles = _search(query)
            query_counts[family].append({"query": query, "titles": len(titles)})
            print(f"search {family} {len(titles)} {query}", flush=True)
            for title in titles:
                found.append(title)
                key = title.casefold()
                if key not in seen:
                    seen.add(key)
                    ordered.append(title)
        by_family[family] = found
    pages = _fetch(ordered)
    fetched_path = dest / "FETCHED.jsonl"
    with fetched_path.open("w", encoding="utf-8") as handle:
        for title in ordered:
            page = pages.get(title)
            if page is None:
                continue
            handle.write(
                json.dumps(
                    {
                        "title": title,
                        "revision_id": page["revision_id"],
                        "revision_sha1": page["revision_sha1"],
                        "revision_timestamp": page["revision_timestamp"],
                        "content": page["content"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    os.chmod(fetched_path, 0o600)
    summary = {
        "discovery_titles": {family: len(titles) for family, titles in by_family.items()},
        "discovery_queries": query_counts,
        "unique_titles": len(ordered),
        "fetched_revisions": len(pages),
        "fetched_path": str(fetched_path),
    }
    (dest / "DISCOVERY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def _load_fetched(path: Path) -> list[dict[str, Any]]:
    pages = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                pages.append(json.loads(line))
    return pages


def settle(pages: list[dict[str, Any]]) -> dict[str, Any]:
    if evidence_seal() != EXPECTED_SEAL:
        raise SystemExit("REFUSE: evidence seal moved")
    sense_rows = _load_sense_rows()
    blocked = blocked_identities()
    admitted_pages = _extend_blocked(blocked, sense_rows)
    exclusions: Counter[str] = Counter()
    candidates: list[dict[str, Any]] = []
    admitted: list[dict[str, Any]] = []
    seen_digests: set[str] = set()
    for page in pages:
        title = str(page["title"])
        decision = classify_wikitext(str(page["content"]))
        prose = str(decision.get("definition_prose") or "").strip()
        record = {
            "title": title,
            "page_url": _page_url(title),
            "revision_id": page["revision_id"],
            "revision_sha1": page["revision_sha1"],
            "revision_timestamp": page["revision_timestamp"],
            "status": decision["status"],
            "family": decision.get("family"),
            "evidence": decision.get("evidence"),
            "sense_labels": list(decision.get("sense_label_arguments") or []),
            "definition_prose": prose,
            "definition_line": decision.get("definition_line") or "",
        }
        if title.casefold() in admitted_pages:
            exclusions["already_admitted_page"] += 1
            record["exclusion"] = "already_admitted_page"
            candidates.append(record)
            continue
        if decision["status"] != "unique" or decision.get("family") not in TARGETS:
            reason = str(decision["status"] if decision["status"] != "unique" else "other_family")
            exclusions[reason] += 1
            record["exclusion"] = reason
            candidates.append(record)
            continue
        if not prose:
            exclusions["empty_prose"] += 1
            record["exclusion"] = "empty_prose"
            candidates.append(record)
            continue
        if not _usable_definition(prose):
            exclusions["not_a_definition"] += 1
            record["exclusion"] = "not_a_definition"
            candidates.append(record)
            continue
        digest = normalized_text_sha256(prose)
        record["normalized_text_sha256"] = digest
        if digest in blocked:
            reason = "blocked:" + blocked[digest]
            exclusions[reason] += 1
            record["exclusion"] = reason
            candidates.append(record)
            continue
        if digest in seen_digests:
            exclusions["batch_duplicate"] += 1
            record["exclusion"] = "batch_duplicate"
            candidates.append(record)
            continue
        row = training_row(
            title,
            decision,
            {
                "revision_id": page["revision_id"],
                "revision_sha1": page["revision_sha1"],
                "revision_timestamp": page["revision_timestamp"],
            },
        )
        if row["text"] != prose or row["split"] != "train":
            raise SystemExit("REFUSE: training_row did not keep the definition prose")
        row["split"] = "val"
        row["provenance"]["page_url"] = record["page_url"]
        row["provenance"]["oldid_url"] = (
            "https://en.wiktionary.org/w/index.php?oldid=" + str(page["revision_id"])
        )
        row["provenance"]["definition_line"] = decision.get("definition_line") or ""
        row["provenance"]["normalized_text_sha256"] = digest
        row["provenance"]["admission"] = "validation"
        row["provenance"]["validation_batch"] = BATCH_ID
        row["provenance"]["rights"] = "CC BY-SA 4.0 and GFDL"
        admitted.append(row)
        seen_digests.add(digest)
        blocked[digest] = "VALIDATION_BATCH"
        record["exclusion"] = None
        record["admitted"] = True
        candidates.append(record)
    admitted.sort(key=lambda row: (str(row["lineage"]), row["provenance"]["normalized_text_sha256"]))
    counts = {family: sum(1 for row in admitted if row["lineage"] == family) for family in TARGETS}
    return {
        "admitted_rows": admitted,
        "candidates": candidates,
        "counts": counts,
        "exclusions": dict(exclusions),
        "fetched": len(pages),
        "sense_rows": len(sense_rows),
    }


def _identity_states(ledger: IdentityLedger, rows: list[dict[str, Any]]) -> dict[str, str]:
    states: dict[str, str] = {}
    for row in rows:
        if row.get("task") != "classify" or row.get("split") not in {"train", "val"}:
            continue
        digest = normalized_text_sha256(str(row.get("text") or ""))
        record = ledger.identity(digest)
        if record is not None:
            states[digest] = derived_state(record)
    return states


def _support_table(rows: list[dict[str, Any]], ledger: IdentityLedger) -> dict[str, Any]:
    from hyperlexical.training_routing import route_rows

    routed, _accounting = route_rows(rows)
    return validation_family_support(
        routed["classify"]["val"],
        identity_state=_identity_states(ledger, rows),
    )


def _public_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    kept = dict(candidate)
    kept.pop("definition_line", None)
    return kept


def write_preview(result: dict[str, Any], discovery: dict[str, Any]) -> None:
    admitted = result["admitted_rows"]
    preview = {
        "admitted": [
            {
                "family": row["lineage"],
                "page": row["provenance"]["page"],
                "page_url": row["provenance"]["page_url"],
                "revision_id": row["provenance"]["revision_id"],
                "revision_sha1": row["provenance"]["revision_sha1"],
                "revision_timestamp": row["provenance"]["revision_timestamp"],
                "sense_labels": row["provenance"]["sense_labels"],
                "evidence": row["provenance"]["evidence"],
                "definition_prose": row["provenance"]["definition_prose"],
                "normalized_text_sha256": row["provenance"]["normalized_text_sha256"],
                "rights": row["provenance"]["rights"],
            }
            for row in admitted
        ],
        "counts": result["counts"],
        "discovery": discovery,
        "exclusions": result["exclusions"],
        "fetched": result["fetched"],
        "evidence_seal": evidence_seal(),
        "jev": "OFF",
    }
    path = DEST / "SETTLEMENT_PREVIEW.json"
    path.write_text(json.dumps(preview, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    print(json.dumps({"preview": str(path), "counts": result["counts"], "exclusions": result["exclusions"]}, sort_keys=True))


def commit_export(result: dict[str, Any], discovery: dict[str, Any]) -> dict[str, Any]:
    if EXPORT_PATH.exists():
        raise SystemExit("REFUSE: validation export already exists")
    admitted = result["admitted_rows"]
    counts = result["counts"]
    if counts.get("internet-slang", 0) < 1 or counts.get("memetic", 0) < 2:
        raise SystemExit(f"REFUSE: validation floor not met by new rows: {counts}")
    for row in admitted:
        if row["split"] != "val" or row["lineage"] not in TARGETS or row["class"] != "OBSERVED":
            raise SystemExit("REFUSE: admitted row left the validation contract")
        if row["text"] != row["provenance"]["definition_prose"]:
            raise SystemExit("REFUSE: validation text is not the definition prose")
        if not str(row["text"]).strip():
            raise SystemExit("REFUSE: empty validation text")
    source = SENSE_EXPORT.read_bytes()
    if hashlib.sha256(source).hexdigest() != SENSE_EXPORT_SHA256:
        raise SystemExit("REFUSE: sense export hash moved before copy")
    if not source.endswith(b"\n"):
        raise SystemExit("REFUSE: sense export does not end in a newline")
    extra = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in admitted)
    body = source + extra.encode("utf-8")
    if body[: len(source)] != source:
        raise SystemExit("REFUSE: sense export prefix changed")
    ledger = IdentityLedger.load(LEDGER)
    for row in admitted:
        digest = row["provenance"]["normalized_text_sha256"]
        if ledger.identity(digest) is not None:
            raise SystemExit(f"REFUSE: validation identity already exists in the ledger ({row['lineage']})")
    prior_events = len(ledger.events)
    prior_consumed = sum(1 for record in ledger.identities.values() if record.get("training_consumed"))
    prior_reserve = sum(1 for record in ledger.identities.values() if record.get("evaluation_reserved"))
    combined = _load_sense_rows() + admitted
    before = _support_table(_load_sense_rows(), ledger)
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST, 0o700)
    EXPORT_PATH.write_bytes(body)
    os.chmod(EXPORT_PATH, 0o600)
    export_sha = _sha256_file(EXPORT_PATH)
    for row in admitted:
        digest = row["provenance"]["normalized_text_sha256"]
        ledger.observe(
            digest,
            source_artifact=str(EXPORT_PATH),
            labels=[
                {
                    "task": "classify",
                    "class": "OBSERVED",
                    "lineage": row["lineage"],
                    "split": "val",
                }
            ],
            current_source=True,
            catalogued=True,
            provenance=(
                "classification v2 validation admission; not training; not evaluation reserve"
            ),
        )
        state = derived_state(ledger.identity(digest) or {})
        if state != "AVAILABLE":
            raise SystemExit(f"REFUSE: validation identity settled as {state}")
        record = ledger.identity(digest) or {}
        if record.get("training_consumed") or record.get("evaluation_reserved") or record.get("train_candidate"):
            raise SystemExit("REFUSE: validation identity received a training or reserve flag")
    appended = ledger.persist_append(LEDGER, prior_events)
    consumed_after = sum(1 for record in ledger.identities.values() if record.get("training_consumed"))
    reserve_after = sum(1 for record in ledger.identities.values() if record.get("evaluation_reserved"))
    if consumed_after != prior_consumed or reserve_after != prior_reserve:
        raise SystemExit("REFUSE: ledger training or reserve census changed")
    after = _support_table(combined, ledger)
    train_before = sum(1 for row in _load_sense_rows() if row.get("split") == "train")
    train_after = sum(1 for row in combined if row.get("split") == "train")
    if train_before != train_after:
        raise SystemExit("REFUSE: training row count changed")
    receipt = {
        "batch_id": BATCH_ID,
        "discovery": discovery,
        "evidence_seal": evidence_seal(),
        "exclusions": result["exclusions"],
        "export_path": str(EXPORT_PATH),
        "export_rows": result["sense_rows"] + len(admitted),
        "export_sha256": export_sha,
        "fetched_revisions": result["fetched"],
        "fresh_validation": counts,
        "jev": "OFF",
        "ledger_events_appended": appended,
        "ledger_state": "AVAILABLE",
        "moves_best": False,
        "rights": "CC BY-SA 4.0 and GFDL",
        "schema": "hyperlex.classification.v2.validation_export.v1",
        "sense_export": str(SENSE_EXPORT),
        "sense_export_sha256": SENSE_EXPORT_SHA256,
        "sense_prefix_preserved": True,
        "source": "en.wiktionary.org",
        "support_after": after["support"],
        "support_before": before["support"],
        "trains": False,
        "train_rows": train_after,
        "validation_identities": [
            {
                "family": row["lineage"],
                "normalized_text_sha256": row["provenance"]["normalized_text_sha256"],
                "page": row["provenance"]["page"],
                "page_url": row["provenance"]["page_url"],
                "revision_id": row["provenance"]["revision_id"],
                "revision_sha1": row["provenance"]["revision_sha1"],
                "revision_timestamp": row["provenance"]["revision_timestamp"],
                "definition_prose": row["text"],
                "sense_labels": row["provenance"]["sense_labels"],
                "evidence": row["provenance"]["evidence"],
                "rights": "CC BY-SA 4.0 and GFDL",
            }
            for row in admitted
        ],
    }
    receipt_path = DEST / "VALIDATION_EXPORT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(receipt_path, 0o600)
    candidates_path = DEST / "CANDIDATES.json"
    candidates_path.write_text(
        json.dumps([_public_candidate(item) for item in result["candidates"]], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.chmod(candidates_path, 0o600)
    print(json.dumps({"export": str(EXPORT_PATH), "sha256": export_sha, "counts": counts, "support": after["support"]}, sort_keys=True))
    return receipt


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--preview"
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    discovery_path = DEST / "DISCOVERY.json"
    fetched_path = DEST / "FETCHED.jsonl"
    if mode == "--discover" or not fetched_path.is_file():
        discovery = discover(DEST)
    else:
        discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
    if mode == "--discover":
        print(json.dumps(discovery, sort_keys=True))
        return 0
    result = settle(_load_fetched(fetched_path))
    write_preview(result, discovery)
    if mode == "--commit":
        commit_export(result, discovery)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
