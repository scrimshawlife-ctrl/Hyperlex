"""Fetch Wiktionary training positives for the fifteen unsupported v2 families.

MediaWiki revisions are the provenance. Evaluation identities are not copied.
This does not train and does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from hyperlexical.classification_v2_acquire import (
    ACTIVE_TARGETS,
    DISCOVERY_QUERIES,
    GLOSS_DISCOVERY,
    PREFERRED_OBSERVED,
    classify_wikitext,
    evidence_seal,
    training_row,
)
from hyperlexical.holdout_guard import normalized_text_sha256
from hyperlexical.identity_ledger import PLANNING_TARGETS, IdentityLedger

API = "https://en.wiktionary.org/w/api.php"
UA = "HyperlexClassificationV2Acquire/1.0 (training acquisition; mediawiki provenance)"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926")
HISTORICAL_EXPORT = Path(
    "/home/morpheus/hlx-private/d1-spark-tree-20260924T213846Z/morph78-train-export.jsonl"
)
DEST = Path("/home/morpheus/hlx-private/classification-v2-acquire-20260929")
BATCH_ID = "HLX-CLASSIFICATION-V2-TRAIN-ACQUIRE-20260929"
MAX_TITLES = 80
PAUSE = 4.0
HASH_KEYS = (
    "normalized_text_sha256",
    "normtext_sha256",
    "normalized_hash",
    "text_hash",
)

ISOLATION_FILES = (
    HISTORICAL_EXPORT,
    LEDGER / "settlement" / "events.jsonl",
    LEDGER / "settlement" / "admit-20260926-002.jsonl",
    Path("/home/morpheus/hlx-private/heldout-stream/store/rows.jsonl"),
    Path("/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-001/RAW_CANDIDATES.jsonl"),
    Path("/home/morpheus/hlx-private/exp-20260929-select-006/reserve-acquisition-002/RAW_CANDIDATES.jsonl"),
    Path("/home/morpheus/hlx-private/exp-20260929-select-007/reserve-001/RAW_CANDIDATES.jsonl"),
    Path("/home/morpheus/hlx-private/exp-20260927-select-005/source-fetch-001/RAW_CANDIDATES.jsonl"),
    Path("/home/morpheus/hlx-private/exp-20260927-select-005/harvest-002/RAW_HARVEST.jsonl"),
    LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001/RESIDUAL_THRESHOLD_V1_CALIBRATION_LABELS.jsonl",
    LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001/RESIDUAL_THRESHOLD_V2_CALIBRATION_LABELS.jsonl",
    LEDGER / "operator-review/HLX-EVAL-UNBIND-SEMANTIC-EVIDENCE-SOURCE-V1-001/RESIDUAL_THRESHOLD_V2_MEASUREMENT_MANIFEST.jsonl",
)


def _api(params: dict[str, str]) -> dict[str, Any]:
    query = dict(params)
    query["format"] = "json"
    query["formatversion"] = "2"
    url = API + "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 4:
                time.sleep(25 + attempt * 10)
                continue
            raise
        finally:
            time.sleep(PAUSE)


def _put(blocked: dict[str, str], digest: str, reason: str) -> None:
    if digest and len(digest) == 64 and digest not in blocked:
        blocked[digest] = reason


def _consume_jsonl(path: Path, blocked: dict[str, str], reason: str) -> int:
    if not path.is_file():
        return 0
    seen = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            for key in HASH_KEYS:
                value = row.get(key)
                if isinstance(value, str):
                    _put(blocked, value, reason)
                    seen += 1
            text = row.get("text")
            if isinstance(text, str) and text:
                _put(blocked, normalized_text_sha256(text), reason)
                seen += 1
    return seen


def blocked_identities() -> dict[str, str]:
    blocked: dict[str, str] = {}
    ledger = json.loads((LEDGER / "ledger.json").read_text(encoding="utf-8"))
    for record in ledger["identities"]:
        state = str(record.get("state") or "")
        if record.get("evaluation_reserved") and state == "EVAL_RESERVE":
            reason = "EVAL_RESERVE"
        elif record.get("evaluation_spent") or state == "EVAL_SPENT":
            reason = "EVAL_SPENT"
        elif state == "EVAL_ABANDONED" or record.get("evaluation_abandoned"):
            reason = "EVAL_ABANDONED"
        elif record.get("training_consumed") or state == "TRAIN_CONSUMED":
            reason = "TRAIN_CONSUMED"
        else:
            reason = "LEDGER_IDENTITY"
        _put(blocked, str(record.get("normalized_text_sha256") or ""), reason)
    for path in ISOLATION_FILES:
        _consume_jsonl(path, blocked, path.name)
    return blocked


def _search(phrase: str, *, gloss: bool) -> list[str]:
    if gloss:
        query = 'insource:"' + phrase + '"'
    else:
        query = 'insource:"{{lb|en|' + phrase + '}}"'
    titles: list[str] = []
    offset = 0
    while len(titles) < MAX_TITLES:
        payload = _api(
            {
                "action": "query",
                "list": "search",
                "srlimit": "20",
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
        offset += 20
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
    return found


def harvest() -> dict[str, Any]:
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    blocked = blocked_identities()
    exclusions: Counter[str] = Counter()
    admitted: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    seen_digests: set[str] = set()
    discovered = 0
    fetched = 0
    per_family: dict[str, list[dict[str, Any]]] = {family: [] for family in ACTIVE_TARGETS}
    for family in ACTIVE_TARGETS:
        queries = [(label, False) for label in DISCOVERY_QUERIES.get(family, ())]
        queries.extend((phrase, True) for phrase in GLOSS_DISCOVERY.get(family, ()))
        for phrase, gloss in queries:
            if len(per_family[family]) >= PREFERRED_OBSERVED:
                break
            titles = _search(phrase, gloss=gloss)
            discovered += len(titles)
            pending = [title for title in titles if title.casefold() not in seen_titles]
            pages = _fetch(pending)
            fetched += len(pages)
            for title in pending:
                seen_titles.add(title.casefold())
                if len(per_family[family]) >= PREFERRED_OBSERVED:
                    break
                page = pages.get(title)
                if page is None:
                    exclusions["revision_missing"] += 1
                    continue
                decision = classify_wikitext(page["content"])
                if decision["status"] != "unique" or decision["family"] != family:
                    reason = decision["status"] if decision["family"] == family or decision["status"] != "unique" else "other_family"
                    exclusions[str(reason)] += 1
                    continue
                digest = normalized_text_sha256(title)
                if digest in blocked:
                    exclusions[blocked[digest]] += 1
                    continue
                if digest in seen_digests:
                    exclusions["batch_duplicate"] += 1
                    continue
                row = training_row(title, decision, page)
                row["provenance"]["discovery_query"] = phrase
                admitted.append(row)
                per_family[family].append(row)
                seen_digests.add(digest)
    counts = {family: len(rows) for family, rows in per_family.items()}
    return {
        "admitted": admitted,
        "blocked_identities": len(blocked),
        "counts": counts,
        "discovered": discovered,
        "exclusions": dict(exclusions),
        "fetched": fetched,
        "titles_seen": len(seen_titles),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def publish(result: dict[str, Any]) -> dict[str, Any]:
    export_path = DEST / "civilian.v0.1.jsonl"
    admitted = result["admitted"]
    if any(row["lineage"] not in ACTIVE_TARGETS or row["class"] != "OBSERVED" for row in admitted):
        raise SystemExit("REFUSE: admitted row left the frozen target set")
    lines = HISTORICAL_EXPORT.read_text(encoding="utf-8").splitlines()
    extra = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in admitted]
    body = "\n".join([*lines, *extra]) + "\n"
    ledger = IdentityLedger.load(LEDGER)
    prior = len(ledger.events)
    report = ledger.admit(
        admitted,
        batch_id=BATCH_ID,
        source_artifact=str(export_path),
        targets={key: 0 for key in PLANNING_TARGETS},
    )
    if report["unique_admitted_to_eval_reserve"] != 0:
        raise SystemExit("REFUSE: training acquisition routed a row into EVAL_RESERVE")
    if report["rejected_unique_identities"] != 0:
        raise SystemExit("REFUSE: an admitted row collided with an existing identity")
    for row in admitted:
        ledger.transition(
            normalized_text_sha256(row["text"]),
            "TRAIN_CONSUMED",
            source_artifact=str(export_path),
            provenance="classification v2 training acquisition",
        )
    export_path.write_text(body, encoding="utf-8")
    appended = ledger.persist_append(LEDGER, prior)
    receipt = {
        "batch_id": BATCH_ID,
        "blocked_identities": result["blocked_identities"],
        "discovered": result["discovered"],
        "evidence_seal": evidence_seal(),
        "exclusions": result["exclusions"],
        "export_path": str(export_path),
        "export_rows": len(lines) + len(admitted),
        "export_sha256": _sha256_file(export_path),
        "fetched_revisions": result["fetched"],
        "fresh_observed": result["counts"],
        "fresh_rows": len(admitted),
        "historical_export": str(HISTORICAL_EXPORT),
        "historical_export_sha256": _sha256_file(HISTORICAL_EXPORT),
        "inferred_admitted": 0,
        "jev": "OFF",
        "ledger_events_appended": appended,
        "ledger_report": {
            key: report[key]
            for key in (
                "unique_routed_to_train_candidate",
                "unique_admitted_to_eval_reserve",
                "rejected_unique_identities",
            )
        },
        "rights": "CC BY-SA 4.0 and GFDL",
        "source": "en.wiktionary.org",
        "titles_seen": result["titles_seen"],
        "trains": False,
        "moves_best": False,
    }
    (DEST / "ACQUISITION.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> None:
    result = harvest()
    receipt = publish(result)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
