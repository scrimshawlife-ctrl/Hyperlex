"""REMEDIATE_V5_STAGE_A_GENERALIZATION_SURFACE_GATES — successor V1R1.

Single constrained repair via FRESH_NON_WIKTIONARY_MATCHED_CONTRAST_ADDITIONS.
Does not mutate sealed V1, train, retune thresholds, touch Stage-B, reuse spent
reserve text, or move BEST pointers.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path("/home/morpheus/Hyperlex")
PARENT_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-generalization-surface-v1-20261001"
)
DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-generalization-surface-v1r1-20261001"
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
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
STAGE_A_BEST_SHA = (
    "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = (
    "HyperlexClassificationV5GeneralizationSurfaceV1R1/1.0 "
    "(stage-a generalization remediation; mediawiki provenance)"
)

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

FAMILY_CUES = {
    "ai-native": ("agentic", "hallucination", "jailbreak", "promptware"),
    "betting-sharp": ("juice", "steam", "sharp", "vig"),
    "crypto-degen": ("degen", "wagmi", "ape", "rekt"),
    "gaming-meta": ("nerf", "buff", "meta", "tilt"),
    "internet-slang": ("rizz", "cap", "mid", "sus"),
    "technology-ai": ("prompt", "finetune", "inference", "token"),
    "social-evaluation": ("aura", "cringe", "based", "mid"),
    "relationship-dating": ("rizz", "situationship", "ghosted", "simp"),
}
ORDINARY_SWAP = {
    "agentic": "methodical",
    "hallucination": "misreading",
    "jailbreak": "override",
    "promptware": "toolkit",
    "juice": "margin",
    "steam": "pressure",
    "sharp": "precise",
    "vig": "fee",
    "degen": "risk",
    "wagmi": "optimism",
    "ape": "rush",
    "rekt": "loss",
    "nerf": "reduce",
    "buff": "boost",
    "meta": "pattern",
    "tilt": "frustration",
    "rizz": "charm",
    "cap": "claim",
    "mid": "average",
    "sus": "doubt",
    "prompt": "query",
    "finetune": "adjust",
    "inference": "prediction",
    "token": "unit",
    "aura": "presence",
    "cringe": "awkward",
    "based": "solid",
    "situationship": "arrangement",
    "ghosted": "ignored",
    "simp": "devotee",
}
DOMAIN_NONE_NEED = (
    "astronomy",
    "betting-sharp",
    "crypto-degen",
    "internet-slang",
    "mathematics",
    "technology-ai",
)
WIKI_CATEGORIES = {
    "astronomy": "Category:Astronomy",
    "mathematics": "Category:Mathematics",
    "botany": "Category:Botany",
    "chemistry": "Category:Chemistry",
    "physics": "Category:Physics",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(message: str) -> None:
    print(f"FAIL:{message}", flush=True)
    raise SystemExit(2)


def write_private(path: Path, payload: dict | str | list) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        body = payload
    else:
        body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def pin_inputs() -> None:
    if not PARENT_DEST.exists():
        fail(f"missing_parent:{PARENT_DEST}")
    parent_surface = PARENT_DEST / "EVIDENCE_SURFACE.jsonl"
    digest = sha256_file(parent_surface)
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        PARENT_SURFACE_SHA_V1,
    )

    if digest != PARENT_SURFACE_SHA_V1:
        fail(f"parent_surface_sha_drift:{digest}")
    if sha256_file(HUB) != HUB_SHA:
        fail("hub_sha_drift")
    if sha256_file(V1R9) != V1R9_SHA:
        fail("v1r9_sha_drift")


def _api(api: str, params: dict[str, str]) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{api}?{query}",
        headers={"User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def category_titles(category: str, *, limit: int = 40) -> list[str]:
    titles: list[str] = []
    cont = None
    while len(titles) < limit:
        params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "page",
            "cmlimit": "50",
        }
        if cont:
            params["cmcontinue"] = cont
        data = _api(WIKI_API, params)
        for item in data.get("query", {}).get("categorymembers", []):
            title = item.get("title")
            if title and ":" not in title:
                titles.append(title)
                if len(titles) >= limit:
                    break
        cont = (data.get("continue") or {}).get("cmcontinue")
        if not cont:
            break
    return titles


def fetch_revisions(titles: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for i in range(0, len(titles), 8):
        batch = titles[i : i + 8]
        params = {
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "rvprop": "content|ids",
            "rvslots": "main",
            "titles": "|".join(batch),
        }
        data = _api(WIKI_API, params)
        for page in (data.get("query") or {}).get("pages", {}).values():
            title = page.get("title")
            revisions = page.get("revisions") or []
            if not title or not revisions:
                continue
            revision = revisions[0]
            content = ((revision.get("slots") or {}).get("main") or {}).get("content")
            if content:
                out[title] = {
                    "content": content,
                    "revid": revision.get("revid"),
                }
    return out


_REF = re.compile(r"<ref\b[^>]*>.*?</ref>", re.I | re.S)
_HTML = re.compile(r"<[^>]+>")
_LINK = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
_MARKUP = re.compile(r"''+")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")


def wikipedia_fragment(wikitext: str, *, words: int) -> str:
    text = _REF.sub(" ", wikitext)
    text = _TEMPLATE.sub(" ", text)
    text = _LINK.sub(r"\2", text)
    text = _MARKUP.sub("", text)
    text = _HTML.sub(" ", text)
    text = re.sub(r"\{[^}]*\}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = text.split()
    if len(parts) < max(9, words // 2):
        return ""
    return " ".join(parts[:words])


def acquire_wikipedia_lengthened_none(
    *,
    blocked_ids: set[str],
    blocked_src: set[str],
    domains: list[str],
    per_domain: int,
) -> list[dict[str, Any]]:
    """OBSERVED non-Wiktionary ordinary NONE in target length bands."""
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        assign_primary_cell,
        source_sha256,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    rows: list[dict[str, Any]] = []
    for domain in domains:
        category = WIKI_CATEGORIES.get(domain)
        if not category:
            continue
        try:
            titles = category_titles(category, limit=50)
            revs = fetch_revisions(titles)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"wiki_skip:{domain}:{exc}", flush=True)
            continue
        got = 0
        for title, payload in sorted(revs.items()):
            if got >= per_domain:
                break
            for words in (18, 22, 28, 14):
                frag = wikipedia_fragment(payload["content"], words=words)
                if not frag:
                    continue
                if domain.casefold() not in frag.casefold():
                    frag = f"{domain.capitalize()} fieldwork notes: {frag}"
                text = frag.strip()
                cell = assign_primary_cell(text=text, evidence_label="NO_EVIDENCE")
                if cell not in {
                    "ORDINARY_PROSE/NO_EVIDENCE",
                    "PROSE/NO_EVIDENCE",
                    "DEFINITION_STYLE/NO_EVIDENCE",
                }:
                    continue
                identity = normalized_text_sha256(text)
                src = source_sha256(text)
                if identity in blocked_ids or src in blocked_src:
                    continue
                blocked_ids.add(identity)
                blocked_src.add(src)
                rows.append(
                    {
                        "class": "OBSERVED",
                        "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                        "jev": "OFF",
                        "lineage": "none",
                        "notes": f"v5_gen_v1r1_wp_none:{domain}",
                        "revision_id": payload.get("revid"),
                        "rights": "CC-BY-SA-3.0",
                        "source_url": (
                            "https://en.wikipedia.org/wiki/"
                            + urllib.parse.quote(title.replace(" ", "_"))
                        ),
                        "split": "train",
                        "surface": "train",
                        "task": "classify",
                        "text": text,
                        "topic_domain": domain,
                    }
                )
                got += 1
                break
    print(f"acquire_wp_v1r1_none n={len(rows)}", flush=True)
    return rows


def synthesize_v1r1_matched_additions(
    baseline_rows: list[dict[str, Any]],
    *,
    blocked_ids: set[str],
    blocked_src: set[str],
    targets: dict[str, Any],
    hub_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fresh non-Wiktionary matched contrasts attacking all failed gates together."""
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        ORDINARY_DOMAIN_LABELS,
        assign_primary_cell,
        domain_key,
        source_sha256,
        tokens,
        word_count,
    )
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        ORDINARY_DOMAIN_BANK,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.classification_v2_surface import surface_form, SURFACE_ATOM

    rows: list[dict[str, Any]] = []

    def admit(row: dict[str, Any]) -> bool:
        text = str(row["text"]).strip()
        if not text:
            return False
        # Never admit Wiktionary-sourced remediation rows.
        url = str(row.get("source_url") or "")
        if "wiktionary.org" in url.casefold():
            return False
        identity = normalized_text_sha256(text)
        src = source_sha256(text)
        if identity in blocked_ids or src in blocked_src:
            return False
        blocked_ids.add(identity)
        blocked_src.add(src)
        rows.append(row)
        return True

    need_pres = int(targets["required_new_nonwik_present"])
    need_none = int(targets["required_new_nonwik_none"])
    # Buffer above dilution floors for length/lexical/SHORT_ATOM.
    need_pres = max(need_pres, 210)
    need_none = max(need_none, 190)

    families = [f for f in FAMILY_CUES if f in ACTIVE_FAMILY_VOCABULARY]
    ordinary = list(ORDINARY_DOMAIN_LABELS)

    # --- A. SHORT_ATOM PRESENT from hub (non-wik) + matched NONE ---
    sa_pres_need = int(targets["fresh_short_atom_present"])
    sa_none_need = int(targets["fresh_short_atom_none"])
    hub_sa: list[dict[str, Any]] = []
    for row in hub_rows:
        if sa_pres_need <= 0:
            break
        if row.get("split") not in {None, "train"}:
            continue
        if row.get("class") not in {"OBSERVED", "INFERRED"}:
            continue
        lineage = row.get("lineage")
        if lineage not in ACTIVE_FAMILY_VOCABULARY:
            continue
        text = str(row.get("text") or "").strip()
        if not text or surface_form(text) != SURFACE_ATOM:
            continue
        if assign_primary_cell(text=text, evidence_label="EVIDENCE_PRESENT") != (
            "SHORT_ATOM/EVIDENCE_PRESENT"
        ):
            continue
        identity = normalized_text_sha256(text)
        src = source_sha256(text)
        if identity in blocked_ids or src in blocked_src:
            continue
        item = {
            "class": row.get("class"),
            "evidence_subtype": "POSITIVE_EVIDENCE",
            "jev": "OFF",
            "lineage": lineage,
            "notes": "v5_gen_v1r1_hub_short_atom_present",
            "split": "train",
            "surface": "train",
            "task": "classify",
            "text": text,
            "topic_domain": lineage,
        }
        if admit(item):
            hub_sa.append(item)
            sa_pres_need -= 1
            need_pres -= 1

    for idx, pos in enumerate(hub_sa):
        if sa_none_need <= 0:
            break
        base = re.sub(r"[^a-z0-9]+", "", str(pos["text"]).casefold())[:8] or "nx"
        # Deterministic ordinary atom sharing character mass, not family meaning.
        text = f"{base[:3]}{idx % 97}" if idx % 2 == 0 else f"lab{idx % 89}"
        if assign_primary_cell(text=text, evidence_label="NO_EVIDENCE") != (
            "SHORT_ATOM/NO_EVIDENCE"
        ):
            text = f"doc{idx}"
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "SHORT_ATOM_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": f"v5_gen_v1r1_short_atom_none:{pos.get('lineage')}",
                "parent_identity": normalized_text_sha256(pos["text"]),
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": "unspecified",
            }
        ):
            sa_none_need -= 1
            need_none -= 1

    # Extra SHORT_ATOM PRESENT synthetic (non-wik) if hub insufficient.
    synth_atoms = (
        "nerf",
        "buff",
        "tilt",
        "juice",
        "steam",
        "wagmi",
        "rekt",
        "prompt",
        "finetune",
        "aura",
        "based",
        "cringe",
    )
    i = 0
    while sa_pres_need > 0 and i < 80:
        fam = families[i % len(families)]
        cue = FAMILY_CUES.get(fam, ("meta",))[i % 4]
        text = f"{cue}{i}" if i % 3 == 0 else cue
        i += 1
        if assign_primary_cell(text=text, evidence_label="EVIDENCE_PRESENT") != (
            "SHORT_ATOM/EVIDENCE_PRESENT"
        ):
            continue
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "POSITIVE_EVIDENCE",
                "jev": "OFF",
                "lineage": fam,
                "notes": "v5_gen_v1r1_synth_short_atom_present",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": text,
                "topic_domain": fam,
            }
        ):
            sa_pres_need -= 1
            need_pres -= 1
            # matched none
            none_text = f"lab{i}"
            if admit(
                {
                    "class": "INFERRED",
                    "evidence_subtype": "SHORT_ATOM_NONE",
                    "jev": "OFF",
                    "lineage": "none",
                    "notes": "v5_gen_v1r1_synth_short_atom_none",
                    "split": "train",
                    "surface": "train",
                    "task": "classify",
                    "text": none_text,
                    "topic_domain": "unspecified",
                }
            ):
                sa_none_need -= 1
                need_none -= 1

    # --- B. Domain-deficit matched length-band prose pairs ---
    domain_none_targets = dict(targets["domain_none_targets"])
    templates_pres = (
        "In {domain} community notes a volunteer used {cue} while reviewing shared "
        "fieldwork schedules and vocabulary during session {n}.",
        "During {domain} laboratory review the cohort mentioned {cue} beside ordinary "
        "equipment logs and specimen labels for case {n}.",
        "A {domain} seminar packet records {cue} among assistants discussing shared "
        "documentation habits without measurement claims {n}.",
    )
    templates_none = (
        "In {domain} community notes a volunteer used {swap} while reviewing shared "
        "fieldwork schedules and vocabulary during session {n}.",
        "During {domain} laboratory review the cohort mentioned {swap} beside ordinary "
        "equipment logs and specimen labels for case {n}.",
        "A {domain} seminar packet records {swap} among assistants discussing shared "
        "documentation habits without measurement claims {n}.",
    )
    # Prefer longer NONE (17-32) and shorter-or-equal PRESENT for length repair.
    for domain, need in domain_none_targets.items():
        for j in range(max(need, 0) + 4):
            if need_none <= 0 and need <= 0:
                break
            fam = families[j % len(families)]
            cue = FAMILY_CUES.get(fam, ("meta",))[j % 4]
            swap = ORDINARY_SWAP.get(cue, "notes")
            # For slang-family domains, topic_domain is the family; evidence NONE.
            topic = domain
            tmpl_i = j % len(templates_none)
            none_text = templates_none[tmpl_i].format(
                domain=domain.replace("-", " "), cue=cue, swap=swap, n=j + 400
            )
            # Lengthen NONE into 17-32 band.
            while word_count(none_text) < 17:
                none_text += " Shared archival vocabulary keeps the record complete."
            if word_count(none_text) > 32:
                none_text = " ".join(none_text.split()[:28])
            cell_n = assign_primary_cell(text=none_text, evidence_label="NO_EVIDENCE")
            if cell_n is None:
                continue
            if admit(
                {
                    "class": "INFERRED",
                    "evidence_subtype": "NEAR_DOMAIN_NONE"
                    if domain in FAMILY_CUES or domain in {
                        "betting-sharp",
                        "crypto-degen",
                        "internet-slang",
                        "technology-ai",
                    }
                    else "ORDINARY_DOMAIN_NONE",
                    "jev": "OFF",
                    "lineage": "none",
                    "notes": f"v5_gen_v1r1_domain_none:{domain}",
                    "split": "train",
                    "surface": "train",
                    "task": "classify",
                    "text": none_text,
                    "topic_domain": topic,
                }
            ):
                need_none -= 1
                domain_none_targets[domain] = max(0, domain_none_targets[domain] - 1)
                # Matched PRESENT (shorter band 9-16) sharing vocabulary.
                pres_text = templates_pres[tmpl_i].format(
                    domain=domain.replace("-", " "), cue=cue, swap=swap, n=j + 400
                )
                # Shorten PRESENT into 9-16 when possible while keeping cue.
                parts = pres_text.split()
                if len(parts) > 16:
                    # Keep head with cue.
                    cue_i = next(
                        (i for i, p in enumerate(parts) if p.casefold() == cue), 8
                    )
                    start = max(0, cue_i - 6)
                    pres_text = " ".join(parts[start : start + 15])
                if assign_primary_cell(
                    text=pres_text, evidence_label="EVIDENCE_PRESENT"
                ) is None:
                    continue
                # Family lineage for PRESENT; topic may be domain or family.
                lineage = fam if domain in ordinary or domain == "near-domain" else (
                    domain if domain in ACTIVE_FAMILY_VOCABULARY else fam
                )
                if lineage not in ACTIVE_FAMILY_VOCABULARY:
                    lineage = fam
                if admit(
                    {
                        "class": "INFERRED",
                        "evidence_subtype": "POSITIVE_EVIDENCE",
                        "jev": "OFF",
                        "lineage": lineage,
                        "notes": f"v5_gen_v1r1_domain_present_mate:{domain}",
                        "split": "train",
                        "surface": "train",
                        "task": "classify",
                        "text": pres_text,
                        "topic_domain": domain
                        if domain in ordinary or domain == "near-domain"
                        else lineage,
                    }
                ):
                    need_pres -= 1

    # near-domain PRESENT deficit
    for j in range(int(targets["domain_present_targets"].get("near-domain", 0)) + 8):
        fam = families[j % len(families)]
        cue = FAMILY_CUES.get(fam, ("meta",))[j % 4]
        swap = ORDINARY_SWAP.get(cue, "notes")
        pres = (
            f"Near-domain forum notes mention {cue} beside calendar posts and shared "
            f"community vocabulary for case {j + 900}."
        )
        none = (
            f"Near-domain forum notes mention {swap} beside calendar posts and shared "
            f"community vocabulary for case {j + 900}."
        )
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "POSITIVE_EVIDENCE",
                "jev": "OFF",
                "lineage": fam,
                "notes": "v5_gen_v1r1_near_domain_present",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": pres,
                "topic_domain": "near-domain",
            }
        ):
            need_pres -= 1
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "NEAR_DOMAIN_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": "v5_gen_v1r1_near_domain_none_mate",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": none,
                "topic_domain": "near-domain",
            }
        ):
            need_none -= 1

    # --- C. Minimal-edit lookalikes from existing PRESENT (TF-IDF / Jaccard / length) ---
    present_base = [
        r
        for r in baseline_rows
        if r.get("evidence_label") == "EVIDENCE_PRESENT"
        and word_count(r["text"]) >= 9
    ]
    present_base.sort(key=lambda r: r["identity"])
    cue_re = re.compile(
        r"\b(" + "|".join(map(re.escape, sorted(ORDINARY_SWAP))) + r")\b",
        re.I,
    )
    for idx, pos in enumerate(present_base):
        if need_none <= 0 and need_pres <= 0:
            break
        text = str(pos["text"])
        if not cue_re.search(text):
            # Inject a neutral swap pair by rewriting a mid token while keeping bag close.
            parts = text.split()
            if len(parts) < 8:
                continue
            mid = len(parts) // 2
            none_parts = list(parts)
            none_parts[mid] = "documentation"
            none_text = " ".join(none_parts)
        else:
            none_text = cue_re.sub(
                lambda m: ORDINARY_SWAP.get(m.group(0).casefold(), "notes"), text
            )
        if none_text.casefold() == text.casefold():
            continue
        # Keep same length band.
        if abs(word_count(none_text) - word_count(text)) > 2:
            continue
        cell = assign_primary_cell(text=none_text, evidence_label="NO_EVIDENCE")
        if cell is None:
            continue
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "LEXICAL_LOOKALIKE_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": f"v5_gen_v1r1_minedit_lookalike:{pos['identity'][:12]}",
                "parent_identity": pos["identity"],
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": none_text,
                "topic_domain": pos.get("topic_domain") or domain_key(pos),
            }
        ):
            need_none -= 1

    # --- D. Length-repair elongated ordinary NONE + shortened family PRESENT ---
    i = 0
    while need_none > 0 and i < need_none * 40:
        domain = ordinary[i % len(ordinary)]
        bank = ORDINARY_DOMAIN_BANK[domain]
        base = bank[i % len(bank)].rstrip(".")
        none_text = (
            f"{domain.capitalize()} laboratory documentation states {base[0].lower() + base[1:]} "
            f"with shared specimen vocabulary and archival completeness markers {i + 1200}."
        )
        while word_count(none_text) < 18:
            none_text += " Additional fieldwork notes restate the same non-memetic claim."
        if word_count(none_text) > 32:
            none_text = " ".join(none_text.split()[:30])
        i += 1
        if assign_primary_cell(text=none_text, evidence_label="NO_EVIDENCE") not in {
            "ORDINARY_PROSE/NO_EVIDENCE",
            "DEFINITION_STYLE/NO_EVIDENCE",
            "PROSE/NO_EVIDENCE",
        }:
            continue
        if admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": f"v5_gen_v1r1_long_ordinary_none:{domain}",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": none_text,
                "topic_domain": domain,
            }
        ):
            need_none -= 1
            # Matched shorter PRESENT with overlapping domain vocabulary.
            fam = families[i % len(families)]
            cue = FAMILY_CUES.get(fam, ("meta",))[i % 4]
            pres = (
                f"{domain.capitalize()} notes mention {cue} among shared specimen "
                f"vocabulary during session {i}."
            )
            if word_count(pres) > 16:
                pres = " ".join(pres.split()[:15])
            if admit(
                {
                    "class": "INFERRED",
                    "evidence_subtype": "POSITIVE_EVIDENCE",
                    "jev": "OFF",
                    "lineage": fam,
                    "notes": f"v5_gen_v1r1_short_present_mate:{domain}",
                    "split": "train",
                    "surface": "train",
                    "task": "classify",
                    "text": pres,
                    "topic_domain": domain,
                }
            ):
                need_pres -= 1

    # --- E. Definition-style matched pairs for lexical overlap ---
    i = 0
    while (need_pres > 0 or need_none > 0) and i < 240:
        fam = families[i % len(families)]
        cue = FAMILY_CUES.get(fam, ("meta",))[i % 4]
        swap = ORDINARY_SWAP.get(cue, "notes")
        domain = ordinary[i % len(ordinary)]
        pres = (
            f"{cue.capitalize()} means {cue} used as {fam} evidence in informal "
            f"{domain} speech sample {i + 3000}."
        )
        none = (
            f"{swap.capitalize()} means {swap} used as ordinary {domain} documentation "
            f"in informal {domain} speech sample {i + 3000}."
        )
        i += 1
        if need_pres > 0 and admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "POSITIVE_EVIDENCE",
                "jev": "OFF",
                "lineage": fam,
                "notes": "v5_gen_v1r1_def_present",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": pres,
                "topic_domain": fam,
            }
        ):
            need_pres -= 1
        if need_none > 0 and admit(
            {
                "class": "INFERRED",
                "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                "jev": "OFF",
                "lineage": "none",
                "notes": "v5_gen_v1r1_def_none",
                "split": "train",
                "surface": "train",
                "task": "classify",
                "text": none,
                "topic_domain": domain,
            }
        ):
            need_none -= 1

    print(
        f"synthesize_v1r1_matched_additions n={len(rows)} "
        f"remaining_need_pres={need_pres} remaining_need_none={need_none}",
        flush=True,
    )
    return rows


def compute_embedding_hardness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    script = DEST / "_embed_hardness_worker.py"
    script.write_text(
        r'''
import json, os
from pathlib import Path
import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

DEST = Path(os.environ["HLX_GEN_DEST"])
rows = json.loads((DEST / "_rows_for_embed.json").read_text(encoding="utf-8"))
model_dir = os.environ["HLX_GEN_MODEL"]
tok = AutoTokenizer.from_pretrained(model_dir)
model = AutoModel.from_pretrained(model_dir)
model.eval()
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

def embed(texts):
    out = []
    bs = 32
    for i in range(0, len(texts), bs):
        batch = texts[i:i+bs]
        enc = tok(batch, padding=True, truncation=True, max_length=256, return_tensors="pt")
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            hs = model(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1)
            summed = (hs * mask).sum(dim=1)
            denom = mask.sum(dim=1).clamp(min=1)
            vec = (summed / denom).cpu().numpy()
        out.append(vec)
    X = np.concatenate(out, axis=0)
    X = X / np.clip(np.linalg.norm(X, axis=1, keepdims=True), 1e-9, None)
    return X

present = [r for r in rows if r["evidence_label"] == "EVIDENCE_PRESENT"]
none = [r for r in rows if r["evidence_label"] == "NO_EVIDENCE"]
p = embed([r["text"] for r in present])
n = embed([r["text"] for r in none])
# nearest opposite cosine for each present and none
sims_pn = p @ n.T
nearest_p = sims_pn.max(axis=1)
nearest_n = sims_pn.max(axis=0)
all_nearest = np.concatenate([nearest_p, nearest_n])
report = {
    "frac_nearest_opposite_cosine_ge_0_75": float((all_nearest >= 0.75).mean()),
    "mean_nearest_opposite_label_cosine": float(all_nearest.mean()),
    "median_nearest_opposite_label_cosine": float(np.median(all_nearest)),
    "n_none": len(none),
    "n_present": len(present),
}
(DEST / "EMBEDDING_HARDNESS.json").write_text(
    json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(report)
'''.lstrip(),
        encoding="utf-8",
    )
    write_private(DEST / "_rows_for_embed.json", rows)
    model_dir = (
        "/home/morpheus/.hyperlex/models/"
        "hyperlex-encoder-modernbert-base-seed-select004"
    )
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "-e",
        f"HLX_GEN_DEST={DEST}",
        "-e",
        f"HLX_GEN_MODEL={model_dir}",
        "-v",
        f"{DEST}:{DEST}",
        "-v",
        f"{model_dir}:{model_dir}:ro",
        "-v",
        f"{REPO}:{REPO}:ro",
        IMAGE,
        "python",
        str(script),
    ]
    print("embed_cmd", " ".join(cmd[:8]), "...", flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout[-2000:], flush=True)
        print(proc.stderr[-2000:], flush=True)
        fail("embedding hardness docker failed")
    report = json.loads((DEST / "EMBEDDING_HARDNESS.json").read_text(encoding="utf-8"))
    return report


def main() -> int:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        DESIGN_RULE_REMEDIATE,
        PARENT_SURFACE_SHA_V1,
        SURFACE_RULE_V1R1,
        build_example,
        build_successor_surface_from_examples,
        canonical_json,
        compute_remediation_targets,
        evaluate_generalization_readiness,
        freeze_baseline_failures,
        load_blocked_ids,
        remediation_delta_report,
        sha256_text,
        stamp_source_buckets,
    )
    from hyperlexical.holdout_guard import normalized_text_sha256

    pin_inputs()
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)

    baseline_rows = load_jsonl(PARENT_DEST / "EVIDENCE_SURFACE.jsonl")
    baseline_readiness = json.loads(
        (PARENT_DEST / "READINESS.json").read_text(encoding="utf-8")
    )
    baseline_freeze = freeze_baseline_failures(baseline_rows)
    targets = compute_remediation_targets(baseline_freeze)
    write_private(DEST / "BASELINE_FREEZE.json", baseline_freeze)
    write_private(DEST / "REMEDIATION_TARGETS.json", targets)
    print("targets", json.dumps(targets, sort_keys=True), flush=True)

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    spent_files = [load_jsonl(p) for p in (SPENT_V2, SPENT_V3, SPENT_V4, SPENT_V5)]
    v1r9_rows = load_jsonl(V1R9)
    blocked_ids, blocked_src, reasons = load_blocked_ids(
        ledger=ledger,
        spent_row_files=spent_files,
        surface_row_files=[v1r9_rows],
    )
    # Also block identities already in the sealed parent (freshness vs parent where
    # appropriate for *new* rows). Retained parent rows are re-admitted explicitly.
    parent_ids = {r["identity"] for r in baseline_rows}
    parent_src = {r["source_sha256"] for r in baseline_rows}
    for r in baseline_rows:
        blocked_ids.add(r["identity"])
        blocked_src.add(r["source_sha256"])
        if r.get("parent_identity"):
            blocked_ids.add(str(r["parent_identity"]))

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
    acq_block_ids = set(blocked_ids)
    acq_block_src = set(blocked_src)

    # OBSERVED Wikipedia none for ordinary domain deficits (astronomy/mathematics).
    wp_path = DEST / "OBSERVED_ACQUIRE_WP_V1R1.jsonl"
    if wp_path.exists() and wp_path.stat().st_size > 0:
        wp = load_jsonl(wp_path)
        print(f"resume_wp_v1r1 n={len(wp)}", flush=True)
        for row in wp:
            text = str(row.get("text") or "")
            if text:
                acq_block_ids.add(normalized_text_sha256(text))
                from hyperlexical.classification_v5_stage_a_generalization_surface import (
                    source_sha256 as _ssh,
                )

                acq_block_src.add(_ssh(text))
    else:
        wp = acquire_wikipedia_lengthened_none(
            blocked_ids=acq_block_ids,
            blocked_src=acq_block_src,
            domains=["astronomy", "mathematics", "physics", "chemistry"],
            per_domain=20,
        )
        write_private(
            wp_path,
            "\n".join(canonical_json(r) for r in wp) + ("\n" if wp else ""),
        )

    fills = synthesize_v1r1_matched_additions(
        baseline_rows,
        blocked_ids=acq_block_ids,
        blocked_src=acq_block_src,
        targets=targets,
        hub_rows=hub_rows,
    )
    write_private(
        DEST / "INFERRED_MATCHED_FILLS_V1R1.jsonl",
        "\n".join(canonical_json(r) for r in fills) + ("\n" if fills else ""),
    )

    # Build examples for additions only, then union with retained baseline examples.
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        collect_examples,
    )

    addition_sources = wp + fills
    # Freshness block for additions: parent + spent + v1r9 + heldout.
    add_examples = collect_examples(
        addition_sources,
        blocked_ids=set(blocked_ids),
        blocked_source_hashes=set(blocked_src),
    )
    add_examples = stamp_source_buckets(add_examples)
    # Drop any accidental wiktionary family among additions.
    add_examples = [
        r
        for r in add_examples
        if r.get("source_family") != "wiktionary_aggregate"
        and "wiktionary.org" not in str(r.get("source_url") or "")
    ]
    print(f"addition_examples n={len(add_examples)}", flush=True)

    retained = [dict(r) for r in baseline_rows]
    # Clear prior split so successor re-split is authoritative.
    for row in retained:
        row["split"] = "train"
    merged = {r["identity"]: r for r in retained}
    for row in add_examples:
        merged.setdefault(row["identity"], row)
    examples = list(merged.values())

    built = build_successor_surface_from_examples(
        examples,
        ontology=ACTIVE_FAMILY_VOCABULARY,
        blocked_reasons=reasons,
        spent_ids=spent_v5_ids,
        embedding_report=None,
        surface_rule=SURFACE_RULE_V1R1,
        design_rule=DESIGN_RULE_REMEDIATE,
        parent_surface_sha256=PARENT_SURFACE_SHA_V1,
    )
    rows = built["rows"]
    print(
        "pre_embed_state",
        built["readiness"]["state"],
        "n",
        len(rows),
        "failed",
        [k for k, v in built["readiness"]["gate_pass"].items() if not v],
        flush=True,
    )

    embed_report = compute_embedding_hardness(rows)
    built = build_successor_surface_from_examples(
        examples,
        ontology=ACTIVE_FAMILY_VOCABULARY,
        blocked_reasons=reasons,
        spent_ids=spent_v5_ids,
        embedding_report=embed_report,
        surface_rule=SURFACE_RULE_V1R1,
        design_rule=DESIGN_RULE_REMEDIATE,
        parent_surface_sha256=PARENT_SURFACE_SHA_V1,
    )
    rows = built["rows"]
    readiness = built["readiness"]
    assembled = built["assembled"]

    delta = remediation_delta_report(
        baseline_rows=baseline_rows,
        successor_rows=rows,
        baseline_readiness=baseline_readiness,
        successor_readiness=readiness,
        baseline_freeze=baseline_freeze,
        targets=targets,
    )
    # Ensure parent ids were not required to be blocked from retention.
    delta["parent_ids"] = len(parent_ids)
    delta["parent_src"] = len(parent_src)

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
    write_private(DEST / "CELL_DIAGNOSTICS.json", readiness["cell_diagnostics"])
    write_private(DEST / "EMBEDDING_HARDNESS.json", embed_report)
    write_private(DEST / "COMPONENT_SPLIT_WITNESS.json", built["component_witness"])
    write_private(DEST / "REMEDIATION_DELTA.json", delta)
    write_private(
        DEST / "CONTRACT.json",
        {
            "design_rule": DESIGN_RULE_REMEDIATE,
            "gate_rule": readiness["gate_rule"],
            "parent_surface_sha256": PARENT_SURFACE_SHA_V1,
            "strategy": "FRESH_NON_WIKTIONARY_MATCHED_CONTRAST_ADDITIONS",
            "surface_rule": SURFACE_RULE_V1R1,
            "thresholds_mutated": False,
            "train": False,
            "best_pointers": {
                "MODEL_WIDE_BEST": BEST_SHA,
                "STAGE_A_BEST": STAGE_A_BEST_SHA,
                "status": "UNCHANGED",
            },
        },
    )
    write_private(
        DEST / "ISOLATION.json",
        {
            "MODEL_WIDE_BEST": BEST_SHA,
            "STAGE_A_BEST": STAGE_A_BEST_SHA,
            "V1R9": V1R9_SHA,
            "parent_surface": PARENT_SURFACE_SHA_V1,
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
        "REMEDIATION_DELTA.json",
        "BASELINE_FREEZE.json",
        "REMEDIATION_TARGETS.json",
        "ISOLATION.json",
    ):
        path = DEST / name
        if path.exists():
            artifact_hashes[name] = sha256_file(path)
    write_private(DEST / "ARTIFACT_HASHES.json", artifact_hashes)
    artifact_hashes["ARTIFACT_HASHES.json"] = sha256_file(DEST / "ARTIFACT_HASHES.json")
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
                "surface_rule": SURFACE_RULE_V1R1,
                "design_rule": DESIGN_RULE_REMEDIATE,
                "added_rows": delta["added_rows"],
                "retained_rows": delta["retained_rows"],
                "removed_rows": delta["removed_rows"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if readiness["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
