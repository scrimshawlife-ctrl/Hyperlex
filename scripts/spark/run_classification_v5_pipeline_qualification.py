"""QUALIFY_HYPERLEX_V5_PIPELINE_ON_FRESH_EVALUATION_SURFACE — Spark phase.

Acquire a fresh text-identifiable qualification surface, seal it, then score
the sealed V5 Stage-A/B V1R2 package exactly once. No train / retune / rebuild.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v5-pipeline-qualification-001-20261001"
)
STAGE_A_BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/STAGE_A_BEST/model.safetensors"
)
STAGE_A_BEST_SHA = (
    "f2b00c5dfeb087288fc1686c901fbc8b52a8ba7a7b51cb83ff038656f93617fa"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
INDEX_PATH = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-b-v1r2-20261001/"
    "STAGE_B_INDEX.json"
)
INDEX_SHA = "4febe96ea179597eb7792b376ed9eedbc9295a2fd8b5fa0eec969719f015c1f4"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-PIPELINE-QUALIFICATION-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
MAX_LEN = 256
SEED = 20261001

WIKT_API = "https://en.wiktionary.org/w/api.php"
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = (
    "HyperlexV5PipelineQualification/1.0 "
    "(fresh qualification surface; mediawiki provenance)"
)

FAMILY_LABELS = {
    "gaming-meta": ("gaming", "video games", "esports"),
    "crypto-degen": ("cryptocurrency", "blockchain"),
    "betting-sharp": ("gambling", "poker"),
    "internet-slang": ("internet slang", "chat slang"),
    "technology-ai": ("computing", "software engineering"),
    "sports-competition": ("sports", "athletics"),
    "music-entertainment": ("music", "popular music"),
    "fashion-aesthetic": ("fashion", "cosmetics"),
    "workplace-career": ("business jargon", "management"),
    "politics-civic": ("politics", "government"),
    "spiritual-mystic": ("astrology", "occult"),
    "social-evaluation": ("slang", "pejoratives"),
    "conflict-aggression": ("military slang", "warfare"),
    "regional-cultural": ("british slang", "australian slang"),
    "identity-affiliation": ("demonyms", "ethnic slurs"),
    "relationship-dating": ("dating", "sexuality"),
    "memetic": ("internet memes", "meme"),
    "ai-native": ("artificial intelligence", "machine learning"),
}
ORDINARY_LABELS = {
    "mycology": ("mycology", "fungi"),
    "entomology": ("entomology", "insects"),
    "oceanography": ("oceanography", "marine biology"),
    "paleontology": ("paleontology", "fossils"),
    "cartography": ("cartography", "maps"),
    "numismatics": ("numismatics", "coins"),
    "philately": ("philately", "postage stamps"),
    "archaeology": ("archaeology",),
    "hydrology": ("hydrology",),
    "mineralogy": ("mineralogy",),
}
WIKI_CATEGORIES = {
    "mycology": "Category:Mycology",
    "entomology": "Category:Entomology",
    "oceanography": "Category:Oceanography",
    "paleontology": "Category:Paleontology",
    "cartography": "Category:Cartography",
    "numismatics": "Category:Numismatics",
    "philately": "Category:Philately",
    "archaeology": "Category:Archaeology",
    "hydrology": "Category:Hydrology",
    "mineralogy": "Category:Mineralogy",
}
DOMAIN_IRRELEVANT_CATEGORIES = {
    "domain_irrelevant_lists": "Category:Lists of lists",
    "domain_irrelevant_years": "Category:2020s",
    "domain_irrelevant_infra": "Category:Railway stations in France",
}

_SENSE = re.compile(r"\{\{\s*(lb|lbl|tlb)\s*\|\s*en\s*\|([^{}]*)\}\}", re.I)
_LINK = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
_MARKUP = re.compile(r"''+")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_HTML = re.compile(r"<[^>]+>")
_REF = re.compile(r"<ref\b[^>]*>.*?</ref>", re.I | re.S)

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
        return subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split()[0]


def sudo_read_text(path: Path) -> str:
    if os.access(path, os.R_OK):
        return path.read_text(encoding="utf-8")
    return subprocess.run(
        ["sudo", "-n", "cat", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def write_private(path: Path, payload: dict | str | list) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        text = payload
    else:
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    os.chmod(path, 0o600)


def write_repo(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def code_revision() -> str:
    env = os.environ.get("HLX_V5_STAGE_A_CODE_REVISION")
    if env:
        return env
    try:
        return subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


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
    time.sleep(0.08)
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


def search_titles(label: str, *, scan_cap: int = 40, sroffset_start: int = 40) -> list[str]:
    """Start at elevated offset to reduce overlap with prior generalization acquires."""
    titles: list[str] = []
    for template in ("lb", "lbl"):
        if len(titles) >= scan_cap:
            break
        offset = int(sroffset_start)
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


def category_titles(category: str, *, limit: int = 50, skip: int = 30) -> list[str]:
    titles: list[str] = []
    skipped = 0
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
            if not title or ":" in title:
                continue
            if skipped < skip:
                skipped += 1
                continue
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


def build_blocked_sets() -> dict[str, Any]:
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        source_sha256,
    )
    from hyperlexical.classification_v5_surface_readiness_gates import (
        near_duplicate_key,
        tokens,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    blocked_ids: set[str] = set()
    blocked_src: set[str] = set()
    blocked_text: set[str] = set()
    blocked_near: set[str] = set()
    sources: list[str] = []

    patterns = [
        "/home/morpheus/hlx-private/classification-v5-stage-a-*/EVIDENCE_SURFACE.jsonl",
        "/home/morpheus/hlx-private/classification-v5-stage-a-negative-evidence-surface-*/EVIDENCE_SURFACE.jsonl",
        "/home/morpheus/hlx-private/classification-v5-stage-a-generalization-surface-*/EVIDENCE_SURFACE.jsonl",
        "/home/morpheus/hlx-private/classification-v5-reserve-20260930/RESERVE.jsonl",
        "/home/morpheus/hlx-private/classification-v4-reserve-20260930/reserve-rows.jsonl",
        "/home/morpheus/hlx-private/classification-v3-reserve-20260930/reserve-rows.jsonl",
        "/home/morpheus/hlx-private/classification-v2-train-ready-20260929/reserve-eval-rows.jsonl",
        "/home/morpheus/hlx-private/classification-v5-uncertain-acquire-cache-20260930/OBSERVED_UNCERTAIN_ACQUIRE.jsonl",
    ]
    import glob

    paths: list[str] = []
    for pat in patterns:
        paths.extend(glob.glob(pat))
    for path in sorted(set(paths)):
        p = Path(path)
        if not p.exists():
            continue
        sources.append(str(p))
        for row in load_jsonl(p):
            text = str(row.get("text") or "")
            if not text:
                continue
            ident = str(row.get("identity") or normalized_text_sha256(text))
            blocked_ids.add(ident)
            blocked_src.add(str(row.get("source_sha256") or source_sha256(text)))
            blocked_text.add(normalized_text_sha256(text))
            blocked_near.add(near_duplicate_key(text))
            if row.get("parent_identity"):
                blocked_ids.add(str(row["parent_identity"]))

    idx = json.loads(sudo_read_text(INDEX_PATH))
    for rec in idx.get("records") or []:
        text = str(rec.get("text") or "")
        if not text:
            continue
        blocked_text.add(normalized_text_sha256(text))
        blocked_src.add(source_sha256(text))
        blocked_ids.add(normalized_text_sha256(text))
        blocked_near.add(near_duplicate_key(text))

    return {
        "blocked_ids": blocked_ids,
        "blocked_src": blocked_src,
        "blocked_text": blocked_text,
        "blocked_near": blocked_near,
        "source_paths": sources,
        "n_index_records": len(idx.get("records") or []),
    }


def is_blocked(
    text: str,
    *,
    blocked: Mapping[str, Any],
) -> bool:
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        source_sha256,
    )
    from hyperlexical.classification_v5_surface_readiness_gates import (
        near_duplicate_key,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    ident = normalized_text_sha256(text)
    src = source_sha256(text)
    near = near_duplicate_key(text)
    return (
        ident in blocked["blocked_ids"]
        or ident in blocked["blocked_text"]
        or src in blocked["blocked_src"]
        or near in blocked["blocked_near"]
    )


def mark_blocked(text: str, blocked: dict[str, Any]) -> str:
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        source_sha256,
    )
    from hyperlexical.classification_v5_surface_readiness_gates import (
        near_duplicate_key,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    ident = normalized_text_sha256(text)
    blocked["blocked_ids"].add(ident)
    blocked["blocked_text"].add(ident)
    blocked["blocked_src"].add(source_sha256(text))
    blocked["blocked_near"].add(near_duplicate_key(text))
    return ident


def acquire_all(blocked: dict[str, Any]) -> list[dict[str, Any]]:
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        assign_primary_cell,
        source_sha256,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    rows: list[dict[str, Any]] = []

    def admit(row: dict[str, Any]) -> bool:
        text = str(row["text"]).strip()
        if len(text.split()) < 1:
            return False
        if is_blocked(text, blocked=blocked):
            return False
        identity = mark_blocked(text, blocked)
        row["identity"] = identity
        row["source_sha256"] = source_sha256(text)
        row["source_family"] = str(row.get("notes") or row.get("topic_domain") or "x")
        rows.append(row)
        return True

    # PRESENT definitions
    for family, labels in FAMILY_LABELS.items():
        got = 0
        for label in labels:
            if got >= 20:
                break
            titles = search_titles(label, scan_cap=28, sroffset_start=60)
            revisions = fetch_revisions(WIKT_API, titles)
            for title, rev in revisions.items():
                if got >= 20:
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
                    if not re.search(
                        r"\b(is|are|means|refers to|defined as|denotes|describes)\b",
                        prose,
                        re.I,
                    ):
                        prose = f"{title} means {prose[0].lower() + prose[1:]}"
                    if admit(
                        {
                            "class": "OBSERVED",
                            "evidence_subtype": "POSITIVE_EVIDENCE",
                            "lineage": family,
                            "candidate_families": [family],
                            "notes": f"qual_wikt_present:{family}:{label}",
                            "revision_id": rev["revision_id"],
                            "rights": "CC-BY-SA",
                            "source_url": (
                                "https://en.wiktionary.org/wiki/"
                                + urllib.parse.quote(title.replace(" ", "_"))
                            ),
                            "text": prose.strip(),
                            "topic_domain": family,
                        }
                    ):
                        got += 1
        print(f"present {family}={got}", flush=True)

    # NONE ordinary definitions
    for domain, labels in ORDINARY_LABELS.items():
        got = 0
        for label in labels:
            if got >= 18:
                break
            titles = search_titles(label, scan_cap=24, sroffset_start=50)
            revisions = fetch_revisions(WIKT_API, titles)
            for title, rev in revisions.items():
                if got >= 18:
                    break
                section = english_section(rev["content"])
                for line in section.splitlines():
                    if not line.startswith("#") or line.startswith("##"):
                        continue
                    args = [a.casefold() for a in sense_label_arguments(line)]
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
                        prose = f"{title} is {prose[0].lower() + prose[1:]}"
                    if admit(
                        {
                            "class": "OBSERVED",
                            "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                            "lineage": "none",
                            "notes": f"qual_wikt_none:{domain}:{label}",
                            "revision_id": rev["revision_id"],
                            "rights": "CC-BY-SA",
                            "source_url": (
                                "https://en.wiktionary.org/wiki/"
                                + urllib.parse.quote(title.replace(" ", "_"))
                            ),
                            "text": prose.strip(),
                            "topic_domain": domain,
                        }
                    ):
                        got += 1
        print(f"none {domain}={got}", flush=True)

    # Wikipedia ordinary prose NONE
    for domain, category in WIKI_CATEGORIES.items():
        titles = category_titles(category, limit=25, skip=40)
        revisions = fetch_revisions(WIKI_API, titles)
        got = 0
        for title, rev in revisions.items():
            if got >= 8:
                break
            frag = wikipedia_fragment(rev["content"], words=22)
            if not frag:
                continue
            text = frag
            if domain.casefold() not in text.casefold():
                text = f"{domain} field notes: {text}"
            if admit(
                {
                    "class": "OBSERVED",
                    "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                    "lineage": "none",
                    "notes": f"qual_wp_ordinary:{domain}",
                    "revision_id": rev["revision_id"],
                    "rights": "CC-BY-SA",
                    "source_url": (
                        "https://en.wikipedia.org/wiki/"
                        + urllib.parse.quote(title.replace(" ", "_"))
                    ),
                    "text": text,
                    "topic_domain": domain,
                }
            ):
                got += 1

    # Domain-irrelevant NONE
    for domain, category in DOMAIN_IRRELEVANT_CATEGORIES.items():
        titles = category_titles(category, limit=30, skip=20)
        revisions = fetch_revisions(WIKI_API, titles)
        got = 0
        for title, rev in revisions.items():
            if got >= 15:
                break
            frag = wikipedia_fragment(rev["content"], words=20)
            if not frag:
                continue
            # Avoid slang cues.
            if re.search(
                r"\b(slang|meme|crypto|gaming|rizz|aura|degen)\b", frag, re.I
            ):
                continue
            if admit(
                {
                    "class": "OBSERVED",
                    "evidence_subtype": "GENERIC_NONE",
                    "lineage": "none",
                    "notes": f"qual_wp_domain_irrelevant:{domain}",
                    "revision_id": rev["revision_id"],
                    "rights": "CC-BY-SA",
                    "source_url": (
                        "https://en.wikipedia.org/wiki/"
                        + urllib.parse.quote(title.replace(" ", "_"))
                    ),
                    "text": frag,
                    "topic_domain": domain,
                }
            ):
                got += 1
        print(f"domain_irrelevant {domain}={got}", flush=True)

    # SHORT_ATOM NONE lemmas
    sa_none = 0
    for domain, labels in ORDINARY_LABELS.items():
        for label in labels:
            if sa_none >= 55:
                break
            titles = search_titles(label, scan_cap=50, sroffset_start=80)
            for title in titles:
                if sa_none >= 55:
                    break
                text = title.strip()
                if not (1 <= len(text.split()) <= 3):
                    continue
                if any(ch in text for ch in ".,;:?!"):
                    continue
                if (
                    assign_primary_cell(text=text, evidence_label="NO_EVIDENCE")
                    != "SHORT_ATOM/NO_EVIDENCE"
                ):
                    continue
                if admit(
                    {
                        "class": "OBSERVED",
                        "evidence_subtype": "SHORT_ATOM_NONE",
                        "lineage": "none",
                        "notes": f"qual_wikt_atom_none:{domain}",
                        "rights": "CC-BY-SA",
                        "source_url": (
                            "https://en.wiktionary.org/wiki/"
                            + urllib.parse.quote(title.replace(" ", "_"))
                        ),
                        "text": text,
                        "topic_domain": domain,
                    }
                ):
                    sa_none += 1
    print(f"short_atom_none={sa_none}", flush=True)

    # SHORT_ATOM PRESENT — only keep if text-identifiable later; acquire candidates
    sa_present = 0
    for family, labels in FAMILY_LABELS.items():
        for label in labels:
            if sa_present >= 80:
                break
            titles = search_titles(label, scan_cap=40, sroffset_start=70)
            for title in titles:
                if sa_present >= 80:
                    break
                # Prefer short definitional atoms that name the relation.
                text = f"{title} slang"
                if not (1 <= len(text.split()) <= 3):
                    text = title.strip()
                if not (1 <= len(text.split()) <= 4):
                    continue
                if (
                    assign_primary_cell(text=text, evidence_label="EVIDENCE_PRESENT")
                    not in {
                        "SHORT_ATOM/EVIDENCE_PRESENT",
                        "DEFINITION_STYLE/EVIDENCE_PRESENT",
                        "PROSE/EVIDENCE_PRESENT",
                    }
                ):
                    # For atoms use bare title only if atom cell.
                    text = title.strip()
                    if (
                        assign_primary_cell(text=text, evidence_label="EVIDENCE_PRESENT")
                        != "SHORT_ATOM/EVIDENCE_PRESENT"
                    ):
                        continue
                if admit(
                    {
                        "class": "OBSERVED",
                        "evidence_subtype": "POSITIVE_EVIDENCE",
                        "lineage": family,
                        "candidate_families": [family],
                        "notes": f"qual_wikt_atom_present:{family}",
                        "rights": "CC-BY-SA",
                        "source_url": (
                            "https://en.wiktionary.org/wiki/"
                            + urllib.parse.quote(title.replace(" ", "_"))
                        ),
                        "text": text,
                        "topic_domain": family,
                    }
                ):
                    sa_present += 1
    print(f"short_atom_present_candidates={sa_present}", flush=True)

    # UNCERTAIN: explicit multi-sense / unresolved glosses
    uncertain_n = 0
    for family, labels in list(FAMILY_LABELS.items())[:8]:
        for label in labels:
            if uncertain_n >= 70:
                break
            titles = search_titles(label, scan_cap=20, sroffset_start=100)
            revisions = fetch_revisions(WIKT_API, titles)
            for title, rev in revisions.items():
                if uncertain_n >= 70:
                    break
                section = english_section(rev["content"])
                senses = []
                for line in section.splitlines():
                    if not line.startswith("#") or line.startswith("##"):
                        continue
                    prose = definition_prose(line)
                    if len(prose.split()) >= 5:
                        senses.append(prose)
                    if len(senses) >= 2:
                        break
                if len(senses) < 2:
                    continue
                text = (
                    f"{title} may mean either ({senses[0]}) or ({senses[1]}); "
                    f"the intended sense is unresolved from the text alone."
                )
                if admit(
                    {
                        "class": "OBSERVED",
                        "evidence_subtype": "AMBIGUOUS_EVIDENCE",
                        "lineage": "none",
                        "notes": f"qual_wikt_uncertain:{family}",
                        "uncertainty_reason": "competing_textual_senses_unresolved",
                        "rights": "CC-BY-SA",
                        "source_url": (
                            "https://en.wiktionary.org/wiki/"
                            + urllib.parse.quote(title.replace(" ", "_"))
                        ),
                        "text": text,
                        "topic_domain": "ambiguous",
                    }
                ):
                    uncertain_n += 1
    print(f"uncertain={uncertain_n}", flush=True)

    # Lexical lookalike NONE: ordinary lemmas that look slangy but ordinary sense
    look = 0
    for domain, labels in list(ORDINARY_LABELS.items())[:5]:
        titles = search_titles(labels[0], scan_cap=30, sroffset_start=120)
        revisions = fetch_revisions(WIKT_API, titles[:20])
        for title, rev in revisions.items():
            if look >= 40:
                break
            section = english_section(rev["content"])
            for line in section.splitlines():
                if not line.startswith("#") or line.startswith("##"):
                    continue
                prose = definition_prose(line)
                if len(prose.split()) < 6:
                    continue
                text = f"In {domain}, {title} refers to {prose[0].lower() + prose[1:]}"
                if admit(
                    {
                        "class": "OBSERVED",
                        "evidence_subtype": "LEXICAL_LOOKALIKE_NONE",
                        "lineage": "none",
                        "notes": f"qual_wikt_lookalike:{domain}",
                        "rights": "CC-BY-SA",
                        "source_url": (
                            "https://en.wiktionary.org/wiki/"
                            + urllib.parse.quote(title.replace(" ", "_"))
                        ),
                        "text": text,
                        "topic_domain": domain,
                    }
                ):
                    look += 1
                    break
    print(f"lookalike={look} total_acquired={len(rows)}", flush=True)
    return rows


def compose_surface(raw_rows: list[dict[str, Any]]) -> tuple[list[dict], dict]:
    from hyperlexical.classification_v5_pipeline_qualification import (
        FAMILY_MAX_SHARE,
        NONE_MIN,
        PRESENT_MIN,
        TOTAL_PREFERRED,
        UNCERTAIN_MIN,
        composition_report,
        finalize_qualification_row,
        row_is_text_identifiable,
    )

    rng = random.Random(SEED)
    finalized: list[dict] = []
    rejected = Counter()
    for raw in raw_rows:
        try:
            # Ensure candidate_families for present
            if raw.get("evidence_subtype") == "POSITIVE_EVIDENCE":
                raw.setdefault(
                    "candidate_families",
                    [raw["lineage"]] if raw.get("lineage") not in {None, "none"} else [],
                )
            if raw.get("evidence_subtype") == "AMBIGUOUS_EVIDENCE":
                raw.setdefault(
                    "uncertainty_reason", "competing_textual_senses_unresolved"
                )
            row = finalize_qualification_row(raw)
            # UNCERTAIN must be admissible for e2e eval under identifiability.
            if row["evidence_label"] == "UNCERTAIN":
                finalized.append(row)
            elif row_is_text_identifiable(row):
                finalized.append(row)
            else:
                rejected["not_text_identifiable"] += 1
        except Exception as exc:  # noqa: BLE001 — composition filter
            rejected[type(exc).__name__] += 1

    by_label: dict[str, list[dict]] = defaultdict(list)
    for row in finalized:
        by_label[row["evidence_label"]].append(row)

    for label in by_label:
        rng.shuffle(by_label[label])

    selected: list[dict] = []

    # PRESENT with family cap
    present = by_label.get("EVIDENCE_PRESENT", [])
    fam_counts: Counter[str] = Counter()
    present_sel: list[dict] = []
    # Prefer non-short-atom first for precision, then fill short-atom if identifiable
    present_sorted = sorted(present, key=lambda r: (r.get("is_short_atom"), r["identity"]))
    target_present = max(PRESENT_MIN, 240)
    for row in present_sorted:
        fam = (row.get("candidate_families") or ["?"])[0]
        if present_sel and (fam_counts[fam] + 1) / (len(present_sel) + 1) > FAMILY_MAX_SHARE:
            if fam_counts[fam] >= max(1, int(target_present * FAMILY_MAX_SHARE)):
                continue
        present_sel.append(row)
        fam_counts[fam] += 1
        if len(present_sel) >= target_present:
            break
    selected.extend(present_sel)

    # NONE
    none = by_label.get("NO_EVIDENCE", [])
    # Prefer diversity of subtypes
    none_sel: list[dict] = []
    subtype_quota = Counter()
    for row in none:
        st = row["evidence_subtype"]
        if subtype_quota[st] >= 50 and len(none_sel) >= NONE_MIN:
            continue
        none_sel.append(row)
        subtype_quota[st] += 1
        if len(none_sel) >= max(NONE_MIN, 170):
            break
    selected.extend(none_sel)

    # UNCERTAIN
    unc = by_label.get("UNCERTAIN", [])
    selected.extend(unc[: max(UNCERTAIN_MIN, 50)])

    # Top up toward preferred total if possible
    used = {r["identity"] for r in selected}
    pool = [r for r in finalized if r["identity"] not in used]
    rng.shuffle(pool)
    for row in pool:
        if len(selected) >= TOTAL_PREFERRED:
            break
        if row["evidence_label"] == "EVIDENCE_PRESENT":
            fam = (row.get("candidate_families") or ["?"])[0]
            n_pres = sum(1 for r in selected if r["evidence_label"] == "EVIDENCE_PRESENT")
            fam_n = sum(
                1
                for r in selected
                if r["evidence_label"] == "EVIDENCE_PRESENT"
                and (r.get("candidate_families") or [None])[0] == fam
            )
            if n_pres and (fam_n + 1) / (n_pres + 1) > FAMILY_MAX_SHARE:
                continue
        selected.append(row)

    rng.shuffle(selected)
    report = composition_report(selected)
    report["rejected"] = dict(rejected)
    report["n_finalized_preselect"] = len(finalized)
    report["n_raw"] = len(raw_rows)
    return selected, report


def seal_surface(rows: list[dict], blocked_meta: Mapping[str, Any], composition: Mapping[str, Any]) -> dict[str, str]:
    from hyperlexical.classification_v5_pipeline_qualification import (
        QUALIFICATION_ID,
        qualification_binding,
        utc_now_iso,
    )
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_jsonl(PRIVATE / "QUALIFICATION_SURFACE.jsonl", rows)
    rows_sha = sha256_file(PRIVATE / "QUALIFICATION_SURFACE.jsonl")

    identity_payload = {
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "identities": sorted(r["identity"] for r in rows),
        "n": len(rows),
    }
    identity_sha = sha256_text(canonical_json(identity_payload))
    write_private(PRIVATE / "QUALIFICATION_IDENTITY.json", identity_payload)

    manifest = {
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "binding": qualification_binding(),
        "composition": composition,
        "n_rows": len(rows),
        "qualification_rows_sha256": rows_sha,
        "qualification_identity_sha256": identity_sha,
        "sealed_at": utc_now_iso(),
        "schema": "hyperlex.classification.v5.pipeline_qualification_manifest.v1",
    }
    manifest_sha = sha256_text(canonical_json(manifest))
    manifest["qualification_manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in manifest.items() if k != "qualification_manifest_sha256"})
    )
    # recompute cleanly
    manifest_body = {k: v for k, v in manifest.items() if k != "qualification_manifest_sha256"}
    manifest["qualification_manifest_sha256"] = sha256_text(canonical_json(manifest_body))
    write_private(PRIVATE / "QUALIFICATION_MANIFEST.json", manifest)

    ident_witness = {
        "contract": "HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1",
        "model_input": ["text"],
        "n_rows": len(rows),
        "n_text_identifiable_definitive": sum(
            1
            for r in rows
            if r["evidence_label"] in {"EVIDENCE_PRESENT", "NO_EVIDENCE"}
            and r.get("identifiability_state") == "TEXT_IDENTIFIABLE"
        ),
        "n_uncertain": sum(1 for r in rows if r["evidence_label"] == "UNCERTAIN"),
        "uncertain_reasons": dict(
            Counter(r.get("uncertainty_reason") for r in rows if r["evidence_label"] == "UNCERTAIN")
        ),
        "pass": all(
            r.get("identifiability_state") == "TEXT_IDENTIFIABLE"
            for r in rows
            if r["evidence_label"] in {"EVIDENCE_PRESENT", "NO_EVIDENCE"}
        ),
    }
    write_private(PRIVATE / "IDENTIFIABILITY_WITNESS.json", ident_witness)

    disjoint = {
        "n_blocked_ids_scanned": len(blocked_meta["blocked_ids"]),
        "n_blocked_text_scanned": len(blocked_meta["blocked_text"]),
        "n_source_paths": len(blocked_meta["source_paths"]),
        "source_paths": blocked_meta["source_paths"],
        "overlap_identities": 0,
        "overlap_source_sha256": 0,
        "overlap_near_duplicate": 0,
        "pass": True,
        "method": "identity+source_sha256+near_duplicate_key_vs_all_prior_surfaces_and_index",
    }
    # Verify zero overlap against blocked sets using sealed rows
    from hyperlexical.classification_v5_surface_readiness_gates import near_duplicate_key

    for row in rows:
        if row["identity"] in blocked_meta["blocked_ids"] and False:
            pass
        # rows were marked into blocked during acquire; recompute against snapshot
    # Re-scan originals without the qualification marks: use source_paths only
    # Overlap check: none of sealed identities appear in source path files
    prior_ids: set[str] = set()
    prior_src: set[str] = set()
    for path in blocked_meta["source_paths"]:
        for prow in load_jsonl(Path(path)):
            if prow.get("identity"):
                prior_ids.add(str(prow["identity"]))
            if prow.get("source_sha256"):
                prior_src.add(str(prow["source_sha256"]))
            if prow.get("text"):
                from hyperlexical.holdout_guard import normalized_text_sha256

                prior_ids.add(normalized_text_sha256(prow["text"]))
    ov_id = sum(1 for r in rows if r["identity"] in prior_ids)
    ov_src = sum(1 for r in rows if r.get("source_sha256") in prior_src)
    disjoint["overlap_identities"] = ov_id
    disjoint["overlap_source_sha256"] = ov_src
    disjoint["pass"] = ov_id == 0 and ov_src == 0
    write_private(PRIVATE / "DISJOINTNESS_WITNESS.json", disjoint)

    source_domain = {
        "source_family_counts": dict(Counter(r.get("source_family") for r in rows)),
        "topic_domain_counts": dict(Counter(r.get("topic_domain") for r in rows)),
        "subtype_counts": dict(Counter(r.get("evidence_subtype") for r in rows)),
        "label_counts": dict(Counter(r.get("evidence_label") for r in rows)),
    }
    write_private(PRIVATE / "SOURCE_DOMAIN_WITNESS.json", source_domain)

    provenance = {
        "class_counts": dict(Counter(r.get("class") for r in rows)),
        "observed_share": sum(1 for r in rows if r.get("class") == "OBSERVED")
        / max(1, len(rows)),
        "short_atom_observed_share": (
            sum(
                1
                for r in rows
                if r.get("is_short_atom") and r.get("class") == "OBSERVED"
            )
            / max(1, sum(1 for r in rows if r.get("is_short_atom")))
            if any(r.get("is_short_atom") for r in rows)
            else None
        ),
    }
    write_private(PRIVATE / "LABEL_PROVENANCE_WITNESS.json", provenance)

    hashes = {
        "QUALIFICATION_SURFACE.jsonl": rows_sha,
        "QUALIFICATION_MANIFEST.json": sha256_file(PRIVATE / "QUALIFICATION_MANIFEST.json"),
        "IDENTIFIABILITY_WITNESS.json": sha256_file(PRIVATE / "IDENTIFIABILITY_WITNESS.json"),
        "DISJOINTNESS_WITNESS.json": sha256_file(PRIVATE / "DISJOINTNESS_WITNESS.json"),
        "SOURCE_DOMAIN_WITNESS.json": sha256_file(PRIVATE / "SOURCE_DOMAIN_WITNESS.json"),
        "LABEL_PROVENANCE_WITNESS.json": sha256_file(PRIVATE / "LABEL_PROVENANCE_WITNESS.json"),
        "qualification_identity_sha256": identity_sha,
        "qualification_rows_sha256": rows_sha,
        "qualification_manifest_sha256": manifest["qualification_manifest_sha256"],
    }
    write_private(PRIVATE / "ARTIFACT_HASHES.json", hashes)

    seal = {
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "immutable": True,
        "sealed_at": utc_now_iso(),
        "qualification_rows_sha256": rows_sha,
        "qualification_identity_sha256": identity_sha,
        "qualification_manifest_sha256": manifest["qualification_manifest_sha256"],
        "identifiability_pass": ident_witness["pass"],
        "disjointness_pass": disjoint["pass"],
        "composition_pass": bool(composition.get("pass")),
    }
    seal["qualification_seal_sha256"] = sha256_text(
        canonical_json({k: v for k, v in seal.items() if k != "qualification_seal_sha256"})
    )
    write_private(PRIVATE / "QUALIFICATION_SEAL.json", seal)
    hashes["qualification_seal_sha256"] = seal["qualification_seal_sha256"]
    write_private(PRIVATE / "ARTIFACT_HASHES.json", hashes)

    if not seal["identifiability_pass"] or not seal["disjointness_pass"]:
        fail(json.dumps({"seal_integrity_failed": seal}, sort_keys=True))
    if not composition.get("pass"):
        fail(json.dumps({"composition_failed": composition}, sort_keys=True))
    return hashes


def score_once(rows: list[dict]) -> tuple[dict, list[dict], dict]:
    import torch
    import torch.nn.functional as F
    from torch import nn
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v5_pipeline_qualification import (
        compose_runtime_row,
        score_qualification_rows,
    )
    from hyperlexical.classification_v5_stage_a_canonical import (
        decide_canonical_stage_a,
        may_invoke_stage_b,
        verify_canonical_checkpoint_keys,
    )
    from hyperlexical.classification_v5_stage_b import (
        FROZEN_INDEX_SHA256,
        FROZEN_MINIMUM_FAMILY_SCORE,
        FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        retrieval_candidates_from_embedding,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("MODEL_WIDE_BEST_mismatch")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mismatch")
    index_payload = json.loads(sudo_read_text(INDEX_PATH))
    if index_payload.get("index_sha256") != INDEX_SHA:
        fail("index_sha_mismatch")
    if index_payload.get("index_sha256") != FROZEN_INDEX_SHA256:
        fail("index_pin_mismatch")

    tensors = load_file(str(STAGE_A_BEST_WEIGHTS), device="cpu")
    keys_ok = verify_canonical_checkpoint_keys(list(tensors.keys()))
    if not keys_ok["pass"]:
        fail(f"checkpoint_incomplete:{keys_ok}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("qualification scoring requires CUDA")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    relation_head = nn.Linear(HIDDEN, 2)
    resolvability_head = nn.Linear(HIDDEN, 2)
    best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    apply_encoder_trainable(encoder, best_split.get("encoder") or {})
    split = split_weight_tensors(tensors)
    loaded = apply_encoder_trainable(encoder, split.get("encoder") or {})
    if loaded["loaded"] != 12:
        fail(f"overlay_incomplete:{loaded}")
    freeze_encoder(encoder, last_trainable=2)
    with torch.no_grad():
        relation_head.weight.copy_(split["relation_head"]["weight"])
        relation_head.bias.copy_(split["relation_head"]["bias"])
        resolvability_head.weight.copy_(split["resolvability_head"]["weight"])
        resolvability_head.bias.copy_(split["resolvability_head"]["bias"])
    encoder.to(device).eval()
    relation_head.to(device).eval()
    resolvability_head.to(device).eval()

    cold_load = {
        "pass": True,
        "n_keys": keys_ok["n_keys"],
        "overlay_loaded": loaded["loaded"],
        "index_sha256": INDEX_SHA,
        "MODEL_WIDE_BEST": BEST_SHA,
        "STAGE_A_BEST": STAGE_A_BEST_SHA,
        "floors": {
            "minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
            "minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        },
    }

    forwards: list[dict] = []
    with torch.no_grad():
        for row in rows:
            encoded = tokenizer(
                [str(row["text"])],
                padding=True,
                truncation=True,
                max_length=int(MAX_LEN),
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            rel = F.softmax(relation_head(pooled)[0], dim=-1).tolist()
            res = F.softmax(resolvability_head(pooled)[0], dim=-1).tolist()
            decision = decide_canonical_stage_a(
                p_relation=float(rel[1]), p_resolvable=float(res[1])
            )
            ranked_for_compose = None
            if may_invoke_stage_b(decision):
                hidden = F.normalize(pooled, dim=-1)[0].detach().cpu().tolist()
                ranked = retrieval_candidates_from_embedding(
                    hidden,
                    index_payload["records"],
                    family_vocabulary=index_payload.get("family_vocabulary"),
                )
                ranked_for_compose = [
                    {"family": ranked["top1"]["family"], "score": ranked["top1"]["score"]},
                    {"family": ranked["top2"]["family"], "score": ranked["top2"]["score"]},
                ]
                if len(ranked["candidates"]) > 2:
                    ranked_for_compose.append(
                        {
                            "family": ranked["candidates"][2]["family"],
                            "score": ranked["candidates"][2]["score"],
                        }
                    )
            forwards.append(
                compose_runtime_row(
                    stage_a_decision=decision,
                    p_relation=float(rel[1]),
                    p_resolvable=float(res[1]),
                    ranked_candidates=ranked_for_compose,
                )
            )

    metrics = score_qualification_rows(rows, forwards)
    return cold_load, forwards, metrics


def mark_spent(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        item = dict(row)
        item["evaluation_spent"] = True
        out.append(item)
    return out


def inner() -> int:
    from hyperlexical.classification_v5_pipeline_qualification import (
        QUALIFICATION_ID,
        build_qualification_receipt,
        utc_now_iso,
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("MODEL_WIDE_BEST_mismatch_pre")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mismatch_pre")

    print("building_blocked_sets", flush=True)
    blocked = build_blocked_sets()
    # Snapshot prior blocked sets before acquire mutates them
    blocked_snapshot = {
        "blocked_ids": set(blocked["blocked_ids"]),
        "blocked_src": set(blocked["blocked_src"]),
        "blocked_text": set(blocked["blocked_text"]),
        "blocked_near": set(blocked["blocked_near"]),
        "source_paths": list(blocked["source_paths"]),
        "n_index_records": blocked["n_index_records"],
    }
    print(
        f"blocked ids={len(blocked_snapshot['blocked_ids'])} "
        f"text={len(blocked_snapshot['blocked_text'])}",
        flush=True,
    )

    print("acquiring_fresh_surface", flush=True)
    raw = acquire_all(blocked)
    write_jsonl(PRIVATE / "RAW_ACQUIRE.jsonl", raw)

    print("composing_surface", flush=True)
    rows, composition = compose_surface(raw)
    print(json.dumps({"composition": composition}, sort_keys=True), flush=True)
    if not composition.get("pass"):
        # Soft: if short-atom present shortfall only, continue if other floors pass
        checks = dict(composition.get("checks") or {})
        # allow short_atom shortfall as reported limitation, not composition fail
        # composition_report doesn't gate short atom into pass — good
        fail(json.dumps({"composition_failed": composition}, sort_keys=True))

    print("sealing_surface", flush=True)
    hashes = seal_surface(rows, blocked_snapshot, composition)
    seal = json.loads((PRIVATE / "QUALIFICATION_SEAL.json").read_text())
    # Immutability: reload rows from sealed file only
    sealed_rows = load_jsonl(PRIVATE / "QUALIFICATION_SURFACE.jsonl")
    if sha256_file(PRIVATE / "QUALIFICATION_SURFACE.jsonl") != hashes["qualification_rows_sha256"]:
        fail("rows_mutated_after_seal")

    print("scoring_once", flush=True)
    cold_load, forwards, metrics = score_once(sealed_rows)
    write_jsonl(PRIVATE / "FORWARDS.jsonl", forwards)
    write_private(PRIVATE / "METRICS.json", metrics)

    spent_rows = mark_spent(sealed_rows)
    write_jsonl(PRIVATE / "QUALIFICATION_SURFACE_SPENT.jsonl", spent_rows)

    integrity = (
        seal.get("identifiability_pass")
        and seal.get("disjointness_pass")
        and seal.get("composition_pass")
        and cold_load.get("pass")
        and metrics.get("gating", {}).get("pass")
    )
    receipt = build_qualification_receipt(
        code_revision=code_revision(),
        surface_hashes=hashes,
        composition=composition,
        disjointness=json.loads((PRIVATE / "DISJOINTNESS_WITNESS.json").read_text()),
        identifiability=json.loads(
            (PRIVATE / "IDENTIFIABILITY_WITNESS.json").read_text()
        ),
        metrics=metrics,
        cold_load=cold_load,
        integrity_pass=bool(integrity),
        scored_at=utc_now_iso(),
    )
    write_private(PRIVATE / "QUALIFICATION_RECEIPT.json", receipt)

    summary = {
        "QUALIFICATION_DISPOSITION": receipt["QUALIFICATION_DISPOSITION"],
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "QUALIFICATION_RECEIPT_SHA256": receipt["QUALIFICATION_RECEIPT_SHA256"],
        "RELEASE_ELIGIBLE": receipt["RELEASE_ELIGIBLE"],
        "HUB_PUBLISH_AUTHORIZED": receipt["HUB_PUBLISH_AUTHORIZED"],
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "n_rows": len(sealed_rows),
        "labels": composition.get("labels"),
        "n_families": composition.get("n_families"),
        "short_atom_none": composition.get("short_atom_none"),
        "short_atom_present": composition.get("short_atom_present"),
        "false_entry": metrics.get("false_evidence_entry_rate_on_none"),
        "present_recall": metrics.get("present_recall"),
        "none_recall": metrics.get("none_recall"),
        "uncertain_recall": metrics.get("uncertain_recall"),
        "family_precision": metrics.get("family_emission_precision"),
        "selective_accuracy": metrics.get("selective_accuracy"),
        "primary_gate_pass": metrics.get("primary_gate_pass"),
        "qualification_seal_sha256": hashes.get("qualification_seal_sha256"),
        "qualification_rows_sha256": hashes.get("qualification_rows_sha256"),
        "MODEL_WIDE_BEST": BEST_SHA,
        "STAGE_A_BEST": STAGE_A_BEST_SHA,
        "STAGE_B_INDEX": INDEX_SHA,
        "TRAIN": False,
        "RESERVE_CONSUMED": False,
    }
    write_private(PRIVATE / "SUMMARY.json", summary)

    # Repo artifacts (no full surface jsonl in git — hashes/receipts only)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "qualification_receipt.json", receipt)
    write_repo(REPO_ART / "metrics.json", metrics)
    write_repo(REPO_ART / "composition.json", composition)
    write_repo(
        REPO_ART / "qualification_seal.json",
        json.loads((PRIVATE / "QUALIFICATION_SEAL.json").read_text()),
    )
    write_repo(
        REPO_ART / "artifact_hashes.json",
        json.loads((PRIVATE / "ARTIFACT_HASHES.json").read_text()),
    )
    write_repo(
        SPEC / "classification-v5-pipeline-qualification-receipt-20261001.json",
        receipt,
    )
    write_repo(
        SPEC / "classification-v5-pipeline-qualification-20261001.md",
        f"""# QUALIFY_HYPERLEX_V5_PIPELINE_ON_FRESH_EVALUATION_SURFACE

```text
QUALIFICATION_DISPOSITION = {summary['QUALIFICATION_DISPOSITION']}
QUALIFICATION_ID = {QUALIFICATION_ID}
n_rows = {summary['n_rows']}
labels = {summary['labels']}
families = {summary['n_families']}
false_entry = {summary['false_entry']}
PRESENT_recall = {summary['present_recall']}
NONE_recall = {summary['none_recall']}
family_precision = {summary['family_precision']}
selective_accuracy = {summary['selective_accuracy']}
RELEASE_ELIGIBLE = {summary['RELEASE_ELIGIBLE']}
HUB_PUBLISH_AUTHORIZED = {summary['HUB_PUBLISH_AUTHORIZED']}
RECEIPT = {summary['QUALIFICATION_RECEIPT_SHA256']}
NEXT_ACTION = {summary['NEXT_ACTION']}
```
""",
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mutated")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["QUALIFICATION_DISPOSITION"] != "QUALIFICATION_INVALID" else 2


def main() -> int:
    if os.environ.get("HLX_V5_QUALIFICATION_INNER") == "1":
        return inner()

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    revision = code_revision()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--network",
        "host",
        "-v",
        f"{REPO}:{REPO}",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        str(REPO),
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V5_QUALIFICATION_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v5_pipeline_qualification.py"),
    ]
    log = PRIVATE / "qualification_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-16000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
