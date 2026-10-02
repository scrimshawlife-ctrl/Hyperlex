#!/usr/bin/env python3
"""NATURAL OBSERVED positive feeder for FUNCTION diversity expand (V3).

Fresh SEED 20261004 — not QUAL-003. Mixes:
  - longer Wiktionary multi-sense concatenations
  - Wikipedia culture/slang lead extracts (encyclopedic positive)

Does not read QUAL-003 rows. Labels are applied later via dual_annotate.
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
    clean_wikitext,
)

SEED = 20261004
UA = "HyperlexV6FunctionDiversityExpand/1.0 (research; contact: hyperlex-operator)"

# Function-bearing lemma seeds (surface acquisition cues only — not gold).
FAMILY_LEMMA_SEEDS: dict[str, tuple[str, ...]] = {
    "relationship-dating": (
        "ghosting", "breadcrumbing", "situationship", "love_bombing", "orbiting",
        "soft_launch", "hard_launch", "benching", "zombieing", "kittenfishing",
        "rizz", "cuffing", "talking_stage", "stashing", "cushioning",
        "nesting", "submarining", "haunting_(dating)",
    ),
    "conflict-aggression": (
        "flame", "ratio", "clapback", "drag", "shade", "cancel", "call_out",
        "beef", "diss", "roast", "owned", "throwing_hands", "pressed",
        "dogpile", "brigading", "doxxing", "swatting",
    ),
    "social-evaluation": (
        "cringe", "based", "mid", "trash", "fire", "lit", "wack", "basic",
        "extra", "tryhard", "poser", "corny", "lame", "dope", "sus", "cap",
        "no_cap", "slay", "ate",
    ),
    "memetic": (
        "kek", "pepe", "wojak", "copypasta", "shitpost", "meme", "doge",
        "rickroll", "normie", "glowie", "chad", "virgin", "npc", "sigma",
        "skibidi", "brainrot", "lore",
    ),
    "internet-slang": (
        "yeet", "sus", "based", "cap", "lmao", "fomo", "goat", "salty",
        "simp", "stan", "flex", "vibe", "lowkey", "highkey", "bussin",
        "rizz", "gyatt", "touch_grass",
    ),
    "gaming-meta": (
        "nerf", "buff", "gg", "noob", "camping", "smurf", "tilt", "clutch",
        "meta", "tryhard", "sweaty", "aimbot", "griefing", "teabagging",
    ),
    "politics-civic": (
        "dogwhistle", "astroturf", "bothsides", "tankie", "whataboutism",
        "cancel_culture", "culture_war", "own_the_libs",
    ),
    "technology-ai": (
        "hallucination", "jailbreak", "prompt", "alignment", "slop",
        "AI_slop", "clanker", "bot",
    ),
    "ai-native": (
        "prompt_engineering", "chain_of_thought", "RLHF", "synthetic_data",
        "vibe_coding", "agentic",
    ),
    "music-entertainment": (
        "bop", "banger", "earworm", "diss_track", "stan", "fandom",
    ),
    "fashion-aesthetic": (
        "drip", "fit_check", "aesthetic", "core", "slay", "snatched",
    ),
    "crypto-degen": (
        "hodl", "rekt", "rugpull", "wagmi", "ngmi", "degen", "cope",
    ),
    "workplace-career": (
        "quiet_quitting", "hustle", "circle_back", "synergy", "grindset",
    ),
    "sports-competition": ("clutch", "goat", "buzzer_beater", "owned"),
    "spiritual-mystic": ("manifest", "vibes", "aura", "mercury_retrograde"),
    "identity-affiliation": ("stan", "fandom", "ship", "ally"),
    "regional-cultural": ("mate", "bruv", "hella", "y'all", "innit"),
    "betting-sharp": ("juice", "vig", "sharp", "steam", "chalk"),
}

# Wikipedia titles expected to yield longer encyclopedic positive prose.
WIKI_CULTURE_TITLES: dict[str, tuple[str, ...]] = {
    "memetic": (
        "Meme", "Internet_meme", "Copypasta", "Image_macro", "Rickrolling",
        "Pepe_the_Frog", "Wojak", "Shitposting", "Viral_phenomenon",
        "Internet_culture", "Rage_comic", "Advice_animal",
    ),
    "relationship-dating": (
        "Ghosting_(behavior)", "Breadcrumbing", "Situationship",
        "Love_bombing", "Online_dating", "Orbiting_(behavior)",
        "Benching_(dating)", "Zombieing_(dating)", "Cuffing_season",
    ),
    "conflict-aggression": (
        "Flaming_(Internet)", "Cancel_culture", "Call-out_culture",
        "Internet_troll", "Doxing", "Brigading", "Flame_war",
        "Cyberbullying", "Ratio_(Internet_slang)",
    ),
    "social-evaluation": (
        "Pejorative", "Insult", "Compliment", "Slang", "Praise",
        "Internet_slang", "Snark", "Shade_(slang)",
    ),
    "internet-slang": (
        "Internet_slang", "Text_messaging", "Leet", "Netspeak",
        "Emoji", "Hashtag", "Subtweet",
    ),
    "gaming-meta": (
        "Video_game_culture", "Nerf_(video_gaming)", "Camping_(gaming)",
        "Smurf_(video_gaming)", "Griefing", "Esports",
    ),
    "politics-civic": (
        "Dog_whistle_(politics)", "Astroturfing", "Whataboutism",
        "Cancel_culture", "Culture_war",
    ),
    "technology-ai": (
        "Hallucination_(artificial_intelligence)", "Prompt_engineering",
        "Jailbreak_(large_language_models)", "AI_alignment",
    ),
    "ai-native": (
        "Prompt_engineering", "Reinforcement_learning_from_human_feedback",
        "Large_language_model", "Synthetic_data",
    ),
}


class _SenseExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_li = False
        self._skip = 0
        self._buf: list[str] = []
        self.senses: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
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
                self.senses.append(text[:700])
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


def extract_english_senses(html: str, *, max_senses: int = 8) -> list[str]:
    m = re.search(
        r'id="English"[^>]*>.*?</span>(.*?)(?:<h2[\s>]|$)',
        html,
        re.S | re.I,
    )
    chunk = m.group(1) if m else html
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


def wiki_summary(title: str) -> dict | None:
    url = (
        "https://en.wikipedia.org/api/rest_v1/page/summary/"
        + urllib.parse.quote(title.replace(" ", "_"), safe="()%'_:-")
    )
    try:
        raw = fetch(url)
    except Exception:  # noqa: BLE001
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    extract = (data.get("extract") or "").strip()
    if len(extract) < 80:
        return None
    return {
        "text": extract[:1200],
        "source_url": data.get("content_urls", {})
        .get("desktop", {})
        .get("page")
        or f"https://en.wikipedia.org/wiki/{title}",
        "title": data.get("title") or title,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wikt-target", type=int, default=500)
    ap.add_argument("--wiki-target", type=int, default=220)
    ap.add_argument("--per-family", type=int, default=28)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(
            "/home/morpheus/hlx-private/"
            "classification-v6-function-diversity-expand-20261002/"
            "RAW_ACQUIRE_EXPAND.jsonl"
        ),
    )
    ap.add_argument("--block-texts", type=Path, action="append", default=[])
    args = ap.parse_args()
    rng = random.Random(SEED)

    blocked: set[str] = set()
    for path in args.block_texts:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            t = (r.get("text") or "").strip().lower()
            if t:
                blocked.add(t)

    raw: list[dict] = []
    seen: set[str] = set()
    fam_counts: dict[str, int] = defaultdict(int)

    def admit(row: dict) -> bool:
        text = (row.get("text") or "").strip()
        key = text.lower()
        if not text or key in seen or key in blocked or len(text) < 40:
            return False
        seen.add(key)
        raw.append(row)
        fam = row.get("acquisition_cue_family")
        if fam:
            fam_counts[str(fam)] += 1
        return True

    # --- Wikipedia culture extracts (longer, non-wikt) ---
    wiki_jobs: list[tuple[str, str]] = []
    for family, titles in WIKI_CULTURE_TITLES.items():
        titles_l = list(titles)
        rng.shuffle(titles_l)
        for title in titles_l:
            wiki_jobs.append((family, title))
    rng.shuffle(wiki_jobs)
    print(f"wiki_jobs={len(wiki_jobs)}", flush=True)
    for family, title in wiki_jobs:
        if sum(1 for r in raw if "wiki_culture" in (r.get("source_family") or "")) >= args.wiki_target:
            break
        hit = wiki_summary(title)
        if not hit:
            continue
        admit(
            {
                "text": hit["text"],
                "source_url": hit["source_url"],
                "provenance": "OBSERVED",
                "construction_tag": "NATURAL",
                "construction_role": "PRODUCT_EXPECTED",
                "source_family": f"v6_expand_wiki_culture:{family}",
                "topic_domain": family,
                "acquisition_cue_family": family,
                "notes": f"wiki_summary:{hit.get('title')}",
            }
        )
        time.sleep(0.05)
    print(
        f"wiki_admitted={sum(1 for r in raw if 'wiki_culture' in (r.get('source_family') or ''))}",
        flush=True,
    )

    # --- Wiktionary multi-sense (prefer longer concatenations) ---
    jobs: list[tuple[str, str]] = []
    for family in ACTIVE_FAMILY_VOCABULARY:
        lemmas: list[str] = []
        lemmas.extend(FAMILY_LEMMA_SEEDS.get(family, ()))
        lemmas.extend(FAMILY_LABELS.get(family, ())[:8])
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
        take = min(len(uniq), max(need + 10, need * 2))
        for lem in uniq[:take]:
            jobs.append((family, lemma_url(lem)))
    rng.shuffle(jobs)
    print(f"wikt_jobs={len(jobs)}", flush=True)

    def work(item: tuple[str, str]) -> list[dict]:
        family, url = item
        try:
            html = fetch(url)
        except Exception as exc:  # noqa: BLE001
            return [{"_error": str(exc), "url": url}]
        senses = extract_english_senses(html, max_senses=8)
        out = []
        # Emit individual medium/long senses
        for sense in senses:
            if len(sense) >= 60:
                out.append(
                    {
                        "text": sense,
                        "source_url": url,
                        "provenance": "OBSERVED",
                        "construction_tag": "NATURAL",
                        "construction_role": "PRODUCT_EXPECTED",
                        "source_family": f"v6_expand_wikt_html:{family}",
                        "topic_domain": family,
                        "acquisition_cue_family": family,
                        "notes": "wikt_sense",
                    }
                )
        # Emit concatenated long multi-sense surface
        if len(senses) >= 2:
            joined = " / ".join(senses[:4])
            if len(joined) >= 160:
                out.append(
                    {
                        "text": joined[:1200],
                        "source_url": url,
                        "provenance": "OBSERVED",
                        "construction_tag": "NATURAL",
                        "construction_role": "PRODUCT_EXPECTED",
                        "source_family": f"v6_expand_wikt_html_multi:{family}",
                        "topic_domain": family,
                        "acquisition_cue_family": family,
                        "notes": "wikt_multi_sense",
                    }
                )
        return out

    wikt_n = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(work, j) for j in jobs]
        for fut in as_completed(futs):
            if wikt_n >= args.wikt_target:
                break
            rows = fut.result()
            for r in rows:
                if "_error" in r:
                    continue
                if admit(r):
                    wikt_n += 1
                    if wikt_n >= args.wikt_target:
                        break

    args.out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as h:
        for r in raw:
            h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    os.chmod(args.out, 0o600)
    styles = defaultdict(int)
    for r in raw:
        sf = r.get("source_family") or ""
        if "wiki_culture" in sf:
            styles["wiki_culture"] += 1
        elif "wikt" in sf:
            styles["wikt"] += 1
        else:
            styles["other"] += 1
    lens = sorted(len(r["text"]) for r in raw)
    print(
        json.dumps(
            {
                "n": len(raw),
                "styles": dict(styles),
                "len_p50": lens[len(lens) // 2] if lens else 0,
                "len_p90": lens[int(len(lens) * 0.9)] if lens else 0,
                "out": str(args.out),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
