"""Fetch a balanced fresh Classification v4 reserve acquire pool.

Preregistered floors in classification_v4_balanced_reserve_acquire. Does not
train, retune, score a reserve, reuse spent v2/v3, or move BEST.
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

REPO = Path("/home/morpheus/Hyperlex")
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")
SURFACE = Path(
    "/home/morpheus/hlx-private/classification-v3-evidence-surface-20260930/"
    "EVIDENCE_SURFACE.jsonl"
)
SURFACE_SHA = "7339c044596a4cc2eb5ae17f3fbab185fface9abffb6151bdb0db69eca0d2d3a"
SPENT_V2 = Path(
    "/home/morpheus/hlx-private/classification-v2-train-ready-20260929/"
    "reserve-eval-rows.jsonl"
)
SPENT_V2_SHA = "8c5276442ce37cf99fff597653a28917b3b4dc69ac87ad01f815fa458416ed36"
SPENT_V3 = Path(
    "/home/morpheus/hlx-private/classification-v3-reserve-20260930/reserve-rows.jsonl"
)
SPENT_V3_SHA = "abb8bf22012bb450dba05ce3129e32c2f28fabe9911030b28c68c5b99d39b937"
HUB = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/"
    "civilian.v0.7.hub.jsonl"
)
HUB_SHA = "0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
DEST = Path(
    "/home/morpheus/hlx-private/classification-v4-balanced-reserve-acquire-20260930"
)
API = "https://en.wiktionary.org/w/api.php"
UA = "HyperlexClassificationV4Acquire/1.0 (balanced reserve acquire; mediawiki provenance)"
TEMPLATE_NAMES = ("lb", "lbl", "tlb")
_HEADING = re.compile(r"=+\s*([^=]+?)\s*=+")
_SENSE = re.compile(
    r"\{\{\s*(lb|lbl|tlb)\s*\|\s*en\s*\|([^{}]*)\}\}",
    re.IGNORECASE,
)
_LINK = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
_MARKUP = re.compile(r"''+")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    try:
        return sha256_file(path)
    except PermissionError:
        import subprocess

        completed = subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.split()[0]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def pin_inputs() -> None:
    if sha256_file(SURFACE) != SURFACE_SHA:
        fail("evidence surface digest mismatch")
    if sha256_file(SPENT_V2) != SPENT_V2_SHA:
        fail("spent v2 rows digest mismatch")
    if sha256_file(SPENT_V3) != SPENT_V3_SHA:
        fail("spent v3 rows digest mismatch")
    if sha256_file(HUB) != HUB_SHA:
        fail("hub export digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")


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
                fail(f"mediawiki http {exc.code}")
            time.sleep(delay)
            delay *= 2
    else:
        fail("mediawiki rate limit")
    time.sleep(0.8)
    if not isinstance(payload, dict) or "error" in payload:
        fail("mediawiki query failed")
    return payload


def sense_label_arguments(line: str) -> list[str]:
    found: list[str] = []
    for match in _SENSE.finditer(line):
        for part in match.group(2).split("|"):
            token = part.strip()
            if token:
                found.append(token)
    return found


def definition_prose(line: str) -> str:
    text = _SENSE.sub(" ", line)
    text = _LINK.sub(r"\2", text)
    text = _TEMPLATE.sub(" ", text)
    text = _MARKUP.sub("", text)
    text = text.lstrip("#").strip()
    return " ".join(text.split())


def english_section(wikitext: str) -> str:
    parts = re.split(r"\n(?===[^=])", "\n" + wikitext)
    for part in parts:
        lines = part.strip().splitlines()
        if not lines:
            continue
        if lines[0].strip("= ").casefold() == "english":
            return part
    return ""


def first_qualifying_line(
    wikitext: str, *, want_family: str | None, want_none: bool
) -> dict[str, Any] | None:
    from hyperlexical.classification_v4_balanced_reserve_acquire import (
        family_for_sense_labels,
    )

    section = english_section(wikitext)
    if not section or wikitext.lstrip().lower().startswith("#redirect"):
        return None
    for line in section.splitlines():
        if not line.startswith("# ") or line.startswith(("#:", "##")):
            continue
        mapped = family_for_sense_labels(sense_label_arguments(line))
        prose = definition_prose(line)
        if not prose:
            continue
        if want_none and mapped.get("status") == "none":
            return {
                "evidence_subtype": "HARD_NONE",
                "line": line,
                "lineage": "none",
                "prose": prose,
            }
        if (
            want_family
            and mapped.get("status") == "unique"
            and mapped.get("family") == want_family
        ):
            return {
                "evidence_subtype": "POSITIVE_EVIDENCE",
                "line": line,
                "lineage": want_family,
                "prose": prose,
            }
    return None


def blocked_identities() -> dict[str, str]:
    from hyperlexical.holdout_guard import normalized_text_sha256

    blocked: dict[str, str] = {}

    def put(digest: str, reason: str) -> None:
        if digest and len(digest) == 64 and digest not in blocked:
            blocked[digest] = reason

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    for record in ledger.get("identities") or []:
        digest = str(record.get("normalized_text_sha256") or "")
        state = str(record.get("state") or "")
        if record.get("evaluation_spent") or state == "EVAL_SPENT":
            put(digest, "EVAL_SPENT")
        elif record.get("evaluation_reserved") or state in {
            "EVAL_RESERVE",
            "EVAL_BOUND",
        }:
            put(digest, "EVAL_RESERVE")
        elif record.get("evaluation_abandoned") or state == "EVAL_ABANDONED":
            put(digest, "EVAL_ABANDONED")
        elif record.get("training_consumed") or state == "TRAIN_CONSUMED":
            put(digest, "TRAIN_CONSUMED")
        else:
            put(digest, "LEDGER_IDENTITY")
    for path, reason in (
        (SPENT_V2, "spent_v2"),
        (SPENT_V3, "spent_v3"),
        (SURFACE, "surface"),
        (HUB, "hub"),
    ):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            for key in (
                "identity",
                "normalized_text_sha256",
                "normalized_hash",
                "normtext_sha256",
            ):
                value = row.get(key)
                if isinstance(value, str):
                    put(value, reason)
            text = row.get("text")
            if isinstance(text, str) and text.strip():
                put(normalized_text_sha256(text), reason)
    return blocked


def search_titles(label: str, *, scan_cap: int = 100) -> list[str]:
    titles: list[str] = []
    for template in TEMPLATE_NAMES:
        if len(titles) >= scan_cap:
            break
        offset = 0
        query = 'insource:"{{' + template + "|en|" + label + '}}"'
        while len(titles) < scan_cap:
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
                if title and ":" not in title and "|" not in title:
                    titles.append(title)
                if len(titles) >= scan_cap:
                    break
            if not payload.get("continue"):
                break
            offset += 20
    # unique preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for title in titles:
        key = title.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(title)
    return ordered


def fetch_revisions(titles: list[str]) -> dict[str, dict[str, Any]]:
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
            if not isinstance(content, str) or not isinstance(revid, int) or not sha1:
                continue
            found[title] = {
                "content": content,
                "revision_id": revid,
                "revision_sha1": sha1,
                "revision_timestamp": timestamp,
                "title": title,
            }
    return found


def collect_for_target(
    *,
    labels: list[str],
    want_family: str | None,
    want_none: bool,
    quota: int,
    blocked: dict[str, str],
    kept: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    from hyperlexical.classification_v4_balanced_reserve_acquire import (
        build_acquire_row,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    for label in labels:
        if len(rows) >= quota:
            break
        titles = search_titles(label)
        cursor = 0
        while cursor < len(titles) and len(rows) < quota:
            chunk = titles[cursor : cursor + 10]
            cursor += 10
            pages = fetch_revisions(chunk)
            for title in chunk:
                if len(rows) >= quota:
                    break
                if title.casefold() in {k.casefold() for k in kept}:
                    rejected["title_kept"] += 1
                    continue
                page = pages.get(title)
                if page is None:
                    rejected["missing_revision"] += 1
                    continue
                hit = first_qualifying_line(
                    page["content"], want_family=want_family, want_none=want_none
                )
                if hit is None:
                    rejected["no_qualifying_sense"] += 1
                    continue
                text = hit["prose"]
                identity = normalized_text_sha256(text)
                if identity in blocked:
                    rejected[f"blocked:{blocked[identity]}"] += 1
                    continue
                if identity in kept:
                    rejected["identity_kept"] += 1
                    continue
                try:
                    row = build_acquire_row(
                        {
                            "text": text,
                            "lineage": hit["lineage"],
                            "class": "OBSERVED",
                            "evidence_subtype": hit["evidence_subtype"],
                            "revision_id": page["revision_id"],
                            "revision_sha1": page["revision_sha1"],
                            "revision_timestamp": page["revision_timestamp"],
                            "source_url": (
                                "https://en.wiktionary.org/wiki/"
                                + urllib.parse.quote(title.replace(" ", "_"))
                            ),
                            "title": title,
                            "rights": "CC-BY-SA",
                        }
                    )
                except ValueError as exc:
                    rejected[f"row_invalid:{exc}"] += 1
                    continue
                kept[identity] = row
                rows.append(row)
    return rows, rejected


def main() -> int:
    from hyperlexical.classification_v4_balanced_reserve_acquire import (
        ACQUIRE_RULE,
        DISCOVERY_NONE,
        DISCOVERY_PER_FAMILY,
        FAMILY_SENSE_LABELS,
        NONE_SENSE_LABELS,
        acquire_contract,
        assemble_acquire_receipt,
        audit_balance,
        decide_acquire_disposition,
        next_action_for_acquire_disposition,
        validate_acquire_disjointness,
        canonical_json,
        sha256_text,
    )

    pin_inputs()
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST, 0o700)
    rows_path = DEST / "acquire-rows.jsonl"
    if rows_path.exists() or (DEST / "ACQUIRE_RECEIPT.json").exists():
        fail("acquire destination already frozen")

    write_private(DEST / "CONTRACT.json", acquire_contract())
    blocked = blocked_identities()
    write_private(
        DEST / "ISOLATION.json",
        {"blocked_n": len(blocked), "rule": ACQUIRE_RULE},
    )

    kept: dict[str, dict[str, Any]] = {}
    rejected_total: Counter[str] = Counter()
    family_got: dict[str, int] = {}
    for family, labels in FAMILY_SENSE_LABELS.items():
        rows, rejected = collect_for_target(
            labels=list(labels),
            want_family=family,
            want_none=False,
            quota=DISCOVERY_PER_FAMILY,
            blocked=blocked,
            kept=kept,
        )
        family_got[family] = len(rows)
        rejected_total.update(rejected)
        print(f"family {family}: got={len(rows)} rejected={dict(rejected)}", flush=True)

    none_rows, none_rejected = collect_for_target(
        labels=list(NONE_SENSE_LABELS),
        want_family=None,
        want_none=True,
        quota=DISCOVERY_NONE,
        blocked=blocked,
        kept=kept,
    )
    rejected_total.update(none_rejected)
    print(f"none: got={len(none_rows)} rejected={dict(none_rejected)}", flush=True)

    rows = sorted(kept.values(), key=lambda item: item["identity"])
    body = "\n".join(canonical_json(row) for row in rows) + ("\n" if rows else "")
    rows_sha = sha256_text(body)
    write_private(rows_path, body)

    invalid = validate_acquire_disjointness(rows, blocked_ids=blocked)
    balance = audit_balance(rows)
    disposition = decide_acquire_disposition(
        invalid_reasons=invalid, balance=balance
    )
    next_action = next_action_for_acquire_disposition(disposition)
    receipt = assemble_acquire_receipt(
        {
            "balance": balance,
            "disposition": disposition,
            "next_action": next_action,
            "rows_sha256": rows_sha,
        }
    )
    summary = {
        "BEST": "UNCHANGED",
        "balance": balance,
        "disposition": disposition,
        "family_got": family_got,
        "n": len(rows),
        "next_action": next_action,
        "none_got": len(none_rows),
        "receipt_sha256": receipt["receipt_sha256"],
        "rejected": dict(rejected_total),
        "rows_sha256": rows_sha,
        "rule": ACQUIRE_RULE,
        "score_reserve": False,
        "train": False,
    }
    write_private(DEST / "ACQUIRE_RECEIPT.json", receipt)
    write_private(DEST / "SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
