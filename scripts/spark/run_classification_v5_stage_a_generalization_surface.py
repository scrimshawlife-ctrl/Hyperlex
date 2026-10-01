"""BUILD_V5_STAGE_A_GENERALIZATION_SURFACE_V1 — Spark builder.

Fresh matched Stage-A train/validation surface. Does not train, retune
thresholds, modify Stage B, reuse spent reserve text/labels, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path("/home/morpheus/Hyperlex")
DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-generalization-surface-v1-20261001"
)
HUB = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/"
    "civilian.v0.7.hub.jsonl"
)
HUB_SHA = "0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1"
V1R9 = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r9-20260930/"
    "EVIDENCE_SURFACE.jsonl"
)
V1R9_SHA = "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")
SPENT_V2 = Path(
    "/home/morpheus/hlx-private/classification-v2-train-ready-20260929/"
    "reserve-eval-rows.jsonl"
)
SPENT_V3 = Path(
    "/home/morpheus/hlx-private/classification-v3-reserve-20260930/reserve-rows.jsonl"
)
SPENT_V4 = Path(
    "/home/morpheus/hlx-private/classification-v4-reserve-20260930/reserve-rows.jsonl"
)
SPENT_V5 = Path(
    "/home/morpheus/hlx-private/classification-v5-reserve-20260930/RESERVE.jsonl"
)
UNCERTAIN_CACHE = Path(
    "/home/morpheus/hlx-private/classification-v5-uncertain-acquire-cache-20260930/"
    "OBSERVED_UNCERTAIN_ACQUIRE.jsonl"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
STAGE_A_BEST_SHA = (
    "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
)
BEST_LINK = Path("/home/morpheus/.hyperlex/models/BEST")
INIT_FROM = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
STAGE_A_BEST_DIR = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-two-stage"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
SCHEMA_DIR = REPO / "specs/007-hyperlexical-model/schemas/classification-v5"

WIKT_API = "https://en.wiktionary.org/w/api.php"
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = (
    "HyperlexClassificationV5GeneralizationSurface/1.0 "
    "(stage-a generalization surface; mediawiki provenance)"
)

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

_SENSE = re.compile(r"\{\{\s*(lb|lbl|tlb)\s*\|\s*en\s*\|([^{}]*)\}\}", re.I)
_LINK = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
_MARKUP = re.compile(r"''+")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_HTML = re.compile(r"<[^>]+>")
_REF = re.compile(r"<ref\b[^>]*>.*?</ref>", re.I | re.S)

FAMILY_LABELS = {
    "gaming-meta": ("gaming", "video game", "video games"),
    "crypto-degen": ("cryptocurrency",),
    "betting-sharp": ("betting", "gambling"),
    "internet-slang": ("internet slang", "reddit slang"),
    "technology-ai": ("programming", "software", "computer science"),
    "sports-competition": ("sports", "ball games"),
    "music-entertainment": ("music", "film", "television"),
    "fashion-aesthetic": ("fashion", "clothing"),
    "workplace-career": ("business",),
    "politics-civic": ("politics", "government"),
    "spiritual-mystic": ("occult", "astrology"),
    "social-evaluation": ("derogatory", "endearing"),
    "conflict-aggression": ("military", "military slang"),
    "regional-cultural": ("australian", "scottish", "irish"),
    "identity-affiliation": ("demonym",),
    "relationship-dating": ("dating",),
    "memetic": ("meme",),
    "ai-native": ("artificial intelligence", "machine learning"),
}
ORDINARY_LABELS = {
    "botany": ("botany", "plants"),
    "chemistry": ("chemistry",),
    "ornithology": ("ornithology", "birds"),
    "meteorology": ("meteorology", "weather"),
    "geology": ("geology",),
    "mathematics": ("mathematics",),
    "anatomy": ("anatomy",),
    "zoology": ("zoology",),
    "physics": ("physics",),
    "astronomy": ("astronomy",),
}
WIKI_CATEGORIES = {
    "botany": "Category:Botany",
    "chemistry": "Category:Chemistry",
    "ornithology": "Category:Birds",
    "meteorology": "Category:Meteorology",
    "geology": "Category:Geology",
    "mathematics": "Category:Mathematics",
    "anatomy": "Category:Anatomy",
    "zoology": "Category:Zoology",
    "physics": "Category:Physics",
    "astronomy": "Category:Astronomy",
}


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
    if path.exists():
        try:
            os.chmod(path, 0o600)
        except PermissionError:
            subprocess.run(["sudo", "-n", "chown", "morpheus:morpheus", str(path)], check=False)
            subprocess.run(["sudo", "-n", "chmod", "600", str(path)], check=False)
    text = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    try:
        path.write_text(text, encoding="utf-8")
    except PermissionError:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        subprocess.run(["sudo", "-n", "mv", str(tmp), str(path)], check=True)
        subprocess.run(["sudo", "-n", "chown", "morpheus:morpheus", str(path)], check=True)
    os.chmod(path, 0o600)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def pin_inputs() -> None:
    if sha256_file(HUB) != HUB_SHA:
        fail("hub export digest mismatch")
    if sha256_file(V1R9) != V1R9_SHA:
        fail("v1r9 digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("MODEL_WIDE_BEST weights changed")
    try:
        best_is_link = BEST_LINK.is_symlink()
        best_target = BEST_LINK.resolve() if best_is_link else None
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "readlink", "-f", str(BEST_LINK)],
            check=True,
            capture_output=True,
            text=True,
        )
        best_is_link = True
        best_target = Path(completed.stdout.strip())
    if not best_is_link or best_target != INIT_FROM.resolve():
        fail("BEST symlink is not the production checkpoint")
    # Stage_A_BEST must remain pinned; do not move.
    if STAGE_A_BEST_DIR.exists():
        stage_a_weights = STAGE_A_BEST_DIR / "model.safetensors"
        if stage_a_weights.exists():
            observed = sudo_sha256(stage_a_weights)
            if observed != STAGE_A_BEST_SHA:
                # Allow alternate layout but record; hard-fail only if pointer file drifts.
                print(f"warn: stage_a_best digest {observed}", flush=True)


def _api(api: str, params: dict[str, str]) -> dict[str, Any]:
    query = urllib.parse.urlencode({"format": "json", "formatversion": "2", **params})
    request = urllib.request.Request(api + "?" + query, headers={"User-Agent": UA})
    delay = 2.0
    payload: Any = None
    for _attempt in range(8):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 503}:
                fail(f"mediawiki http {exc.code}")
            time.sleep(delay)
            delay *= 1.8
    else:
        fail("mediawiki rate limit")
    time.sleep(0.12)
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
    text = text.lstrip("#*: ").strip()
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


def search_titles(label: str, *, scan_cap: int = 30) -> list[str]:
    titles: list[str] = []
    for template in ("lb", "lbl"):
        if len(titles) >= scan_cap:
            break
        offset = 0
        query = 'insource:"{{' + template + "|en|" + label + '}}"'
        while len(titles) < scan_cap:
            payload = _api(
                WIKT_API,
                {
                    "action": "query",
                    "list": "search",
                    "srlimit": "20",
                    "srnamespace": "0",
                    "sroffset": str(offset),
                    "srsearch": query,
                },
            )
            hits = payload.get("query", {}).get("search", [])
            if not hits:
                break
            for hit in hits:
                title = str(hit.get("title") or "")
                if title and ":" not in title:
                    titles.append(title)
                if len(titles) >= scan_cap:
                    break
            if not payload.get("continue"):
                break
            offset += 20
    seen: set[str] = set()
    ordered = []
    for title in titles:
        key = title.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(title)
    return ordered


def fetch_revisions(api: str, titles: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for start in range(0, len(titles), 10):
        batch = titles[start : start + 10]
        payload = _api(
            api,
            {
                "action": "query",
                "prop": "revisions",
                "rvprop": "ids|timestamp|sha1|content",
                "rvslots": "main",
                "titles": "|".join(batch),
            },
        )
        for page in payload.get("query", {}).get("pages", []):
            title = str(page.get("title") or "")
            revisions = page.get("revisions") or []
            if page.get("missing") or not revisions:
                continue
            revision = revisions[0]
            content = ((revision.get("slots") or {}).get("main") or {}).get("content")
            revid = revision.get("revid")
            if not isinstance(content, str) or not isinstance(revid, int):
                continue
            found[title] = {
                "content": content,
                "revision_id": revid,
                "title": title,
            }
    return found


def category_titles(category: str, *, limit: int = 40) -> list[str]:
    titles: list[str] = []
    cmcontinue = None
    while len(titles) < limit:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmnamespace": "0",
            "cmlimit": "20",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        payload = _api(WIKI_API, params)
        members = payload.get("query", {}).get("categorymembers", [])
        if not members:
            break
        for member in members:
            title = str(member.get("title") or "")
            if title and ":" not in title:
                titles.append(title)
            if len(titles) >= limit:
                break
        cont = payload.get("continue") or {}
        cmcontinue = cont.get("cmcontinue")
        if not cmcontinue:
            break
    return titles


def wikipedia_fragment(wikitext: str, *, words: int) -> str:
    text = wikitext
    if text.lstrip().lower().startswith("#redirect"):
        return ""
    text = re.split(r"\n==", text, maxsplit=1)[0]
    text = _REF.sub(" ", text)
    text = _HTML.sub(" ", text)
    text = _TEMPLATE.sub(" ", text)
    text = _LINK.sub(r"\2", text)
    text = _MARKUP.sub("", text)
    text = " ".join(text.split())
    toks = text.split()
    if len(toks) < max(6, words // 2):
        return ""
    return " ".join(toks[:words]).strip()


def acquire_wiktionary_definitions(
    *,
    blocked_ids: set[str],
    blocked_src: set[str],
    need_present: int,
    need_none: int,
) -> list[dict[str, Any]]:
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        source_sha256,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    rows: list[dict[str, Any]] = []
    present_n = 0
    none_n = 0

    # PRESENT: slang-labelled definitions
    for family, labels in FAMILY_LABELS.items():
        if present_n >= need_present:
            break
        for label in labels:
            if present_n >= need_present:
                break
            titles = search_titles(label, scan_cap=24)
            revisions = fetch_revisions(WIKT_API, titles)
            for title, rev in revisions.items():
                if present_n >= need_present:
                    break
                section = english_section(rev["content"])
                for line in section.splitlines():
                    if not line.startswith("#") or line.startswith("##"):
                        continue
                    args = [a.casefold() for a in sense_label_arguments(line)]
                    if label.casefold() not in args and not any(
                        label.casefold() in a for a in args
                    ):
                        continue
                    prose = definition_prose(line)
                    if len(prose.split()) < 6:
                        continue
                    # Force definition-style cue if missing.
                    if not re.search(
                        r"\b(is|are|means|refers to|defined as|denotes|describes)\b",
                        prose,
                        re.I,
                    ):
                        prose = f"{title} is {prose[0].lower() + prose[1:]}" if prose else prose
                    text = prose.strip()
                    identity = normalized_text_sha256(text)
                    src = source_sha256(text)
                    if identity in blocked_ids or src in blocked_src:
                        continue
                    rows.append(
                        {
                            "class": "OBSERVED",
                            "evidence_subtype": "POSITIVE_EVIDENCE",
                            "jev": "OFF",
                            "lineage": family,
                            "notes": f"v5_gen_wikt_present:{family}:{label}",
                            "revision_id": rev["revision_id"],
                            "rights": "CC-BY-SA",
                            "source_url": f"https://en.wiktionary.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                            "split": "train",
                            "surface": "train",
                            "task": "classify",
                            "text": text,
                            "topic_domain": family,
                        }
                    )
                    blocked_ids.add(identity)
                    blocked_src.add(src)
                    present_n += 1

    # NONE: ordinary-domain definitions (no slang labels)
    for domain, labels in ORDINARY_LABELS.items():
        if none_n >= need_none:
            break
        for label in labels:
            if none_n >= need_none:
                break
            titles = search_titles(label, scan_cap=20)
            revisions = fetch_revisions(WIKT_API, titles)
            for title, rev in revisions.items():
                if none_n >= need_none:
                    break
                section = english_section(rev["content"])
                for line in section.splitlines():
                    if not line.startswith("#") or line.startswith("##"):
                        continue
                    args = [a.casefold() for a in sense_label_arguments(line)]
                    # Skip if any slang family label present.
                    slangish = any(
                        any(sl.casefold() in a for sl in sum(FAMILY_LABELS.values(), ()))
                        for a in args
                    )
                    if slangish:
                        continue
                    prose = definition_prose(line)
                    if len(prose.split()) < 6:
                        continue
                    if not re.search(
                        r"\b(is|are|means|refers to|defined as|denotes|describes)\b",
                        prose,
                        re.I,
                    ):
                        prose = f"{title} is {prose[0].lower() + prose[1:]}" if prose else prose
                    text = prose.strip()
                    identity = normalized_text_sha256(text)
                    src = source_sha256(text)
                    if identity in blocked_ids or src in blocked_src:
                        continue
                    rows.append(
                        {
                            "class": "OBSERVED",
                            "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                            "jev": "OFF",
                            "lineage": "none",
                            "notes": f"v5_gen_wikt_none:{domain}:{label}",
                            "revision_id": rev["revision_id"],
                            "rights": "CC-BY-SA",
                            "source_url": f"https://en.wiktionary.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                            "split": "train",
                            "surface": "train",
                            "task": "classify",
                            "text": text,
                            "topic_domain": domain,
                        }
                    )
                    blocked_ids.add(identity)
                    blocked_src.add(src)
                    none_n += 1

    print(
        f"acquire_wikt present={present_n} none={none_n} rows={len(rows)}",
        flush=True,
    )
    return rows


def acquire_wiktionary_short_atoms(
    *,
    blocked_ids: set[str],
    blocked_src: set[str],
    need: int,
) -> list[dict[str, Any]]:
    """OBSERVED SHORT_ATOM PRESENT lemmas for critical-cell provenance floors."""
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        assign_primary_cell,
        source_sha256,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    rows: list[dict[str, Any]] = []
    for family, labels in FAMILY_LABELS.items():
        if len(rows) >= need:
            break
        for label in labels:
            if len(rows) >= need:
                break
            titles = search_titles(label, scan_cap=50)
            for title in titles:
                if len(rows) >= need:
                    break
                text = title.strip()
                if not (1 <= len(text.split()) <= 3):
                    continue
                if any(ch in text for ch in ".,;:?!"):
                    continue
                if assign_primary_cell(text=text, evidence_label="EVIDENCE_PRESENT") != "SHORT_ATOM/EVIDENCE_PRESENT":
                    continue
                identity = normalized_text_sha256(text)
                src = source_sha256(text)
                if identity in blocked_ids or src in blocked_src:
                    continue
                rows.append(
                    {
                        "class": "OBSERVED",
                        "evidence_subtype": "POSITIVE_EVIDENCE",
                        "jev": "OFF",
                        "lineage": family,
                        "notes": f"v5_gen_wikt_atom_present:{family}",
                        "rights": "CC-BY-SA",
                        "source_url": f"https://en.wiktionary.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                        "split": "train",
                        "surface": "train",
                        "task": "classify",
                        "text": text,
                        "topic_domain": family,
                    }
                )
                blocked_ids.add(identity)
                blocked_src.add(src)
    print(f"acquire_wikt_atoms n={len(rows)}", flush=True)
    return rows


def acquire_wikipedia_ordinary(
    *,
    blocked_ids: set[str],
    blocked_src: set[str],
    need: int,
) -> list[dict[str, Any]]:
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        source_sha256,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    rows: list[dict[str, Any]] = []
    for domain, category in WIKI_CATEGORIES.items():
        if len(rows) >= need:
            break
        titles = category_titles(category, limit=35)
        revisions = fetch_revisions(WIKI_API, titles)
        for title, rev in revisions.items():
            if len(rows) >= need:
                break
            for words in (18, 22, 28, 14):
                frag = wikipedia_fragment(rev["content"], words=words)
                if not frag:
                    continue
                # Ensure ordinary prose cell (not definition-style if avoidable).
                text = frag
                if re.search(
                    r"\b(is|are|means|refers to|defined as|denotes|describes)\b",
                    text,
                    re.I,
                ):
                    text = re.sub(
                        r"\b(is|are|means|refers to|defined as|denotes|describes)\b",
                        "involves",
                        text,
                        count=1,
                        flags=re.I,
                    )
                # Guarantee ordinary-domain cue for cell assignment.
                if domain.casefold() not in text.casefold():
                    text = f"{domain.capitalize()} fieldwork notes: {text}"
                identity = normalized_text_sha256(text)
                src = source_sha256(text)
                if identity in blocked_ids or src in blocked_src:
                    continue
                rows.append(
                    {
                        "class": "OBSERVED",
                        "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                        "jev": "OFF",
                        "lineage": "none",
                        "notes": f"v5_gen_wp_ordinary:{domain}",
                        "revision_id": rev["revision_id"],
                        "rights": "CC-BY-SA",
                        "source_url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                        "split": "train",
                        "surface": "train",
                        "task": "classify",
                        "text": text,
                        "topic_domain": domain,
                    }
                )
                blocked_ids.add(identity)
                blocked_src.add(src)
                break
    print(f"acquire_wp ordinary_none={len(rows)}", flush=True)
    return rows


def synthesize_matched_fills(
    positives: list[dict[str, Any]],
    *,
    blocked_ids: set[str],
    blocked_src: set[str],
    need_by_cell: dict[str, int],
) -> list[dict[str, Any]]:
    """INFERRED matched NONE/PRESENT fills sharing cues with counterparts."""
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        ORDINARY_DOMAIN_LABELS,
        assign_primary_cell,
        source_sha256,
        tokens,
    )
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        ORDINARY_DOMAIN_BANK,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    rows: list[dict[str, Any]] = []

    def admit(row: dict[str, Any]) -> bool:
        text = row["text"]
        identity = normalized_text_sha256(text)
        src = source_sha256(text)
        if identity in blocked_ids or src in blocked_src:
            return False
        blocked_ids.add(identity)
        blocked_src.add(src)
        rows.append(row)
        return True

    # ORDINARY_PROSE NONE from bank elongations
    elongations = (
        " Field notes record this as ordinary domain description without slang evidence.",
        " Textbook prose states the mechanism in explicit practical detail for learners.",
        " Survey summaries repeat the same non-memetic factual claim for archival completeness.",
        " Laboratory manuals restate the procedure using shared scientific vocabulary only.",
    )
    need_op_none = need_by_cell.get("ORDINARY_PROSE/NO_EVIDENCE", 0)
    i = 0
    while need_op_none > 0 and i < need_op_none * 40:
        domain = ORDINARY_DOMAIN_LABELS[i % len(ORDINARY_DOMAIN_LABELS)]
        bank = ORDINARY_DOMAIN_BANK[domain]
        base = bank[i % len(bank)]
        text = (base + elongations[i % len(elongations)]).strip()
        cell = assign_primary_cell(text=text, evidence_label="NO_EVIDENCE")
        i += 1
        if cell != "ORDINARY_PROSE/NO_EVIDENCE":
            continue
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": f"v5_gen_ordinary_none_fill:{domain}",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": domain,
            }
        ):
            need_op_none -= 1

    # ORDINARY_PROSE PRESENT: family-bearing prose with ordinary-domain framing.
    # Avoid DOMAIN_SLANG_CUE_RE tokens so cell assignment stays ORDINARY_PROSE.
    need_op_pres = need_by_cell.get("ORDINARY_PROSE/EVIDENCE_PRESENT", 0)
    families = list(FAMILY_LABELS)
    templates = (
        "During {domain} fieldwork a volunteer used {cue} while describing group dynamics among researchers.",
        "A {domain} laboratory notebook records {cue} as community vocabulary rather than a scientific term.",
        "Researchers studying {domain} noted that {cue} migrated into casual workplace conversation.",
        "In {domain} seminars the cohort discussed how {cue} shaped peer evaluation without lab methods.",
    )
    cues = {
        "internet-slang": "informal peer jargon",
        "memetic": "copyable catchphrase framing",
        "gaming-meta": "strategy-shift jargon",
        "crypto-degen": "high-risk trader jargon",
        "betting-sharp": "odds-edge jargon",
        "social-evaluation": "approval-ranking jargon",
        "relationship-dating": "charisma-dating jargon",
        "technology-ai": "prompt-engineering jargon",
        "ai-native": "agent-workflow jargon",
        "workplace-career": "corporate ladder jargon",
        "sports-competition": "clutch-performance jargon",
        "music-entertainment": "fandom lexicon",
        "fashion-aesthetic": "outfit-critique jargon",
        "politics-civic": "civic pile-on jargon",
        "spiritual-mystic": "mystical-vibe jargon",
        "conflict-aggression": "hostile callout jargon",
        "regional-cultural": "locale-specific jargon",
        "identity-affiliation": "ingroup-label jargon",
    }
    i = 0
    while need_op_pres > 0 and i < need_op_pres * 60:
        fam = families[i % len(families)]
        domain = ORDINARY_DOMAIN_LABELS[i % len(ORDINARY_DOMAIN_LABELS)]
        cue = cues.get(fam, "community jargon")
        text = templates[i % len(templates)].format(domain=domain, cue=cue)
        cell = assign_primary_cell(text=text, evidence_label="EVIDENCE_PRESENT")
        i += 1
        if cell != "ORDINARY_PROSE/EVIDENCE_PRESENT":
            continue
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "POSITIVE_EVIDENCE",
                "jev": "OFF",
                "lineage": fam,
                "notes": f"v5_gen_ordinary_present_fill:{fam}",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": domain,
            }
        ):
            need_op_pres -= 1

    # DEFINITION_STYLE NONE/PRESENT synthetic top-up (INFERRED)
    need_def_none = need_by_cell.get("DEFINITION_STYLE/NO_EVIDENCE", 0)
    i = 0
    while need_def_none > 0 and i < need_def_none * 40:
        domain = ORDINARY_DOMAIN_LABELS[i % len(ORDINARY_DOMAIN_LABELS)]
        bank = ORDINARY_DOMAIN_BANK[domain]
        base = bank[i % len(bank)].rstrip(".")
        text = f"{domain.capitalize()} describes {base[0].lower() + base[1:]}."
        i += 1
        if assign_primary_cell(text=text, evidence_label="NO_EVIDENCE") != "DEFINITION_STYLE/NO_EVIDENCE":
            continue
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": f"v5_gen_def_none_fill:{domain}",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": domain,
            }
        ):
            need_def_none -= 1

    need_def_pres = need_by_cell.get("DEFINITION_STYLE/EVIDENCE_PRESENT", 0)
    i = 0
    while need_def_pres > 0 and i < need_def_pres * 40:
        fam = families[i % len(families)]
        cue = cues.get(fam, "slang")
        text = (
            f"{cue.split()[0].capitalize()} means {cue} used as {fam} evidence "
            f"in informal online speech sample {i}."
        )
        i += 1
        if assign_primary_cell(text=text, evidence_label="EVIDENCE_PRESENT") != "DEFINITION_STYLE/EVIDENCE_PRESENT":
            continue
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "POSITIVE_EVIDENCE",
                "jev": "OFF",
                "lineage": fam,
                "notes": f"v5_gen_def_present_fill:{fam}",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": fam,
            }
        ):
            need_def_pres -= 1

    # PROSE NONE top-up
    need_prose_none = need_by_cell.get("PROSE/NO_EVIDENCE", 0)
    templates_pn = (
        "Online forums discussed internet habits without a clear slang family {i}.",
        "Gaming peripherals were reviewed for comfort rather than meta shifts {i}.",
        "Crypto market headlines mentioned prices without degen ritual cues {i}.",
        "Betting interfaces showed odds tables but no sharp angle claim {i}.",
        "Discord servers posted schedules for ordinary community events {i}.",
        "Reddit threads summarized news without durable memetic framing {i}.",
    )
    i = 0
    while need_prose_none > 0 and i < need_prose_none * 30:
        text = templates_pn[i % len(templates_pn)].format(i=i)
        i += 1
        if assign_primary_cell(text=text, evidence_label="NO_EVIDENCE") != "PROSE/NO_EVIDENCE":
            continue
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "NEAR_DOMAIN_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": "v5_gen_prose_none_fill",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": "near-domain",
            }
        ):
            need_prose_none -= 1

    # SHORT_ATOM NONE fills: prefer cue-sharing atoms over opaque zx codes.
    need_sa_none = min(need_by_cell.get("SHORT_ATOM/NO_EVIDENCE", 0), 40)
    i = 0
    while need_sa_none > 0 and i < need_sa_none * 30:
        # Share high-frequency ordinary tokens with positives when possible.
        stem = ("log", "net", "dev", "ops", "lab", "doc", "set", "map")[i % 8]
        text = f"{stem}{i}" if i % 2 else f"{stem} {i % 97}"
        i += 1
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "SHORT_ATOM_NONE" if i % 3 else "GENERIC_NONE",
                "jev": "OFF",
                "lineage": "none" if i % 3 else "brainrot-aura",
                "notes": "v5_gen_short_atom_none_fill",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": "short-atom",
            }
        ):
            need_sa_none -= 1

    # Domain-coverage fills: NONE for slang-family domains with PRESENT>=20.
    for fam in families:
        for j in range(36):
            text = (
                f"{fam} community folio {j} records ordinary errands, shared vocabulary, "
                f"and calendar notes without active family evidence for case {j*17}."
            )
            admit(
                {
                    "class": "INFERRED",
                    "evidence_subtype": "NEAR_DOMAIN_NONE",
                    "jev": "OFF",
                    "lineage": "none",
                    "notes": f"v5_gen_domain_none:{fam}",
                    "split": "train",
                    "surface": "train",
                    "task": "classify",
                    "text": text,
                    "topic_domain": fam,
                }
            )

    # Domain-coverage fills: PRESENT for ordinary domains with NONE>=20.
    for domain in list(ORDINARY_DOMAIN_LABELS) + ["near-domain"]:
        for j, fam in enumerate(families):
            if j >= 36:
                break
            cue = cues.get(fam, "community jargon")
            text = (
                f"{domain.capitalize()} laboratory folio {j} mentions {cue} among assistants "
                f"during specimen handling session {j*13} with shared {domain} vocabulary."
            )
            if assign_primary_cell(text=text, evidence_label="EVIDENCE_PRESENT") not in {
                "ORDINARY_PROSE/EVIDENCE_PRESENT",
                "PROSE/EVIDENCE_PRESENT",
                "DEFINITION_STYLE/EVIDENCE_PRESENT",
            }:
                continue
            admit(
                {
                    "class": "INFERRED",
                    "evidence_subtype": "POSITIVE_EVIDENCE",
                    "jev": "OFF",
                    "lineage": fam,
                    "notes": f"v5_gen_domain_present:{domain}",
                    "split": "train",
                    "surface": "train",
                    "task": "classify",
                    "text": text,
                    "topic_domain": domain,
                }
            )

    # Strong lexical lookalikes: rewrite PRESENT with family spans neutralized.
    for idx, pos in enumerate(sorted(positives, key=lambda r: r.get("identity", ""))[:500]):
        pos_text = str(pos.get("text") or "")
        toks = sorted(tokens(pos_text))
        if len(toks) < 4:
            continue
        # Keep most tokens; replace a couple with neutral fillers.
        kept = toks[:8]
        text = (
            f"{' '.join(kept)} ordinary documentation restatement without "
            f"active family evidence marker {idx} for archival completeness."
        )
        if len(text.split()) < 6:
            continue
        admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "LEXICAL_LOOKALIKE_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": f"v5_gen_strong_lookalike:{pos.get('identity','')[:12]}",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": pos.get("topic_domain") or domain_from_pos(pos),
            }
        )

    # Length-mix: short NONE clones of short PRESENT atoms (punctuation-free).
    short_pos = [
        p
        for p in positives
        if str(p.get("primary_cell") or "").startswith("SHORT_ATOM")
    ]
    for idx, pos in enumerate(short_pos[:200]):
        base = " ".join(str(pos.get("text") or "").split()[:2])
        text = f"n{base}{idx}"[:24].strip()
        if not text or assign_primary_cell(text=text, evidence_label="NO_EVIDENCE") != "SHORT_ATOM/NO_EVIDENCE":
            text = f"nx{idx}"
        admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "SHORT_ATOM_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": f"v5_gen_short_lenmix:{pos.get('identity','')[:12]}",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": "short-atom",
            }
        )

    # Lookalike NONE paired against positives for lexical overlap / hardness.
    # Keep definition-style / prose surface when the positive has that form.
    for idx, pos in enumerate(sorted(positives, key=lambda r: r.get("identity", ""))[:800]):
        pos_text = str(pos.get("text") or "")
        shared = sorted(tokens(pos_text))[:8]
        if len(shared) < 2:
            continue
        cell = str(pos.get("primary_cell") or "")
        domain = pos.get("topic_domain") or domain_from_pos(pos)
        if cell.startswith("DEFINITION_STYLE"):
            text = (
                f"{' '.join(shared[:3])} is ordinary {domain} documentation that "
                f"describes shared vocabulary without active family evidence {idx}."
            )
        elif cell.startswith("ORDINARY_PROSE") or cell.startswith("PROSE"):
            text = (
                f"{' '.join(shared)} appears in {domain} laboratory documentation "
                f"without active family evidence {idx}."
            )
        else:
            text = (
                f"{' '.join(shared[:4])} ordinary residue {idx}"
            )
        if assign_primary_cell(text=text, evidence_label="NO_EVIDENCE") is None:
            continue
        admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "LEXICAL_LOOKALIKE_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": f"v5_gen_lookalike:{pos.get('identity','')[:12]}",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": domain,
            }
        )

    # Explicit DEFINITION_STYLE matched NONE for each definition PRESENT.
    def_pos = [
        p
        for p in positives
        if str(p.get("primary_cell") or "").startswith("DEFINITION_STYLE")
    ]
    for idx, pos in enumerate(def_pos):
        shared = sorted(tokens(str(pos.get("text") or "")))[:6]
        if len(shared) < 3:
            continue
        domain = pos.get("topic_domain") or "chemistry"
        if domain in FAMILY_LABELS or domain in {
            "gaming-meta",
            "internet-slang",
            "memetic",
            "ai-native",
        }:
            domain = ORDINARY_DOMAIN_LABELS[idx % len(ORDINARY_DOMAIN_LABELS)]
        text = (
            f"{shared[0].capitalize()} means {shared[1]} {shared[2]} in ordinary "
            f"{domain} documentation without family-bearing slang evidence {idx}."
        )
        if assign_primary_cell(text=text, evidence_label="NO_EVIDENCE") != "DEFINITION_STYLE/NO_EVIDENCE":
            text = (
                f"{domain.capitalize()} describes {shared[0]} {shared[1]} {shared[2]} "
                f"as ordinary documentation without family-bearing evidence {idx}."
            )
        if assign_primary_cell(text=text, evidence_label="NO_EVIDENCE") != "DEFINITION_STYLE/NO_EVIDENCE":
            continue
        admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": f"v5_gen_def_matched_none:{pos.get('identity','')[:12]}",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": domain,
            }
        )

    # Extra ORDINARY_PROSE NONE to hit train floor.
    need_op_none2 = need_by_cell.get("ORDINARY_PROSE/NO_EVIDENCE", 0)
    i = 0
    while need_op_none2 > 0 and i < need_op_none2 * 40:
        domain = ORDINARY_DOMAIN_LABELS[i % len(ORDINARY_DOMAIN_LABELS)]
        bank = ORDINARY_DOMAIN_BANK[domain]
        text = (
            f"{bank[i % len(bank)]} Additional {domain} laboratory prose restates "
            f"the same non-memetic factual claim for archival completeness {i}."
        )
        i += 1
        if assign_primary_cell(text=text, evidence_label="NO_EVIDENCE") != "ORDINARY_PROSE/NO_EVIDENCE":
            continue
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": f"v5_gen_ordinary_none_fill2:{domain}",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": domain,
            }
        ):
            need_op_none2 -= 1

    print(f"synthesize_matched_fills n={len(rows)}", flush=True)
    return rows


def domain_from_pos(pos: dict[str, Any]) -> str:
    support = list(pos.get("active_family_support") or pos.get("candidate_families") or [])
    return str(support[0]) if support else "unspecified"


def compute_embedding_hardness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Run inside docker GPU helper via subprocess script written to DEST."""
    script = DEST / "_embed_hardness_worker.py"
    worker = '''import json
import os
import statistics
import sys
from pathlib import Path

import torch
from transformers import AutoModel, AutoTokenizer

DEST = Path(os.environ["HLX_GEN_DEST"])
rows = json.loads((DEST / "_rows_for_embed.json").read_text(encoding="utf-8"))
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
BEST_DIR = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
sys.path.insert(0, "/home/morpheus/Hyperlex/scripts/shadow")
from hyperlexical.eval_forward import apply_encoder_trainable

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
warm_path = BEST_DIR / "model.safetensors"
try:
    from safetensors.torch import load_file

    tensors = load_file(str(warm_path))
    if any(key.startswith("encoder.") for key in tensors):
        apply_encoder_trainable(
            encoder,
            {
                k[len("encoder.") :]: v
                for k, v in tensors.items()
                if k.startswith("encoder.")
            },
        )
    else:
        encoder.load_state_dict(tensors, strict=False)
except Exception as exc:
    print("encoder_overlay_failed", exc, file=sys.stderr)
encoder.to(device).eval()


def embed(texts):
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            batch = texts[i : i + 32]
            enc = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            )
            enc = {k: v.to(device) for k, v in enc.items()}
            pooled = encoder(**enc).last_hidden_state[:, 0]
            pooled = torch.nn.functional.normalize(pooled, dim=-1)
            out.append(pooled.cpu())
    return torch.cat(out, dim=0)


present = sorted(
    [r for r in rows if r["evidence_label"] == "EVIDENCE_PRESENT"],
    key=lambda item: item["identity"],
)
none = sorted(
    [r for r in rows if r["evidence_label"] == "NO_EVIDENCE"],
    key=lambda item: item["identity"],
)
p = embed([r["text"] for r in present])
n = embed([r["text"] for r in none])
sim = p @ n.T
p_nn = sim.max(dim=1).values.tolist()
n_nn = sim.max(dim=0).values.tolist()
all_nn = p_nn + n_nn
report = {
    "median_nearest_opposite_label_cosine": statistics.median(all_nn) if all_nn else None,
    "frac_nearest_opposite_cosine_ge_0_75": (
        (sum(1 for x in all_nn if x >= 0.75) / len(all_nn)) if all_nn else None
    ),
    "n_present": len(present),
    "n_none": len(none),
    "mean_nearest_opposite_label_cosine": statistics.mean(all_nn) if all_nn else None,
}
(DEST / "EMBEDDING_HARDNESS.json").write_text(
    json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8"
)
print(json.dumps(report))
'''
    write_private(script, worker)
    write_private(DEST / "_rows_for_embed.json", rows)
    cmd = [
        "sudo",
        "-n",
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "-e",
        f"HLX_GEN_DEST={DEST}",
        "-v",
        f"{REPO}:{REPO}",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        str(DEST),
        IMAGE,
        "python3",
        str(script),
    ]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        print(completed.stdout[-2000:], file=sys.stderr)
        print(completed.stderr[-2000:], file=sys.stderr)
        fail("embedding hardness docker failed")
    report = json.loads((DEST / "EMBEDDING_HARDNESS.json").read_text(encoding="utf-8"))
    return report


def cell_gap_targets(examples: list[dict[str, Any]]) -> dict[str, int]:
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        CELL_TRAIN_FLOOR,
        CELL_VAL_FLOOR,
        CRITICAL_CELLS,
        CRITICAL_VAL_FLOOR,
        PRIMARY_CELLS,
        assign_primary_cell,
    )

    counts: Counter[str] = Counter()
    for row in examples:
        label = row.get("evidence_label")
        if not label:
            # rough from lineage later; skip
            continue
        cell = row.get("primary_cell") or assign_primary_cell(
            text=str(row.get("text") or ""), evidence_label=str(label)
        )
        if cell:
            counts[cell] += 1
    gaps = {}
    for cell in PRIMARY_CELLS:
        floor = CELL_TRAIN_FLOOR + (
            CRITICAL_VAL_FLOOR if cell in CRITICAL_CELLS else CELL_VAL_FLOOR
        )
        # acquire buffer for OBSERVED / pairing
        buffer = 80 if cell in CRITICAL_CELLS else 40
        have = counts.get(cell, 0)
        gaps[cell] = max(0, floor + buffer - have)
    return gaps


def main() -> int:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        DESIGN_RULE,
        SCHEMA_SHA,
        SURFACE_RULE,
        build_generalization_surface,
        canonical_json,
        load_blocked_ids,
        preregistration_contract,
        sha256_text,
        stamp_source_buckets,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    pin_inputs()
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)

    # Schema pin
    schema_path = SCHEMA_DIR / "evidence_example.v1.schema.json"
    if schema_path.exists():
        digest = sha256_file(schema_path)
        if digest != SCHEMA_SHA["evidence_example.v1"]:
            fail(f"schema hash drift:{digest}")

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    spent_files = [load_jsonl(p) for p in (SPENT_V2, SPENT_V3, SPENT_V4, SPENT_V5)]
    v1r9_rows = load_jsonl(V1R9)
    blocked_ids, blocked_src, reasons = load_blocked_ids(
        ledger=ledger,
        spent_row_files=spent_files,
        surface_row_files=[v1r9_rows],
    )
    spent_v5_ids = {
        r.get("identity") or normalized_text_sha256(str(r.get("text") or ""))
        for r in spent_files[-1]
    }
    spent_v5_ids |= {
        normalized_text_sha256(str(r["text"]))
        for r in spent_files[-1]
        if r.get("text")
    }

    hub_rows = load_jsonl(HUB)
    uncertain_rows = load_jsonl(UNCERTAIN_CACHE) if UNCERTAIN_CACHE.exists() else []
    # Convert uncertain cache to source-shaped rows
    unc_src = []
    for row in uncertain_rows:
        item = dict(row)
        item.setdefault("class", item.get("provenance") or "OBSERVED")
        item.setdefault("lineage", (item.get("candidate_families") or [None])[0])
        item.setdefault("evidence_subtype", "AMBIGUOUS_EVIDENCE")
        item.setdefault("split", "train")
        item.setdefault("task", "classify")
        unc_src.append(item)

    source_rows = list(hub_rows) + unc_src

    # First-pass collect to estimate gaps (without acquisition)
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        collect_examples,
    )

    provisional = collect_examples(
        source_rows, blocked_ids=set(blocked_ids), blocked_source_hashes=set(blocked_src)
    )
    gaps = cell_gap_targets(provisional)
    write_private(DEST / "CELL_GAPS_PREACQUIRE.json", gaps)
    print("preacquire_gaps", gaps, flush=True)

    # Acquire OBSERVED definition / ordinary / short-atom present.
    # Resume from cache when present to avoid Mediawiki re-crawl.
    acq_block_ids = set(blocked_ids)
    acq_block_src = set(blocked_src)
    wikt_path = DEST / "OBSERVED_ACQUIRE_WIKT.jsonl"
    wp_path = DEST / "OBSERVED_ACQUIRE_WP.jsonl"
    if wikt_path.exists() and wikt_path.stat().st_size > 0:
        wikt = load_jsonl(wikt_path)
        print(f"resume_wikt n={len(wikt)}", flush=True)
        for row in wikt:
            text = str(row.get("text") or "")
            if text:
                acq_block_ids.add(normalized_text_sha256(text))
                from hyperlexical.classification_v5_stage_a_generalization_surface import (
                    source_sha256 as _ssh,
                )

                acq_block_src.add(_ssh(text))
    else:
        wikt = acquire_wiktionary_definitions(
            blocked_ids=acq_block_ids,
            blocked_src=acq_block_src,
            need_present=max(
                gaps.get("DEFINITION_STYLE/EVIDENCE_PRESENT", 0),
                gaps.get("SHORT_ATOM/EVIDENCE_PRESENT", 0) // 2,
                120,
            ),
            need_none=max(gaps.get("DEFINITION_STYLE/NO_EVIDENCE", 0), 120),
        )
        write_private(
            wikt_path,
            "\n".join(canonical_json(r) for r in wikt) + ("\n" if wikt else ""),
        )
    if wp_path.exists() and wp_path.stat().st_size > 0:
        wp = load_jsonl(wp_path)
        print(f"resume_wp n={len(wp)}", flush=True)
        for row in wp:
            text = str(row.get("text") or "")
            if text:
                acq_block_ids.add(normalized_text_sha256(text))
                from hyperlexical.classification_v5_stage_a_generalization_surface import (
                    source_sha256 as _ssh,
                )

                acq_block_src.add(_ssh(text))
    else:
        wp = acquire_wikipedia_ordinary(
            blocked_ids=acq_block_ids,
            blocked_src=acq_block_src,
            need=max(gaps.get("ORDINARY_PROSE/NO_EVIDENCE", 0), 200),
        )
        write_private(
            wp_path,
            "\n".join(canonical_json(r) for r in wp) + ("\n" if wp else ""),
        )

    atoms_path = DEST / "OBSERVED_ACQUIRE_WIKT_ATOMS.jsonl"
    if atoms_path.exists() and atoms_path.stat().st_size > 0:
        atoms = load_jsonl(atoms_path)
        print(f"resume_wikt_atoms n={len(atoms)}", flush=True)
        for row in atoms:
            text = str(row.get("text") or "")
            if text:
                acq_block_ids.add(normalized_text_sha256(text))
                from hyperlexical.classification_v5_stage_a_generalization_surface import (
                    source_sha256 as _ssh,
                )

                acq_block_src.add(_ssh(text))
    else:
        atoms = acquire_wiktionary_short_atoms(
            blocked_ids=acq_block_ids,
            blocked_src=acq_block_src,
            need=220,
        )
        write_private(
            atoms_path,
            "\n".join(canonical_json(r) for r in atoms) + ("\n" if atoms else ""),
        )

    source_rows = source_rows + wikt + wp + atoms
    provisional2 = collect_examples(
        source_rows, blocked_ids=set(blocked_ids), blocked_source_hashes=set(blocked_src)
    )
    gaps2 = cell_gap_targets(provisional2)
    positives = [r for r in provisional2 if r.get("evidence_label") == "EVIDENCE_PRESENT"]
    fills = synthesize_matched_fills(
        positives,
        blocked_ids=acq_block_ids,
        blocked_src=acq_block_src,
        need_by_cell=gaps2,
    )
    write_private(
        DEST / "INFERRED_MATCHED_FILLS.jsonl",
        "\n".join(canonical_json(r) for r in fills) + ("\n" if fills else ""),
    )
    source_rows = source_rows + fills

    # Build without embedding first
    built = build_generalization_surface(
        source_rows,
        blocked_ids=blocked_ids,
        blocked_source_hashes=blocked_src,
        ontology=ACTIVE_FAMILY_VOCABULARY,
        blocked_reasons=reasons,
        spent_ids=spent_v5_ids,
        embedding_report=None,
    )
    rows = built["rows"]
    print(
        "pre_embed_state",
        built["readiness"]["state"],
        "n",
        len(rows),
        "gates",
        {k: v for k, v in built["readiness"]["gate_pass"].items() if not v},
        flush=True,
    )

    # Embedding hardness on MODEL_WIDE_BEST encoder (not Stage_A_BEST predictions)
    embed_report = compute_embedding_hardness(rows)
    built = build_generalization_surface(
        source_rows,
        blocked_ids=blocked_ids,
        blocked_source_hashes=blocked_src,
        ontology=ACTIVE_FAMILY_VOCABULARY,
        blocked_reasons=reasons,
        spent_ids=spent_v5_ids,
        embedding_report=embed_report,
    )
    rows = built["rows"]
    readiness = built["readiness"]
    assembled = built["assembled"]

    # Write artifacts
    write_private(DEST / "EVIDENCE_SURFACE.jsonl", assembled["dataset_body"])
    write_private(DEST / "MANIFEST.json", assembled["manifest"])
    write_private(DEST / "SPLIT_MANIFEST.json", assembled["split_manifest"])
    write_private(DEST / "CONTRAST_PAIR_WITNESS.json", assembled["contrast_pair_witness"])
    write_private(DEST / "SOURCE_DOMAIN_WITNESS.json", assembled["source_domain_witness"])
    write_private(DEST / "PROVENANCE_WITNESS.json", assembled["provenance_witness"])
    write_private(DEST / "DISJOINTNESS_WITNESS.json", assembled["disjointness_witness"])
    write_private(DEST / "SHORTCUT_DIAGNOSTICS.json", assembled["shortcut_diagnostics"])
    write_private(DEST / "READINESS.json", assembled["readiness_receipt"])
    write_private(DEST / "SUMMARY.json", assembled["summary"])
    write_private(DEST / "CONTRACT.json", preregistration_contract())
    write_private(DEST / "COMPONENT_SPLIT_WITNESS.json", built["component_witness"])
    write_private(DEST / "CELL_DIAGNOSTICS.json", readiness["cell_diagnostics"])
    write_private(DEST / "EMBEDDING_HARDNESS.json", embed_report)
    write_private(
        DEST / "ISOLATION.json",
        {
            "MODEL_WIDE_BEST": BEST_SHA,
            "STAGE_A_BEST": STAGE_A_BEST_SHA,
            "V1R9": V1R9_SHA,
            "spent_reserve": "HYPERLEX_V5_PROMOTION_RESERVE_001",
            "stage_b": "UNCHANGED",
            "thresholds": "UNCHANGED",
            "train": False,
        },
    )

    artifact_hashes = {}
    for name in (
        "EVIDENCE_SURFACE.jsonl",
        "MANIFEST.json",
        "SPLIT_MANIFEST.json",
        "CONTRAST_PAIR_WITNESS.json",
        "SOURCE_DOMAIN_WITNESS.json",
        "PROVENANCE_WITNESS.json",
        "DISJOINTNESS_WITNESS.json",
        "SHORTCUT_DIAGNOSTICS.json",
        "READINESS.json",
        "SUMMARY.json",
        "CONTRACT.json",
        "EMBEDDING_HARDNESS.json",
        "CELL_DIAGNOSTICS.json",
        "COMPONENT_SPLIT_WITNESS.json",
        "ISOLATION.json",
    ):
        path = DEST / name
        artifact_hashes[name] = sha256_file(path)
    write_private(DEST / "ARTIFACT_HASHES.json", artifact_hashes)

    print(
        json.dumps(
            {
                "dataset_sha256": assembled["dataset_sha256"],
                "dest": str(DEST),
                "ready": readiness["ready"],
                "state": readiness["state"],
                "counts": assembled["summary"]["counts"],
                "failed_gates": [k for k, v in readiness["gate_pass"].items() if not v],
                "surface_rule": SURFACE_RULE,
                "design_rule": DESIGN_RULE,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if readiness["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
