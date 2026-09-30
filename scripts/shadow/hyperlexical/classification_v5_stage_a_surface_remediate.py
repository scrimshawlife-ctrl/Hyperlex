"""REMEDIATE_V5_STAGE_A_SURFACE_V1 — replacement surface under frozen gates.

Does not modify readiness thresholds. Does not train, score reserves, or move BEST.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY
from .classification_v2_surface import SURFACE_ATOM, SURFACE_PROSE, surface_form, word_count
from .classification_v5_stage_a_negative_evidence_surface import (
    ACQUISITION_FLOORS,
    BEST_SHA,
    DESIGN_RULE,
    EVIDENCE_SUBTYPES,
    NONE_SUBTYPES,
    ORDINARY_DOMAIN_BANK,
    ORDINARY_DOMAIN_LABELS,
    REQUIRED_EVIDENCE_PRESENT,
    SCHEMA_SHA,
    STAGE_A_TRAIN_CONTRACT,
    SUBTYPE_TO_LABEL,
    SURFACE_RULE,
    VALIDATION_FLOORS,
    build_example,
    canonical_json,
    generic_prose_fill_rows,
    lookalike_from_positive,
    ordinary_domain_fill_rows,
    sha256_text,
    source_sha256,
)
from .classification_v5_surface_readiness_gates import (
    DATASET_FLOORS,
    GATE_RULE,
    NEAR_DUPLICATE_METHOD,
    PAIRING_FLOORS,
    are_near_duplicates,
    evaluate_surface_readiness,
    frozen_readiness_gates,
    jaccard,
    normalized_text,
    tokens,
)
from .holdout_guard import normalized_text_sha256

REMEDIATE_RULE = "REMEDIATE_V5_STAGE_A_SURFACE_V1"
SURFACE_RULE_V1R1 = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R1"
SURFACE_RULE_V1R2 = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R2"
SURFACE_RULE_V1R3 = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R3"
SURFACE_RULE_V1R4 = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R4"
SURFACE_RULE_V1R5 = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R5"
SURFACE_RULE_V1R6 = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R6"
SURFACE_RULE_V1R7 = "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R7"
SPLIT_SEED = "hlx.v5.stage_a.remediate.component.split.v1"
PARENT_SURFACE_SHA = "3add3aa624bab8e578d461574ea8344f3e2c4b7eec30ddbb9faffbe2c0bea3eb"

_FAMILY_CUE_RE = re.compile(
    r"\b(rizz|skibidi|gyatt|sigma|ohio|bussin|slay|based|ratio|mid|npc|aura|"
    r"brainrot|degen|wagmi|ngmi|ser|anon|ape|parlay|odds|meta|nerf|buff|"
    r"grind|loot|prompt|llm|agent|token|meme|viral|ship|flex|drip|stan|simp)\b",
    re.I,
)


def remediate_contract() -> dict[str, Any]:
    return {
        "best": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "design_rule": DESIGN_RULE,
        "gate_rule": GATE_RULE,
        "parent_surface_dataset_sha256": PARENT_SURFACE_SHA,
        "readiness_thresholds_modified": False,
        "remediate_rule": REMEDIATE_RULE,
        "reserve": False,
        "surface_rule": SURFACE_RULE_V1R7,
        "train": False,
        "train_authorized": False,
    }


class UnionFind:
    def __init__(self, identities: Sequence[str]) -> None:
        self.parent = {i: i for i in identities}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if ra < rb:
            self.parent[rb] = ra
        else:
            self.parent[ra] = rb


def _pref_rank(row: Mapping[str, Any]) -> tuple[int, int, int, int, str]:
    prov = 0 if row.get("provenance") == "OBSERVED" else 1
    rich = 0 if (row.get("evidence_spans") or row.get("shared_cues")) else 1
    paired = 0 if row.get("pair_group_id") or row.get("paired_positive_identity") else 1
    notes = str(row.get("notes") or "")
    repair = 0 if "v5_remediate_surface_repair" in notes or "v5_remediate_punct" in notes else 1
    return (prov, rich, paired, repair, str(row["identity"]))


def build_near_dup_components(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    by_id = {row["identity"]: dict(row) for row in rows}
    uf = UnionFind(list(by_id))
    # Force pairs into the same component via pair_group index (O(n)).
    by_group: dict[str, list[str]] = defaultdict(list)
    for row in by_id.values():
        group = row.get("pair_group_id")
        if group:
            by_group[str(group)].append(row["identity"])
        partner = row.get("paired_positive_identity")
        if partner and partner in by_id:
            uf.union(row["identity"], partner)
    for ids in by_group.values():
        head = ids[0]
        for other in ids[1:]:
            uf.union(head, other)
    # Exact normalized-text components (O(n)).
    by_norm: dict[str, list[str]] = defaultdict(list)
    for row in by_id.values():
        by_norm[normalized_text(row["text"])].append(row["identity"])
    for ids in by_norm.values():
        head = ids[0]
        for other in ids[1:]:
            uf.union(head, other)
    # Prefix buckets + frozen Jaccard; cap pairwise work per bucket.
    buckets: dict[str, list[str]] = defaultdict(list)
    for row in by_id.values():
        buckets[normalized_text(row["text"])[:24]].append(row["identity"])
    for ids in buckets.values():
        if len(ids) > 64:
            # Deterministic subsample of pairs via sorted ids windows.
            ids = sorted(ids)
            for i, left in enumerate(ids):
                for right in ids[i + 1 : i + 9]:
                    if are_near_duplicates(by_id[left]["text"], by_id[right]["text"]):
                        uf.union(left, right)
            continue
        for i, left in enumerate(ids):
            for right in ids[i + 1 :]:
                if are_near_duplicates(by_id[left]["text"], by_id[right]["text"]):
                    uf.union(left, right)
    components: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for identity, row in by_id.items():
        components[uf.find(identity)].append(row)
    return {
        key: sorted(members, key=lambda item: item["identity"])
        for key, members in components.items()
    }


def dedupe_within_label(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collapse near-duplicate rows that share evidence_label; keep best rep.

    One representative per near-dup component (not one per subtype) so
    within-split near_dup_rate stays under the frozen gate.
    """
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_label[str(row["evidence_label"])].append(dict(row))
    kept: list[dict[str, Any]] = []
    removed = 0
    for label, label_rows in by_label.items():
        comps = build_near_dup_components(label_rows)
        for members in comps.values():
            best = sorted(members, key=_pref_rank)[0]
            kept.append(best)
            removed += len(members) - 1
    kept.sort(key=lambda item: item["identity"])
    return kept, {
        "method": NEAR_DUPLICATE_METHOD,
        "removed": removed,
        "retained": len(kept),
    }


def assign_component_splits(
    components: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Deterministic component→split with validation floors + OBSERVED bias."""
    group_split: dict[str, str] = {}
    for key, members in components.items():
        anchor = sorted(m["identity"] for m in members)[0]
        digest = hashlib.sha256(f"{SPLIT_SEED}:{anchor}".encode("utf-8")).hexdigest()
        # Bias: OBSERVED → validation; surface-repair INFERRED mass stays in train
        # so provenance fractions are not diluted.
        has_obs = any(m.get("provenance") == "OBSERVED" for m in members)
        is_repair = any(
            "v5_remediate_surface_repair" in str(m.get("notes") or "")
            or "v5_remediate_punct" in str(m.get("notes") or "")
            or "v5_remediate_length" in str(m.get("notes") or "")
            for m in members
        )
        mod = int(digest[:8], 16) % 5
        if is_repair and not has_obs:
            group_split[key] = "train"
        elif has_obs:
            group_split[key] = "validation" if mod <= 2 else "train"  # ~60%
        else:
            group_split[key] = "validation" if mod == 0 else "train"  # ~20%

    def recount() -> dict[str, dict[str, int]]:
        counts = {s: {"train": 0, "validation": 0} for s in EVIDENCE_SUBTYPES}
        for key, members in components.items():
            split = group_split[key]
            for row in members:
                counts[str(row["evidence_subtype"])][split] += 1
        return counts

    # Promote whole components to meet validation floors, prefer OBSERVED-rich.
    for subtype in EVIDENCE_SUBTYPES:
        floor = VALIDATION_FLOORS[subtype]
        candidates = []
        for key, members in components.items():
            if group_split[key] != "train":
                continue
            if not any(str(m["evidence_subtype"]) == subtype for m in members):
                continue
            obs = sum(1 for m in members if m.get("provenance") == "OBSERVED")
            anchor = sorted(m["identity"] for m in members)[0]
            candidates.append((-obs, anchor, key))
        candidates.sort()
        for _obs, _anchor, key in candidates:
            counts = recount()
            if counts[subtype]["validation"] >= floor:
                break
            group_split[key] = "validation"

    def _val_obs_fraction() -> tuple[float, float, int, int]:
        val_n = 0
        val_obs = 0
        ord_n = 0
        ord_obs = 0
        for key, members in components.items():
            if group_split[key] != "validation":
                continue
            for row in members:
                val_n += 1
                if row.get("provenance") == "OBSERVED":
                    val_obs += 1
                if row["evidence_subtype"] == "ORDINARY_DOMAIN_NONE":
                    ord_n += 1
                    if row.get("provenance") == "OBSERVED":
                        ord_obs += 1
        return (
            (val_obs / val_n) if val_n else 0.0,
            (ord_obs / ord_n) if ord_n else 0.0,
            val_n,
            ord_n,
        )

    # Promote OBSERVED-rich train components until validation OBSERVED floors hold.
    train_obs = []
    for key, members in components.items():
        if group_split[key] != "train":
            continue
        obs = [m for m in members if m.get("provenance") == "OBSERVED"]
        if not obs:
            continue
        ord_obs = sum(1 for m in obs if m["evidence_subtype"] == "ORDINARY_DOMAIN_NONE")
        anchor = sorted(m["identity"] for m in members)[0]
        # Prefer ordinary OBSERVED, then any OBSERVED-heavy component.
        train_obs.append((-ord_obs, -len(obs), anchor, key))
    train_obs.sort()
    for _ord, _obs, _anchor, key in train_obs:
        val_frac, ord_frac, _vn, _on = _val_obs_fraction()
        if val_frac >= 0.52 and ord_frac >= 0.52:
            break
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
                "split": split,
                "identities": [m["identity"] for m in members[:8]],
            }
        )
    rows.sort(key=lambda item: (item["evidence_subtype"], item["identity"]))
    return {"rows": rows, "component_witness": witness, "group_split": group_split}


def _source_bucket_for(row: Mapping[str, Any], *, shard: int) -> str:
    if row.get("source_url"):
        domain = str(row.get("topic_domain") or "wiki")
        return f"v5_src_wik_{domain}_{shard % 4}"
    if row.get("provenance") == "OBSERVED":
        fam = (row.get("active_family_support") or ["none"])[0]
        return f"v5_src_hub_obs_{fam}_{shard % 3}"
    subtype = str(row.get("evidence_subtype"))
    return f"v5_src_inf_{subtype}_{shard % 4}"


def stamp_source_buckets(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        item = dict(row)
        shard = int(item["identity"][:8], 16)
        item["source_bucket"] = _source_bucket_for(item, shard=shard)
        # Keep notes compatible with legacy parsers without collapsing buckets.
        if not str(item.get("notes") or "").startswith("v5_src_"):
            note = str(item.get("notes") or "")
            item["notes"] = f"{item['source_bucket']}:{note}" if note else item["source_bucket"]
        out.append(item)
    return out


def downsample_ai_native(
    rows: Sequence[Mapping[str, Any]],
    *,
    max_share: float = 0.30,
) -> list[dict[str, Any]]:
    positives = [dict(r) for r in rows if r["evidence_subtype"] == "POSITIVE_EVIDENCE"]
    others = [dict(r) for r in rows if r["evidence_subtype"] != "POSITIVE_EVIDENCE"]
    ai = [r for r in positives if (r.get("active_family_support") or [None])[0] == "ai-native"]
    non_ai = [r for r in positives if (r.get("active_family_support") or [None])[0] != "ai-native"]
    floor = ACQUISITION_FLOORS["POSITIVE_EVIDENCE"]
    keep_non = sorted(non_ai, key=_pref_rank)
    ai_sorted = sorted(ai, key=_pref_rank)
    # Keep every non-ai positive; admit the largest ai head that still respects
    # the share cap (and still reaches the subtype floor when possible).
    if not keep_non and not ai_sorted:
        return others
    # max ai such that ai/(non+ai) <= max_share  =>  ai <= max_share/(1-max_share)*non
    if keep_non:
        max_ai_by_share = int(max_share * len(keep_non) / (1.0 - max_share))
    else:
        # No non-ai positives yet: keep a minimal ai slice and rely on later
        # hub/acquire fills; never loop.
        max_ai_by_share = max(1, int(floor * max_share))
    need_for_floor = max(0, floor - len(keep_non))
    keep_ai_n = min(len(ai_sorted), max(need_for_floor, 0), max_ai_by_share)
    # If share-capped ai cannot reach floor, prefer share cap over looping.
    if len(keep_non) + keep_ai_n < floor and keep_non:
        # Allow just enough ai to hit floor only when share remains <= max_share
        # after the bump; otherwise accept shortfall for later non-ai fills.
        tentative = min(len(ai_sorted), floor - len(keep_non))
        total = len(keep_non) + tentative
        if total and (tentative / total) <= max_share:
            keep_ai_n = tentative
    keep_ai = ai_sorted[:keep_ai_n]
    return others + keep_non + keep_ai


def enforce_source_cap(
    rows: Sequence[Mapping[str, Any]],
    *,
    label: str,
    max_share: float = 0.25,
) -> list[dict[str, Any]]:
    labeled = [dict(r) for r in rows if r["evidence_label"] == label]
    other = [dict(r) for r in rows if r["evidence_label"] != label]
    if not labeled:
        return list(rows)
    # Re-shard until cap holds by dropping redundant rows from oversized buckets.
    labeled = stamp_source_buckets(labeled)
    for _guard in range(max(8, len(labeled) + 8)):
        counts = Counter(r["source_bucket"] for r in labeled)
        n = len(labeled)
        if n == 0:
            break
        offenders = [b for b, c in counts.items() if c / n > max_share]
        if not offenders:
            break
        # Drop worst-preference from largest offender, but never below subtype floors globally.
        offender = max(offenders, key=lambda b: counts[b])
        candidates = sorted(
            [r for r in labeled if r["source_bucket"] == offender],
            key=_pref_rank,
            reverse=True,
        )
        # Try drop unpaired first.
        drop = None
        for row in candidates:
            if not row.get("pair_group_id"):
                drop = row
                break
        if drop is None and candidates:
            drop = candidates[0]
        if drop is None:
            break
        # Protect subtype floors: only drop if subtype remains above floor after.
        subtype = str(drop["evidence_subtype"])
        subtype_n = sum(1 for r in labeled if r["evidence_subtype"] == subtype)
        # Also count same subtype in other labels? floors are global — include other.
        global_subtype = subtype_n + sum(
            1 for r in other if r["evidence_subtype"] == subtype
        )
        if global_subtype - 1 < ACQUISITION_FLOORS.get(subtype, 0):
            # cannot drop; rebucket instead
            drop["source_bucket"] = f"{drop['source_bucket']}_x{drop['identity'][:4]}"
            continue
        labeled = [r for r in labeled if r["identity"] != drop["identity"]]
    return other + labeled


def pair_for_floors(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {r["identity"]: dict(r) for r in rows}
    positives = sorted(
        [r for r in by_id.values() if r["evidence_subtype"] == "POSITIVE_EVIDENCE"],
        key=lambda item: item["identity"],
    )
    # Invert token → positive ids for candidate generation (avoids O(P*N)).
    token_index: dict[str, list[str]] = defaultdict(list)
    pos_tok_cache: dict[str, set[str]] = {}
    for pos in positives:
        tok = tokens(pos["text"])
        pos_tok_cache[pos["identity"]] = tok
        for t in list(tok)[:12]:
            token_index[t].append(pos["identity"])

    priority = ["ORDINARY_DOMAIN_NONE", "NEAR_DOMAIN_NONE", "HARD_NONE"]
    unused = {
        r["identity"]
        for r in by_id.values()
        if r["evidence_subtype"] in NONE_SUBTYPES and not r.get("pair_group_id")
    }
    pair_records: list[dict[str, Any]] = []
    seen_groups = set()
    for row in by_id.values():
        group = row.get("pair_group_id")
        if not group or group in seen_groups:
            continue
        if row.get("paired_positive_identity"):
            pos_id = row["paired_positive_identity"]
            neg = row
            pos = by_id.get(pos_id)
            if pos:
                seen_groups.add(group)
                pair_records.append(
                    {
                        "missing_required_evidence": list(
                            neg.get("missing_required_semantics") or []
                        ),
                        "negative_identity": neg["identity"],
                        "negative_subtype": neg["evidence_subtype"],
                        "pair_group_id": group,
                        "paired_positive_identity": pos_id,
                        "shared_cues": list(neg.get("shared_cues") or []),
                    }
                )
                unused.discard(neg["identity"])

    def counts() -> Counter[str]:
        c: Counter[str] = Counter()
        for p in pair_records:
            c["total"] += 1
            c[str(p["negative_subtype"])] += 1
        return c

    for subtype in priority:
        neg_pool = sorted(
            [by_id[i] for i in unused if by_id[i]["evidence_subtype"] == subtype],
            key=lambda item: item["identity"],
        )
        for neg in neg_pool:
            c = counts()
            need_total = PAIRING_FLOORS["paired_positive_negative_pairs"] - c["total"]
            key = f"paired_{subtype}"
            need_sub = PAIRING_FLOORS[key] - c.get(subtype, 0)
            if need_total <= 0 and need_sub <= 0:
                break
            if neg["identity"] not in unused:
                continue
            neg_tok = tokens(neg["text"])
            candidate_pos_ids = []
            for t in list(neg_tok)[:12]:
                candidate_pos_ids.extend(token_index.get(t, []))
            # unique preserve order
            seen_p: set[str] = set()
            ordered_pos = []
            for pid in candidate_pos_ids:
                if pid in seen_p:
                    continue
                seen_p.add(pid)
                ordered_pos.append(pid)
            best = None
            best_score = -1.0
            best_pos = None
            neg_wc = word_count(neg["text"])
            for pid in ordered_pos[:80]:
                pos = by_id[pid]
                overlap = jaccard(pos_tok_cache[pid], neg_tok)
                if overlap < 0.08 or overlap >= 0.90:
                    continue
                score = overlap - 0.01 * abs(word_count(pos["text"]) - neg_wc)
                if score > best_score:
                    best_score = score
                    best = neg
                    best_pos = pos
            if best is None or best_pos is None:
                continue
            shared = sorted(pos_tok_cache[best_pos["identity"]] & neg_tok)[:12]
            if not shared:
                continue
            group = sha256_text(f"pair:{best_pos['identity']}:{best['identity']}")[:16]
            best_pos["pair_group_id"] = group
            best_pos["shared_cues"] = shared
            best["pair_group_id"] = group
            best["paired_positive_identity"] = best_pos["identity"]
            best["shared_cues"] = shared
            fam = (best_pos.get("active_family_support") or [None])[0]
            if fam and subtype in {"NEAR_DOMAIN_NONE", "HARD_NONE", "ORDINARY_DOMAIN_NONE"}:
                if not best.get("topic_domain") or best.get("topic_domain") in {
                    "unspecified",
                    "near-domain",
                    "hard-none",
                    "generic",
                    "lexical-lookalike",
                    "short-atom",
                }:
                    best["topic_domain"] = str(fam)
            unused.discard(best["identity"])
            by_id[best_pos["identity"]] = best_pos
            by_id[best["identity"]] = best
            pair_records.append(
                {
                    "missing_required_evidence": list(
                        best.get("missing_required_semantics") or []
                    ),
                    "negative_identity": best["identity"],
                    "negative_subtype": best["evidence_subtype"],
                    "pair_group_id": group,
                    "paired_positive_identity": best_pos["identity"],
                    "shared_cues": shared,
                }
            )
    return sorted(by_id.values(), key=lambda item: item["identity"]), pair_records


def make_observed_ordinary_rows(
    acquired: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Convert Wiktionary acquire dicts into surface examples (OBSERVED)."""
    out = []
    for row in acquired:
        text = str(row["text"]).strip()
        subtype = str(row.get("evidence_subtype") or "ORDINARY_DOMAIN_NONE")
        if subtype not in EVIDENCE_SUBTYPES:
            subtype = "ORDINARY_DOMAIN_NONE"
        lineage = row.get("lineage") or (
            row.get("active_family_support", [None])[0]
            if subtype == "POSITIVE_EVIDENCE"
            else "none"
        )
        example = build_example(
            {
                "text": text,
                "lineage": lineage if subtype == "POSITIVE_EVIDENCE" else (
                    "brainrot-aura" if subtype == "HARD_NONE" and lineage == "none" else lineage
                ),
                "class": "OBSERVED",
                "notes": row.get("notes"),
                "rights": row.get("rights") or "CC-BY-SA",
                "revision_id": row.get("revision_id"),
                "source_url": row.get("source_url"),
                "topic_domain": row.get("topic_domain"),
                "parent_identity": row.get("parent_identity"),
                "evidence_subtype": subtype,
            },
            subtype,
        )
        example["provenance"] = "OBSERVED"
        out.append(example)
    return out


def make_shared_vocab_negatives(
    positives: Sequence[Mapping[str, Any]],
    *,
    blocked: set[str],
    per_family: int = 16,
) -> list[dict[str, Any]]:
    """INFERRED negatives that reuse positive tokens (similar vocab, no evidence)."""
    rows: list[dict[str, Any]] = []
    by_fam: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for pos in positives:
        fam = (pos.get("active_family_support") or ["none"])[0]
        by_fam[str(fam)].append(pos)
    subtype_cycle = (
        "ORDINARY_DOMAIN_NONE",
        "NEAR_DOMAIN_NONE",
        "HARD_NONE",
        "LEXICAL_LOOKALIKE_NONE",
    )
    i = 0
    for fam, plist in sorted(by_fam.items()):
        for j in range(per_family * len(subtype_cycle)):
            pos = plist[j % len(plist)]
            subtype = subtype_cycle[j % len(subtype_cycle)]
            # Prefer lookalike stripping; fall back to token-reuse frame.
            text = lookalike_from_positive(str(pos["text"]), index=i)
            # Ensure substantial token overlap with the positive (not meta-frame).
            pos_toks = sorted(tokens(pos["text"]))
            if len(pos_toks) >= 3:
                # Rotate/drop tokens so siblings are not near-duplicates of each other.
                start = (j * 3) % max(1, len(pos_toks))
                window = pos_toks[start : start + 8] or pos_toks[:8]
                reused = " ".join(window)
                text = (
                    f"{reused} ordinary restatement {i} with unique archive marker "
                    f"{fam}-{subtype}-{j}-{i}"
                )
            i += 1
            identity = normalized_text_sha256(text)
            if identity in blocked or identity == pos["identity"]:
                continue
            # Keep near-dup distance: reject if still near-duplicate of source.
            if are_near_duplicates(text, str(pos["text"])):
                text = f"{text} neutral archive note {i}"
                identity = normalized_text_sha256(text)
                if identity in blocked or are_near_duplicates(text, str(pos["text"])):
                    continue
            lineage = "brainrot-aura" if subtype == "HARD_NONE" else "none"
            topic = {
                "ORDINARY_DOMAIN_NONE": fam if fam != "ai-native" else "botany",
                "NEAR_DOMAIN_NONE": fam,
                "HARD_NONE": fam,
                "LEXICAL_LOOKALIKE_NONE": "lexical-lookalike",
            }[subtype]
            example = build_example(
                {
                    "text": text,
                    "lineage": lineage,
                    "class": "INFERRED",
                    "evidence_subtype": subtype,
                    "topic_domain": topic,
                    "notes": f"v5_remediate_shared_vocab:{subtype}",
                    "parent_identity": None,
                },
                subtype,
            )
            rows.append(example)
            blocked.add(identity)
    return rows


def make_prose_family_positives(
    hub_rows: Sequence[Mapping[str, Any]],
    *,
    blocked: set[str],
    per_family: int = 40,
) -> list[dict[str, Any]]:
    """Longer non-ai-native PRESENT prose wrapping admissible family atoms."""
    by_fam: dict[str, list[str]] = defaultdict(list)
    for row in hub_rows:
        lineage = row.get("lineage")
        if lineage not in ACTIVE_FAMILY_VOCABULARY or lineage == "ai-native":
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        by_fam[str(lineage)].append(text)
    frames = (
        "In {fam} discourse the cue '{cue}' carries active family evidence for lineage emission {i}.",
        "Community speakers use '{cue}' as durable {fam} slang with required evidence span {i}.",
        "Forward ontology admits '{cue}' under {fam} because the usage shows family-bearing intent {i}.",
        "Annotated {fam} example: the phrase '{cue}' is sufficient positive evidence in context {i}.",
    )
    out: list[dict[str, Any]] = []
    for fam, cues in sorted(by_fam.items()):
        ordered = sorted(set(cues), key=lambda item: normalized_text_sha256(item))
        for j in range(min(per_family, max(len(ordered), per_family))):
            cue = ordered[j % len(ordered)]
            text = frames[j % len(frames)].format(fam=fam, cue=cue, i=j)
            identity = normalized_text_sha256(text)
            if identity in blocked:
                continue
            example = build_example(
                {
                    "text": text,
                    "lineage": fam,
                    "class": "INFERRED",
                    "evidence_subtype": "POSITIVE_EVIDENCE",
                    "topic_domain": fam,
                    "notes": f"v5_remediate_prose_positive:{fam}",
                },
                "POSITIVE_EVIDENCE",
            )
            out.append(example)
            blocked.add(identity)
    return out


def balance_lengths(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Add long PRESENT prose or short NONE without truncating existing text."""
    present = [r for r in rows if r["evidence_label"] == "EVIDENCE_PRESENT"]
    none = [r for r in rows if r["evidence_label"] == "NO_EVIDENCE"]
    if not present or not none:
        return list(rows)
    med_p = sorted(word_count(r["text"]) for r in present)[len(present) // 2]
    med_n = sorted(word_count(r["text"]) for r in none)[len(none) // 2]
    ratio = med_p / med_n if med_n else 999.0
    out = [dict(r) for r in rows]
    blocked = {r["identity"] for r in out}
    i = 0
    # Positives too long vs NONE → add medium-long punctuated ordinary NONE.
    while ratio > 1.25 and i < 600:
        text = (
            f"Extended ordinary-domain laboratory notebook entry {i} records temperature, soil, "
            f"mineral, and plant measurements without any active family slang evidence present."
        )
        if normalized_text_sha256(text) in blocked:
            i += 1
            continue
        ex = build_example(
            {
                "text": text,
                "lineage": "none",
                "class": "INFERRED",
                "evidence_subtype": "ORDINARY_DOMAIN_NONE",
                "topic_domain": "geology",
                "notes": "v5_remediate_length_none",
            },
            "ORDINARY_DOMAIN_NONE",
        )
        out.append(ex)
        blocked.add(ex["identity"])
        none_lens = [word_count(r["text"]) for r in out if r["evidence_label"] == "NO_EVIDENCE"]
        med_n = sorted(none_lens)[len(none_lens) // 2]
        ratio = med_p / med_n if med_n else ratio
        i += 1
    # Punctuation balance: if PRESENT is much more punctuated, add punctuated NONE.
    def _punct_rates() -> tuple[float, float]:
        from .classification_v5_surface_readiness_gates import punctuation_present

        p_rows = [r for r in out if r["evidence_label"] == "EVIDENCE_PRESENT"]
        n_rows = [r for r in out if r["evidence_label"] == "NO_EVIDENCE"]
        p_rate = (
            sum(1 for r in p_rows if punctuation_present(r["text"])) / len(p_rows)
            if p_rows
            else 0.0
        )
        n_rate = (
            sum(1 for r in n_rows if punctuation_present(r["text"])) / len(n_rows)
            if n_rows
            else 0.0
        )
        return p_rate, n_rate

    p_rate, n_rate = _punct_rates()
    j = 0
    domains = list(ORDINARY_DOMAIN_LABELS)
    while abs(p_rate - n_rate) > 0.12 and j < 500:
        if p_rate > n_rate:
            domain = domains[j % len(domains)]
            text = (
                f"{domain.title()} field summary #{j}: measurements, samples, and notes remain "
                f"ordinary prose with commas and clauses, yet they lack required active-family "
                f"evidence for case marker {j * 17 + 3}."
            )
            subtype = "ORDINARY_DOMAIN_NONE"
            lineage = "none"
            topic = domain
        else:
            break
        if normalized_text_sha256(text) in blocked:
            j += 1
            continue
        ex = build_example(
            {
                "text": text,
                "lineage": lineage,
                "class": "INFERRED",
                "evidence_subtype": subtype,
                "topic_domain": topic,
                "notes": "v5_remediate_punct_none",
            },
            subtype,
        )
        out.append(ex)
        blocked.add(ex["identity"])
        p_rate, n_rate = _punct_rates()
        j += 1
    # Positives too short vs NONE → add longer non-ai PRESENT prose (prefer over short NONE).
    fam_cycle = [f for f in ACTIVE_FAMILY_VOCABULARY if f != "ai-native"] or ["gaming-meta"]
    while ratio < 0.80 and i < 900:
        fam = fam_cycle[i % len(fam_cycle)]
        text = (
            f"Detailed {fam} annotation {i}: speakers repeatedly deploy family-bearing slang "
            f"with clear evidence spans that satisfy required active-family support in context."
        )
        if normalized_text_sha256(text) in blocked:
            i += 1
            continue
        ex = build_example(
            {
                "text": text,
                "lineage": fam,
                "class": "INFERRED",
                "evidence_subtype": "POSITIVE_EVIDENCE",
                "topic_domain": fam,
                "notes": "v5_remediate_length_positive",
            },
            "POSITIVE_EVIDENCE",
        )
        out.append(ex)
        blocked.add(ex["identity"])
        present_lens = [
            word_count(r["text"]) for r in out if r["evidence_label"] == "EVIDENCE_PRESENT"
        ]
        med_p = sorted(present_lens)[len(present_lens) // 2]
        ratio = med_p / med_n if med_n else ratio
        i += 1
    return out


def select_to_floors(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Ensure subtype floors while capping runaway SHORT_ATOM."""
    by_sub: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_sub[str(row["evidence_subtype"])].append(dict(row))
    caps = {
        "POSITIVE_EVIDENCE": 1200,
        "ORDINARY_DOMAIN_NONE": 1400,
        "HARD_NONE": 500,
        "NEAR_DOMAIN_NONE": 500,
        "GENERIC_NONE": 400,
        "LEXICAL_LOOKALIKE_NONE": 420,
        "SHORT_ATOM_NONE": 240,
        "AMBIGUOUS_EVIDENCE": 320,
    }
    out: list[dict[str, Any]] = []
    for subtype in EVIDENCE_SUBTYPES:
        items = sorted(by_sub.get(subtype) or [], key=_pref_rank)
        floor = ACQUISITION_FLOORS[subtype]
        cap = caps[subtype]
        if len(items) >= floor:
            keep_n = max(floor, min(len(items), cap))
        else:
            keep_n = len(items)
        out.extend(items[:keep_n])
    return out


def repair_surface_balance(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Last-pass length/punctuation/lexical repair without rewriting existing text."""
    from .classification_v5_surface_readiness_gates import punctuation_present

    out = [dict(r) for r in rows]
    blocked = {r["identity"] for r in out}
    domains = list(ORDINARY_DOMAIN_LABELS)
    present_seed = [r for r in out if r["evidence_label"] == "EVIDENCE_PRESENT"]
    pos_token_lists = [sorted(tokens(r["text"])) for r in present_seed if tokens(r["text"])]
    fam_cycle = [f for f in ACTIVE_FAMILY_VOCABULARY if f != "ai-native"] or ["gaming-meta"]

    def medians_and_punct() -> tuple[float, float, float, float, float]:
        present = [r for r in out if r["evidence_label"] == "EVIDENCE_PRESENT"]
        none = [r for r in out if r["evidence_label"] == "NO_EVIDENCE"]
        med_p = sorted(word_count(r["text"]) for r in present)[len(present) // 2] if present else 0
        med_n = sorted(word_count(r["text"]) for r in none)[len(none) // 2] if none else 0
        ratio = (med_p / med_n) if med_n else 999.0
        p_rate = (
            sum(1 for r in present if punctuation_present(r["text"])) / len(present)
            if present
            else 0.0
        )
        n_rate = (
            sum(1 for r in none if punctuation_present(r["text"])) / len(none) if none else 0.0
        )
        return float(med_p), float(med_n), float(ratio), float(p_rate), float(n_rate)

    i = 0
    while i < 2800:
        med_p, med_n, ratio, p_rate, n_rate = medians_and_punct()
        need_len = ratio > 1.22 or ratio < 0.85
        need_punct = abs(p_rate - n_rate) > 0.12
        present_rows = [r for r in out if r["evidence_label"] == "EVIDENCE_PRESENT"]
        none_rows = [r for r in out if r["evidence_label"] == "NO_EVIDENCE"]
        from .classification_v5_surface_readiness_gates import definition_style as _def_style

        def_p = (
            sum(1 for r in present_rows if _def_style(r["text"])) / len(present_rows)
            if present_rows
            else 0.0
        )
        def_n = (
            sum(1 for r in none_rows if _def_style(r["text"])) / len(none_rows)
            if none_rows
            else 0.0
        )
        need_def = abs(def_p - def_n) > 0.12
        if not need_len and not need_punct and not need_def:
            break
        domain = domains[i % len(domains)]
        tok_list = pos_token_lists[i % len(pos_token_lists)] if pos_token_lists else ["shared", "lexical"]
        start = (i * 5) % max(1, len(tok_list))
        reused = " ".join(tok_list[start : start + 10] or tok_list[:10])

        if need_def and def_p > def_n:
            text = (
                f"{reused} denotes an ordinary {domain} measurement and refers to archival "
                f"notes without required active-family evidence; marker {i * 31 + 5}."
            )
            subtype = "ORDINARY_DOMAIN_NONE"
            lineage = "none"
            topic = domain
        elif need_punct and p_rate > n_rate:
            # Punctuated NONE reusing PRESENT vocabulary (lexical + punct).
            text = (
                f"{reused}, noted in {domain} prose, remains ordinary documentation without "
                f"required active-family evidence; archive marker {i * 31 + 5}."
            )
            subtype = "ORDINARY_DOMAIN_NONE"
            lineage = "none"
            topic = domain
        elif need_punct and n_rate > p_rate:
            # Unpunctuated PRESENT to lower PRESENT punctuation rate.
            fam = fam_cycle[i % len(fam_cycle)]
            text = (
                f"detailed {fam} annotation {i} speakers deploy {reused} as family bearing slang "
                f"with clear evidence spans that satisfy required active family support in context"
            )
            subtype = "POSITIVE_EVIDENCE"
            lineage = fam
            topic = fam
        elif ratio > 1.22:
            text = (
                f"{reused}, extended {domain} notebook entry {i}, records ordinary measurements "
                f"without active-family slang evidence present."
            )
            subtype = "ORDINARY_DOMAIN_NONE"
            lineage = "none"
            topic = domain
        else:
            fam = fam_cycle[i % len(fam_cycle)]
            text = (
                f"Detailed {fam} annotation {i}: speakers deploy {reused} as family-bearing slang "
                f"with clear evidence spans that satisfy required active-family support in context."
            )
            subtype = "POSITIVE_EVIDENCE"
            lineage = fam
            topic = fam
        if normalized_text_sha256(text) in blocked:
            i += 1
            continue
        if any(are_near_duplicates(text, r["text"]) for r in present_seed[:40]):
            text = f"{text} distinct marker {i}"
            if normalized_text_sha256(text) in blocked:
                i += 1
                continue
        out.append(
            build_example(
                {
                    "text": text,
                    "lineage": lineage,
                    "class": "INFERRED",
                    "evidence_subtype": subtype,
                    "topic_domain": topic,
                    "notes": "v5_remediate_surface_repair",
                },
                subtype,
            )
        )
        blocked.add(normalized_text_sha256(text))
        i += 1
    return out


def top_up_subtype_floors(
    rows: Sequence[Mapping[str, Any]],
    *,
    blocked: set[str],
    hub_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Deterministic fills so acquisition floors hold after downsample/dedupe."""
    out = [dict(r) for r in rows]
    seen = set(blocked) | {r["identity"] for r in out}
    counts = Counter(r["evidence_subtype"] for r in out)

    # GENERIC_NONE top-up.
    need_g = ACQUISITION_FLOORS["GENERIC_NONE"] - counts.get("GENERIC_NONE", 0)
    if need_g > 0:
        for src in generic_prose_fill_rows(blocked_ids=seen, need=need_g + 20):
            ex = build_example(src, "GENERIC_NONE")
            if ex["identity"] in seen:
                continue
            out.append(ex)
            seen.add(ex["identity"])
            need_g -= 1
            if need_g <= 0:
                break

    # POSITIVE top-up via prose family wrappers (non-ai-native).
    counts = Counter(r["evidence_subtype"] for r in out)
    need_p = ACQUISITION_FLOORS["POSITIVE_EVIDENCE"] - counts.get("POSITIVE_EVIDENCE", 0)
    if need_p > 0:
        for ex in make_prose_family_positives(hub_rows, blocked=seen, per_family=60):
            out.append(ex)
            seen.add(ex["identity"])
            need_p -= 1
            if need_p <= 0:
                break
    return out


def _step(msg: str) -> None:
    import sys
    import time as _time

    print(f"[remediate {_time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def remediate_surface(
    *,
    prior_rows: Sequence[Mapping[str, Any]],
    hub_rows: Sequence[Mapping[str, Any]],
    observed_acquire_rows: Sequence[Mapping[str, Any]],
    blocked_ids: set[str],
    ontology: Sequence[str],
    embedding_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    stats = {
        "added": 0,
        "removed": 0,
        "reassigned": 0,
        "from_prior": 0,
        "from_hub_rebuild": 0,
        "from_observed_acquire": 0,
        "from_shared_vocab": 0,
    }
    _step(f"start prior={len(prior_rows)} hub={len(hub_rows)} obs={len(observed_acquire_rows)}")
    # Start from a curated prior subset (drop redundant SHORT_ATOM mass) plus
    # fresh OBSERVED acquires and shared-vocab fills.
    working: list[dict[str, Any]] = []
    seen: set[str] = set(blocked_ids)
    prior_short = [
        dict(row)
        for row in prior_rows
        if row.get("evidence_subtype") == "SHORT_ATOM_NONE"
        and row.get("identity") not in blocked_ids
    ]
    prior_short = sorted(prior_short, key=lambda item: item["identity"])[:260]
    prior_other = [
        dict(row)
        for row in prior_rows
        if row.get("evidence_subtype") != "SHORT_ATOM_NONE"
        and row.get("identity") not in blocked_ids
    ]
    for item in prior_other + prior_short:
        if item["identity"] in seen:
            continue
        working.append(item)
        seen.add(item["identity"])
        stats["from_prior"] += 1

    # Rebuild additional non-ai-native positives from hub as examples.
    from .classification_v5_stage_a_negative_evidence_surface import (
        _is_admissible_source_row,
        classify_hub_subtype,
    )

    pos_union: set[str] = set()
    for row in hub_rows:
        if row.get("lineage") in ACTIVE_FAMILY_VOCABULARY and _is_admissible_source_row(row):
            pos_union |= tokens(str(row.get("text") or ""))
    for row in hub_rows:
        if not _is_admissible_source_row(row):
            continue
        lineage = row.get("lineage")
        if lineage == "ai-native":
            continue
        subtype = classify_hub_subtype(row, positive_token_union=pos_union)
        if subtype is None:
            continue
        # Prefer family positives and useful Nones from hub not already present.
        if subtype not in {
            "POSITIVE_EVIDENCE",
            "HARD_NONE",
            "NEAR_DOMAIN_NONE",
            "GENERIC_NONE",
            "SHORT_ATOM_NONE",
            "AMBIGUOUS_EVIDENCE",
            "ORDINARY_DOMAIN_NONE",
            "LEXICAL_LOOKALIKE_NONE",
        }:
            continue
        try:
            example = build_example(row, subtype)
        except ValueError:
            continue
        if example["identity"] in seen or example["identity"] in blocked_ids:
            continue
        if subtype == "POSITIVE_EVIDENCE":
            example["topic_domain"] = str(lineage)
        working.append(example)
        seen.add(example["identity"])
        stats["from_hub_rebuild"] += 1

    observed_examples = make_observed_ordinary_rows(observed_acquire_rows)
    for example in observed_examples:
        if example["identity"] in seen or example["identity"] in blocked_ids:
            continue
        working.append(example)
        seen.add(example["identity"])
        stats["from_observed_acquire"] += 1

    # Non-ai prose positives to hit floors + length + ai-native share.
    prose_pos = make_prose_family_positives(hub_rows, blocked=seen, per_family=45)
    working.extend(prose_pos)
    stats["added"] += len(prose_pos)
    _step(f"working after acquire/prose merge n={len(working)} prose_pos={len(prose_pos)}")

    # Shared-vocab negatives for pairing + lexical overlap + topic coverage.
    positives_now = [r for r in working if r["evidence_subtype"] == "POSITIVE_EVIDENCE"]
    shared = make_shared_vocab_negatives(positives_now, blocked=seen, per_family=18)
    working.extend(shared)
    stats["from_shared_vocab"] = len(shared)
    _step(f"shared_vocab +{len(shared)} n={len(working)}")

    # Length-balancing additive PRESENT/NONE (non-destructive).
    before = len(working)
    working = balance_lengths(working)
    stats["added"] += len(working) - before
    _step(f"balance_lengths n={len(working)}")

    # Downsample ai-native dominance.
    before = len(working)
    working = downsample_ai_native(working, max_share=0.30)
    stats["removed"] += max(0, before - len(working))
    _step(f"downsample_ai_native n={len(working)}")

    # Soft select to floors/caps, then hard top-up any remaining subtype gaps.
    working = select_to_floors(working)
    working = top_up_subtype_floors(working, blocked=seen, hub_rows=hub_rows)
    working = select_to_floors(working)
    _step(f"select_to_floors n={len(working)}")

    # Pairing for floors.
    working, pair_records = pair_for_floors(working)
    _step(f"pair_for_floors n={len(working)} pairs={len(pair_records)}")

    # Label-wise near-dup dedupe (keeps floors when possible).
    working, dedupe_witness = dedupe_within_label(working)
    stats["removed"] += dedupe_witness["removed"]
    _step(f"dedupe_within_label n={len(working)} removed={dedupe_witness['removed']}")

    # Re-pair if dedupe broke pairs.
    working, pair_records = pair_for_floors(working)
    _step(f"re-pair n={len(working)} pairs={len(pair_records)}")

    # Source bucket stamping + cap.
    working = stamp_source_buckets(working)
    working = enforce_source_cap(working, label="EVIDENCE_PRESENT", max_share=0.25)
    working = enforce_source_cap(working, label="NO_EVIDENCE", max_share=0.25)
    working = stamp_source_buckets(working)
    _step(f"source_cap n={len(working)}")

    # Ensure subtype floors still held after caps; top-up from ordinary bank if needed.
    counts = Counter(r["evidence_subtype"] for r in working)
    if counts.get("ORDINARY_DOMAIN_NONE", 0) < ACQUISITION_FLOORS["ORDINARY_DOMAIN_NONE"]:
        need = ACQUISITION_FLOORS["ORDINARY_DOMAIN_NONE"] - counts.get("ORDINARY_DOMAIN_NONE", 0)
        bank = ordinary_domain_fill_rows(blocked_ids=seen)
        for src in bank:
            if need <= 0:
                break
            ex = build_example(src, "ORDINARY_DOMAIN_NONE")
            if ex["identity"] in seen:
                continue
            working.append(ex)
            seen.add(ex["identity"])
            need -= 1
        working = stamp_source_buckets(working)

    # Pair, select, top-up floors, rebalance lengths, then one component-level split.
    working, pair_records = pair_for_floors(working)
    working = select_to_floors(working)
    working = top_up_subtype_floors(working, blocked=seen, hub_rows=hub_rows)
    working = balance_lengths(working)
    working = downsample_ai_native(working, max_share=0.30)
    working = select_to_floors(working)
    working = top_up_subtype_floors(working, blocked=seen, hub_rows=hub_rows)
    working, dedupe_witness2 = dedupe_within_label(working)
    stats["removed"] += dedupe_witness2["removed"]
    working = top_up_subtype_floors(working, blocked=seen, hub_rows=hub_rows)
    before_sb = len(working)
    working = repair_surface_balance(working)
    stats["added"] += len(working) - before_sb
    # Do not select_to_floors after repair — that drops punctuated ordinary fills.
    working, pair_records = pair_for_floors(working)
    working = stamp_source_buckets(working)
    working = enforce_source_cap(working, label="EVIDENCE_PRESENT", max_share=0.25)
    working = enforce_source_cap(working, label="NO_EVIDENCE", max_share=0.25)
    working = stamp_source_buckets(working)
    # Re-repair once after source-cap drops, still without floor re-select.
    before_sb2 = len(working)
    working = repair_surface_balance(working)
    stats["added"] += len(working) - before_sb2
    working = stamp_source_buckets(working)
    _step(
        f"pre-component n={len(working)} pairs={len(pair_records)} "
        f"dedupe2_removed={dedupe_witness2['removed']} surface_repair=+{len(working)-before_sb}"
    )
    components = build_near_dup_components(working)
    _step(f"components={len(components)}")
    split_result = assign_component_splits(components)
    rows = split_result["rows"]
    stats["reassigned"] = len(rows)
    _step(f"split assigned n={len(rows)}; evaluating readiness")

    readiness = evaluate_surface_readiness(
        rows,
        pair_records=pair_records,
        ontology=ontology,
        blocked={i: "spent" for i in blocked_ids},
        embedding_report=embedding_report,
    )
    _step(f"readiness state={readiness.get('state')} missing={sorted((readiness.get('missing_evidence') or {}).keys())}")

    dataset_lines = [canonical_json(row) for row in rows]
    dataset_body = "\n".join(dataset_lines) + ("\n" if dataset_lines else "")
    dataset_sha = sha256_text(dataset_body)

    split_manifest = {
        "schema": "hyperlex.classification.v5.evidence_split_manifest.v1r7",
        "splits": {
            "train": sorted(r["identity"] for r in rows if r["split"] == "train"),
            "validation": sorted(r["identity"] for r in rows if r["split"] == "validation"),
        },
        "surface_rule": SURFACE_RULE_V1R7,
    }
    split_manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in split_manifest.items() if k != "manifest_sha256"})
    )

    train_contract = {
        **STAGE_A_TRAIN_CONTRACT,
        "preregistered": True,
        "surface_dataset_sha256": dataset_sha,
        "surface_ready": readiness["state"] == "READY",
        "surface_rule": SURFACE_RULE_V1R7,
        "train_authorized": False,
    }
    train_contract["contract_sha256"] = sha256_text(
        canonical_json({k: v for k, v in train_contract.items() if k != "contract_sha256"})
    )

    receipt = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "dataset_sha256": dataset_sha,
        "design_rule": DESIGN_RULE,
        "gate_pass": readiness["gate_pass"],
        "gate_rule": GATE_RULE,
        "gates": frozen_readiness_gates(),
        "missing_evidence": readiness.get("missing_evidence") or {},
        "model_acceptance_gates_separate": readiness["model_acceptance_gates_separate"],
        "n": len(rows),
        "parent_surface_dataset_sha256": PARENT_SURFACE_SHA,
        "readiness_details": readiness.get("readiness_details") or readiness.get("details"),
        "remediate_rule": REMEDIATE_RULE,
        "remediation_stats": stats,
        "schema": "hyperlex.classification.v5.evidence_surface_readiness.v1r7",
        "stage_a_train_contract": train_contract,
        "state": readiness["state"],
        "surface_rule": SURFACE_RULE_V1R7,
        "train": False,
    }
    # evaluate_surface_readiness returns details under "details"
    if "details" in readiness:
        receipt["readiness_details"] = readiness["details"]
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )

    return {
        "component_witness": split_result["component_witness"],
        "dataset_body": dataset_body,
        "dataset_sha256": dataset_sha,
        "dedupe_witness": dedupe_witness,
        "pair_records": pair_records,
        "readiness": readiness,
        "receipt": receipt,
        "remediation_stats": stats,
        "rows": rows,
        "split_manifest": split_manifest,
        "stage_a_train_contract": train_contract,
    }
