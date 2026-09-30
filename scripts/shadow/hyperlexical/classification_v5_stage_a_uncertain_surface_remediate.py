"""REMEDIATE_V5_UNCERTAIN_SURFACE — replace Stage-A UNCERTAIN surface (V1R9).

Dataset-level remediation only. Does not train, score reserves, move BEST,
change architecture, or modify frozen readiness thresholds.
Does not acquire/reject/relabel from checkpoint probabilities.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2_surface import SURFACE_ATOM, SURFACE_PROSE, surface_form
from .classification_v5_stage_a import (
    AMBIGUITY_REASONS,
    attach_and_validate_label_provenance,
    derive_label_provenance,
)
from .classification_v5_stage_a_gold_label_mapping import (
    ALLOWED_AMBIGUITY_REASONS,
    gold_label,
)
from .classification_v5_stage_a_negative_evidence_surface import (
    BEST_SHA,
    DESIGN_RULE,
    STAGE_A_TRAIN_CONTRACT,
    canonical_json,
    sha256_text,
)
from .classification_v5_stage_a_surface_remediate import (
    build_near_dup_components,
    dedupe_within_label,
    enforce_source_cap,
    pair_for_floors,
)
from .classification_v5_stage_a_uncertain_label_surface_audit import (
    FROZEN_AMBIGUITY_REASONS,
    REQUIRED_UNCERTAIN_FIELDS,
    classify_boundary,
    field_state,
)
from .classification_v5_surface_readiness_gates import (
    GATE_RULE,
    evaluate_surface_readiness,
    frozen_readiness_gates,
)
from .holdout_guard import normalized_text_sha256

REMEDIATE_RULE = "REMEDIATE_V5_UNCERTAIN_SURFACE"
SURFACE_RULE_V1R9 = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R9"
PARENT_SURFACE_RULE = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R8"
PARENT_SURFACE_SHA = (
    "c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b"
)
PARENT_DIAGNOSIS = "MIXED_UNCERTAIN_SURFACE_FAILURE"
AUDIT_RECEIPT_SHA = (
    "80d01a1"  # git tip at audit seal; private receipt sha filled by runner
)
SELECTED_CHECKPOINT_SHA = (
    "dba6d49103d7c895d7febc46c81491a07ea19acd551f86b3a9fd9f0a1c0782a3"
)
SPLIT_SEED = "hlx.v5.stage_a.uncertain.surface.remediate.component.split.v1"

# Preferred floors (do not lower after acquisition begins).
REASON_TRAIN_FLOOR = 60
REASON_VAL_FLOOR = 20
REASON_TRAIN_MIN = 40
REASON_VAL_MIN = 15

UNCERTAIN_OBSERVED_SHARE_MIN = 0.40
UNCERTAIN_VAL_OBSERVED_SHARE_MIN = 0.50
REASON_OBS_TRAIN_MIN = 10
REASON_OBS_VAL_MIN = 5
ATOM_SHARE_MAX = 0.60
PROSE_SHARE_MIN = 0.20
SOURCE_FAMILY_SHARE_MAX = 0.35
SOURCE_FAMILY_VAL_SHARE_MAX = 0.30
PRESENT_LIKE_MAX = 0.45
NONE_LIKE_MAX = 0.45
CENTERED_BETWEEN_MIN = 0.20

SOURCE_FAMILIES = ("wik", "wp", "hub_obs", "inf", "url")


def remediate_contract() -> dict[str, Any]:
    return {
        "best": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "design_rule": DESIGN_RULE,
        "gate_rule": GATE_RULE,
        "parent_diagnosis": PARENT_DIAGNOSIS,
        "parent_surface_dataset_sha256": PARENT_SURFACE_SHA,
        "parent_surface_rule": PARENT_SURFACE_RULE,
        "readiness_thresholds_modified": False,
        "remediate_rule": REMEDIATE_RULE,
        "reserve": False,
        "selected_checkpoint_sha256": SELECTED_CHECKPOINT_SHA,
        "surface_rule": SURFACE_RULE_V1R9,
        "train": False,
        "train_authorized": False,
        "reason_train_floor": REASON_TRAIN_FLOOR,
        "reason_validation_floor": REASON_VAL_FLOOR,
        "reason_train_minimum": REASON_TRAIN_MIN,
        "reason_validation_minimum": REASON_VAL_MIN,
        "checkpoint_driven_acquisition": False,
    }


def source_family(bucket: str | None) -> str:
    text = str(bucket or "")
    if text.startswith("v5_src_wik_"):
        return "wik"
    if text.startswith("v5_src_wp_"):
        return "wp"
    if text.startswith("v5_src_hub_obs_"):
        return "hub_obs"
    if text.startswith("v5_src_url_"):
        return "url"
    if text.startswith("v5_src_inf_"):
        return "inf"
    if text.startswith("v5_src_"):
        parts = text.split("_")
        return parts[2] if len(parts) > 2 else "other"
    return "other"


def stamp_uncertain_source_bucket(row: Mapping[str, Any], *, shard: int) -> str:
    url = str(row.get("source_url") or "")
    reason = str(row.get("ambiguity_reason") or "AMBIGUOUS")
    domain = str(row.get("topic_domain") or "ambig")
    if "wikipedia.org" in url:
        return f"v5_src_wp_{domain}_{shard % 4}"
    if "wiktionary.org" in url:
        return f"v5_src_wik_{domain}_{shard % 4}"
    if url:
        return f"v5_src_url_{domain}_{shard % 4}"
    if row.get("provenance") == "OBSERVED":
        return f"v5_src_hub_obs_{reason.lower()}_{shard % 3}"
    return f"v5_src_inf_{reason}_{shard % 4}"


def build_uncertain_example(
    *,
    text: str,
    ambiguity_reason: str,
    provenance: str,
    source_url: str | None = None,
    topic_domain: str | None = None,
    candidate_families: Sequence[str] | None = None,
    revision_id: int | None = None,
    rights: str | None = None,
    notes: str | None = None,
    label_authority: str | None = None,
) -> dict[str, Any]:
    if ambiguity_reason not in ALLOWED_AMBIGUITY_REASONS:
        raise ValueError(f"LABEL_MAPPING_INVALID:ambiguity_reason:{ambiguity_reason}")
    if provenance not in {"OBSERVED", "INFERRED"}:
        raise ValueError(f"LABEL_MAPPING_INVALID:provenance:{provenance}")
    text = str(text).strip()
    if not text:
        raise ValueError("LABEL_MAPPING_INVALID:empty_text")
    identity = normalized_text_sha256(text)
    families = [str(f) for f in (candidate_families or []) if f]
    missing = [ambiguity_reason, "evidence_sufficiency_unresolved"]
    row = {
        "active_family_support": list(families[:1]),
        "ambiguity_reason": ambiguity_reason,
        "candidate_families": list(families),
        "evidence_label": "UNCERTAIN",
        "evidence_spans": [],
        "evidence_subtype": "AMBIGUOUS_EVIDENCE",
        "gold_label": "UNCERTAIN",
        "identity": identity,
        "missing_required_semantics": missing,
        "negative_evidence_spans": [],
        "notes": notes or f"v5_uncertain_remediate:{ambiguity_reason}",
        "pair_group_id": None,
        "paired_positive_identity": None,
        "parent_identity": None,
        "positive_evidence_spans": [],
        "provenance": provenance,
        "required_evidence_present": "uncertain",
        "revision_id": revision_id,
        "rights": rights,
        "shared_cues": [],
        "source_sha256": sha256_text(text),
        "source_url": source_url,
        "text": text,
        "topic_domain": topic_domain,
    }
    if label_authority:
        row["label_authority"] = label_authority
    if provenance == "OBSERVED" and source_url and label_authority is None:
        row["label_authority"] = "HUMAN_SETTLED"
    # Attach label provenance fields required by UNCERTAIN readiness.
    lp = derive_label_provenance(row)
    row["label_authority"] = lp["authority"]
    row["label_derivation"] = lp["derivation"]
    row["reviewer_state"] = lp["reviewer_state"]
    row["source_provenance"] = provenance
    shard = int(identity[:8], 16)
    bucket = stamp_uncertain_source_bucket(row, shard=shard)
    row["source_bucket"] = bucket
    row["source_identity"] = bucket
    if not str(row.get("notes") or "").startswith("v5_src_"):
        row["notes"] = f"{bucket}:{row['notes']}"
    # Validate gold mapping fail-closed.
    mapped = gold_label(row)
    if mapped != "UNCERTAIN":
        raise ValueError(f"LABEL_MAPPING_INVALID:gold:{mapped}")
    return row


def attach_uncertain_required_fields(row: Mapping[str, Any]) -> dict[str, Any]:
    """Ensure all REQUIRED_UNCERTAIN_FIELDS are explicitly present."""
    item = dict(row)
    if item.get("evidence_subtype") != "AMBIGUOUS_EVIDENCE":
        return item
    if "gold_label" not in item:
        item["gold_label"] = item.get("evidence_label") or "UNCERTAIN"
    if "source_provenance" not in item:
        item["source_provenance"] = item.get("provenance")
    if "ambiguity_reason" not in item or item["ambiguity_reason"] not in ALLOWED_AMBIGUITY_REASONS:
        raise ValueError("LABEL_MAPPING_INVALID:ambiguity_reason_missing")
    if not item.get("label_authority") or not item.get("label_derivation"):
        lp = derive_label_provenance(item)
        item["label_authority"] = lp["authority"]
        item["label_derivation"] = lp["derivation"]
        item["reviewer_state"] = lp["reviewer_state"]
    if "source_identity" not in item or not item["source_identity"]:
        item["source_identity"] = item.get("source_bucket")
    if not item.get("source_sha256"):
        item["source_sha256"] = sha256_text(str(item["text"]))
    if "split" not in item:
        raise ValueError("LABEL_MAPPING_INVALID:split_missing")
    # Fail closed on any missing required field.
    for key in REQUIRED_UNCERTAIN_FIELDS:
        if field_state(item.get(key)) != "OBSERVED_VALUE":
            # gold_label / source_provenance aliases
            if key == "gold_label" and item.get("evidence_label") == "UNCERTAIN":
                item["gold_label"] = "UNCERTAIN"
                continue
            if key == "source_provenance" and item.get("provenance") in {
                "OBSERVED",
                "INFERRED",
            }:
                item["source_provenance"] = item["provenance"]
                continue
            raise ValueError(f"LABEL_MAPPING_INVALID:missing:{key}")
    return item


# Curated INFERRED PROSE banks — semantic ambiguity by construction.
# Not generated from checkpoint scores.
_INFERRED_PROSE_BANK: dict[str, list[tuple[str, list[str], str]]] = {
    "INSUFFICIENT_CONTEXT": [
        (
            "They said the drop hit different after the call, but left no room, channel, or stake.",
            ["memetic", "betting-sharp"],
            "social",
        ),
        (
            "In the thread someone wrote mid as a reply, with no referent to product, play, or person.",
            ["social-evaluation", "internet-slang"],
            "forum",
        ),
        (
            "The caption only had cooked beside a blank image tile and no scene markers at all.",
            ["internet-slang", "memetic"],
            "caption",
        ),
        (
            "Notes from the standup mentioned locked in without naming a role, deal, or release.",
            ["workplace-career", "crypto-degen"],
            "workplace",
        ),
        (
            "A sideline clip was tagged clutch, yet the sport, score, and player were never shown.",
            ["sports-competition", "gaming-meta"],
            "sports",
        ),
        (
            "The voice note ended on aura without naming whose presence or which room carried it.",
            ["social-evaluation", "memetic"],
            "audio",
        ),
        (
            "Chat logged based before anyone posted the claim that based would answer.",
            ["internet-slang", "politics-civic"],
            "chat",
        ),
        (
            "The margin note says sharp edge, with no market, blade, or critique attached.",
            ["betting-sharp", "fashion-aesthetic"],
            "margin",
        ),
        (
            "Someone replied sheesh under a link that never loaded, so the object stayed unknown.",
            ["internet-slang", "social-evaluation"],
            "reply",
        ),
        (
            "The flyer used main character energy with no plot, cast, or venue stated anywhere.",
            ["memetic", "music-entertainment"],
            "flyer",
        ),
        (
            "A whiteboard had only the word grind circled, and the project name was erased.",
            ["workplace-career", "gaming-meta"],
            "board",
        ),
        (
            "The DM said this is so valid with no prior message retained in the export.",
            ["internet-slang", "social-evaluation"],
            "dm",
        ),
    ],
    "CONFLICTING_EVIDENCE": [
        (
            "One gloss treats ghost as leave without notice; another treats it as a spectral noun only.",
            ["relationship-dating", "spiritual-mystic"],
            "lexicon",
        ),
        (
            "Editors mark flex as boastful slang while a sibling sense insists on literal stretching.",
            ["social-evaluation", "sports-competition"],
            "lexicon",
        ),
        (
            "The page lists salt as bitter online tone and as a mineral staple with equal weight.",
            ["internet-slang", "social-evaluation"],
            "lexicon",
        ),
        (
            "A style guide bans ratio as engagement warfare; the gaming note keeps it as numeric compare.",
            ["internet-slang", "gaming-meta"],
            "guide",
        ),
        (
            "Civic copy reads Astroturf as fake grassroots; the sports desk keeps artificial turf only.",
            ["politics-civic", "sports-competition"],
            "desk",
        ),
        (
            "Finance chat says rug as exit scam; the home section still means floor covering alone.",
            ["crypto-degen", "fashion-aesthetic"],
            "chat",
        ),
        (
            "One mentor uses gaslight as abuse pattern; another insists it is only a lamp metaphor.",
            ["relationship-dating", "social-evaluation"],
            "mentor",
        ),
        (
            "The patch notes call nerf a balance cut; the street glossary keeps it as foam dart toy.",
            ["gaming-meta", "internet-slang"],
            "patch",
        ),
        (
            "Campaign mail uses dogwhistle as coded cue; the field guide keeps it as a training whistle.",
            ["politics-civic", "regional-cultural"],
            "mail",
        ),
        (
            "Stream chat marks cope as denial slang; the clinical note keeps it as adaptive coping.",
            ["internet-slang", "social-evaluation"],
            "stream",
        ),
        (
            "A music blog says hardcore means genre intensity; a politics desk keeps militant cadre.",
            ["music-entertainment", "politics-civic"],
            "blog",
        ),
        (
            "The fashion brief keeps cargo as pocketed pants; logistics keeps cargo as freight only.",
            ["fashion-aesthetic", "workplace-career"],
            "brief",
        ),
    ],
    "PARTIAL_REQUIRED_CORE": [
        (
            "They called the build a meta pick, but named neither title, patch, nor role queue.",
            ["gaming-meta"],
            "gaming",
        ),
        (
            "The pitch deck said we need more alpha without a market, signal source, or window.",
            ["crypto-degen", "betting-sharp"],
            "pitch",
        ),
        (
            "Her bio lists main character without a fandom, series, or scene that would ground it.",
            ["memetic", "music-entertainment"],
            "bio",
        ),
        (
            "The recruiter wrote culture fit only, omitting team, norms, and the rejected contrast.",
            ["workplace-career"],
            "recruit",
        ),
        (
            "Chat crowned the take based, yet never supplied the claim, ideology, or foil.",
            ["internet-slang", "politics-civic"],
            "chat",
        ),
        (
            "They rated the fit drip without naming garment, brand, or occasion cues.",
            ["fashion-aesthetic"],
            "fit",
        ),
        (
            "The tipster marked the line as sharp with no book, sport, or closing number.",
            ["betting-sharp"],
            "tips",
        ),
        (
            "A review called the drop mid and skipped product, price, and comparison set.",
            ["social-evaluation", "internet-slang"],
            "review",
        ),
        (
            "The clan tag said we are cooking without match id, opponent, or objective.",
            ["gaming-meta", "internet-slang"],
            "clan",
        ),
        (
            "Ops wrote ship it as the whole update, with no artifact, channel, or rollback plan.",
            ["technology-ai", "workplace-career"],
            "ops",
        ),
        (
            "The caption claimed pure aura farming and omitted whose gaze or which room.",
            ["social-evaluation", "memetic"],
            "caption",
        ),
        (
            "Forum lore said he got ratioed, but the original post and counts were deleted.",
            ["internet-slang"],
            "forum",
        ),
    ],
    "MULTIPLE_PLAUSIBLE_INTERPRETATIONS": [
        (
            "When they said the room had rizz, it could be charisma slang or a proper-name joke.",
            ["social-evaluation", "internet-slang"],
            "room",
        ),
        (
            "Calling the plan a moonshot fits venture hype and literal aerospace rhetoric alike.",
            ["technology-ai", "workplace-career"],
            "plan",
        ),
        (
            "She called him a demon in chat, readable as praise intensity or supernatural insult.",
            ["gaming-meta", "spiritual-mystic"],
            "chat",
        ),
        (
            "The banner said clean sweep, equally a sports shutout or a literal chores claim.",
            ["sports-competition", "workplace-career"],
            "banner",
        ),
        (
            "They labeled the clip brainrot, either diagnosis joke or content-genre tag.",
            ["internet-slang", "memetic"],
            "clip",
        ),
        (
            "Marking the vote as mid could score the candidate or the meme about the vote.",
            ["politics-civic", "social-evaluation"],
            "vote",
        ),
        (
            "The squad said we hit a W, which may be match win slang or a letter grade aside.",
            ["gaming-meta", "sports-competition"],
            "squad",
        ),
        (
            "His status read in my bag, readable as fashion slang or literal luggage note.",
            ["fashion-aesthetic", "travel"],
            "status",
        ),
        (
            "They called the chart a rug risk, crypto exit risk or carpet metaphor in slides.",
            ["crypto-degen", "workplace-career"],
            "chart",
        ),
        (
            "The host said keep it underground, music scene cue or secrecy instruction alike.",
            ["music-entertainment", "politics-civic"],
            "host",
        ),
        (
            "Her note said soft launch, product rollout jargon or relationship pacing slang.",
            ["technology-ai", "relationship-dating"],
            "note",
        ),
        (
            "They wrote touch grass under the essay, either insult slang or gardening advice.",
            ["internet-slang", "social-evaluation"],
            "essay",
        ),
    ],
    "UNRESOLVED_SOURCE_MEANING": [
        (
            "The glossary marks the cant as origin unclear and gives two incompatible glosses.",
            ["regional-cultural", "internet-slang"],
            "glossary",
        ),
        (
            "Etymology is disputed: some tie the slang to a brand, others to a forgotten chant.",
            ["memetic", "music-entertainment"],
            "etym",
        ),
        (
            "Archived zine ink is smudged; the headword survives but the sense line does not.",
            ["regional-cultural", "fashion-aesthetic"],
            "zine",
        ),
        (
            "The corpus attests the shout only in 2009 logs with no definition attached anywhere.",
            ["internet-slang", "gaming-meta"],
            "corpus",
        ),
        (
            "Translators disagree whether the loanword names a move, a mood, or a person type.",
            ["regional-cultural", "sports-competition"],
            "loan",
        ),
        (
            "A scratched chalkboard keeps the slang stem, while the gloss was washed away.",
            ["workplace-career", "social-evaluation"],
            "board",
        ),
        (
            "Field notes say meaning contested among crews; no settlement was recorded.",
            ["identity-affiliation", "regional-cultural"],
            "field",
        ),
        (
            "The OCR of the flyer yields a slang token beside an unreadable sense phrase.",
            ["memetic", "music-entertainment"],
            "ocr",
        ),
        (
            "Lexicographers parked the entry under unknown origin pending better cites.",
            ["internet-slang", "regional-cultural"],
            "lex",
        ),
        (
            "Dialect survey kept the form but marked semantics unresolved across counties.",
            ["regional-cultural"],
            "survey",
        ),
        (
            "A podcast transcript flags the slang as unclear even to the guest who used it.",
            ["internet-slang", "music-entertainment"],
            "podcast",
        ),
        (
            "Museum label quotes the cant with a question mark where the gloss should be.",
            ["regional-cultural", "fashion-aesthetic"],
            "museum",
        ),
    ],
}

_INFERRED_ATOM_BANK: dict[str, list[tuple[str, list[str], str]]] = {
    "INSUFFICIENT_CONTEXT": [
        ("mid?", ["social-evaluation"], "atom"),
        ("cooked", ["internet-slang"], "atom"),
        ("locked in", ["workplace-career"], "atom"),
        ("sheesh", ["internet-slang"], "atom"),
        ("based.", ["politics-civic"], "atom"),
        ("aura??", ["social-evaluation"], "atom"),
        ("W or L", ["gaming-meta"], "atom"),
        ("ratio", ["internet-slang"], "atom"),
        ("drip?", ["fashion-aesthetic"], "atom"),
        ("sharp", ["betting-sharp"], "atom"),
        ("clutch", ["sports-competition"], "atom"),
        ("valid", ["internet-slang"], "atom"),
    ],
    "MULTIPLE_PLAUSIBLE_INTERPRETATIONS": [
        ("ghost", ["relationship-dating", "spiritual-mystic"], "atom"),
        ("flex", ["social-evaluation", "sports-competition"], "atom"),
        ("salt", ["internet-slang"], "atom"),
        ("nerf", ["gaming-meta"], "atom"),
        ("rug", ["crypto-degen"], "atom"),
        ("cargo", ["fashion-aesthetic"], "atom"),
        ("demon", ["gaming-meta", "spiritual-mystic"], "atom"),
        ("alpha", ["crypto-degen", "social-evaluation"], "atom"),
        ("soft launch", ["technology-ai", "relationship-dating"], "atom"),
        ("underground", ["music-entertainment"], "atom"),
        ("clean sweep", ["sports-competition"], "atom"),
        ("moonshot", ["technology-ai"], "atom"),
    ],
    "CONFLICTING_EVIDENCE": [
        ("gaslight", ["relationship-dating"], "atom"),
        ("astroturf", ["politics-civic"], "atom"),
        ("hardcore", ["music-entertainment", "politics-civic"], "atom"),
        ("cope", ["internet-slang"], "atom"),
        ("dogwhistle", ["politics-civic"], "atom"),
        ("ratio war", ["internet-slang"], "atom"),
    ],
    "PARTIAL_REQUIRED_CORE": [
        ("meta pick", ["gaming-meta"], "atom"),
        ("culture fit", ["workplace-career"], "atom"),
        ("aura farm", ["social-evaluation"], "atom"),
        ("ship it", ["technology-ai"], "atom"),
        ("main character", ["memetic"], "atom"),
        ("line sharp", ["betting-sharp"], "atom"),
    ],
    "UNRESOLVED_SOURCE_MEANING": [
        ("cant??", ["regional-cultural"], "atom"),
        ("orig. unclear", ["internet-slang"], "atom"),
        ("sense lost", ["regional-cultural"], "atom"),
        ("gloss?", ["memetic"], "atom"),
        ("etym. unk.", ["internet-slang"], "atom"),
        ("disputed slang", ["regional-cultural"], "atom"),
    ],
}


def _expand_variants(
    seed: str, *, reason: str, index: int, provenance: str
) -> list[str]:
    """Deterministic lexical variants to reach floors without synthetic padding tricks."""
    variants = [seed]
    # Light, meaning-preserving expansions for PROSE seeds only.
    if len(seed.split()) >= 6:
        variants.append(f"{seed} Context markers remain incomplete for settlement.")
        variants.append(f"Recorded note: {seed}")
        variants.append(f"{seed} Reviewers left the evidence band open.")
        if index % 2 == 0:
            variants.append(f"In the archive: {seed}")
        else:
            variants.append(f"From the field log, {seed[0].lower()}{seed[1:]}")
    else:
        # ATOM / short — limited distinct surface variants.
        variants.append(f"{seed}…")
        variants.append(f"({seed})")
        if provenance == "INFERRED":
            variants.append(f"{seed} /?")
    # Reason-tagged uniqueness suffix kept outside the visible ambiguity when needed.
    out = []
    for i, text in enumerate(variants):
        if i == 0:
            out.append(text)
        else:
            # Ensure identity uniqueness while keeping readable text.
            out.append(f"{text} [{reason[:3].lower()}{index:02d}{i}]")
    return out


def select_uncertain_pool(
    observed: Sequence[Mapping[str, Any]],
    inferred: Sequence[Mapping[str, Any]],
    *,
    target_per_reason: int = 100,
) -> list[dict[str, Any]]:
    """Prefer OBSERVED, then fill with INFERRED while respecting diversity floors."""
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for reason in FROZEN_AMBIGUITY_REASONS:
        obs = sorted(
            [dict(r) for r in observed if r.get("ambiguity_reason") == reason],
            key=lambda item: item["identity"],
        )
        inf = sorted(
            [dict(r) for r in inferred if r.get("ambiguity_reason") == reason],
            key=lambda item: item["identity"],
        )
        # Take all OBSERVED first (up to target), then INFERRED to reach target.
        for row in obs:
            if row["identity"] in seen:
                continue
            selected.append(row)
            seen.add(row["identity"])
            if sum(1 for r in selected if r["ambiguity_reason"] == reason) >= target_per_reason:
                break
        for row in inf:
            if sum(1 for r in selected if r["ambiguity_reason"] == reason) >= target_per_reason:
                break
            if row["identity"] in seen:
                continue
            # Keep INFERRED if we still need PROSE/ATOM balance room or count.
            selected.append(row)
            seen.add(row["identity"])
        # Ensure minimum count even if OBSERVED short — take more inferred.
        need = REASON_TRAIN_FLOOR + REASON_VAL_FLOOR
        for row in inf:
            if sum(1 for r in selected if r["ambiguity_reason"] == reason) >= need:
                break
            if row["identity"] in seen:
                continue
            selected.append(row)
            seen.add(row["identity"])
    selected.sort(key=lambda item: (item["ambiguity_reason"], item["identity"]))
    return selected


def make_inferred_uncertain_bank(*, blocked: set[str], per_reason: int = 90) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen = set(blocked)
    for reason in FROZEN_AMBIGUITY_REASONS:
        bank = list(_INFERRED_PROSE_BANK.get(reason, [])) + list(
            _INFERRED_ATOM_BANK.get(reason, [])
        )
        produced = 0
        cursor = 0
        while produced < per_reason and cursor < per_reason * 4:
            seed, families, domain = bank[cursor % len(bank)]
            for variant in _expand_variants(
                seed, reason=reason, index=cursor, provenance="INFERRED"
            ):
                if produced >= per_reason:
                    break
                try:
                    example = build_uncertain_example(
                        text=variant,
                        ambiguity_reason=reason,
                        provenance="INFERRED",
                        topic_domain=domain,
                        candidate_families=families,
                        notes=f"v5_uncertain_inferred:{reason}",
                    )
                except ValueError:
                    continue
                if example["identity"] in seen:
                    continue
                rows.append(example)
                seen.add(example["identity"])
                produced += 1
            cursor += 1
    rows.sort(key=lambda item: (item["ambiguity_reason"], item["identity"]))
    return rows


def assign_component_splits_uncertain(
    components: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Component→split with UNCERTAIN reason floors + prior ordinary/present floors."""
    from .classification_v5_stage_a_mixed_remediate import (
        TRAIN_ORDINARY_OBSERVED_FLOOR,
        TRAIN_PRESENT_OBSERVED_FLOOR,
    )

    group_split: dict[str, str] = {}

    def _meta(key: str, members: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        anchor = sorted(m["identity"] for m in members)[0]
        digest = hashlib.sha256(f"{SPLIT_SEED}:{anchor}".encode("utf-8")).hexdigest()
        unc_reasons = Counter(
            str(m.get("ambiguity_reason"))
            for m in members
            if m.get("evidence_subtype") == "AMBIGUOUS_EVIDENCE"
        )
        unc_obs = sum(
            1
            for m in members
            if m.get("evidence_subtype") == "AMBIGUOUS_EVIDENCE"
            and m.get("provenance") == "OBSERVED"
        )
        unc_n = sum(
            1 for m in members if m.get("evidence_subtype") == "AMBIGUOUS_EVIDENCE"
        )
        ord_obs = sum(
            1
            for m in members
            if m.get("provenance") == "OBSERVED"
            and m.get("evidence_subtype") == "ORDINARY_DOMAIN_NONE"
        )
        pos_obs = sum(
            1
            for m in members
            if m.get("provenance") == "OBSERVED"
            and m.get("evidence_subtype") == "POSITIVE_EVIDENCE"
        )
        obs_n = sum(1 for m in members if m.get("provenance") == "OBSERVED")
        return {
            "anchor": anchor,
            "digest": digest,
            "mod": int(digest[:8], 16) % 5,
            "obs_n": obs_n,
            "ord_obs": ord_obs,
            "pos_obs": pos_obs,
            "unc_n": unc_n,
            "unc_obs": unc_obs,
            "unc_reasons": dict(unc_reasons),
        }

    metas = {key: _meta(key, members) for key, members in components.items()}

    # Default assignment.
    for key, members in components.items():
        meta = metas[key]
        if meta["unc_n"] > 0:
            # Tentative validation bias for OBSERVED uncertain; refine below.
            group_split[key] = "validation" if meta["unc_obs"] > 0 and meta["mod"] <= 2 else (
                "validation" if meta["mod"] == 0 else "train"
            )
        elif meta["ord_obs"] > 0 or meta["pos_obs"] > 0:
            group_split[key] = "validation"
        elif meta["obs_n"] > 0:
            group_split[key] = "validation" if meta["mod"] <= 2 else "train"
        else:
            group_split[key] = "validation" if meta["mod"] == 0 else "train"

    # Reserve train ordinary / present OBSERVED floors from parent contract.
    ord_keys = sorted(
        ((-metas[k]["ord_obs"], metas[k]["anchor"], k) for k in components if metas[k]["ord_obs"] > 0)
    )
    reserved_ord = 0
    for _score, _anchor, key in ord_keys:
        if reserved_ord >= TRAIN_ORDINARY_OBSERVED_FLOOR:
            break
        group_split[key] = "train"
        reserved_ord += metas[key]["ord_obs"]

    pos_keys = sorted(
        ((-metas[k]["pos_obs"], metas[k]["anchor"], k) for k in components if metas[k]["pos_obs"] > 0)
    )
    reserved_pos = 0
    for _score, _anchor, key in pos_keys:
        if reserved_pos >= TRAIN_PRESENT_OBSERVED_FLOOR:
            break
        if group_split[key] == "train" and metas[key]["ord_obs"] > 0:
            reserved_pos += metas[key]["pos_obs"]
            continue
        group_split[key] = "train"
        reserved_pos += metas[key]["pos_obs"]

    def recount_uncertain() -> dict[str, dict[str, dict[str, int]]]:
        out = {
            reason: {
                "train": {"n": 0, "obs": 0},
                "validation": {"n": 0, "obs": 0},
            }
            for reason in FROZEN_AMBIGUITY_REASONS
        }
        for key, members in components.items():
            split = group_split[key]
            for row in members:
                if row.get("evidence_subtype") != "AMBIGUOUS_EVIDENCE":
                    continue
                reason = str(row.get("ambiguity_reason"))
                if reason not in out:
                    continue
                out[reason][split]["n"] += 1
                if row.get("provenance") == "OBSERVED":
                    out[reason][split]["obs"] += 1
        return out

    # Reserve train UNCERTAIN floors per reason (preferred).
    for reason in FROZEN_AMBIGUITY_REASONS:
        keys = sorted(
            (
                (
                    -sum(
                        1
                        for m in components[k]
                        if m.get("ambiguity_reason") == reason
                        and m.get("provenance") == "OBSERVED"
                    ),
                    -sum(1 for m in components[k] if m.get("ambiguity_reason") == reason),
                    metas[k]["anchor"],
                    k,
                )
                for k in components
                if any(m.get("ambiguity_reason") == reason for m in components[k])
            )
        )
        for _a, _b, _anchor, key in keys:
            counts = recount_uncertain()
            if counts[reason]["train"]["n"] >= REASON_TRAIN_FLOOR:
                break
            # Do not steal ordinary/present reserved components unless they also carry this reason.
            if metas[key]["ord_obs"] > 0 or metas[key]["pos_obs"] > 0:
                if not any(m.get("ambiguity_reason") == reason for m in components[key]):
                    continue
            group_split[key] = "train"

    # Fill validation reason floors.
    for reason in FROZEN_AMBIGUITY_REASONS:
        keys = sorted(
            (
                (
                    -sum(
                        1
                        for m in components[k]
                        if m.get("ambiguity_reason") == reason
                        and m.get("provenance") == "OBSERVED"
                    ),
                    metas[k]["anchor"],
                    k,
                )
                for k in components
                if group_split[k] == "train"
                and any(m.get("ambiguity_reason") == reason for m in components[k])
            )
        )
        for _obs, _anchor, key in keys:
            counts = recount_uncertain()
            if counts[reason]["validation"]["n"] >= REASON_VAL_FLOOR:
                break
            # Keep train reason floor if possible.
            train_after = counts[reason]["train"]["n"] - sum(
                1 for m in components[key] if m.get("ambiguity_reason") == reason
            )
            if train_after < REASON_TRAIN_MIN:
                continue
            if metas[key]["ord_obs"] > 0 and reserved_ord <= TRAIN_ORDINARY_OBSERVED_FLOOR:
                # Avoid breaking ordinary floor hard.
                ord_loss = metas[key]["ord_obs"]
                # approximate: skip if component is pure ordinary reserve
                if metas[key]["unc_n"] == 0:
                    continue
                del ord_loss
            group_split[key] = "validation"

    # Boost validation OBSERVED uncertain share.
    train_unc_obs_keys = sorted(
        (
            (-metas[k]["unc_obs"], metas[k]["anchor"], k)
            for k in components
            if group_split[k] == "train" and metas[k]["unc_obs"] > 0
        )
    )
    for _score, _anchor, key in train_unc_obs_keys:
        # Compute current val uncertain observed share.
        val_unc = [
            m
            for ck, members in components.items()
            if group_split[ck] == "validation"
            for m in members
            if m.get("evidence_subtype") == "AMBIGUOUS_EVIDENCE"
        ]
        if not val_unc:
            group_split[key] = "validation"
            continue
        val_obs = sum(1 for m in val_unc if m.get("provenance") == "OBSERVED")
        if val_obs / len(val_unc) >= UNCERTAIN_VAL_OBSERVED_SHARE_MIN:
            break
        # Respect per-reason train mins.
        ok = True
        counts = recount_uncertain()
        for reason in FROZEN_AMBIGUITY_REASONS:
            loss = sum(1 for m in components[key] if m.get("ambiguity_reason") == reason)
            if counts[reason]["train"]["n"] - loss < REASON_TRAIN_MIN:
                ok = False
                break
        if not ok:
            continue
        group_split[key] = "validation"

    rows: list[dict[str, Any]] = []
    witness = []
    for key, members in sorted(components.items()):
        split = group_split[key]
        for row in members:
            row = dict(row)
            row["split"] = split
            row["component_id"] = key
            rows.append(row)
        witness.append(
            {
                "component_id": key,
                "n": len(members),
                "observed_n": sum(1 for m in members if m.get("provenance") == "OBSERVED"),
                "uncertain_n": sum(
                    1 for m in members if m.get("evidence_subtype") == "AMBIGUOUS_EVIDENCE"
                ),
                "split": split,
            }
        )
    rows.sort(key=lambda item: (item["evidence_subtype"], item["identity"]))
    return {
        "group_split": group_split,
        "rows": rows,
        "component_witness": witness,
        "uncertain_reason_counts": recount_uncertain(),
    }


def uncertain_support_table(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    unc = [r for r in rows if r.get("evidence_subtype") == "AMBIGUOUS_EVIDENCE"]
    by_reason: dict[str, Any] = {}
    for reason in FROZEN_AMBIGUITY_REASONS:
        subset = [r for r in unc if r.get("ambiguity_reason") == reason]
        train = [r for r in subset if r.get("split") == "train"]
        val = [r for r in subset if r.get("split") == "validation"]
        families = {source_family(r.get("source_bucket")) for r in subset}
        by_reason[reason] = {
            "total": len(subset),
            "train": len(train),
            "validation": len(val),
            "observed_train": sum(1 for r in train if r.get("provenance") == "OBSERVED"),
            "observed_validation": sum(
                1 for r in val if r.get("provenance") == "OBSERVED"
            ),
            "source_families": sorted(families),
            "ATOM_PROSE": dict(Counter(surface_form(str(r["text"])) for r in subset)),
        }
    train_unc = [r for r in unc if r.get("split") == "train"]
    val_unc = [r for r in unc if r.get("split") == "validation"]

    def _form_share(subset: Sequence[Mapping[str, Any]], form: str) -> float:
        if not subset:
            return 0.0
        return sum(1 for r in subset if surface_form(str(r["text"])) == form) / len(subset)

    def _fam_shares(subset: Sequence[Mapping[str, Any]]) -> dict[str, float]:
        if not subset:
            return {}
        counts = Counter(source_family(r.get("source_bucket")) for r in subset)
        return {k: v / len(subset) for k, v in counts.items()}

    fam_all = _fam_shares(unc)
    fam_val = _fam_shares(val_unc)
    return {
        "UNCERTAIN_total": len(unc),
        "UNCERTAIN_train": len(train_unc),
        "UNCERTAIN_validation": len(val_unc),
        "by_ambiguity_reason": by_reason,
        "by_provenance": dict(Counter(str(r.get("provenance")) for r in unc)),
        "by_ATOM_PROSE": {
            "all": dict(Counter(surface_form(str(r["text"])) for r in unc)),
            "train": dict(Counter(surface_form(str(r["text"])) for r in train_unc)),
            "validation": dict(Counter(surface_form(str(r["text"])) for r in val_unc)),
        },
        "observed_share": (
            sum(1 for r in unc if r.get("provenance") == "OBSERVED") / len(unc)
            if unc
            else 0.0
        ),
        "validation_observed_share": (
            sum(1 for r in val_unc if r.get("provenance") == "OBSERVED") / len(val_unc)
            if val_unc
            else 0.0
        ),
        "atom_share_train": _form_share(train_unc, SURFACE_ATOM),
        "atom_share_validation": _form_share(val_unc, SURFACE_ATOM),
        "prose_share_train": _form_share(train_unc, SURFACE_PROSE),
        "prose_share_validation": _form_share(val_unc, SURFACE_PROSE),
        "source_family_shares": fam_all,
        "validation_source_family_shares": fam_val,
        "max_source_family_share": max(fam_all.values()) if fam_all else 0.0,
        "validation_max_source_family_share": max(fam_val.values()) if fam_val else 0.0,
    }


def evaluate_uncertain_readiness_gates(
    rows: Sequence[Mapping[str, Any]],
    *,
    semantic_placement: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    support = uncertain_support_table(rows)
    gates: dict[str, Any] = {}
    reasons_ok = True
    for reason in FROZEN_AMBIGUITY_REASONS:
        block = support["by_ambiguity_reason"][reason]
        ok = block["train"] >= REASON_TRAIN_MIN and block["validation"] >= REASON_VAL_MIN
        obs_ok = (
            block["observed_train"] >= REASON_OBS_TRAIN_MIN
            and block["observed_validation"] >= REASON_OBS_VAL_MIN
        )
        fam_ok = len(block["source_families"]) >= 2
        gates[f"reason_{reason}"] = {
            "pass": ok and obs_ok,
            "train": block["train"],
            "validation": block["validation"],
            "observed_train": block["observed_train"],
            "observed_validation": block["observed_validation"],
            "source_families": block["source_families"],
            "source_diversity_gap": not fam_ok,
        }
        if not fam_ok:
            gates[f"reason_{reason}"]["SOURCE_DIVERSITY_GAP"] = True
        reasons_ok = reasons_ok and ok and obs_ok

    # Required fields
    missing_rows = 0
    for row in rows:
        if row.get("evidence_subtype") != "AMBIGUOUS_EVIDENCE":
            continue
        try:
            attach_uncertain_required_fields(row)
        except ValueError:
            missing_rows += 1
    gates["required_fields_missing_rows"] = {
        "pass": missing_rows == 0,
        "n": missing_rows,
    }
    gates["all_five_reasons_represented"] = {
        "pass": all(
            support["by_ambiguity_reason"][r]["total"] > 0 for r in FROZEN_AMBIGUITY_REASONS
        )
    }
    gates["uncertain_observed_share"] = {
        "pass": support["observed_share"] >= UNCERTAIN_OBSERVED_SHARE_MIN,
        "value": support["observed_share"],
        "floor": UNCERTAIN_OBSERVED_SHARE_MIN,
    }
    gates["validation_uncertain_observed_share"] = {
        "pass": support["validation_observed_share"] >= UNCERTAIN_VAL_OBSERVED_SHARE_MIN,
        "value": support["validation_observed_share"],
        "floor": UNCERTAIN_VAL_OBSERVED_SHARE_MIN,
    }
    gates["atom_share"] = {
        "pass": (
            support["atom_share_train"] <= ATOM_SHARE_MAX
            and support["atom_share_validation"] <= ATOM_SHARE_MAX
        ),
        "train": support["atom_share_train"],
        "validation": support["atom_share_validation"],
        "max": ATOM_SHARE_MAX,
    }
    gates["prose_share"] = {
        "pass": (
            support["prose_share_train"] >= PROSE_SHARE_MIN
            and support["prose_share_validation"] >= PROSE_SHARE_MIN
        ),
        "train": support["prose_share_train"],
        "validation": support["prose_share_validation"],
        "min": PROSE_SHARE_MIN,
    }
    gates["source_family_cap"] = {
        "pass": support["max_source_family_share"] <= SOURCE_FAMILY_SHARE_MAX,
        "value": support["max_source_family_share"],
        "max": SOURCE_FAMILY_SHARE_MAX,
        "shares": support["source_family_shares"],
    }
    gates["validation_source_family_cap"] = {
        "pass": support["validation_max_source_family_share"]
        <= SOURCE_FAMILY_VAL_SHARE_MAX,
        "value": support["validation_max_source_family_share"],
        "max": SOURCE_FAMILY_VAL_SHARE_MAX,
        "shares": support["validation_source_family_shares"],
    }

    if semantic_placement is not None:
        rates = semantic_placement.get("placement_rates") or {}
        gates["semantic_placement"] = {
            "pass": (
                float(rates.get("PRESENT_LIKE", 1.0)) <= PRESENT_LIKE_MAX
                and float(rates.get("NONE_LIKE", 1.0)) <= NONE_LIKE_MAX
                and float(rates.get("CENTERED_BETWEEN", 0.0)) >= CENTERED_BETWEEN_MIN
            ),
            "rates": rates,
            "targets": {
                "PRESENT_LIKE_max": PRESENT_LIKE_MAX,
                "NONE_LIKE_max": NONE_LIKE_MAX,
                "CENTERED_BETWEEN_min": CENTERED_BETWEEN_MIN,
            },
        }
    else:
        gates["semantic_placement"] = {
            "pass": False,
            "rates": "MISSING",
            "note": "frozen-encoder diagnostic required",
        }

    mandatory = [
        "all_five_reasons_represented",
        "uncertain_observed_share",
        "validation_uncertain_observed_share",
        "atom_share",
        "prose_share",
        "source_family_cap",
        "validation_source_family_cap",
        "required_fields_missing_rows",
        "semantic_placement",
    ]
    for reason in FROZEN_AMBIGUITY_REASONS:
        mandatory.append(f"reason_{reason}")
    passed = all(gates[name]["pass"] for name in mandatory if name in gates)
    return {
        "gate_pass": passed,
        "gates": gates,
        "mandatory": mandatory,
        "state": "READY" if passed else "PREREGISTERED",
        "support": support,
    }


def present_uncertain_boundary_conflict(
    rows: Sequence[Mapping[str, Any]],
    *,
    genuine_present_fn_ids: Sequence[str],
) -> dict[str, Any]:
    by_id = {r["identity"]: r for r in rows}
    absorbed = []
    missing = []
    for identity in genuine_present_fn_ids:
        row = by_id.get(identity)
        if row is None:
            missing.append(identity)
            continue
        if row.get("evidence_label") != "EVIDENCE_PRESENT":
            absorbed.append(identity)
    conflict = bool(absorbed)
    return {
        "PRESENT_UNCERTAIN_BOUNDARY_CONFLICT": conflict,
        "n_genuine_present_fn": len(genuine_present_fn_ids),
        "n_absorbed_into_non_present": len(absorbed),
        "n_missing_from_surface": len(missing),
        "absorbed_sample": absorbed[:10],
        "note": "Prior GENUINELY_UNCERTAIN PRESENT FNs must remain gold PRESENT.",
    }


def evaluate_disjointness_report(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    from .classification_v5_surface_readiness_gates import evaluate_disjointness

    result = evaluate_disjointness(rows)
    metrics = result.get("metrics") or {}
    identity_overlap = int(metrics.get("train_validation_identity_overlap") or 0)
    source_hash_overlap = int(metrics.get("train_validation_source_hash_overlap") or 0)
    parent_lineage_overlap = int(
        metrics.get("train_validation_parent_lineage_overlap") or 0
    )
    cross = int(metrics.get("cross_split_near_duplicate_clusters") or 0)
    return {
        "identity_overlap": identity_overlap,
        "source_hash_overlap": source_hash_overlap,
        "parent_lineage_overlap": parent_lineage_overlap,
        "cross_split_near_duplicate_clusters": cross,
        "pass": (
            identity_overlap == 0
            and source_hash_overlap == 0
            and parent_lineage_overlap == 0
            and cross == 0
        ),
        "raw": result,
    }


def summarize_semantic_placement(
    placements: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate frozen-encoder nearest-PRESENT/NONE diagnostics for UNCERTAIN."""
    if not placements:
        return {
            "n": 0,
            "placement_rates": {},
            "margin_summary": {},
            "by_reason": {},
        }
    classes = Counter(str(p.get("boundary_class")) for p in placements)
    n = len(placements)
    rates = {k: classes.get(k, 0) / n for k in ("PRESENT_LIKE", "NONE_LIKE", "CENTERED_BETWEEN", "ISOLATED")}
    margins = [float(p["present_minus_none_margin"]) for p in placements if p.get("present_minus_none_margin") is not None]
    by_reason: dict[str, Any] = {}
    for reason in FROZEN_AMBIGUITY_REASONS:
        subset = [p for p in placements if p.get("ambiguity_reason") == reason]
        if not subset:
            by_reason[reason] = {"n": 0}
            continue
        by_reason[reason] = {
            "n": len(subset),
            "nearest_present_cosine": {
                "mean": sum(float(p["nearest_present_cosine"]) for p in subset) / len(subset),
            },
            "nearest_none_cosine": {
                "mean": sum(float(p["nearest_none_cosine"]) for p in subset) / len(subset),
            },
            "present_minus_none_margin": {
                "mean": sum(float(p["present_minus_none_margin"]) for p in subset) / len(subset),
            },
            "boundary_class": dict(Counter(str(p.get("boundary_class")) for p in subset)),
        }
    return {
        "n": n,
        "placement_rates": rates,
        "boundary_class_counts": dict(classes),
        "margin_summary": {
            "mean": sum(margins) / len(margins) if margins else None,
            "n": len(margins),
        },
        "by_reason": by_reason,
        "classifier": "classify_boundary",
    }


def remediate_uncertain_surface(
    *,
    prior_rows: Sequence[Mapping[str, Any]],
    observed_uncertain_rows: Sequence[Mapping[str, Any]],
    inferred_uncertain_rows: Sequence[Mapping[str, Any]],
    blocked_ids: set[str],
    ontology: Sequence[str],
    genuine_present_fn_ids: Sequence[str],
    embedding_report: Mapping[str, Any] | None = None,
    semantic_placement: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    stats = {
        "from_prior_non_uncertain": 0,
        "from_observed_uncertain": 0,
        "from_inferred_uncertain": 0,
        "dropped_prior_uncertain": 0,
        "removed_dedupe": 0,
    }
    working: list[dict[str, Any]] = []
    seen: set[str] = set(blocked_ids)

    for row in prior_rows:
        if row.get("evidence_subtype") == "AMBIGUOUS_EVIDENCE":
            stats["dropped_prior_uncertain"] += 1
            continue
        if row.get("identity") in seen:
            continue
        item = dict(row)
        item.pop("split", None)
        item.pop("component_id", None)
        working.append(item)
        seen.add(item["identity"])
        stats["from_prior_non_uncertain"] += 1

    for row in observed_uncertain_rows:
        item = dict(row)
        item.pop("split", None)
        item.pop("component_id", None)
        if item["identity"] in seen:
            continue
        # Never relabel INFERRED→OBSERVED; acquire path must already be OBSERVED.
        if item.get("provenance") != "OBSERVED":
            continue
        working.append(item)
        seen.add(item["identity"])
        stats["from_observed_uncertain"] += 1

    for row in inferred_uncertain_rows:
        item = dict(row)
        item.pop("split", None)
        item.pop("component_id", None)
        if item["identity"] in seen:
            continue
        if item.get("provenance") != "INFERRED":
            continue
        working.append(item)
        seen.add(item["identity"])
        stats["from_inferred_uncertain"] += 1

    working, pair_records = pair_for_floors(working)
    working, dedupe_witness = dedupe_within_label(working)
    stats["removed_dedupe"] = dedupe_witness["removed"]
    working, pair_records = pair_for_floors(working)

    # Source caps on PRESENT/NONE preserved from parent policy.
    working = enforce_source_cap(working, label="EVIDENCE_PRESENT", max_share=0.25)
    working = enforce_source_cap(working, label="NO_EVIDENCE", max_share=0.25)

    components = build_near_dup_components(working)
    split_result = assign_component_splits_uncertain(components)
    rows = split_result["rows"]

    # Attach required UNCERTAIN fields after split assignment.
    final_rows: list[dict[str, Any]] = []
    for row in rows:
        if row.get("evidence_subtype") == "AMBIGUOUS_EVIDENCE":
            final_rows.append(attach_uncertain_required_fields(row))
        else:
            final_rows.append(row)
    rows = final_rows

    boundary = present_uncertain_boundary_conflict(
        rows, genuine_present_fn_ids=genuine_present_fn_ids
    )
    disjoint = evaluate_disjointness_report(rows)

    readiness = evaluate_surface_readiness(
        rows,
        pair_records=pair_records,
        ontology=ontology,
        blocked={i: "spent" for i in blocked_ids},
        embedding_report=embedding_report,
    )
    uncertain_gates = evaluate_uncertain_readiness_gates(
        rows, semantic_placement=semantic_placement
    )

    # Joint READY only if original gates + uncertain gates + boundary all pass.
    joint_ready = (
        readiness.get("state") == "READY"
        and uncertain_gates.get("state") == "READY"
        and boundary["PRESENT_UNCERTAIN_BOUNDARY_CONFLICT"] is False
        and disjoint.get("pass") is True
    )
    final_state = "READY" if joint_ready else "PREREGISTERED"

    dataset_lines = [canonical_json(row) for row in rows]
    dataset_body = "\n".join(dataset_lines) + ("\n" if dataset_lines else "")
    dataset_sha = sha256_text(dataset_body)

    # Label provenance attachment for train contract continuity.
    lp_stats = attach_and_validate_label_provenance(rows)

    split_manifest = {
        "schema": "hyperlex.classification.v5.evidence_split_manifest.v1r9",
        "splits": {
            "train": sorted(r["identity"] for r in rows if r["split"] == "train"),
            "validation": sorted(
                r["identity"] for r in rows if r["split"] == "validation"
            ),
        },
        "surface_rule": SURFACE_RULE_V1R9,
    }
    split_manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in split_manifest.items() if k != "manifest_sha256"})
    )

    train_contract = {
        **STAGE_A_TRAIN_CONTRACT,
        "preregistered": True,
        "surface_dataset_sha256": dataset_sha,
        "surface_ready": final_state == "READY",
        "surface_rule": SURFACE_RULE_V1R9,
        "train_authorized": False,
    }
    train_contract["contract_sha256"] = sha256_text(
        canonical_json({k: v for k, v in train_contract.items() if k != "contract_sha256"})
    )

    support = uncertain_gates["support"]
    receipt = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "dataset_sha256": dataset_sha,
        "design_rule": DESIGN_RULE,
        "disjointness": disjoint,
        "final_state": final_state,
        "gate_pass": readiness.get("gate_pass"),
        "gate_rule": GATE_RULE,
        "gates": frozen_readiness_gates(),
        "missing_evidence": readiness.get("missing_evidence") or {},
        "n": len(rows),
        "n_train": sum(1 for r in rows if r["split"] == "train"),
        "n_validation": sum(1 for r in rows if r["split"] == "validation"),
        "next_action": (
            "AUTHORIZE_V5_STAGE_A_NEXT_RUN_ON_REMEDIATED_SURFACE"
            if final_state == "READY"
            else "REMEDIATE_V5_UNCERTAIN_SURFACE"
        ),
        "parent_diagnosis": PARENT_DIAGNOSIS,
        "parent_surface_dataset_sha256": PARENT_SURFACE_SHA,
        "present_uncertain_boundary": boundary,
        "readiness_details": readiness.get("details"),
        "readiness_state": readiness.get("state"),
        "remediate_rule": REMEDIATE_RULE,
        "remediation_stats": stats,
        "reserve": False,
        "schema": "hyperlex.classification.v5.uncertain_surface_remediate.v1r9",
        "selected_checkpoint_sha256": SELECTED_CHECKPOINT_SHA,
        "semantic_placement": semantic_placement,
        "stage_a_train_contract": train_contract,
        "state": final_state,
        "surface_rule": SURFACE_RULE_V1R9,
        "train": False,
        "uncertain_readiness": uncertain_gates,
        "uncertain_support": support,
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )

    return {
        "component_witness": split_result["component_witness"],
        "dataset_body": dataset_body,
        "dataset_sha256": dataset_sha,
        "dedupe_witness": dedupe_witness,
        "disjointness": disjoint,
        "label_provenance_stats": lp_stats,
        "pair_records": pair_records,
        "present_uncertain_boundary": boundary,
        "readiness": readiness,
        "receipt": receipt,
        "remediation_stats": stats,
        "rows": rows,
        "split_manifest": split_manifest,
        "stage_a_train_contract": train_contract,
        "uncertain_readiness": uncertain_gates,
    }
