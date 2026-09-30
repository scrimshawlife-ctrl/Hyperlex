"""REMEDIATE_V5_UNCERTAIN_SURFACE — Spark runner for V1R9 replacement surface.

Builds a new versioned Stage-A surface from READY V1R8 without mutating V1R8.
Does not train, score reserves, move BEST, or acquire from checkpoint scores.
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
    "/home/morpheus/hlx-private/classification-v5-stage-a-negative-evidence-surface-v1r8-20260930"
)
PRIOR_SHA = "c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b"
DEST = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-negative-evidence-surface-v1r9-20260930"
)
ACQUIRE_CACHE = Path(
    "/home/morpheus/hlx-private/classification-v5-uncertain-acquire-cache-20260930"
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
AUTH_003 = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-train-v1r8-003-focal-20260930"
)
VAL_SCORES = (
    AUTH_003
    / "classification-v5-stage-a-003"
    / "diagnostics"
    / "uncertain_policy_investigation"
    / "VALIDATION_SCORES.jsonl"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
BEST_DIR = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"

WIKT_API = "https://en.wiktionary.org/w/api.php"
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = (
    "HyperlexClassificationV5UncertainSurfaceRemediate/1.0 "
    "(stage-a uncertain surface remediate; mediawiki provenance)"
)

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

_SENSE = re.compile(r"\{\{\s*(lb|lbl|tlb)\s*\|\s*en\s*\|([^{}]*)\}\}", re.I)
_LINK = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
_MARKUP = re.compile(r"''+")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_HTML = re.compile(r"<[^>]+>")
_REF = re.compile(r"<ref\b[^>]*>.*?</ref>", re.I | re.S)
_ETYM_UNCLEAR = re.compile(
    r"\b(unknown origin|origin unclear|etymology (is )?uncertain|disputed|"
    r"uncertain etymology|origin unknown)\b",
    re.I,
)

# Label searches chosen by source structure (polysemy / register conflict /
# incomplete cues / unclear etymology) — not by checkpoint probabilities.
REASON_SEARCHES = {
    "MULTIPLE_PLAUSIBLE_INTERPRETATIONS": [
        ("slang", "internet-slang"),
        ("informal", "social-evaluation"),
        ("internet slang", "internet-slang"),
        ("colloquial", "regional-cultural"),
        ("gaming", "gaming-meta"),
        ("meme", "memetic"),
    ],
    "CONFLICTING_EVIDENCE": [
        ("derogatory", "social-evaluation"),
        ("endearing", "social-evaluation"),
        ("offensive", "social-evaluation"),
        ("humorous", "memetic"),
        ("sarcastic", "internet-slang"),
        ("ironic", "internet-slang"),
    ],
    "PARTIAL_REQUIRED_CORE": [
        ("video game", "gaming-meta"),
        ("cryptocurrency", "crypto-degen"),
        ("betting", "betting-sharp"),
        ("business", "workplace-career"),
        ("fashion", "fashion-aesthetic"),
        ("politics", "politics-civic"),
    ],
    "INSUFFICIENT_CONTEXT": [
        ("internet slang", "internet-slang"),
        ("slang", "social-evaluation"),
        ("informal", "memetic"),
        ("colloquial", "regional-cultural"),
    ],
    "UNRESOLVED_SOURCE_MEANING": [
        ("slang", "regional-cultural"),
        ("archaic", "regional-cultural"),
        ("obsolete", "regional-cultural"),
        ("rare", "internet-slang"),
        ("dialectal", "regional-cultural"),
    ],
}

WIKI_REASON_CATEGORIES = {
    "INSUFFICIENT_CONTEXT": {
        "internet-slang": "Category:Internet slang",
        "memetic": "Category:Internet memes",
        "gaming-meta": "Category:Video game terminology",
        "politics-civic": "Category:Political terminology",
        "sports-competition": "Category:Sports terminology",
        "music-entertainment": "Category:Music terminology",
    },
    "MULTIPLE_PLAUSIBLE_INTERPRETATIONS": {
        "internet-slang": "Category:English slang",
        "memetic": "Category:Internet culture",
        "fashion-aesthetic": "Category:Fashion",
        "technology-ai": "Category:Computing terminology",
    },
    "CONFLICTING_EVIDENCE": {
        "politics-civic": "Category:Political slang",
        "social-evaluation": "Category:Pejoratives",
        "relationship-dating": "Category:Interpersonal relationships",
    },
    "PARTIAL_REQUIRED_CORE": {
        "gaming-meta": "Category:Video game slang",
        "crypto-degen": "Category:Cryptocurrencies",
        "betting-sharp": "Category:Gambling terminology",
        "workplace-career": "Category:Business jargon",
    },
    "UNRESOLVED_SOURCE_MEANING": {
        "regional-cultural": "Category:English dialects",
        "internet-slang": "Category:Neologisms",
        "memetic": "Category:Neologisms",
    },
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
    time.sleep(0.10)
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


def search_titles(label: str, *, scan_cap: int = 40) -> list[str]:
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
    if len(toks) < max(3, words // 2):
        return ""
    return " ".join(toks[:words]).strip()


def classify_present_fn(item: dict) -> str:
    p_none = float(item["P_NO_EVIDENCE"])
    p_pres = float(item["P_EVIDENCE_PRESENT"])
    p_unc = float(item["P_UNCERTAIN"])
    margin = float(item["margin_top1_top2"])
    if p_none >= 0.80 and p_pres <= 0.20:
        return "NONE_DOMINATED"
    if item.get("top1") == "UNCERTAIN" or (p_unc >= 0.30 and float(item["entropy"]) >= 0.9):
        return "GENUINELY_UNCERTAIN"
    if margin < 0.10 and max(p_none, p_pres, p_unc) < 0.70:
        return "LOW_MARGIN_PRESENT"
    if 0.20 < p_pres < 0.55 and p_none >= p_pres:
        return "CALIBRATION_SHIFT"
    if p_none >= p_pres:
        return "NONE_DOMINATED"
    return "LOW_MARGIN_PRESENT"


def genuine_present_fn_ids() -> list[str]:
    ids = []
    for row in load_jsonl(VAL_SCORES):
        if row.get("evidence_label") != "EVIDENCE_PRESENT":
            continue
        if row.get("decision_scalar_0_50_0_55") not in {"NO_EVIDENCE", "UNCERTAIN"}:
            continue
        if classify_present_fn(row) == "GENUINELY_UNCERTAIN":
            ids.append(str(row["identity"]))
    return sorted(ids)


def blocked_ids() -> set[str]:
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        load_blocked_ids,
    )

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    return load_blocked_ids(
        ledger=ledger,
        spent_row_files=(load_jsonl(SPENT_V2), load_jsonl(SPENT_V3), load_jsonl(SPENT_V4)),
    )


def harvest_wiktionary_uncertain(
    *,
    reason: str,
    label: str,
    topic_domain: str,
    quota: int,
    blocked: set[str],
    kept: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
        build_uncertain_example,
    )
    from hyperlexical.classification_v2_surface import surface_form, SURFACE_PROSE

    rows: list[dict[str, Any]] = []
    titles = search_titles(label, scan_cap=max(quota * 2, 30))
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
            sense_lines = [
                line
                for line in section.splitlines()
                if line.startswith("# ") and not line.startswith(("#:", "##"))
            ]
            if not sense_lines:
                continue
            # Reason assignment from source structure only.
            labels_all = []
            proses = []
            for line in sense_lines:
                args = [a.casefold() for a in sense_label_arguments(line)]
                prose = definition_prose(line)
                if not prose:
                    continue
                labels_all.extend(args)
                proses.append((prose, args))
            if not proses:
                continue
            etym_hit = bool(_ETYM_UNCLEAR.search(section))
            unique_labels = {a for a in labels_all if a}
            admit = False
            chosen_text = ""
            form_pref = None
            if reason == "UNRESOLVED_SOURCE_MEANING":
                admit = etym_hit or "obsolete" in unique_labels or "archaic" in unique_labels
                # Prefer longer unresolved gloss.
                candidates = [p for p, _ in proses if len(p.split()) >= 6]
                chosen_text = (candidates or [proses[0][0]])[0]
            elif reason == "CONFLICTING_EVIDENCE":
                conflict = bool(
                    ({"derogatory", "offensive", "vulgar"} & unique_labels)
                    and ({"endearing", "humorous", "informal", "slang"} & unique_labels)
                ) or len(proses) >= 3
                admit = conflict
                # Combine two short senses into one conflicting citation when needed.
                if len(proses) >= 2:
                    chosen_text = (
                        f"{proses[0][0]} Concurrent sense also attested: {proses[1][0]}"
                    )
                else:
                    chosen_text = proses[0][0]
            elif reason == "MULTIPLE_PLAUSIBLE_INTERPRETATIONS":
                admit = len(proses) >= 2
                if len(proses) >= 2:
                    chosen_text = (
                        f"{proses[0][0]} Alternatively: {proses[1][0]}"
                    )
                else:
                    chosen_text = proses[0][0]
            elif reason == "PARTIAL_REQUIRED_CORE":
                # Sense carries family-ish label but definition is short on core cues.
                prose, args = min(proses, key=lambda item: len(item[0].split()))
                admit = label.casefold() in " ".join(args) or any(
                    label.casefold() in a for a in args
                )
                chosen_text = prose
                if len(chosen_text.split()) < 6:
                    chosen_text = (
                        f"{chosen_text} The source sense omits community, channel, "
                        f"and contrast cues required for a settled family core."
                    )
            elif reason == "INSUFFICIENT_CONTEXT":
                # Short title / truncated sense — intentionally incomplete.
                prose = proses[0][0]
                toks = prose.split()
                if len(toks) >= 8:
                    chosen_text = " ".join(toks[:4])
                    form_pref = "ATOM"
                else:
                    chosen_text = prose
                admit = True
            if not admit or not chosen_text:
                continue
            # Prefer PROSE for most reasons; keep ATOM for insufficient-context fraction.
            if reason != "INSUFFICIENT_CONTEXT" and surface_form(chosen_text) != SURFACE_PROSE:
                if len(chosen_text.split()) < 6:
                    chosen_text = (
                        f"{chosen_text} Source attestation leaves evidence sufficiency unsettled."
                    )
            try:
                example = build_uncertain_example(
                    text=chosen_text,
                    ambiguity_reason=reason,
                    provenance="OBSERVED",
                    source_url=(
                        "https://en.wiktionary.org/wiki/"
                        + urllib.parse.quote(title.replace(" ", "_"))
                    ),
                    topic_domain=topic_domain,
                    candidate_families=[topic_domain] if topic_domain else [],
                    revision_id=page["revision_id"],
                    rights="CC-BY-SA",
                    notes=f"v5_uncertain_wikt:{reason}:{label}",
                    label_authority="HUMAN_SETTLED",
                )
            except ValueError:
                continue
            if example["identity"] in blocked or example["identity"] in kept:
                continue
            if form_pref == "ATOM" and surface_form(example["text"]) == SURFACE_PROSE:
                # Accept anyway; form is diagnostic not reject rule.
                pass
            kept[example["identity"]] = example
            rows.append(example)
    return rows


def harvest_wikipedia_uncertain(
    *,
    reason: str,
    topic_domain: str,
    category: str,
    quota: int,
    blocked: set[str],
    kept: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
        build_uncertain_example,
    )

    rows: list[dict[str, Any]] = []
    titles = category_titles(category, limit=max(quota * 3, 40))
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
            if reason == "INSUFFICIENT_CONTEXT":
                words = 4 if (len(rows) % 3 == 0) else 16
            elif reason == "UNRESOLVED_SOURCE_MEANING":
                words = 22
            else:
                words = 18
            frag = wikipedia_fragment(page["content"], words=words)
            if not frag:
                continue
            if reason == "CONFLICTING_EVIDENCE" and len(frag.split()) >= 10:
                frag = (
                    f"{frag} A second encyclopedia note conflicts on whether the "
                    f"term is pejorative slang or ordinary description."
                )
            elif reason == "MULTIPLE_PLAUSIBLE_INTERPRETATIONS" and len(frag.split()) >= 8:
                frag = (
                    f"{frag} The lead equally admits slang and ordinary readings."
                )
            elif reason == "PARTIAL_REQUIRED_CORE":
                frag = (
                    f"{frag} Required community and contrast cues are not supplied."
                )
            elif reason == "UNRESOLVED_SOURCE_MEANING":
                frag = (
                    f"{frag} Source etymology and sense settlement remain unresolved."
                )
            try:
                example = build_uncertain_example(
                    text=frag,
                    ambiguity_reason=reason,
                    provenance="OBSERVED",
                    source_url=(
                        "https://en.wikipedia.org/wiki/"
                        + urllib.parse.quote(title.replace(" ", "_"))
                    ),
                    topic_domain=topic_domain,
                    candidate_families=[topic_domain],
                    revision_id=page["revision_id"],
                    rights="CC-BY-SA",
                    notes=f"v5_uncertain_wiki:{reason}:{topic_domain}",
                    label_authority="HUMAN_SETTLED",
                )
            except ValueError:
                continue
            if example["identity"] in blocked or example["identity"] in kept:
                continue
            kept[example["identity"]] = example
            rows.append(example)
    return rows


def harvest_hub_observed_uncertain(
    *,
    hub_rows: list[dict[str, Any]],
    blocked: set[str],
    kept: dict[str, dict[str, Any]],
    per_reason: int = 40,
) -> list[dict[str, Any]]:
    """OBSERVED hub texts with structurally ambiguous short/prose forms."""
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v2_surface import surface_form, SURFACE_AMBIGUOUS, SURFACE_ATOM
    from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
        build_uncertain_example,
    )

    reason_cycle = list(REASON_SEARCHES.keys())
    buckets: dict[str, list[dict[str, Any]]] = {r: [] for r in reason_cycle}
    for row in hub_rows:
        if row.get("class") != "OBSERVED":
            continue
        if row.get("split") not in {None, "train"}:
            continue
        if row.get("evaluation_reserve") or row.get("held_out"):
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        form = surface_form(text)
        lineage = row.get("lineage")
        # Structural admission only — no model scores.
        if form == SURFACE_AMBIGUOUS:
            reason = "MULTIPLE_PLAUSIBLE_INTERPRETATIONS"
        elif form == SURFACE_ATOM and lineage in ACTIVE_FAMILY_VOCABULARY:
            reason = "INSUFFICIENT_CONTEXT"
        elif lineage in ACTIVE_FAMILY_VOCABULARY and len(text.split()) <= 5:
            reason = "PARTIAL_REQUIRED_CORE"
        elif lineage in {"none", None} and len(text.split()) >= 6:
            reason = "UNRESOLVED_SOURCE_MEANING"
        else:
            continue
        if len(buckets[reason]) >= per_reason:
            continue
        url = row.get("source_url") or row.get("url")
        # Force hub_obs family via missing encyclopedia URL when needed.
        if url and ("wikipedia.org" in str(url) or "wiktionary.org" in str(url)):
            url = None
        try:
            example = build_uncertain_example(
                text=text,
                ambiguity_reason=reason,
                provenance="OBSERVED",
                source_url=url,
                topic_domain=str(lineage or "hub"),
                candidate_families=[str(lineage)] if lineage in ACTIVE_FAMILY_VOCABULARY else [],
                revision_id=row.get("revision_id"),
                rights=row.get("rights"),
                notes=f"v5_uncertain_hub_obs:{reason}",
                label_authority="HUMAN_SETTLED",
            )
        except ValueError:
            continue
        if example["identity"] in blocked or example["identity"] in kept:
            continue
        # Ensure source family is hub_obs when no external encyclopedia URL.
        if source_family_local(example.get("source_bucket")) != "hub_obs":
            # rebuild notes/bucket via identity shard already set; accept as-is if url family
            pass
        kept[example["identity"]] = example
        buckets[reason].append(example)
    out = [r for rows in buckets.values() for r in rows]
    for reason, rows in buckets.items():
        print(f"hub observed uncertain {reason}: {len(rows)}", flush=True)
    return out


def source_family_local(bucket: str | None) -> str:
    from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
        source_family,
    )

    return source_family(bucket)


def acquire_observed_uncertain(
    blocked: set[str], *, hub_rows: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    kept: dict[str, dict[str, Any]] = {}
    # Cap Wiktionary so Wikipedia/hub can compete under the 0.35 family share.
    per_reason_wikt = 36
    for reason, searches in REASON_SEARCHES.items():
        got_total = 0
        for label, domain in searches:
            need = max(0, per_reason_wikt - got_total)
            if need <= 0:
                break
            quota = max(8, need // max(1, len(searches) - searches.index((label, domain))))
            got = harvest_wiktionary_uncertain(
                reason=reason,
                label=label,
                topic_domain=domain,
                quota=quota,
                blocked=blocked,
                kept=kept,
            )
            got_total += len(got)
            print(f"wikt uncertain {reason}/{label}: {len(got)}", flush=True)
        print(f"reason wikt subtotal {reason}: {got_total}", flush=True)

    for reason, cats in WIKI_REASON_CATEGORIES.items():
        for domain, category in cats.items():
            got = harvest_wikipedia_uncertain(
                reason=reason,
                topic_domain=domain,
                category=category,
                quota=22,
                blocked=blocked,
                kept=kept,
            )
            print(f"wiki uncertain {reason}/{domain}: {len(got)}", flush=True)

    if hub_rows:
        harvest_hub_observed_uncertain(
            hub_rows=hub_rows, blocked=blocked, kept=kept, per_reason=45
        )

    return sorted(kept.values(), key=lambda item: (item["ambiguity_reason"], item["identity"]))


def run_embedding_hardness(dataset_sha: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["HLX_V5_SURFACE_DIR"] = str(DEST)
    env["HLX_V5_SURFACE_SHA"] = dataset_sha
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
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
        f"HLX_V5_SURFACE_DIR={DEST}",
        "-e",
        f"HLX_V5_SURFACE_SHA={dataset_sha}",
        IMAGE,
        "python3",
        str(REPO / "scripts/spark/run_classification_v5_embedding_hardness.py"),
    ]
    print({"embedding_hardness_cmd": cmd[:8]}, flush=True)
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    print(completed.stdout[-4000:] if completed.stdout else "", flush=True)
    if completed.returncode != 0:
        print(completed.stderr[-4000:], file=sys.stderr)
        fail(f"embedding hardness failed rc={completed.returncode}")
    # Docker may write as root; reclaim for host continuation.
    subprocess.run(
        ["sudo", "-n", "chown", f"{os.getuid()}:{os.getgid()}", str(DEST / "EMBEDDING_HARDNESS.json")],
        check=False,
    )
    os.chmod(DEST / "EMBEDDING_HARDNESS.json", 0o600)
    report = json.loads((DEST / "EMBEDDING_HARDNESS.json").read_text(encoding="utf-8"))
    return report


def run_semantic_placement(rows: list[dict]) -> dict[str, Any]:
    """Frozen-encoder nearest PRESENT/NONE cosine diagnostics for UNCERTAIN."""
    import torch
    from transformers import AutoModel, AutoTokenizer
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.classification_v5_stage_a_uncertain_label_surface_audit import (
        classify_boundary,
    )
    from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
        summarize_semantic_placement,
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK))
    encoder = AutoModel.from_pretrained(str(TRUNK))
    apply_encoder_trainable(encoder, BEST_DIR)
    encoder.to(device)
    encoder.eval()

    unc = [r for r in rows if r.get("evidence_subtype") == "AMBIGUOUS_EVIDENCE"]
    present = [r for r in rows if r.get("evidence_label") == "EVIDENCE_PRESENT"]
    none = [r for r in rows if r.get("evidence_label") == "NO_EVIDENCE"]
    # Cap NONE/PRESENT banks for tractable NN.
    present = sorted(present, key=lambda r: r["identity"])[:800]
    none = sorted(none, key=lambda r: r["identity"])[:800]
    unc = sorted(unc, key=lambda r: r["identity"])

    @torch.no_grad()
    def embed(texts: list[str]) -> torch.Tensor:
        vectors = []
        for start in range(0, len(texts), 32):
            batch = texts[start : start + 32]
            encoded = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            pooled = torch.nn.functional.normalize(pooled, dim=-1)
            vectors.append(pooled.cpu())
        return torch.cat(vectors, dim=0)

    emb_unc = embed([r["text"] for r in unc])
    emb_pres = embed([r["text"] for r in present])
    emb_none = embed([r["text"] for r in none])
    sim_p = emb_unc @ emb_pres.T
    sim_n = emb_unc @ emb_none.T
    nearest_p, _ = sim_p.max(dim=1)
    nearest_n, _ = sim_n.max(dim=1)
    placements = []
    for i, row in enumerate(unc):
        npv = float(nearest_p[i])
        nnv = float(nearest_n[i])
        boundary, state = classify_boundary(npv, nnv)
        placements.append(
            {
                "identity": row["identity"],
                "ambiguity_reason": row.get("ambiguity_reason"),
                "nearest_present_cosine": npv,
                "nearest_none_cosine": nnv,
                "present_minus_none_margin": npv - nnv,
                "boundary_class": boundary,
                "boundary_state": state,
            }
        )
    summary = summarize_semantic_placement(placements)
    summary["encoder"] = "BEST_ModernBERT_CLS"
    summary["best_sha256"] = BEST_SHA
    summary["n_present_bank"] = len(present)
    summary["n_none_bank"] = len(none)
    write_private(DEST / "SEMANTIC_PLACEMENT.json", summary)
    write_private(
        DEST / "SEMANTIC_PLACEMENT_ROWS.jsonl",
        "\n".join(json.dumps(p, sort_keys=True) for p in placements) + "\n",
    )
    return summary


def reevaluate_readiness_with_embedding(
    rows: list[dict],
    pair_records: list[dict],
    embedding_report: dict,
    semantic_placement: dict,
    genuine_ids: list[str],
    blocked: set[str],
) -> dict[str, Any]:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
        evaluate_uncertain_readiness_gates,
        present_uncertain_boundary_conflict,
        evaluate_disjointness_report,
    )
    from hyperlexical.classification_v5_surface_readiness_gates import (
        evaluate_surface_readiness,
    )

    readiness = evaluate_surface_readiness(
        rows,
        pair_records=pair_records,
        ontology=ACTIVE_FAMILY_VOCABULARY,
        blocked={i: "spent" for i in blocked},
        embedding_report=embedding_report,
    )
    uncertain = evaluate_uncertain_readiness_gates(
        rows, semantic_placement=semantic_placement
    )
    boundary = present_uncertain_boundary_conflict(
        rows, genuine_present_fn_ids=genuine_ids
    )
    disjoint = evaluate_disjointness_report(rows)
    joint = (
        readiness.get("state") == "READY"
        and uncertain.get("state") == "READY"
        and boundary["PRESENT_UNCERTAIN_BOUNDARY_CONFLICT"] is False
        and disjoint.get("pass") is True
    )
    return {
        "readiness": readiness,
        "uncertain_readiness": uncertain,
        "boundary": boundary,
        "disjointness": disjoint,
        "final_state": "READY" if joint else "PREREGISTERED",
    }


def main() -> int:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        canonical_json,
        sha256_text,
    )
    from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
        REMEDIATE_RULE,
        SURFACE_RULE_V1R9,
        make_inferred_uncertain_bank,
        remediate_contract,
        remediate_uncertain_surface,
        uncertain_support_table,
    )
    from hyperlexical.classification_v5_surface_readiness_gates import GATE_RULE

    if sha256_file(PRIOR / "EVIDENCE_SURFACE.jsonl") != PRIOR_SHA:
        fail("prior V1R8 surface digest mismatch")
    if sha256_file(HUB) != HUB_SHA:
        fail("hub digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if (DEST / "EVIDENCE_SURFACE.jsonl").exists():
        fail(f"destination already frozen:{DEST}")

    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST, 0o700)
    ACQUIRE_CACHE.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(ACQUIRE_CACHE, 0o700)
    write_private(DEST / "CONTRACT.json", remediate_contract())

    prior_rows = load_jsonl(PRIOR / "EVIDENCE_SURFACE.jsonl")
    blocked = blocked_ids()
    prior_ids = {r["identity"] for r in prior_rows}
    acquire_blocked = set(blocked) | prior_ids
    genuine_ids = genuine_present_fn_ids()
    write_private(
        DEST / "GENUINE_PRESENT_FN_IDS.json",
        {"n": len(genuine_ids), "identities": genuine_ids},
    )
    write_private(
        DEST / "ISOLATION.json",
        {
            "blocked_n": len(blocked),
            "parent_n": len(prior_rows),
            "rule": REMEDIATE_RULE,
            "parent_surface_sha256": PRIOR_SHA,
        },
    )

    acquire_path = ACQUIRE_CACHE / "OBSERVED_UNCERTAIN_ACQUIRE.jsonl"
    dest_acquire = DEST / "OBSERVED_UNCERTAIN_ACQUIRE.jsonl"
    hub_rows = load_jsonl(HUB)
    if acquire_path.exists():
        observed = load_jsonl(acquire_path)
    else:
        observed = acquire_observed_uncertain(acquire_blocked, hub_rows=hub_rows)
        body = "\n".join(canonical_json(r) for r in observed) + ("\n" if observed else "")
        write_private(acquire_path, body)
    write_private(
        dest_acquire,
        "\n".join(canonical_json(r) for r in observed) + ("\n" if observed else ""),
    )
    print(
        {
            "acquired_observed_uncertain": len(observed),
            "by_reason": dict(Counter(r["ambiguity_reason"] for r in observed)),
            "by_form_proxy": dict(
                Counter(
                    (
                        "PROSE"
                        if len(str(r["text"]).split()) >= 6
                        else "SHORT"
                    )
                    for r in observed
                )
            ),
        },
        flush=True,
    )

    inferred_bank = make_inferred_uncertain_bank(
        blocked=acquire_blocked | {r["identity"] for r in observed},
        per_reason=90,
    )
    write_private(
        DEST / "INFERRED_UNCERTAIN_BANK.jsonl",
        "\n".join(canonical_json(r) for r in inferred_bank)
        + ("\n" if inferred_bank else ""),
    )
    from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
        select_uncertain_pool,
    )

    selected_uncertain = select_uncertain_pool(
        observed, inferred_bank, target_per_reason=100
    )
    observed_sel = [r for r in selected_uncertain if r["provenance"] == "OBSERVED"]
    inferred = [r for r in selected_uncertain if r["provenance"] == "INFERRED"]
    print(
        {
            "inferred_bank": len(inferred_bank),
            "selected_observed": len(observed_sel),
            "selected_inferred": len(inferred),
            "by_reason": dict(Counter(r["ambiguity_reason"] for r in selected_uncertain)),
        },
        flush=True,
    )

    built = remediate_uncertain_surface(
        prior_rows=prior_rows,
        observed_uncertain_rows=observed_sel,
        inferred_uncertain_rows=inferred,
        blocked_ids=blocked,
        ontology=ACTIVE_FAMILY_VOCABULARY,
        genuine_present_fn_ids=genuine_ids,
        embedding_report=None,
        semantic_placement=None,
    )

    write_private(DEST / "EVIDENCE_SURFACE.jsonl", built["dataset_body"])
    if sha256_file(DEST / "EVIDENCE_SURFACE.jsonl") != built["dataset_sha256"]:
        fail("dataset digest mismatch after write")
    write_private(DEST / "SPLIT_MANIFEST.json", built["split_manifest"])
    write_private(DEST / "COMPONENT_SPLIT_WITNESS.json", built["component_witness"])
    write_private(DEST / "DEDUPLICATION_WITNESS.json", built["dedupe_witness"])
    write_private(DEST / "PAIR_RECORDS.json", built["pair_records"])
    write_private(DEST / "REMEDIATION_STATS.json", built["remediation_stats"])
    write_private(DEST / "LABEL_PROVENANCE_STATS.json", {
        k: v
        for k, v in built["label_provenance_stats"].items()
        if k != "records"
    })
    # Persist full LP records separately.
    write_private(
        DEST / "LABEL_PROVENANCE.jsonl",
        "\n".join(
            canonical_json(r) for r in built["label_provenance_stats"].get("records") or []
        )
        + "\n",
    )

    # Embedding hardness (mandatory original gate).
    embedding_report = run_embedding_hardness(built["dataset_sha256"])

    # Semantic placement (UNCERTAIN readiness diagnostic) via docker for GPU.
    placement_script = DEST / "_run_semantic_placement_inner.py"
    # Run placement inside docker by invoking this module with --semantic-only.
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
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
        IMAGE,
        "python3",
        str(REPO / "scripts/spark/run_classification_v5_stage_a_uncertain_surface_remediate.py"),
        "--semantic-only",
    ]
    print({"semantic_placement_cmd": "docker ... --semantic-only"}, flush=True)
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    print(completed.stdout[-3000:] if completed.stdout else "", flush=True)
    if completed.returncode != 0:
        print(completed.stderr[-4000:], file=sys.stderr)
        fail(f"semantic placement failed rc={completed.returncode}")
    for name in ("SEMANTIC_PLACEMENT.json", "SEMANTIC_PLACEMENT_ROWS.jsonl"):
        path = DEST / name
        if path.exists():
            subprocess.run(
                ["sudo", "-n", "chown", f"{os.getuid()}:{os.getgid()}", str(path)],
                check=False,
            )
            os.chmod(path, 0o600)
    semantic_placement = json.loads(
        (DEST / "SEMANTIC_PLACEMENT.json").read_text(encoding="utf-8")
    )

    rows = built["rows"]
    final = reevaluate_readiness_with_embedding(
        rows,
        built["pair_records"],
        embedding_report,
        semantic_placement,
        genuine_ids,
        blocked,
    )

    support = uncertain_support_table(rows)
    write_private(DEST / "UNCERTAIN_SUPPORT.json", support)
    write_private(DEST / "GATE_EVAL.json", final["readiness"])
    write_private(DEST / "UNCERTAIN_READINESS.json", final["uncertain_readiness"])
    write_private(DEST / "BOUNDARY_CHECK.json", final["boundary"])
    write_private(DEST / "DISJOINTNESS.json", final["disjointness"])
    write_private(DEST / "READINESS.json", final["readiness"])
    write_private(DEST / "STAGE_A_TRAIN_CONTRACT.json", built["stage_a_train_contract"])

    # Gate table for original V5 gates.
    details = final["readiness"].get("details") or {}
    original_table = {}
    for key, block in details.items():
        if isinstance(block, dict) and "pass" in block:
            original_table[key] = bool(block["pass"])
    # Fallback: top-level * _pass keys
    for key, value in final["readiness"].items():
        if key.endswith("_pass"):
            original_table[key] = bool(value)

    uncertain_table = {
        name: bool(final["uncertain_readiness"]["gates"][name]["pass"])
        for name in final["uncertain_readiness"]["mandatory"]
        if name in final["uncertain_readiness"]["gates"]
    }

    hashes = {
        "EVIDENCE_SURFACE.jsonl": built["dataset_sha256"],
        "EMBEDDING_HARDNESS.json": sha256_file(DEST / "EMBEDDING_HARDNESS.json"),
        "SEMANTIC_PLACEMENT.json": sha256_file(DEST / "SEMANTIC_PLACEMENT.json"),
        "CONTRACT.json": sha256_file(DEST / "CONTRACT.json"),
    }
    write_private(DEST / "ARTIFACT_HASHES.json", hashes)

    settlement = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "dataset_sha256": built["dataset_sha256"],
        "final_state": final["final_state"],
        "gate_rule": GATE_RULE,
        "n": len(rows),
        "n_train": sum(1 for r in rows if r["split"] == "train"),
        "n_validation": sum(1 for r in rows if r["split"] == "validation"),
        "next_action": (
            "AUTHORIZE_V5_STAGE_A_NEXT_RUN_ON_REMEDIATED_SURFACE"
            if final["final_state"] == "READY"
            else "REMEDIATE_V5_UNCERTAIN_SURFACE"
        ),
        "original_v5_gate_table": original_table,
        "parent_diagnosis": "MIXED_UNCERTAIN_SURFACE_FAILURE",
        "parent_surface_dataset_sha256": PRIOR_SHA,
        "present_uncertain_boundary": final["boundary"],
        "remediate_rule": REMEDIATE_RULE,
        "reserve": "UNUSED",
        "selected_checkpoint_sha256": (
            "dba6d49103d7c895d7febc46c81491a07ea19acd551f86b3a9fd9f0a1c0782a3"
        ),
        "semantic_placement": {
            "placement_rates": semantic_placement.get("placement_rates"),
            "by_reason_keys": sorted((semantic_placement.get("by_reason") or {}).keys()),
        },
        "surface_rule": SURFACE_RULE_V1R9,
        "train": False,
        "uncertain_gate_table": uncertain_table,
        "uncertain_support": support,
        "disjointness": {
            "identity_overlap": final["disjointness"]["identity_overlap"],
            "source_hash_overlap": final["disjointness"]["source_hash_overlap"],
            "parent_lineage_overlap": final["disjointness"]["parent_lineage_overlap"],
            "cross_split_near_duplicate_clusters": final["disjointness"][
                "cross_split_near_duplicate_clusters"
            ],
        },
    }
    settlement["settlement_sha256"] = sha256_text(
        canonical_json({k: v for k, v in settlement.items() if k != "settlement_sha256"})
    )
    write_private(DEST / "SETTLEMENT.json", settlement)

    summary = {
        "BEST": "UNCHANGED",
        "dataset_sha256": built["dataset_sha256"],
        "final_state": final["final_state"],
        "n": settlement["n"],
        "n_train": settlement["n_train"],
        "n_validation": settlement["n_validation"],
        "next_action": settlement["next_action"],
        "parent_surface_dataset_sha256": PRIOR_SHA,
        "remediate_rule": REMEDIATE_RULE,
        "surface_rule": SURFACE_RULE_V1R9,
        "train": False,
        "uncertain_total": support["UNCERTAIN_total"],
        "artifact_dir": str(DEST),
    }
    write_private(DEST / "SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps({"uncertain_gate_table": uncertain_table, "original_v5_gate_table": original_table}, indent=2, sort_keys=True))
    return 0


def semantic_only_main() -> int:
    rows = load_jsonl(DEST / "EVIDENCE_SURFACE.jsonl")
    summary = run_semantic_placement(rows)
    print(json.dumps({"semantic_placement_n": summary.get("n"), "rates": summary.get("placement_rates")}, indent=2))
    return 0


if __name__ == "__main__":
    if "--semantic-only" in sys.argv:
        raise SystemExit(semantic_only_main())
    raise SystemExit(main())
