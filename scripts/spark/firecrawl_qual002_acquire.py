#!/usr/bin/env python3
"""Firecrawl-backed NATURAL OBSERVED feeder for QUAL-002.

Bypasses MediaWiki API 429s by scraping Wiktionary/Wikipedia category + lemma
pages via the Firecrawl CLI (keyless scrape works). Emits jsonl rows compatible
with run_classification_v6_qualification_surface_002.acquire_fresh resume.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Forward 18-family ontology (social-evaluation merge)
os.environ.setdefault("HLX_V2_FORWARD_ONTOLOGY", "1")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY  # noqa: E402
from hyperlexical.classification_v6_data_foundation_acquire import (  # noqa: E402
    DOMAIN_IRRELEVANT_CATEGORIES,
    WIKI_ORDINARY_CATEGORIES,
    WIKT_FAMILY_CATEGORIES,
    clean_wikitext,
)

SEED = 20261002
FIRECRAWL = os.environ.get("FIRECRAWL_BIN", "firecrawl")
OUT_DIR = Path(os.environ.get("HLX_FIRECRAWL_DIR") or (REPO / ".firecrawl" / "qual002"))

# Working Firecrawl category overrides (foundation names that 404 stay unused).
FIRECRAWL_WIKT_CATEGORIES: dict[str, tuple[str, ...]] = {
    **WIKT_FAMILY_CATEGORIES,
    "social-evaluation": (
        "Category:English vulgarities",
        "Category:English slang",
    ),
    "regional-cultural": (
        "Category:British English",
        "Category:en:United Kingdom",
    ),
    "relationship-dating": (
        "Category:en:Love",
        "Category:en:Sex",
    ),
    "memetic": (
        "Category:English internet slang",
        "Category:en:Internet",
    ),
    "internet-slang": (
        "Category:English internet slang",
        "Category:English text messaging slang",
    ),
}

_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]+\)")
_MD_BOLD = re.compile(r"\*\*|__")
_MD_ITAL = re.compile(r"(?<!\*)\*(?!\*)|_")
_NUM_DEF = re.compile(r"(?m)^\d+\.\s+(.+)$")
_WIKI_URL_CLEAN = re.compile(r'\s*"[^"]*"\s*$')
_LOCK = threading.Lock()


def _run(cmd: list[str], retries: int = 3) -> subprocess.CompletedProcess[str]:
    last: subprocess.CompletedProcess[str] | None = None
    for attempt in range(retries):
        last = subprocess.run(cmd, capture_output=True, text=True)
        if last.returncode == 0:
            return last
        sleep_s = min(45.0, (2**attempt) + random.random())
        err = (last.stderr or last.stdout or "")[:160]
        print(f"firecrawl_retry rc={last.returncode} sleep={sleep_s:.1f}s stderr={err!r}", flush=True)
        time.sleep(sleep_s)
    assert last is not None
    return last


def scrape_to(url: str, out: Path, *, fmt: str | None = None, main: bool = False) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 40:
        return True
    cmd = [FIRECRAWL, "scrape", url, "-o", str(out)]
    if fmt:
        cmd.extend(["--format", fmt])
    if main:
        cmd.append("--only-main-content")
    proc = _run(cmd)
    ok = proc.returncode == 0 and out.exists() and out.stat().st_size > 40
    if not ok:
        print(f"scrape_fail {url}", flush=True)
        if out.exists() and out.stat().st_size <= 40:
            out.unlink(missing_ok=True)
    return ok


def cat_slug(cat: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", cat)[:120]


def wikt_category_url(cat: str) -> str:
    title = cat.replace(" ", "_")
    return "https://en.wiktionary.org/wiki/" + urllib.parse.quote(title, safe=":_")


def wiki_category_url(cat: str) -> str:
    title = cat.replace(" ", "_")
    return "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title, safe=":_")


def filter_wikt_lemmas(links: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for u in links:
        if not u.startswith("https://en.wiktionary.org/wiki/"):
            continue
        title = urllib.parse.unquote(u.split("/wiki/", 1)[1]).split("#", 1)[0]
        if not title or ":" in title:
            continue
        if title in seen:
            continue
        seen.add(title)
        out.append(
            "https://en.wiktionary.org/wiki/"
            + urllib.parse.quote(title.replace(" ", "_"), safe="()%'")
        )
    return out


def lemmas_from_md(md: str) -> list[str]:
    if "does not yet have a category" in md.lower():
        return []
    links = re.findall(r"\((https://en\.wiktionary\.org/wiki/[^)\s]+)\)", md)
    return filter_wikt_lemmas(links)


def filter_wiki_articles_from_md(md: str) -> list[str]:
    links = re.findall(r"\((https://en\.wikipedia\.org/wiki/[^)\s]+)\)", md)
    out: list[str] = []
    seen: set[str] = set()
    for raw in links:
        u = _WIKI_URL_CLEAN.sub("", raw).rstrip("\\")
        title = urllib.parse.unquote(u.split("/wiki/", 1)[1]).split("#", 1)[0]
        if not title or ":" in title:
            continue
        if title in seen:
            continue
        seen.add(title)
        out.append(
            "https://en.wikipedia.org/wiki/"
            + urllib.parse.quote(title.replace(" ", "_"), safe="()%'")
        )
    return out


def strip_md(text: str) -> str:
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_BOLD.sub("", text)
    text = _MD_ITAL.sub("", text)
    text = re.sub(r"`+", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"↑\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .;,:")


def extract_wikt_senses(md: str) -> list[str]:
    eng = md
    m = re.search(r"(?im)^##\s+English\s*$", md)
    if m:
        eng = md[m.end() :]
        nxt = re.search(r"(?im)^##\s+\S+", eng)
        if nxt:
            eng = eng[: nxt.start()]
    senses: list[str] = []
    for match in _NUM_DEF.finditer(eng):
        line = strip_md(match.group(1))
        body = re.sub(r"^\([^)]*\)\s*", "", line).strip()
        if len(body) < 12:
            continue
        if body.lower().startswith("citations"):
            continue
        senses.append(body)
    return senses


def extract_wiki_paras(md: str, *, max_paras: int = 3) -> list[str]:
    paras: list[str] = []
    body = md
    m = re.search(r"(?im)^From Wikipedia", md)
    if m:
        body = md[m.end() :]
    for chunk in re.split(r"\n\s*\n", body):
        text = strip_md(chunk.replace("\n", " "))
        if len(text) < 40:
            continue
        if text.startswith("[") or text.startswith("!"):
            continue
        low = text.lower()
        if low.startswith("jump to") or low.startswith("contents"):
            continue
        if "may refer to" in low and len(text) < 80:
            continue
        paras.append(text[:800])
        if len(paras) >= max_paras:
            break
    return paras


def lemma_path(url: str) -> Path:
    title = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
    return OUT_DIR / "lemmas" / f"{cat_slug(title)}.md"


def wiki_path(url: str) -> Path:
    title = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
    return OUT_DIR / "wiki" / f"{cat_slug(title)}.md"


def load_existing(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        if not path or not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def discover_wikt_lemmas(family: str) -> list[str]:
    urls: list[str] = []
    for cat in FIRECRAWL_WIKT_CATEGORIES.get(family, ()):
        # Prefer links JSON; fall back to markdown member list.
        jout = OUT_DIR / "cats" / f"wikt_{cat_slug(cat)}.json"
        if scrape_to(wikt_category_url(cat), jout, fmt="links"):
            try:
                payload = json.loads(jout.read_text(encoding="utf-8"))
                got = filter_wikt_lemmas(payload.get("links") or [])
                if got:
                    urls.extend(got)
                else:
                    mout = OUT_DIR / "cats" / f"wikt_{cat_slug(cat)}.md"
                    if scrape_to(wikt_category_url(cat), mout, main=True):
                        urls.extend(lemmas_from_md(mout.read_text(encoding="utf-8")))
            except Exception as exc:  # noqa: BLE001
                print(f"cat_parse_fail {cat}: {exc}", flush=True)
        time.sleep(0.1)
    uniq, seen = [], set()
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def acquire(
    *,
    target: int,
    per_family: int,
    none_per_cat: int,
    workers: int,
    existing: list[dict],
    checkpoint: Path | None,
) -> list[dict]:
    rng = random.Random(SEED)
    raw: list[dict] = []
    seen_text: set[str] = set()
    seen_url_text: set[tuple[str, str]] = set()
    family_counts: dict[str, int] = defaultdict(int)

    def checkpoint_write() -> None:
        if not checkpoint:
            return
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        with checkpoint.open("w", encoding="utf-8") as h:
            for r in raw:
                h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")

    def admit(row: dict) -> bool:
        text = row["text"]
        key = (row["source_url"], text)
        with _LOCK:
            if text in seen_text or key in seen_url_text:
                return False
            if len(text) < 12:
                return False
            seen_text.add(text)
            seen_url_text.add(key)
            raw.append(row)
            fam = row.get("acquisition_cue_family")
            if fam:
                family_counts[fam] += 1
            return True

    for r in existing:
        admit(
            {
                "text": r["text"],
                "source_url": r["source_url"],
                "provenance": r.get("provenance") or "OBSERVED",
                "construction_tag": r.get("construction_tag") or "NATURAL",
                "construction_role": r.get("construction_role") or "PRODUCT_EXPECTED",
                "source_family": r.get("source_family"),
                "topic_domain": r.get("topic_domain"),
                "acquisition_cue_family": r.get("acquisition_cue_family"),
                "notes": r.get("notes") or "existing_partial",
            }
        )
    print(
        f"seeded_existing={len(raw)} vocab_n={len(ACTIVE_FAMILY_VOCABULARY)} "
        f"vocab_head={list(ACTIVE_FAMILY_VOCABULARY)[:3]}",
        flush=True,
    )

    # Discover lemmas per shortfall family
    family_lemmas: dict[str, list[str]] = {}
    url_families: dict[str, list[str]] = defaultdict(list)
    for family in ACTIVE_FAMILY_VOCABULARY:
        if family_counts[family] >= per_family:
            continue
        lemmas = discover_wikt_lemmas(family)
        rng.shuffle(lemmas)
        family_lemmas[family] = lemmas
        for u in lemmas:
            url_families[u].append(family)
        print(
            f"discover family={family} lemmas={len(lemmas)} have={family_counts[family]}",
            flush=True,
        )

    # Build scrape queue (deduped URLs), prefer shortfall families
    lemma_urls: list[str] = []
    seen_u: set[str] = set()
    for family, lemmas in family_lemmas.items():
        need = max(0, per_family - family_counts[family])
        take = min(len(lemmas), max(need * 4, need + 30))
        offset = (SEED + sum(map(ord, family))) % max(1, min(30, len(lemmas) // 4 or 1))
        rotated = lemmas[offset:] + lemmas[:offset]
        for u in rotated[:take]:
            if u not in seen_u:
                seen_u.add(u)
                lemma_urls.append(u)

    print(f"lemma_urls={len(lemma_urls)} workers={workers}", flush=True)

    def scrape_lemma(url: str) -> str | None:
        out = lemma_path(url)
        ok = scrape_to(url, out, main=True)
        return out.read_text(encoding="utf-8") if ok else None

    def harvest_lemma_md(url: str, md: str) -> int:
        title = urllib.parse.unquote(url.rstrip("/").split("/")[-1]).replace("_", " ")
        senses = extract_wikt_senses(md)
        added = 0
        # Assign each sense to a still-short family that claimed this URL.
        claimants = url_families.get(url) or ["internet-slang"]
        for sense in senses:
            text = clean_wikitext(sense) if "{{" in sense else sense
            text = strip_md(text)
            if len(text) < 12:
                continue
            # pick claimant with lowest count among those under per_family
            under = [f for f in claimants if family_counts[f] < per_family]
            if not under:
                # still keep NATURAL rows under a generic cue if global target unmet
                if len(raw) >= target:
                    break
                fam = claimants[0]
            else:
                fam = min(under, key=lambda f: family_counts[f])
            if admit(
                {
                    "text": text,
                    "source_url": url,
                    "provenance": "OBSERVED",
                    "construction_tag": "NATURAL",
                    "construction_role": "PRODUCT_EXPECTED",
                    "source_family": f"v6_qual002_firecrawl_wikt:{fam}",
                    "topic_domain": fam,
                    "acquisition_cue_family": fam,
                    "notes": f"firecrawl_wikt_sense:{title}",
                }
            ):
                added += 1
        return added

    # First: harvest any already-cached lemmas (from prior run)
    cached_added = 0
    for url in lemma_urls:
        path = lemma_path(url)
        if path.exists() and path.stat().st_size > 40:
            cached_added += harvest_lemma_md(url, path.read_text(encoding="utf-8"))
    print(f"cached_harvest_added={cached_added} total={len(raw)}", flush=True)
    checkpoint_write()

    need_scrape = [
        u for u in lemma_urls if not (lemma_path(u).exists() and lemma_path(u).stat().st_size > 40)
    ]
    # Also scrape if family still short even when cache partially covered
    if any(family_counts[f] < per_family for f in family_lemmas):
        pass
    else:
        need_scrape = []

    print(f"need_scrape={len(need_scrape)}", flush=True)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futs = {pool.submit(scrape_lemma, u): u for u in need_scrape}
        done = 0
        for fut in as_completed(futs):
            url = futs[fut]
            done += 1
            try:
                md = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"lemma_exc {url}: {exc}", flush=True)
                continue
            if md:
                harvest_lemma_md(url, md)
            if done % 20 == 0:
                print(
                    f"lemma_progress {done}/{len(need_scrape)} total={len(raw)} "
                    f"short={[f for f,c in family_counts.items() if c < per_family and f in family_lemmas][:8]}",
                    flush=True,
                )
                checkpoint_write()

    print(
        "family_counts_after_wikt="
        + json.dumps({k: family_counts[k] for k in sorted(family_counts)}, sort_keys=True),
        flush=True,
    )
    checkpoint_write()

    # Wikipedia NONE / domain-irrelevant
    none_targets = list(WIKI_ORDINARY_CATEGORIES.items()) + list(
        DOMAIN_IRRELEVANT_CATEGORIES.items()
    )
    rng.shuffle(none_targets)
    article_urls: list[tuple[str, str]] = []
    for key, cat in none_targets:
        out = OUT_DIR / "cats" / f"wiki_{cat_slug(cat)}.md"
        if not scrape_to(wiki_category_url(cat), out, main=True):
            continue
        arts = filter_wiki_articles_from_md(out.read_text(encoding="utf-8"))
        rng.shuffle(arts)
        for u in arts[: max(none_per_cat * 2, 50)]:
            article_urls.append((key, u))
        print(f"discover none={key} arts={len(arts)}", flush=True)
        time.sleep(0.08)

    none_counts: dict[str, int] = defaultdict(int)
    print(f"article_jobs={len(article_urls)}", flush=True)

    def scrape_article(url: str) -> str | None:
        out = wiki_path(url)
        ok = scrape_to(url, out, main=True)
        return out.read_text(encoding="utf-8") if ok else None

    def harvest_wiki(key: str, url: str, md: str) -> int:
        title = urllib.parse.unquote(url.rstrip("/").split("/")[-1]).replace("_", " ")
        added = 0
        for para in extract_wiki_paras(md, max_paras=2):
            if none_counts[key] >= none_per_cat:
                break
            if admit(
                {
                    "text": para,
                    "source_url": url,
                    "provenance": "OBSERVED",
                    "construction_tag": "NATURAL",
                    "construction_role": "PRODUCT_EXPECTED",
                    "source_family": f"v6_qual002_firecrawl_wiki_none:{key}",
                    "topic_domain": key,
                    "acquisition_cue_family": None,
                    "notes": f"firecrawl_wiki_prose:{title}",
                }
            ):
                none_counts[key] += 1
                added += 1
        return added

    # cached wiki first
    for key, url in article_urls:
        path = wiki_path(url)
        if path.exists() and path.stat().st_size > 40:
            harvest_wiki(key, url, path.read_text(encoding="utf-8"))
    print(f"wiki_cached_total={len(raw)}", flush=True)

    need_wiki = [
        (k, u)
        for k, u in article_urls
        if none_counts[k] < none_per_cat
        and not (wiki_path(u).exists() and wiki_path(u).stat().st_size > 40)
    ]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futs = {pool.submit(scrape_article, u): (k, u) for k, u in need_wiki}
        done = 0
        for fut in as_completed(futs):
            key, url = futs[fut]
            done += 1
            try:
                md = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"wiki_exc {url}: {exc}", flush=True)
                continue
            if md:
                harvest_wiki(key, url, md)
            if done % 20 == 0:
                print(
                    f"wiki_progress {done}/{len(need_wiki)} total={len(raw)}",
                    flush=True,
                )
                checkpoint_write()

    print(f"none_counts={dict(none_counts)} total={len(raw)}", flush=True)
    checkpoint_write()
    rng.shuffle(raw)
    return raw[:target]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1200)
    ap.add_argument("--per-family", type=int, default=55)
    ap.add_argument("--none-per-cat", type=int, default=35)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--existing", action="append", default=[])
    ap.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR / "RAW_ACQUIRE_QUAL002.firecrawl.jsonl",
    )
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_existing([Path(p) for p in args.existing])
    ckpt = Path(str(args.out) + ".partial")
    rows = acquire(
        target=args.target,
        per_family=args.per_family,
        none_per_cat=args.none_per_cat,
        workers=args.workers,
        existing=existing,
        checkpoint=ckpt,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as h:
        for r in rows:
            h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    meta = {
        "n": len(rows),
        "out": str(args.out),
        "per_family": args.per_family,
        "none_per_cat": args.none_per_cat,
        "seed": SEED,
        "source": "firecrawl_cli",
        "vocab": list(ACTIVE_FAMILY_VOCABULARY),
    }
    args.out.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(meta, indent=2, sort_keys=True))
    return 0 if len(rows) >= 750 else 2


if __name__ == "__main__":
    raise SystemExit(main())
