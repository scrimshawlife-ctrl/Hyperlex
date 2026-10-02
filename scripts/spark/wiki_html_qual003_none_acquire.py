#!/usr/bin/env python3
"""NATURAL OBSERVED zero-label feeder for QUAL-003 via Wikipedia HTML.

Bypasses MediaWiki Action API 429s by fetching article HTML with urllib and
extracting plain paragraphs. Fresh SEED vs QUAL-002. Emits Firecrawl-compatible
jsonl for run_classification_v6_qualification_surface_003 resume.
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

from hyperlexical.classification_v6_data_foundation_acquire import (  # noqa: E402
    DOMAIN_IRRELEVANT_CATEGORIES,
    WIKI_ORDINARY_CATEGORIES,
)

SEED = 20261003
UA = "HyperlexV6QUAL003/1.0 (research; contact: hyperlex-operator)"

# Seed articles for ordinary/irrelevant NONE traffic (disjoint offsets vs QUAL-002).
WIKI_NONE_SEEDS: dict[str, tuple[str, ...]] = {
    "mycology": (
        "Mycology", "Fungus", "Mushroom", "Basidiomycota", "Ascomycota", "Spore",
        "Mycorrhiza", "Lichen", "Yeast", "Truffle", "Puffball", "Morel",
        "Amanita", "Boletus", "Chitin", "Hypha", "Mycelium", "Rust_(fungus)",
        "Smut_(fungus)", "Penicillium", "Aspergillus", "Cordyceps",
    ),
    "entomology": (
        "Entomology", "Insect", "Beetle", "Lepidoptera", "Hymenoptera", "Diptera",
        "Butterfly", "Ant", "Dragonfly", "Grasshopper", "Termite", "Cicada",
        "Mosquito", "Honey_bee", "Wasp", "Moth", "Flea", "Aphid", "Praying_mantis",
        "Ladybird", "Firefly", "Locust",
    ),
    "oceanography": (
        "Oceanography", "Ocean", "Thermohaline_circulation", "Phytoplankton",
        "Upwelling", "Seamount", "Abyssal_plain", "Tide", "Salinity", "Gulf_Stream",
        "Coral_reef", "Estuary", "Tsunami", "Wave", "Seawater", "Pelagic_zone",
        "Benthic_zone", "Hydrothermal_vent", "El_Niño", "Marine_snow",
    ),
    "paleontology": (
        "Paleontology", "Fossil", "Dinosaur", "Trilobite", "Amber", "Extinction",
        "Geologic_time_scale", "Cambrian", "Pterosaur", "Ammonite", "Mammoth",
        "Ichthyosaur", "Tyrannosaurus", "Stegosaurus", "Plesiosaur", "Burgess_Shale",
        "Trace_fossil", "La_Brea_Tar_Pits", "Archaeopteryx", "Permian",
    ),
    "cartography": (
        "Cartography", "Map", "Mercator_projection", "Topographic_map", "Atlas",
        "Geographic_information_system", "Latitude", "Longitude", "Contour_line",
        "Choropleth_map", "Orthographic_projection", "Scale_(map)", "Rhumb_line",
        "Geoid", "Surveying", "Cadastral_map", "Thematic_map", "Isogonic_line",
    ),
    "numismatics": (
        "Numismatics", "Coin", "Currency", "Mint_(facility)", "Medal", "Token_coin",
        "Bullion", "Obverse_and_reverse", "Seigniorage", "Coin_collecting",
        "Ancient_Greek_coinage", "Roman_currency", "Denarius", "Solidus_(coin)",
        "Doubloon", "Sovereign_(British_coin)", "Dollar_coin", "Euro_coins",
    ),
    "philately": (
        "Philately", "Postage_stamp", "Stamp_collecting", "Postal_history",
        "Airmail", "Penny_Black", "Stamp_album", "First_day_of_issue",
        "Definitive_stamp", "Postage_stamp_paper", "Stamp_hinge",
        "Commemorative_stamp", "Postage_stamp_separation", "Cinderella_stamp",
        "Overprint", "Postage_due",
    ),
    "archaeology": (
        "Archaeology", "Excavation_(archaeology)", "Artifact_(archaeology)",
        "Stratigraphy", "Radiocarbon_dating", "Pottery", "Megalith", "Taphonomy",
        "Zooarchaeology", "Lithic_analysis", "Underwater_archaeology",
        "Paleoethnobotany", "Ötzi", "Pompeii", "Knossos", "Troy", "Machu_Picchu",
        "Seriation_(archaeology)", "Typology_(archaeology)", "Feature_(archaeology)",
    ),
    "hydrology": (
        "Hydrology", "Water_cycle", "Watershed", "Aquifer", "Groundwater", "Flood",
        "Streamflow", "Evapotranspiration", "Hydrograph", "Drainage_basin",
        "Runoff_(hydrology)", "Spring_(hydrology)", "Karst", "Geyser", "Wetland",
        "Marsh", "Swamp", "Reservoir", "Dam", "Irrigation",
    ),
    "mineralogy": (
        "Mineralogy", "Mineral", "Crystal", "Quartz", "Feldspar", "Mohs_scale",
        "Silicate_mineral", "Ore", "Gemstone", "Crystallography", "Calcite",
        "Gypsum", "Diamond", "Emerald", "Ruby", "Sapphire", "Olivine", "Mica",
        "Pyrite", "Hematite",
    ),
    "botany": (
        "Botany", "Plant", "Photosynthesis", "Xylem", "Phloem", "Angiosperm",
        "Gymnosperm", "Chloroplast", "Root", "Leaf", "Stoma", "Meristem",
        "Cambium", "Transpiration", "Pollination", "Seed", "Fruit", "Flower",
        "Algae", "Moss",
    ),
    "chemistry": (
        "Chemistry", "Chemical_reaction", "Molecule", "Periodic_table", "Acid",
        "Base_(chemistry)", "Organic_chemistry", "Catalyst", "Stoichiometry",
        "Ion", "Redox", "Polymer", "Alkane", "Benzene", "Enzyme", "pH",
        "Titration", "Spectroscopy", "Isotope", "Valence_(chemistry)",
    ),
    "domain_irrelevant_lists": (
        "List_of_countries_by_population", "List_of_rivers_of_Europe",
        "List_of_chemical_elements", "List_of_lakes_by_area",
        "List_of_mountains_by_elevation", "List_of_islands_by_area",
        "List_of_deserts_by_area", "List_of_canals", "List_of_bridges",
        "List_of_tunnels", "List_of_airports_by_IATA_code:_B",
        "List_of_national_parks",
    ),
    "domain_irrelevant_years": (
        "2016", "2017", "2018", "2019", "2015", "2014", "2013", "2012",
        "2011", "2010", "2009", "2008",
    ),
    "domain_irrelevant_infra": (
        "Gare_de_Lyon", "Berlin_Hauptbahnhof", "Railway_station",
        "Railway_platform", "Grand_Central_Terminal", "Shinjuku_Station",
        "Paddington_station", "Union_Station_(Washington,_D.C.)",
        "Frankfurt_(Main)_Hauptbahnhof", "Madrid_Atocha_railway_station",
        "Platform_screen_doors", "Railway_signalling",
    ),
}


class _ParagraphExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_p = False
        self._skip_depth = 0
        self._buf: list[str] = []
        self.paras: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        attrs_d = dict(attrs)
        cls = attrs_d.get("class", "")
        if tag in {"script", "style", "table", "sup", "math"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "p" and "mw-empty-elt" not in cls:
            self._in_p = True
            self._buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "table", "sup", "math"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "p" and self._in_p:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if len(text) >= 40:
                self.paras.append(text[:800])
            self._in_p = False
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._in_p and not self._skip_depth:
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


def extract_paras(html: str, *, max_paras: int = 3) -> list[str]:
    # Prefer content div if present
    m = re.search(
        r'<div[^>]+id="mw-content-text"[^>]*>(.*?)</div>\s*<div[^>]+id="catlinks"',
        html,
        re.S | re.I,
    )
    chunk = m.group(1) if m else html
    parser = _ParagraphExtractor()
    try:
        parser.feed(chunk)
    except Exception:  # noqa: BLE001
        return []
    out: list[str] = []
    for p in parser.paras:
        low = p.lower()
        if low.startswith("coordinates") or "may refer to" in low:
            continue
        out.append(p)
        if len(out) >= max_paras:
            break
    return out


def article_url(title: str) -> str:
    return "https://en.wikipedia.org/wiki/" + title


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=700)
    ap.add_argument("--none-per-cat", type=int, default=45)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO / ".firecrawl" / "qual003" / "RAW_ACQUIRE_QUAL003.wiki_html_none.jsonl",
    )
    args = ap.parse_args()
    rng = random.Random(SEED)

    jobs: list[tuple[str, str]] = []
    keys = list(WIKI_ORDINARY_CATEGORIES) + list(DOMAIN_IRRELEVANT_CATEGORIES)
    # Prefer seed keys we know; then any remaining ordinary keys
    seed_keys = list(WIKI_NONE_SEEDS)
    rng.shuffle(seed_keys)
    for key in seed_keys:
        titles = list(WIKI_NONE_SEEDS[key])
        rng.shuffle(titles)
        # rotate by SEED for QUAL-003 disjointness vs QUAL-002 seed order
        offset = (SEED + sum(map(ord, key))) % max(1, len(titles))
        titles = titles[offset:] + titles[:offset]
        for t in titles:
            jobs.append((key, article_url(t)))

    rng.shuffle(jobs)
    print(f"jobs={len(jobs)} workers={args.workers}", flush=True)

    raw: list[dict] = []
    seen: set[str] = set()
    none_counts: dict[str, int] = defaultdict(int)

    def admit(row: dict) -> bool:
        text = row["text"]
        if text in seen or len(text) < 40:
            return False
        seen.add(text)
        raw.append(row)
        return True

    def work(item: tuple[str, str]) -> list[dict]:
        key, url = item
        try:
            html = fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"fetch_fail {url}: {exc}", flush=True)
            return []
        out = []
        for para in extract_paras(html, max_paras=2):
            out.append(
                {
                    "text": para,
                    "source_url": url,
                    "provenance": "OBSERVED",
                    "construction_tag": "NATURAL",
                    "construction_role": "PRODUCT_EXPECTED",
                    "source_family": f"v6_qual003_wiki_html_none:{key}",
                    "topic_domain": key,
                    "acquisition_cue_family": None,
                    "notes": f"wiki_html_prose:{urllib.parse.unquote(url.split('/')[-1])}",
                }
            )
        time.sleep(0.15)
        return out

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {pool.submit(work, j): j for j in jobs}
        done = 0
        for fut in as_completed(futs):
            key, url = futs[fut]
            done += 1
            try:
                rows = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"exc {url}: {exc}", flush=True)
                continue
            for row in rows:
                if none_counts[key] >= args.none_per_cat:
                    break
                if len(raw) >= args.target:
                    break
                if admit(row):
                    none_counts[key] += 1
            if done % 15 == 0:
                print(
                    f"progress {done}/{len(jobs)} total={len(raw)} "
                    f"cats={len(none_counts)}",
                    flush=True,
                )
                args.out.parent.mkdir(parents=True, exist_ok=True)
                with args.out.open("w", encoding="utf-8") as h:
                    for r in raw:
                        h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
            if len(raw) >= args.target:
                break

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as h:
        for r in raw:
            h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    meta = {
        "n": len(raw),
        "out": str(args.out),
        "none_counts": dict(none_counts),
        "seed": SEED,
        "source": "wikipedia_html",
    }
    args.out.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(meta, indent=2, sort_keys=True))
    return 0 if len(raw) >= 400 else 2


if __name__ == "__main__":
    raise SystemExit(main())
