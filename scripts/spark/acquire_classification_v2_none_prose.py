"""Acquire encyclopedic NONE prose for the applicability surface.

English Wikipedia lead sentences from a frozen geographic category list.
The family label is not consulted. A frozen gloss match rejects the sentence.
Reserve, spent, held-out, and existing export identities are blocked.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.classification_v2_acquire import GLOSS_RULES  # noqa: E402
from hyperlexical.classification_v2_acquire_run import blocked_identities  # noqa: E402
from hyperlexical.classification_v2_surface import SURFACE_PROSE, surface_form  # noqa: E402
from hyperlexical.holdout_guard import normalized_text_sha256  # noqa: E402

import re

DEST = Path("/home/morpheus/hlx-private/classification-v2-surface-20260929")
EXPORT = Path("/home/morpheus/hlx-private/classification-v2-validation-20260929/civilian.v0.2.jsonl")
OUT = DEST / "NONE_PROSE.jsonl"
API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "HyperlexClassificationV2Surface/1.0 (applicability surface; encyclopedic none)"
PAUSE = 2.5
TARGET = 48
CATEGORIES = (
    "Category:Rivers of Scotland",
    "Category:Mountains and hills of Wales",
    "Category:Lighthouses in Wales",
    "Category:Country houses in Cornwall",
    "Category:Islands of Greece",
    "Category:Lakes of Sweden",
)
GLOSS = tuple((family, re.compile(pattern, re.IGNORECASE)) for family, pattern in GLOSS_RULES)


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def api(params: dict[str, str]) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json"})
    request = urllib.request.Request(API + "?" + query, headers={"User-Agent": USER_AGENT})
    delay = PAUSE
    for _attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            time.sleep(PAUSE)
            return payload
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            time.sleep(delay)
            delay *= 2
    fail("wikipedia returned 429 after retries")


def blocked_texts() -> dict[str, str]:
    blocked = blocked_identities()
    with EXPORT.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            text = str(row.get("text") or "")
            if text:
                blocked.setdefault(normalized_text_sha256(text), "EXPORT_TEXT")
    return blocked


def gloss_family(sentence: str) -> str | None:
    for family, pattern in GLOSS:
        if pattern.search(sentence):
            return family
    return None


def lead_sentence(extract: str) -> str:
    text = " ".join(extract.split())
    return text.strip()


def category_titles(category: str) -> list[str]:
    titles: list[str] = []
    continuation = ""
    while len(titles) < 80:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "page",
            "cmlimit": "20",
            "cmnamespace": "0",
        }
        if continuation:
            params["cmcontinue"] = continuation
        payload = api(params)
        members = payload.get("query", {}).get("categorymembers", [])
        for member in members:
            title = str(member.get("title") or "")
            if title and title not in titles:
                titles.append(title)
        continuation = str(payload.get("continue", {}).get("cmcontinue") or "")
        if not continuation:
            break
    return titles


def fetch_pages(titles: list[str]) -> list[dict]:
    found = []
    for start in range(0, len(titles), 8):
        batch = titles[start : start + 8]
        payload = api(
            {
                "action": "query",
                "prop": "extracts|revisions",
                "exintro": "1",
                "explaintext": "1",
                "exsentences": "1",
                "rvprop": "ids|timestamp|sha1",
                "titles": "|".join(batch),
            }
        )
        pages = payload.get("query", {}).get("pages", {})
        for page in pages.values():
            if page.get("missing") is not None:
                continue
            found.append(page)
    return found


def row_from_page(page: dict, blocked: dict[str, str]) -> tuple[dict | None, str]:
    sentence = lead_sentence(str(page.get("extract") or ""))
    if not sentence:
        return None, "empty"
    folded = sentence.casefold()
    if "may refer to" in folded:
        return None, "disambiguation"
    if surface_form(sentence) != SURFACE_PROSE:
        return None, "not_prose"
    family = gloss_family(sentence)
    if family:
        return None, "gloss:" + family
    digest = normalized_text_sha256(sentence)
    if digest in blocked:
        return None, "blocked:" + blocked[digest]
    revisions = page.get("revisions") or []
    if not revisions:
        return None, "no_revision"
    revision = revisions[0]
    title = str(page.get("title") or "")
    revid = int(revision["revid"])
    return {
        "class": "INFERRED",
        "fillers": [],
        "license": "CC BY-SA 4.0 (English Wikipedia lead sentence)",
        "lineage": "none",
        "provenance": {
            "admission": "surface-none-prose",
            "category_source": "frozen_geographic_categories",
            "none_rule": (
                "English Wikipedia lead sentence from a frozen geographic category. "
                "Rejected when a frozen family gloss matches. Surface must be PROSE."
            ),
            "normalized_text_sha256": digest,
            "oldid_from_mediawiki": True,
            "oldid_url": f"https://en.wikipedia.org/w/index.php?oldid={revid}",
            "page": title,
            "page_url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            "representation": "PROSE",
            "revision_id": revid,
            "revision_sha1": revision.get("sha1"),
            "revision_timestamp": revision.get("timestamp"),
            "rights": "CC BY-SA 4.0",
            "source": "en.wikipedia.org",
            "surface": "PROSE",
        },
        "role_scheme": None,
        "roles": [],
        "split": "train",
        "stage": "circulating",
        "task": "classify",
        "text": sentence,
        "typology": [],
    }, "accepted"


def assign_splits(rows: list[dict]) -> None:
    rows.sort(key=lambda row: row["provenance"]["normalized_text_sha256"])
    for index, row in enumerate(rows):
        row["split"] = "val" if index % 6 == 0 else "train"


def main() -> int:
    if OUT.exists():
        fail(f"NONE prose file already exists: {OUT}")
    blocked = blocked_texts()
    accepted: list[dict] = []
    exclusions: dict[str, int] = {}
    seen: set[str] = set()
    for category in CATEGORIES:
        if len(accepted) >= TARGET:
            break
        titles = category_titles(category)
        pages = fetch_pages(titles)
        for page in pages:
            if len(accepted) >= TARGET:
                break
            title = str(page.get("title") or "")
            if title in seen:
                continue
            seen.add(title)
            row, reason = row_from_page(page, blocked)
            if row is None:
                exclusions[reason] = exclusions.get(reason, 0) + 1
                continue
            digest = row["provenance"]["normalized_text_sha256"]
            blocked[digest] = "NONE_PROSE"
            row["provenance"]["category"] = category
            accepted.append(row)
    assign_splits(accepted)
    train = sum(1 for row in accepted if row["split"] == "train")
    val = sum(1 for row in accepted if row["split"] == "val")
    if train < 8 or val < 2:
        fail(f"NONE prose cells are too small: train {train} val {val} exclusions {exclusions}")
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST, 0o700)
    with OUT.open("w", encoding="utf-8") as handle:
        for row in accepted:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(OUT, 0o600)
    print(json.dumps({"accepted": len(accepted), "exclusions": exclusions, "train": train, "val": val, "path": str(OUT)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
