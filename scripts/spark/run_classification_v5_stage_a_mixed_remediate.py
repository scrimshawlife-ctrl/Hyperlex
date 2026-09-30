"""REMEDIATE_V5_STAGE_A_MIXED_FAILURE_V1 — Spark runner.

Builds V1R8 replacement surface from READY V1R7 parent under frozen gates.
Does not train, score reserves, or move BEST.
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
PRIOR = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-negative-evidence-surface-v1r7-20260930"
)
PRIOR_SHA = "a81ca68ad3310981c60d2500a83a0989adeb967cbee6ad6dff003ed2c705efa9"
DEST = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-negative-evidence-surface-v1r8-20260930"
)
HUB = Path(
    "/home/morpheus/hlx-private/classification-v2-train-forward-20260930/civilian.v0.7.hub.jsonl"
)
HUB_SHA = "0d8f4532f84ed9fade3fd4e69af0d1e0717fb1098d40754e95c0090d8282bfe1"
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")
SPENT_V2 = Path(
    "/home/morpheus/hlx-private/classification-v2-train-ready-20260929/reserve-eval-rows.jsonl"
)
SPENT_V3 = Path(
    "/home/morpheus/hlx-private/classification-v3-reserve-20260930/reserve-rows.jsonl"
)
SPENT_V4 = Path(
    "/home/morpheus/hlx-private/classification-v4-reserve-20260930/reserve-rows.jsonl"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"

WIKT_API = "https://en.wiktionary.org/w/api.php"
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = (
    "HyperlexClassificationV5MixedRemediate/1.0 "
    "(stage-a mixed failure remediate; mediawiki provenance)"
)

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

_SENSE = re.compile(r"\{\{\s*(lb|lbl|tlb)\s*\|\s*en\s*\|([^{}]*)\}\}", re.I)
_LINK = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
_MARKUP = re.compile(r"''+")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_HTML = re.compile(r"<[^>]+>")
_REF = re.compile(r"<ref\b[^>]*>.*?</ref>", re.I | re.S)

# Priority domains from sealed ordinary false-PRESENT concentration + diagnosis.
ORDINARY_LABELS = (
    "anatomy",
    "chemistry",
    "astronomy",
    "botany",
    "ornithology",
    "meteorology",
    "geology",
    "mathematics",
    "zoology",
    "physics",
    "pharmacology",
    "mineralogy",
    "mycology",
    "entomology",
    "archaeology",
    "paleontology",
    "linguistics",
    "architecture",
)

WIKI_CATEGORIES = {
    "anatomy": "Category:Anatomy",
    "chemistry": "Category:Chemistry",
    "astronomy": "Category:Astronomy",
    "botany": "Category:Botany",
    "mathematics": "Category:Mathematics",
    "physics": "Category:Physics",
    "zoology": "Category:Zoology",
    "geology": "Category:Geology",
    "meteorology": "Category:Meteorology",
    "ornithology": "Category:Ornithology",
    "pharmacology": "Category:Pharmacology",
    "mineralogy": "Category:Mineralogy",
    "mycology": "Category:Mycology",
    "entomology": "Category:Entomology",
    "archaeology": "Category:Archaeology",
    "paleontology": "Category:Paleontology",
}

# PRESENT families with concentrated false-NONE in sealed diagnosis.
FAMILY_LABELS = {
    "workplace-career": ("business", "management"),
    "conflict-aggression": ("military", "military slang"),
    "politics-civic": ("politics", "government"),
    "regional-cultural": ("australian", "scottish", "irish"),
    "social-evaluation": ("derogatory", "endearing"),
    "internet-slang": ("internet slang", "reddit slang"),
    "crypto-degen": ("cryptocurrency",),
    "technology-ai": ("programming", "software", "computer science"),
    "sports-competition": ("sports", "ball games"),
    "betting-sharp": ("betting", "gambling"),
    "memetic": ("meme",),
    "gaming-meta": ("gaming", "video game"),
    "fashion-aesthetic": ("fashion", "clothing"),
    "identity-affiliation": ("demonym",),
    "music-entertainment": ("music", "film"),
    "relationship-dating": ("dating",),
    "spiritual-mystic": ("occult", "astrology"),
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
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


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


def search_titles(label: str, *, scan_cap: int = 50) -> list[str]:
    titles: list[str] = []
    for template in ("lb", "lbl", "tlb"):
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


def extract_wiktionary_rows(
    *,
    label: str,
    subtype: str,
    lineage: str,
    topic_domain: str,
    quota: int,
    blocked: set[str],
    kept: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    from hyperlexical.holdout_guard import normalized_text_sha256

    rows: list[dict[str, Any]] = []
    titles = search_titles(label)
    cursor = 0
    while cursor < len(titles) and len(rows) < quota:
        chunk = titles[cursor : cursor + 10]
        cursor += 10
        pages = fetch_revisions(WIKT_API, chunk)
        for title in chunk:
            if len(rows) >= quota:
                break
            page = pages.get(title)
            if page is None:
                continue
            section = english_section(page["content"])
            if not section or page["content"].lstrip().lower().startswith("#redirect"):
                continue
            for line in section.splitlines():
                if not line.startswith("# ") or line.startswith(("#:", "##")):
                    continue
                args = [a.casefold() for a in sense_label_arguments(line)]
                if label.casefold() not in args and label.casefold().replace(" ", "-") not in args:
                    if not any(label.casefold() in a for a in args):
                        continue
                prose = definition_prose(line)
                if not prose or len(prose.split()) < 4:
                    continue
                identity = normalized_text_sha256(prose)
                if identity in blocked or identity in kept:
                    continue
                row = {
                    "text": prose,
                    "lineage": lineage,
                    "class": "OBSERVED",
                    "evidence_subtype": subtype,
                    "topic_domain": topic_domain,
                    "revision_id": page["revision_id"],
                    "source_url": (
                        "https://en.wiktionary.org/wiki/"
                        + urllib.parse.quote(title.replace(" ", "_"))
                    ),
                    "rights": "CC-BY-SA",
                    "notes": f"v5_mixed_wiktionary:{topic_domain}",
                    "title": title,
                }
                kept[identity] = row
                rows.append(row)
                break
    return rows


def wikipedia_lead_prose(wikitext: str) -> str:
    text = wikitext
    if text.lstrip().lower().startswith("#redirect"):
        return ""
    # Cut at first section heading.
    text = re.split(r"\n==", text, maxsplit=1)[0]
    text = _REF.sub(" ", text)
    text = _HTML.sub(" ", text)
    text = _TEMPLATE.sub(" ", text)
    text = _LINK.sub(r"\2", text)
    text = _MARKUP.sub("", text)
    text = text.replace("{{", " ").replace("}}", " ")
    text = " ".join(text.split())
    # Keep a single sentence-ish window of ordinary prose.
    if len(text.split()) < 12:
        return ""
    words = text.split()
    if len(words) > 60:
        text = " ".join(words[:60])
    return text.strip()


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


def extract_wikipedia_ordinary(
    *,
    domain: str,
    category: str,
    quota: int,
    blocked: set[str],
    kept: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    from hyperlexical.holdout_guard import normalized_text_sha256

    rows: list[dict[str, Any]] = []
    titles = category_titles(category, limit=max(quota * 2, 30))
    cursor = 0
    while cursor < len(titles) and len(rows) < quota:
        chunk = titles[cursor : cursor + 10]
        cursor += 10
        pages = fetch_revisions(WIKI_API, chunk)
        for title in chunk:
            if len(rows) >= quota:
                break
            page = pages.get(title)
            if page is None:
                continue
            prose = wikipedia_lead_prose(page["content"])
            if not prose:
                continue
            identity = normalized_text_sha256(prose)
            if identity in blocked or identity in kept:
                continue
            row = {
                "text": prose,
                "lineage": "none",
                "class": "OBSERVED",
                "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                "topic_domain": domain,
                "revision_id": page["revision_id"],
                "source_url": (
                    "https://en.wikipedia.org/wiki/"
                    + urllib.parse.quote(title.replace(" ", "_"))
                ),
                "rights": "CC-BY-SA",
                "notes": f"v5_mixed_wikipedia:{domain}",
                "title": title,
            }
            kept[identity] = row
            rows.append(row)
    return rows


def acquire_observed(blocked: set[str]) -> list[dict[str, Any]]:
    kept: dict[str, dict[str, Any]] = {}
    # Priority ordinary domains get higher Wiktionary quotas.
    priority = {"anatomy", "chemistry", "astronomy", "zoology", "physics", "mathematics"}
    for label in ORDINARY_LABELS:
        quota = 55 if label in priority else 35
        got = extract_wiktionary_rows(
            label=label,
            subtype="ORDINARY_DOMAIN_NONE",
            lineage="none",
            topic_domain=label,
            quota=quota,
            blocked=blocked,
            kept=kept,
        )
        print(f"wikt ordinary {label}: {len(got)}", flush=True)

    # Wikipedia ordinary — diversify away from v5_src_wik_* dominance.
    for domain, category in WIKI_CATEGORIES.items():
        quota = 30 if domain in priority else 18
        got = extract_wikipedia_ordinary(
            domain=domain,
            category=category,
            quota=quota,
            blocked=blocked,
            kept=kept,
        )
        print(f"wiki ordinary {domain}: {len(got)}", flush=True)

    # Alternate subtype OBSERVED fills for hardness/pairing diversity.
    for label in ("anatomy", "chemistry", "astronomy", "geology", "mathematics"):
        got = extract_wiktionary_rows(
            label=label,
            subtype="HARD_NONE",
            lineage="brainrot-aura",
            topic_domain=label,
            quota=20,
            blocked=blocked,
            kept=kept,
        )
        print(f"wikt hard {label}: {len(got)}", flush=True)
    for label in ("meteorology", "zoology", "physics", "astronomy", "pharmacology"):
        got = extract_wiktionary_rows(
            label=label,
            subtype="NEAR_DOMAIN_NONE",
            lineage="none",
            topic_domain=label,
            quota=20,
            blocked=blocked,
            kept=kept,
        )
        print(f"wikt near {label}: {len(got)}", flush=True)

    # PRESENT OBSERVED for diagnosis-underrepresented families.
    for family, labels in FAMILY_LABELS.items():
        for label in labels[:2]:
            got = extract_wiktionary_rows(
                label=label,
                subtype="POSITIVE_EVIDENCE",
                lineage=family,
                topic_domain=family,
                quota=18,
                blocked=blocked,
                kept=kept,
            )
            print(f"wikt present {family}/{label}: {len(got)}", flush=True)

    return sorted(kept.values(), key=lambda item: item["text"])


def blocked_ids() -> set[str]:
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        load_blocked_ids,
    )

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    return load_blocked_ids(
        ledger=ledger,
        spent_row_files=(load_jsonl(SPENT_V2), load_jsonl(SPENT_V3), load_jsonl(SPENT_V4)),
    )


def main() -> int:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v5_stage_a_mixed_remediate import (
        REMEDIATE_RULE,
        SURFACE_RULE_V1R8,
        remediate_contract,
        remediate_mixed_surface,
    )
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        canonical_json,
        sha256_text,
    )
    from hyperlexical.classification_v5_surface_readiness_gates import GATE_RULE

    if sha256_file(PRIOR / "EVIDENCE_SURFACE.jsonl") != PRIOR_SHA:
        fail("prior V1R7 surface digest mismatch")
    if sha256_file(HUB) != HUB_SHA:
        fail("hub digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if (DEST / "EVIDENCE_SURFACE.jsonl").exists():
        fail(f"destination already frozen:{DEST}")

    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST, 0o700)
    write_private(DEST / "CONTRACT.json", remediate_contract())

    blocked = blocked_ids()
    # Also block exact validation texts from parent so we do not re-admit them
    # as "new" train rows via acquire near-copies of the same identities.
    prior_rows = load_jsonl(PRIOR / "EVIDENCE_SURFACE.jsonl")
    prior_ids = {r["identity"] for r in prior_rows}
    blocked |= prior_ids  # acquires must be fresh vs parent body
    # But remediator keeps prior rows explicitly — only acquire path uses blocked∪prior.
    acquire_blocked = set(blocked)

    write_private(
        DEST / "ISOLATION.json",
        {
            "blocked_n": len(blocked),
            "parent_n": len(prior_rows),
            "rule": REMEDIATE_RULE,
        },
    )

    acquire_path = DEST / "OBSERVED_ACQUIRE.jsonl"
    if acquire_path.exists():
        acquired = load_jsonl(acquire_path)
    else:
        acquired = acquire_observed(acquire_blocked)
        body = "\n".join(canonical_json(r) for r in acquired) + ("\n" if acquired else "")
        write_private(acquire_path, body)
    print(f"acquired_observed={len(acquired)}", flush=True)
    print(
        "acquire_subtype",
        dict(Counter(r.get("evidence_subtype") for r in acquired)),
        flush=True,
    )
    print(
        "acquire_domain_top",
        Counter(r.get("topic_domain") for r in acquired).most_common(20),
        flush=True,
    )

    hub_rows = load_jsonl(HUB)
    # Remediator may keep prior identities; only spent/ledger stay hard-blocked.
    spent_only = blocked_ids()
    built = remediate_mixed_surface(
        prior_rows=prior_rows,
        hub_rows=hub_rows,
        observed_acquire_rows=acquired,
        blocked_ids=spent_only,
        ontology=ACTIVE_FAMILY_VOCABULARY,
        embedding_report=None,
    )

    write_private(DEST / "EVIDENCE_SURFACE.jsonl", built["dataset_body"])
    if sha256_file(DEST / "EVIDENCE_SURFACE.jsonl") != built["dataset_sha256"]:
        fail("dataset digest mismatch after write")
    write_private(DEST / "SPLIT_MANIFEST.json", built["split_manifest"])
    write_private(DEST / "COMPONENT_SPLIT_WITNESS.json", built["component_witness"])
    write_private(DEST / "DEDUPLICATION_WITNESS.json", built["dedupe_witness"])
    write_private(DEST / "PAIR_RECORDS.json", built["pair_records"])
    write_private(DEST / "REMEDIATION_STATS.json", built["remediation_stats"])
    write_private(DEST / "SOURCE_DOMAIN_BALANCE.json", built["source_balance"])
    write_private(DEST / "SPLIT_SUPPORT_FLOORS.json", built["split_support_floors"])
    write_private(DEST / "READINESS.json", built["receipt"])
    write_private(DEST / "STAGE_A_TRAIN_CONTRACT.json", built["stage_a_train_contract"])

    summary = {
        "BEST": "UNCHANGED",
        "dataset_sha256": built["dataset_sha256"],
        "gate_rule": GATE_RULE,
        "n": built["receipt"]["n"],
        "parent_diagnosis": "MIXED_STAGE_A_FAILURE",
        "parent_surface_dataset_sha256": PRIOR_SHA,
        "readiness_state": built["readiness"]["state"],
        "receipt_sha256": built["receipt"]["receipt_sha256"],
        "remediate_rule": REMEDIATE_RULE,
        "remediation_stats": built["remediation_stats"],
        "split_support_floors": built["split_support_floors"],
        "surface_rule": SURFACE_RULE_V1R8,
        "train": False,
        "missing_evidence_gates": sorted(built["readiness"].get("missing_evidence") or {}),
    }
    write_private(DEST / "SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
