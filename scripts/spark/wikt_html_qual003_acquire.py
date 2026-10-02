#!/usr/bin/env python3
"""NATURAL OBSERVED positive-sense feeder for QUAL-003 via Wiktionary HTML.

Bypasses MediaWiki Action API 429s and Firecrawl rate limits. Fresh SEED
20261003 lemma offsets. Emits OBSERVED NATURAL jsonl for QUAL-003 resume.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path

os.environ.setdefault("HLX_V2_FORWARD_ONTOLOGY", "1")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY  # noqa: E402
from hyperlexical.classification_v6_data_foundation_acquire import (  # noqa: E402
    FAMILY_LABELS,
    WIKT_FAMILY_CATEGORIES,
    clean_wikitext,
)

SEED = 20261003
UA = "HyperlexV6QUAL003/1.0 (research; contact: hyperlex-operator)"

# Extra lemma seeds per family (observed slang/register lemmas; not gold labels).
FAMILY_LEMMA_SEEDS: dict[str, tuple[str, ...]] = {
    "internet-slang": (
        "yeet", "sus", "based", "cap", "noob", "lmao", "brb", "imo", "tbh",
        "fomo", "goat", "salty", "ghosting", "simp", "stan", "flex", "vibe",
        "ratio", "copium", "deadass", "lowkey", "highkey", "snatched", "bussin",
        "mid", "rizz", "gyatt", "skibidi", "sigma", "npc", "touch_grass",
    ),
    "memetic": (
        "kek", "pepe", "wojak", "copypasta", "shitpost", "meme", "doge",
        "rickroll", "normie", "based", "redpilled", "bluepilled", "glowie",
        "boomer", "zoomer", "doomer", "bloomer", "chad", "virgin", "jokerfy",
    ),
    "social-evaluation": (
        "cringe", "based", "mid", "trash", "fire", "lit", "wack", "basic",
        "extra", "tryhard", "poser", "fake", "real", "authentic", "corny",
        "lame", "cool", "dope", "sick", "whack",
    ),
    "gaming-meta": (
        "nerf", "buff", "gg", "noob", "camping", "smurf", "tilt", "clutch",
        "meta", "op", "tryhard", "grinding", "loot", "respawn", "afk",
        "ping", "lag", "hitbox", "aimbot", "sweaty",
    ),
    "betting-sharp": (
        "odds", "parlay", "handicap", "juice", "vig", "sharp", "square",
        "action", "chalk", "dog", "spread", "over", "under", "unit", "bankroll",
        "hedge", "middle", "steam", "line", "ticket",
    ),
    "crypto-degen": (
        "hodl", "wagmi", "ngmi", "rekt", "rugpull", "ape", "moon", "bagholder",
        "gas", "mint", "airdrop", "whale", "degen", "ser", "gm", "gn",
        "probably_nothing", "wen", "lambo", "diamond_hands",
    ),
    "relationship-dating": (
        "ghosting", "breadcrumbing", "situationship", "talking_stage", "cuffing",
        "orbiting", "love_bombing", "soft_launch", "hard_launch", "benching",
        "zombieing", "cushioning", "stashing", "kittenfishing", "rizz",
    ),
    "conflict-aggression": (
        "flame", "ratio", "clapback", "drag", "shade", "cancel", "call_out",
        "beef", "diss", "roast", "owned", "destroyed", "slammed", "pressed",
        "throwing_hands", "mad", "heated", "triggered",
    ),
    "technology-ai": (
        "prompt", "hallucination", "LLM", "finetune", "transformer", "token",
        "embedding", "alignment", "jailbreak", "RAG", "agent", "copilot",
        "autocomplete", "dataset", "benchmark", "overfit",
    ),
    "ai-native": (
        "prompt_engineering", "chain_of_thought", "system_prompt", "temperature",
        "zero_shot", "few_shot", "RLHF", "synthetic_data", "tool_use",
        "multimodal", "diffusion", "latent_space", "context_window",
    ),
    "workplace-career": (
        "quiet_quitting", "hustle", "grindset", "synergy", "bandwidth",
        "circle_back", "deep_dive", "touch_base", "pivot", "lean_in",
        "side_hustle", "WFH", "stand-up", "OKR", "deliverable",
    ),
    "sports-competition": (
        "clutch", "goat", "buzzer_beater", "hat_trick", "own_goal", "offside",
        "dunk", "alley-oop", "pick_and_roll", "blitz", "sack", "touchdown",
        "home_run", "walk-off", "ace", "deuce",
    ),
    "music-entertainment": (
        "bop", "banger", "earworm", "feat", "drop", "remix", "cover", "sample",
        "diss_track", "collab", "tour", "mixtape", "A-side", "B-side",
        "chart", "streaming", "vinyl", "EP",
    ),
    "fashion-aesthetic": (
        "drip", "fit", "fit_check", "drip_check", "aesthetic", "core", "vintage",
        "thrift", "streetwear", "couture", "dapper", "slay", "snatched",
        "y2k", "cottagecore", "gorpcore",
    ),
    "regional-cultural": (
        "mate", "bruv", "innit", "y'all", "hella", "wicked", "bogan", "lah",
        "leh", "lor", "eh", "dude", "bro", "cuz", "fam", "homie",
    ),
    "spiritual-mystic": (
        "manifest", "vibes", "aura", "chakras", "astrology", "mercury_retrograde",
        "synchronicity", "meditation", "mindfulness", "karma", "zodiac",
        "tarot", "crystal", "energy", "aligned",
    ),
    "identity-affiliation": (
        "stan", "fandom", "ship", "OTP", "canon", "headcanon", "ally",
        "community", "diaspora", "local", "expat", "native", "creole",
        "hybrid", "third_culture",
    ),
    "politics-civic": (
        "grassroots", "astroturf", "dogwhistle", "bothsides", "tankie",
        "neolib", "progressive", "populist", "gerrymander", "filibuster",
        "turnout", "swing_state", "primary", "caucus",
    ),
}


class _SenseExtractor(HTMLParser):
    """Extract ordered-list definition lines under English section."""

    def __init__(self) -> None:
        super().__init__()
        self._in_li = False
        self._skip = 0
        self._buf: list[str] = []
        self.senses: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in {"script", "style", "table", "sup", "math", "ul", "ol"}:
            # nested lists: still allow li at top of ol; track skip for junk
            if tag in {"script", "style", "table", "sup", "math"}:
                self._skip += 1
                return
        if self._skip:
            return
        if tag == "li":
            self._in_li = True
            self._buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "table", "sup", "math"} and self._skip:
            self._skip -= 1
            return
        if tag == "li" and self._in_li:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            text = re.sub(r"^\([^)]*\)\s*", "", text).strip()
            if len(text) >= 12 and not text.lower().startswith("citations"):
                self.senses.append(text[:500])
            self._in_li = False
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._in_li and not self._skip:
            self._buf.append(data)


def fetch(url: str, retries: int = 5) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code in {429, 500, 502, 503, 504}:
                time.sleep(min(90.0, (2**attempt) + random.random()))
                continue
            raise
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(min(30.0, (2**attempt)))
    assert last is not None
    raise last


def extract_english_senses(html: str, *, max_senses: int = 6) -> list[str]:
    # Isolate English section if marked
    m = re.search(
        r'id="English"[^>]*>.*?</span>(.*?)(?:<h2[\s>]|$)',
        html,
        re.S | re.I,
    )
    chunk = m.group(1) if m else html
    # Prefer ol under part-of-speech
    ols = re.findall(r"<ol[^>]*>(.*?)</ol>", chunk, re.S | re.I)
    senses: list[str] = []
    for ol in ols:
        parser = _SenseExtractor()
        try:
            parser.feed(ol)
        except Exception:  # noqa: BLE001
            continue
        for s in parser.senses:
            body = clean_wikitext(s) if "{{" in s else s
            body = re.sub(r"\s+", " ", body).strip()
            if len(body) < 12:
                continue
            senses.append(body)
            if len(senses) >= max_senses:
                return senses
    return senses


def lemma_url(title: str) -> str:
    return "https://en.wiktionary.org/wiki/" + urllib.parse.quote(
        title.replace(" ", "_"), safe="()%'_-"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=900)
    ap.add_argument("--per-family", type=int, default=50)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO / ".firecrawl" / "qual003" / "RAW_ACQUIRE_QUAL003.wikt_html.jsonl",
    )
    ap.add_argument("--existing", action="append", default=[])
    args = ap.parse_args()
    rng = random.Random(SEED)

    raw: list[dict] = []
    seen: set[str] = set()
    fam_counts: dict[str, int] = defaultdict(int)

    def admit(row: dict) -> bool:
        text = row["text"]
        if text in seen or len(text) < 12:
            return False
        seen.add(text)
        raw.append(row)
        fam = row.get("acquisition_cue_family")
        if fam:
            fam_counts[str(fam)] += 1
        return True

    for path_s in args.existing:
        path = Path(path_s)
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            admit(
                {
                    "text": r["text"],
                    "source_url": r["source_url"],
                    "provenance": "OBSERVED",
                    "construction_tag": "NATURAL",
                    "construction_role": r.get("construction_role") or "PRODUCT_EXPECTED",
                    "source_family": r.get("source_family"),
                    "topic_domain": r.get("topic_domain"),
                    "acquisition_cue_family": r.get("acquisition_cue_family"),
                    "notes": r.get("notes") or "existing",
                }
            )
    print(f"seeded_existing={len(raw)}", flush=True)

    jobs: list[tuple[str, str]] = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        lemmas: list[str] = []
        lemmas.extend(FAMILY_LEMMA_SEEDS.get(family, ()))
        lemmas.extend(FAMILY_LABELS.get(family, ())[:8])
        # category-derived labels already in FAMILY_LABELS; keep unique
        uniq, seen_l = [], set()
        for lem in lemmas:
            key = lem.lower()
            if key in seen_l:
                continue
            seen_l.add(key)
            uniq.append(lem)
        rng.shuffle(uniq)
        offset = (SEED + sum(map(ord, family))) % max(1, len(uniq))
        uniq = uniq[offset:] + uniq[:offset]
        need = max(0, args.per_family - fam_counts[family])
        take = min(len(uniq), max(need + 8, need * 2))
        for lem in uniq[:take]:
            jobs.append((family, lemma_url(lem)))
    rng.shuffle(jobs)
    print(f"jobs={len(jobs)}", flush=True)

    def work(item: tuple[str, str]) -> tuple[str, str, list[str]]:
        family, url = item
        try:
            html = fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"fetch_fail {url}: {exc}", flush=True)
            return family, url, []
        senses = extract_english_senses(html)
        time.sleep(0.12)
        return family, url, senses

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {pool.submit(work, j): j for j in jobs}
        done = 0
        for fut in as_completed(futs):
            family, url = futs[fut]
            done += 1
            try:
                fam, u, senses = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"exc {url}: {exc}", flush=True)
                continue
            title = urllib.parse.unquote(u.rstrip("/").split("/")[-1]).replace("_", " ")
            for sense in senses:
                if fam_counts[fam] >= args.per_family:
                    break
                if len(raw) >= args.target:
                    break
                admit(
                    {
                        "text": sense,
                        "source_url": u,
                        "provenance": "OBSERVED",
                        "construction_tag": "NATURAL",
                        "construction_role": "PRODUCT_EXPECTED",
                        "source_family": f"v6_qual003_wikt_html:{fam}",
                        "topic_domain": fam,
                        "acquisition_cue_family": fam,
                        "notes": f"wikt_html_sense:{title}",
                    }
                )
            if done % 25 == 0:
                print(
                    f"progress {done}/{len(jobs)} total={len(raw)} "
                    f"short={[f for f in ACTIVE_FAMILY_VOCABULARY if fam_counts[f] < args.per_family][:6]}",
                    flush=True,
                )
                args.out.parent.mkdir(parents=True, exist_ok=True)
                with args.out.open("w", encoding="utf-8") as h:
                    for r in raw:
                        h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
            if len(raw) >= args.target and all(
                fam_counts[f] >= args.per_family for f in ACTIVE_FAMILY_VOCABULARY
            ):
                break

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as h:
        for r in raw:
            h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    meta = {
        "n": len(raw),
        "out": str(args.out),
        "family_counts": {k: fam_counts[k] for k in sorted(fam_counts)},
        "seed": SEED,
        "source": "wiktionary_html",
        "categories_ref": {k: list(v)[:2] for k, v in WIKT_FAMILY_CATEGORIES.items()},
    }
    args.out.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(meta, indent=2, sort_keys=True))
    return 0 if len(raw) >= 500 else 2


if __name__ == "__main__":
    raise SystemExit(main())
