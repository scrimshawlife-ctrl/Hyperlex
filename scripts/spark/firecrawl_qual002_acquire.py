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
import time
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY  # noqa: E402
from hyperlexical.classification_v6_data_foundation_acquire import (  # noqa: E402
    DOMAIN_IRRELEVANT_CATEGORIES,
    FAMILY_LABELS,
    WIKI_ORDINARY_CATEGORIES,
    WIKT_FAMILY_CATEGORIES,
    clean_wikitext,
)

SEED = 20261002
FIRECRAWL = os.environ.get("FIRECRAWL_BIN", "firecrawl")
OUT_DIR = Path(os.environ.get("HLX_FIRECRAWL_DIR") or (REPO / ".firecrawl" / "qual002"))

_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]+\)")
_MD_BOLD = re.compile(r"\*\*|__")
_MD_ITAL = re.compile(r"(?<!\*)\*(?!\*)|_")
_NUM_DEF = re.compile(r"(?m)^\d+\.\s+(.+)$")
_WIKI_URL_CLEAN = re.compile(r'\s*"[^"]*"\s*$')


def _run(cmd: list[str], retries: int = 4) -> subprocess.CompletedProcess[str]:
    last: subprocess.CompletedProcess[str] | None = None
    for attempt in range(retries):
        last = subprocess.run(cmd, capture_output=True, text=True)
        if last.returncode == 0:
            return last
        sleep_s = min(60.0, (2**attempt) + random.random())
        print(
            f"firecrawl_retry rc={last.returncode} sleep={sleep_s:.1f}s "
            f"stderr={(last.stderr or '')[:160]!r}",
            flush=True,
        )
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
        print(f"scrape_fail {url} -> {out}", flush=True)
        if out.exists() and out.stat().st_size <= 40:
            out.unlink(missing_ok=True)
    return ok


def cat_slug(cat: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", cat)[:120]


def wikt_category_url(cat: str) -> str:
    # Category:en:Video games -> Category:en:Video_games
    title = cat.replace(" ", "_")
    return "https://en.wiktionary.org/wiki/" + urllib.parse.quote(title, safe=":_")


def wiki_category_url(cat: str) -> str:
    title = cat.replace(" ", "_")
    return "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title, safe=":_")


def filter_wikt_lemmas(links: list[str]) -> list[str]:
    out = []
    seen = set()
    for u in links:
        if not u.startswith("https://en.wiktionary.org/wiki/"):
            continue
        title = urllib.parse.unquote(u.split("/wiki/", 1)[1])
        title = title.split("#", 1)[0]
        if not title or ":" in title:
            continue
        if title in seen:
            continue
        seen.add(title)
        out.append("https://en.wiktionary.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe="()%'"))
    return out


def filter_wiki_articles_from_md(md: str) -> list[str]:
    links = re.findall(r"\((https://en\.wikipedia\.org/wiki/[^)\s]+)\)", md)
    out = []
    seen = set()
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
    text = re.sub(r"\s+", " ", text).strip()
    # drop leftover citation markers
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"↑\s*", "", text)
    return text.strip(" .;,:")


def extract_wikt_senses(md: str) -> list[str]:
    """Pull English numbered definition lines from Firecrawl markdown."""
    # Prefer English section if present
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
        # drop pure label lines like "(Internet slang)"
        body = re.sub(r"^\([^)]*\)\s*", "", line).strip()
        if len(body) < 12:
            continue
        if body.startswith("↑") or body.lower().startswith("citations"):
            continue
        if re.fullmatch(r"[\W\d]+", body):
            continue
        senses.append(body if len(body) >= 12 else line)
    return senses


def extract_wiki_paras(md: str, *, max_paras: int = 3) -> list[str]:
    paras: list[str] = []
    # Drop nav chrome before first real heading/paragraph
    body = md
    m = re.search(r"(?im)^From Wikipedia", md)
    if m:
        body = md[m.end() :]
    chunks = re.split(r"\n\s*\n", body)
    for chunk in chunks:
        text = strip_md(chunk.replace("\n", " "))
        if len(text) < 40:
            continue
        if text.startswith("[") or text.startswith("!"):
            continue
        if text.lower().startswith("jump to") or text.lower().startswith("contents"):
            continue
        if "may refer to" in text.lower() and len(text) < 80:
            continue
        paras.append(text[:800])
        if len(paras) >= max_paras:
            break
    return paras


def load_existing(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        if not path or not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def acquire(
    *,
    target: int,
    per_family: int,
    none_per_cat: int,
    workers: int,
    existing: list[dict],
) -> list[dict]:
    rng = random.Random(SEED)
    raw: list[dict] = []
    seen_text: set[str] = set()
    seen_url_text: set[tuple[str, str]] = set()

    def admit(row: dict) -> bool:
        text = row["text"]
        key = (row["source_url"], text)
        if text in seen_text or key in seen_url_text:
            return False
        if len(text) < 12:
            return False
        seen_text.add(text)
        seen_url_text.add(key)
        raw.append(row)
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
    print(f"seeded_existing={len(raw)}", flush=True)

    family_counts: dict[str, int] = defaultdict(int)
    for r in raw:
        fam = r.get("acquisition_cue_family")
        if fam:
            family_counts[fam] += 1

    # --- Category discovery via Firecrawl ---
    family_lemmas: dict[str, list[str]] = {}
    for family in ACTIVE_FAMILY_VOCABULARY:
        if family_counts[family] >= per_family:
            continue
        urls: list[str] = []
        for cat in WIKT_FAMILY_CATEGORIES.get(family, ()):
            out = OUT_DIR / "cats" / f"wikt_{cat_slug(cat)}.json"
            if scrape_to(wikt_category_url(cat), out, fmt="links"):
                try:
                    payload = json.loads(out.read_text(encoding="utf-8"))
                    urls.extend(filter_wikt_lemmas(payload.get("links") or []))
                except Exception as exc:  # noqa: BLE001
                    print(f"cat_parse_fail {cat}: {exc}", flush=True)
            time.sleep(0.15)
        # also try secondary labels as Category:en:<Label>
        for label in FAMILY_LABELS.get(family, ())[:1]:
            cat = f"Category:en:{label.title()}"
            out = OUT_DIR / "cats" / f"wikt_{cat_slug(cat)}.json"
            if scrape_to(wikt_category_url(cat), out, fmt="links"):
                try:
                    payload = json.loads(out.read_text(encoding="utf-8"))
                    urls.extend(filter_wikt_lemmas(payload.get("links") or []))
                except Exception:
                    pass
            time.sleep(0.15)
        uniq, seen = [], set()
        for u in urls:
            if u not in seen:
                seen.add(u)
                uniq.append(u)
        rng.shuffle(uniq)
        family_lemmas[family] = uniq
        print(f"discover family={family} lemmas={len(uniq)} have={family_counts[family]}", flush=True)

    # Scrape lemmas for shortfall families
    lemma_jobs: list[tuple[str, str]] = []  # (family, url)
    for family, lemmas in family_lemmas.items():
        need = max(0, per_family - family_counts[family])
        if need <= 0:
            continue
        # oversample pages; each page may yield multiple senses
        take = min(len(lemmas), max(need * 3, need + 20))
        offset = (SEED + hash(family)) % max(1, min(30, len(lemmas) // 4 or 1))
        rotated = lemmas[offset:] + lemmas[:offset]
        for u in rotated[:take]:
            lemma_jobs.append((family, u))

    print(f"lemma_jobs={len(lemma_jobs)} workers={workers}", flush=True)

    def scrape_lemma(url: str) -> tuple[str, str | None]:
        title = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
        slug = cat_slug(title)
        out = OUT_DIR / "lemmas" / f"{slug}.md"
        ok = scrape_to(url, out, main=True)
        return url, (out.read_text(encoding="utf-8") if ok else None)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(scrape_lemma, u): (fam, u) for fam, u in lemma_jobs}
        done = 0
        for fut in as_completed(futs):
            fam, url = futs[fut]
            done += 1
            try:
                _, md = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"lemma_exc {url}: {exc}", flush=True)
                continue
            if not md:
                continue
            title = urllib.parse.unquote(url.rstrip("/").split("/")[-1]).replace("_", " ")
            senses = extract_wikt_senses(md)
            for sense in senses:
                text = clean_wikitext(sense) if "{{" in sense else sense
                text = strip_md(text)
                if len(text) < 12:
                    continue
                if family_counts[fam] >= per_family:
                    break
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
                    family_counts[fam] += 1
            if done % 25 == 0:
                print(
                    f"lemma_progress {done}/{len(lemma_jobs)} total={len(raw)}",
                    flush=True,
                )

    print(
        "family_counts_after_wikt="
        + json.dumps(dict(sorted(family_counts.items())), sort_keys=True),
        flush=True,
    )

    # --- Wikipedia ordinary / domain-irrelevant NONE via Firecrawl markdown cats ---
    none_targets = list(WIKI_ORDINARY_CATEGORIES.items()) + list(
        DOMAIN_IRRELEVANT_CATEGORIES.items()
    )
    rng.shuffle(none_targets)
    article_jobs: list[tuple[str, str]] = []
    for key, cat in none_targets:
        out = OUT_DIR / "cats" / f"wiki_{cat_slug(cat)}.md"
        if not scrape_to(wiki_category_url(cat), out, main=True):
            continue
        arts = filter_wiki_articles_from_md(out.read_text(encoding="utf-8"))
        rng.shuffle(arts)
        for u in arts[: max(none_per_cat * 2, 40)]:
            article_jobs.append((key, u))
        print(f"discover none={key} arts={len(arts)}", flush=True)
        time.sleep(0.1)

    print(f"article_jobs={len(article_jobs)}", flush=True)
    none_counts: dict[str, int] = defaultdict(int)

    def scrape_article(url: str) -> tuple[str, str | None]:
        title = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
        out = OUT_DIR / "wiki" / f"{cat_slug(title)}.md"
        ok = scrape_to(url, out, main=True)
        return url, (out.read_text(encoding="utf-8") if ok else None)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(scrape_article, u): (key, u) for key, u in article_jobs}
        done = 0
        for fut in as_completed(futs):
            key, url = futs[fut]
            done += 1
            if len(raw) >= target and none_counts[key] >= none_per_cat:
                continue
            try:
                _, md = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"wiki_exc {url}: {exc}", flush=True)
                continue
            if not md:
                continue
            title = urllib.parse.unquote(url.rstrip("/").split("/")[-1]).replace("_", " ")
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
            if done % 25 == 0:
                print(
                    f"wiki_progress {done}/{len(article_jobs)} total={len(raw)}",
                    flush=True,
                )

    print(f"none_counts={dict(none_counts)} total={len(raw)}", flush=True)
    rng.shuffle(raw)
    return raw[:target]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1200)
    ap.add_argument("--per-family", type=int, default=55)
    ap.add_argument("--none-per-cat", type=int, default=35)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument(
        "--existing",
        action="append",
        default=[],
        help="Existing jsonl partials to seed (repeatable)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR / "RAW_ACQUIRE_QUAL002.firecrawl.jsonl",
    )
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_existing([Path(p) for p in args.existing])
    rows = acquire(
        target=args.target,
        per_family=args.per_family,
        none_per_cat=args.none_per_cat,
        workers=args.workers,
        existing=existing,
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
    }
    meta_path = args.out.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2, sort_keys=True))
    return 0 if len(rows) >= 750 else 2


if __name__ == "__main__":
    raise SystemExit(main())
