"""V6 representative data acquisition helpers (no train).

Natural OBSERVED-preferring acquisition utilities and split assignment.
Network I/O is performed by the Spark runner; this module stays importable
without network for unit tests of assignment/finalization logic.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY
from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_generalization_surface import assign_primary_cell
from .classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID as GOLD_CONTRACT_ID,
    classify_row as classify_identifiability,
    is_short_atom,
)
from .classification_v6_data_foundation import (
    MAX_FAMILY_SHARE_TRAIN,
    QUALIFICATION_HOLD_ID,
)
from .holdout_guard import normalized_text_sha256
from .classification_v5_surface_readiness_gates import near_duplicate_key

FAMILY_LABELS: dict[str, tuple[str, ...]] = {
    "gaming-meta": ("gaming", "video games", "esports", "online gaming"),
    "crypto-degen": ("cryptocurrency", "blockchain", "bitcoin"),
    "betting-sharp": ("gambling", "poker", "betting"),
    "internet-slang": ("internet slang", "chat slang", "text messaging", "leet"),
    "technology-ai": ("computing", "software", "programming", "artificial intelligence"),
    "sports-competition": ("sports", "athletics", "football", "baseball"),
    "music-entertainment": ("music", "popular music", "hip-hop", "rap"),
    "fashion-aesthetic": ("fashion", "cosmetics", "clothing"),
    "workplace-career": ("business", "management", "corporate"),
    "politics-civic": ("politics", "government", "political slang"),
    "spiritual-mystic": ("astrology", "occult", "new age"),
    "social-evaluation": ("slang", "pejoratives", "derogatory"),
    "conflict-aggression": ("military slang", "warfare", "violence"),
    "regional-cultural": ("british slang", "australian slang", "american slang", "dialectal"),
    "identity-affiliation": ("demonyms", "ethnic", "identity"),
    "relationship-dating": ("dating", "sexuality", "romance"),
    "memetic": ("internet memes", "meme", "imageboard"),
    "ai-native": ("artificial intelligence", "machine learning", "neural network"),
}

# Wiktionary categories used as high-volume NATURAL PRESENT sources.
WIKT_FAMILY_CATEGORIES: dict[str, tuple[str, ...]] = {
    "gaming-meta": ("Category:en:Video games", "Category:en:Gaming"),
    "crypto-degen": ("Category:en:Cryptocurrency", "Category:en:Cryptocurrencies"),
    "betting-sharp": ("Category:en:Gambling", "Category:en:Poker"),
    "internet-slang": (
        "Category:English internet slang",
        "Category:English text messaging slang",
    ),
    "technology-ai": ("Category:en:Computing", "Category:en:Artificial intelligence"),
    "sports-competition": ("Category:en:Sports", "Category:en:Baseball"),
    "music-entertainment": ("Category:en:Music", "Category:en:Hip-hop"),
    "fashion-aesthetic": ("Category:en:Fashion", "Category:en:Clothing"),
    "workplace-career": ("Category:en:Business", "Category:English business slang"),
    "politics-civic": ("Category:en:Politics", "Category:English political slang"),
    "spiritual-mystic": ("Category:en:Astrology", "Category:en:Occult"),
    "social-evaluation": (
        "Category:English pejoratives",
        "Category:English slang",
    ),
    "conflict-aggression": ("Category:en:Military", "Category:English military slang"),
    "regional-cultural": (
        "Category:British English slang",
        "Category:Australian English slang",
    ),
    "identity-affiliation": ("Category:en:Demonyms", "Category:English ethnic slurs"),
    "relationship-dating": ("Category:en:Sex", "Category:English sexual slang"),
    "memetic": ("Category:English internet slang", "Category:en:Internet"),
    "ai-native": ("Category:en:Artificial intelligence", "Category:en:Machine learning"),
}

ORDINARY_NONE_LABELS: dict[str, tuple[str, ...]] = {
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
    "botany": ("botany", "plants"),
    "chemistry": ("chemistry",),
}

WIKI_ORDINARY_CATEGORIES: dict[str, str] = {
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
    "botany": "Category:Botany",
    "chemistry": "Category:Chemistry",
}

DOMAIN_IRRELEVANT_CATEGORIES: dict[str, str] = {
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


def clean_wikitext(raw: str) -> str:
    text = _REF.sub(" ", raw or "")
    text = _TEMPLATE.sub(" ", text)
    text = _LINK.sub(lambda m: m.group(2) or "", text)
    text = _MARKUP.sub("", text)
    text = _HTML.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sense_labels(line: str) -> list[str]:
    labels: list[str] = []
    for match in _SENSE.finditer(line or ""):
        for part in re.split(r"\|", match.group(2) or ""):
            part = part.strip().lower()
            if part and part not in {"en", "english"}:
                labels.append(part)
    return labels


def row_identity(text: str, source_url: str) -> str:
    return sha256_text(canonical_json({"text": text, "source_url": source_url}))


def assign_split(identity: str) -> str:
    """Deterministic role assignment with QUAL holdout bucket.

    Buckets (stable under sha256):
      00-54 TRAIN
      55-64 DEVELOPMENT_VALIDATION
      65-89 REPRESENTATIVE_VALIDATION
      90-99 QUALIFICATION
    """
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    if bucket < 55:
        return "TRAIN"
    if bucket < 65:
        return "DEVELOPMENT_VALIDATION"
    if bucket < 90:
        return "REPRESENTATIVE_VALIDATION"
    return "QUALIFICATION"


def finalize_candidate(raw: Mapping[str, Any]) -> dict[str, Any] | None:
    text = str(raw.get("text") or "").strip()
    if len(text) < 2:
        return None
    evidence_label = str(raw["evidence_label"])
    subtype = str(raw.get("evidence_subtype") or "")
    gold_family = raw.get("gold_family")
    if evidence_label == "EVIDENCE_PRESENT" and not gold_family:
        return None
    if evidence_label == "EVIDENCE_PRESENT" and gold_family not in ACTIVE_FAMILY_VOCABULARY:
        return None

    primary_cell = str(
        raw.get("primary_cell")
        or assign_primary_cell(text=text, evidence_label=evidence_label)
    )
    provisional = {
        "text": text,
        "evidence_label": evidence_label,
        "evidence_subtype": subtype,
        "gold_family": gold_family,
        "primary_cell": primary_cell,
        "notes": raw.get("notes") or "",
    }
    short = bool(is_short_atom(provisional))
    provisional["is_short_atom"] = short
    ident = classify_identifiability(provisional)
    if evidence_label != "UNCERTAIN":
        state = ident.get("identifiability_state")
        if state in {
            "CONTEXT_REQUIRED",
            "INSUFFICIENT_TEXT",
            "INVALID_GOLD_FOR_TEXT_ONLY_MODEL",
        } or ident.get("disposition") == "EXCLUDE_FROM_TEXT_ONLY_STAGE_A":
            return None

    source_url = str(raw.get("source_url") or "")
    identity = row_identity(text, source_url)
    source_sha = normalized_text_sha256(text)
    split = assign_split(identity)
    construction = str(raw.get("construction_tag") or "NATURAL")
    if construction not in {"NATURAL", "MATCHED_CONTRAST", "SYNTHETIC", "DERIVED"}:
        construction = "NATURAL"

    gold_decision_type = {
        "EVIDENCE_PRESENT": "FAMILY",
        "NO_EVIDENCE": "NONE",
        "UNCERTAIN": "ABSTAIN",
    }[evidence_label]

    return {
        "schema": "hyperlex.classification.v6.foundation_row.v1",
        "identity": identity,
        "text": text,
        "evidence_label": evidence_label,
        "evidence_subtype": subtype,
        "gold_decision_type": gold_decision_type,
        "gold_family": gold_family if evidence_label == "EVIDENCE_PRESENT" else None,
        "candidate_families": list(
            raw.get("candidate_families") or ([] if not gold_family else [gold_family])
        ),
        "topic_domain": raw.get("topic_domain"),
        "source_family": raw.get("source_family"),
        "source_url": source_url,
        "source_sha256": source_sha,
        "near_duplicate_key": near_duplicate_key(text),
        "parent_identity": raw.get("parent_identity"),
        "provenance": raw.get("provenance") or "OBSERVED",
        "class": raw.get("provenance") or "OBSERVED",
        "construction_tag": construction,
        "construction_role": raw.get("construction_role") or "PRODUCT_EXPECTED",
        "primary_cell": primary_cell,
        "is_short_atom": short,
        "identifiability_state": ident.get("identifiability_state"),
        "identifiability_disposition": ident.get("disposition"),
        "gold_contract": GOLD_CONTRACT_ID,
        "uncertainty_reason": raw.get("uncertainty_reason"),
        "split": split,
        "qualification_hold_id": QUALIFICATION_HOLD_ID if split == "QUALIFICATION" else None,
        "rights": raw.get("rights") or "wikimedia",
        "notes": raw.get("notes") or "",
        "evaluation_spent": False,
        "optimization_forbidden": split
        in {"REPRESENTATIVE_VALIDATION", "QUALIFICATION"},
    }


def enforce_train_family_cap(
    rows: Sequence[Mapping[str, Any]],
    *,
    max_share: float = MAX_FAMILY_SHARE_TRAIN,
) -> list[dict[str, Any]]:
    """Downsample TRAIN PRESENT rows so no family exceeds max_share.

    Finds the largest per-family keep-count ``k`` such that
    ``max_family_count / total <= max_share``. If the active family set is too
    small for the bound (theoretical floor is ``1/n_families``), keeps the
    equalized best-effort sample and leaves the residual share for audit.
    """
    train = [dict(r) for r in rows if r.get("split") == "TRAIN"]
    other = [dict(r) for r in rows if r.get("split") != "TRAIN"]
    present = [r for r in train if r.get("evidence_label") == "EVIDENCE_PRESENT"]
    non_present = [r for r in train if r.get("evidence_label") != "EVIDENCE_PRESENT"]
    if not present:
        return other + train

    by_fam: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in present:
        by_fam[str(row.get("gold_family"))].append(row)
    for fam in by_fam:
        by_fam[fam] = sorted(by_fam[fam], key=lambda r: r["identity"])

    max_avail = max(len(v) for v in by_fam.values())
    retained: list[dict[str, Any]] = list(present)
    for k in range(max_avail, 0, -1):
        candidate: list[dict[str, Any]] = []
        for fam in sorted(by_fam):
            candidate.extend(by_fam[fam][:k])
        if not candidate:
            continue
        top = max(Counter(r["gold_family"] for r in candidate).values())
        if top / len(candidate) <= max_share + 1e-9:
            retained = candidate
            break
    else:
        # Impossible under max_share with current family cardinality — equalize at 1.
        retained = [by_fam[fam][0] for fam in sorted(by_fam) if by_fam[fam]]
    return other + non_present + retained


def disjointness_report(
    splits: Mapping[str, Sequence[Mapping[str, Any]]],
    blocked: Mapping[str, set[str]],
    *,
    historical_blocked: Mapping[str, set[str]] | None = None,
) -> dict[str, Any]:
    """Report cross-split and historical-spent overlap.

    ``blocked`` may include current-corpus identities during top-up dedupe.
    Overlap against spent history must use ``historical_blocked`` when provided.
    """
    ids: dict[str, set[str]] = {}
    src: dict[str, set[str]] = {}
    near: dict[str, set[str]] = {}
    for name, rows in splits.items():
        ids[name] = {r["identity"] for r in rows}
        src[name] = {r["source_sha256"] for r in rows}
        near[name] = {r["near_duplicate_key"] for r in rows}

    pairwise = {}
    names = list(splits)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            pairwise[f"{a}__{b}"] = {
                "identity_overlap": len(ids[a] & ids[b]),
                "source_overlap": len(src[a] & src[b]),
                "near_overlap": len(near[a] & near[b]),
            }

    hist = historical_blocked if historical_blocked is not None else blocked
    blocked_overlap = {
        "identity": sum(len(ids[n] & hist.get("blocked_ids", set())) for n in names),
        "source": sum(len(src[n] & hist.get("blocked_src", set())) for n in names),
        "near": sum(len(near[n] & hist.get("blocked_near", set())) for n in names),
        "text": sum(
            len({r.get("text") for r in splits[n]} & hist.get("blocked_text", set()))
            for n in names
        ),
    }
    ok = (
        all(
            v["identity_overlap"] == 0
            and v["source_overlap"] == 0
            and v["near_overlap"] == 0
            for v in pairwise.values()
        )
        and all(v == 0 for v in blocked_overlap.values())
    )
    return {"pass": ok, "pairwise": pairwise, "blocked_overlap": blocked_overlap}


def label_source_correlation(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Flag major label↔source correlations (shortcut diagnostic)."""
    from math import log

    n = len(rows)
    if n == 0:
        return {"n": 0, "flags": []}
    joint: Counter[tuple[str, str]] = Counter()
    labels = Counter()
    sources = Counter()
    for row in rows:
        lab = str(row.get("evidence_label"))
        src = str(row.get("source_family") or "unknown")
        # collapse source to family prefix
        src_root = src.split(":")[0]
        joint[(lab, src_root)] += 1
        labels[lab] += 1
        sources[src_root] += 1
    flags = []
    for (lab, src), c in joint.most_common():
        # PMI-like
        p_xy = c / n
        p_x = labels[lab] / n
        p_y = sources[src] / n
        if p_x * p_y <= 0:
            continue
        pmi = log(p_xy / (p_x * p_y) + 1e-12)
        share = c / max(1, labels[lab])
        if share >= 0.45 and pmi >= 0.6 and labels[lab] >= 20:
            flags.append(
                {
                    "label": lab,
                    "source_root": src,
                    "label_share": share,
                    "pmi": pmi,
                    "n": c,
                }
            )
    return {"n": n, "flags": flags[:20]}
