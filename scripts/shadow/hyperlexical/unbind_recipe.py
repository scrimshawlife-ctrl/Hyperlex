"""Hyperlexical unbind train recipe: morph hard-negs + OBSERVED upsample.

Train-loop multiplicity / sample weights only. Does not invent OBSERVED
gold in the SoT. ne0l0gist harvest is unchanged. name_gate stays false.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

UNBIND_OBSERVED_UPSAMPLE_ENV = "HYPERLEX_UNBIND_OBSERVED_UPSAMPLE"
UNBIND_INFERRED_CAP_ENV = "HYPERLEX_UNBIND_INFERRED_CAP"
UNBIND_INFERRED_WEIGHT_ENV = "HYPERLEX_UNBIND_INFERRED_WEIGHT"
UNBIND_MORPH_MARGIN_ENV = "HYPERLEX_UNBIND_MORPH_MARGIN"
UNBIND_FILLER_DENYLIST_ENV = "HYPERLEX_UNBIND_FILLER_DENYLIST"
UNBIND_FILLER_DENYLIST_PATH_ENV = "HYPERLEX_UNBIND_FILLER_DENYLIST_PATH"
UNBIND_HARD_ATOMS_PATH_ENV = "HYPERLEX_UNBIND_HARD_ATOMS_PATH"
UNBIND_HARD_UPSAMPLE_ENV = "HYPERLEX_UNBIND_HARD_UPSAMPLE"
UNBIND_OBSERVED_UPSAMPLE_DEFAULT = 1
# Extra copies of already-OBSERVED hard phrases after the normal upsample.
# 1 = identity (no extra). Operator JSONL is env-path only — not SoT gold.
UNBIND_HARD_UPSAMPLE_DEFAULT = 1
# 0 = off. Hard low caps starve morph-negs (do not default a cap).
UNBIND_INFERRED_CAP_DEFAULT = 0
# Soft scale on unbind loss for class != OBSERVED. 1.0 = identity.
# Prefer this over a hard INFERRED_CAP (Morph4 CAP=1000 lost).
UNBIND_INFERRED_WEIGHT_DEFAULT = 1.0
UNBIND_INFERRED_WEIGHT_MAX = 2.0
UNBIND_MORPH_MARGIN_DEFAULT = 0.5

# Seeded from civilian unbind failure themes (live5 + Morph1 + Morph3 dump).
# Surfaces only — pairing is gated to fillers already present on unbind
# rows (no new slang atoms). Merge, do not duplicate, existing clusters.
# Morph3 residual bleed: aped↔aping, fanum taxed↔tax/fanumtax, looksmaxxed↔
# looksmaxxing, rizzed↔rizz/rizzless, quiet quitter↔quitting, mewing↔mew*.
# vibe coded↔cooked is not a morph — do not pair.
MORPH_CLUSTERS: tuple[frozenset[str], ...] = (
    frozenset({"aped", "aping"}),
    frozenset({"looksmax", "looksmaxx", "looksmaxxing", "looksmaxxed", "looksmaxxer"}),
    frozenset({"rizz", "rizzed", "rizzless", "rizzing"}),
    frozenset({"fanum", "fanum tax", "fanumtax", "fanum taxed", "tax", "taxed"}),
    frozenset({"quiet quit", "quiet quitter", "quiet quitting"}),
    frozenset({"mew", "mewing", "mewed"}),
    frozenset({"crash", "crashed", "crashout"}),
    frozenset(
        {
            "aura",
            "aura farming",
            "aura farm",
            "aura farmed",
            "aura farmer",
            "aura points",
            "negative aura",
            "minus aura",
        }
    ),
)

# ``tax`` / ``taxed`` sit on the fanum cluster so gold-is-fanum* can take
# them as siblings. Gold ``tax`` / ``taxed`` must not pull fanum* — too broad.
_FANUM_BROAD_ONLY: frozenset[str] = frozenset({"tax", "taxed"})

# Longest-first inflectional / productive slang suffixes.
_AUTO_SUFFIXES = (
    "maxxing",
    "maxxed",
    "maxxer",
    "maxx",
    "xing",
    "ing",
    "ers",
    "er",
    "ed",
    "es",
    "s",
)


def _norm_surface(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def inflection_stem(token: str) -> str:
    """Conservative stem. Too-short leftovers stay the surface (no invent)."""
    t = _norm_surface(token)
    if " " in t or len(t) < 4:
        return t
    for suf in _AUTO_SUFFIXES:
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)]
    return t


def resolve_unbind_observed_upsample(raw: str | int | None = None) -> int:
    """Repeat factor for OBSERVED unbind train rows. Default 1. Fail-closed."""
    if raw is None:
        raw = os.environ.get(UNBIND_OBSERVED_UPSAMPLE_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return UNBIND_OBSERVED_UPSAMPLE_DEFAULT
    try:
        n = int(str(raw).strip(), 10)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{UNBIND_OBSERVED_UPSAMPLE_ENV} must be a positive int, got {raw!r}") from exc
    if n < 1:
        raise ValueError(f"{UNBIND_OBSERVED_UPSAMPLE_ENV} must be a positive int, got {n}")
    return n


def resolve_unbind_hard_upsample(raw: str | int | None = None) -> int:
    """Extra copies of matched OBSERVED hard atoms. Default 1 = none. Fail-closed."""
    if raw is None:
        raw = os.environ.get(UNBIND_HARD_UPSAMPLE_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return UNBIND_HARD_UPSAMPLE_DEFAULT
    try:
        n = int(str(raw).strip(), 10)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{UNBIND_HARD_UPSAMPLE_ENV} must be an int >= 1, got {raw!r}") from exc
    if n < 1:
        raise ValueError(f"{UNBIND_HARD_UPSAMPLE_ENV} must be an int >= 1, got {n}")
    return n


def resolve_unbind_hard_atoms_path(raw: str | Path | None = None) -> str:
    """Operator JSONL path. Empty default. Does not invent a file."""
    if raw is None:
        raw = os.environ.get(UNBIND_HARD_ATOMS_PATH_ENV)
    if raw is None or (isinstance(raw, str) and not str(raw).strip()):
        return ""
    return str(raw).strip()


def hard_atoms_receipt_path(path: str | Path | None) -> str:
    """Basename when a path is set; empty string otherwise."""
    token = str(path or "").strip()
    if not token:
        return ""
    return Path(token).name


def unbind_row_hard_atom_keys(row: Mapping[str, Any]) -> set[str]:
    """Normalized row text plus joined filler atom text. No invented surfaces."""
    keys: set[str] = set()
    text = _norm_surface(str(row.get("text") or ""))
    if text:
        keys.add(text)
    fillers = [str(item).strip() for item in (row.get("fillers") or []) if str(item).strip()]
    if fillers:
        joined = _norm_surface(" ".join(fillers))
        if joined:
            keys.add(joined)
    return keys


def unbind_row_matches_hard_atoms(row: Mapping[str, Any], atoms: Iterable[str]) -> bool:
    atom_set = {_norm_surface(str(item)) for item in atoms if _norm_surface(str(item))}
    if not atom_set:
        return False
    return bool(unbind_row_hard_atom_keys(row) & atom_set)


def load_hard_atom_texts(path: str | Path | None = None) -> frozenset[str]:
    """Load normalized ``text`` fields from operator JSONL. Fail-closed if set.

    Unset / empty path → empty set (identity). A configured path that is
    missing, unreadable, or invalid raises. Does not invent OBSERVED gold.
    """
    raw = resolve_unbind_hard_atoms_path(path)
    if not raw:
        return frozenset()
    p = Path(raw)
    if not p.is_file():
        raise ValueError(f"{UNBIND_HARD_ATOMS_PATH_ENV} is not a file: {p}")
    try:
        body = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"{UNBIND_HARD_ATOMS_PATH_ENV} is unreadable: {p}") from exc
    atoms: set[str] = set()
    for index, line in enumerate(body.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{UNBIND_HARD_ATOMS_PATH_ENV} line {index} is not valid JSON") from exc
        if not isinstance(obj, dict):
            raise ValueError(
                f"{UNBIND_HARD_ATOMS_PATH_ENV} line {index} must be a JSON object "
                "with a string text field"
            )
        if "text" not in obj:
            raise ValueError(
                f"{UNBIND_HARD_ATOMS_PATH_ENV} line {index} is missing required field 'text'"
            )
        raw_text = obj.get("text")
        if not isinstance(raw_text, str):
            raise ValueError(
                f"{UNBIND_HARD_ATOMS_PATH_ENV} line {index} field 'text' must be a string, "
                f"got {type(raw_text).__name__}"
            )
        norm = _norm_surface(raw_text)
        if not norm:
            raise ValueError(f"{UNBIND_HARD_ATOMS_PATH_ENV} line {index} has an empty text field")
        atoms.add(norm)
    return frozenset(atoms)


def hard_atom_upsample_stats(
    unbind_rows: Iterable[Mapping[str, Any]],
    *,
    hard_upsample: int,
    atoms: Iterable[str],
    path: str = "",
) -> dict[str, Any]:
    """Receipt counts. Only class==OBSERVED rows already in ``unbind_rows``."""
    atom_set = {_norm_surface(str(item)) for item in atoms if _norm_surface(str(item))}
    observed = [r for r in unbind_rows if r.get("class") == "OBSERVED"]
    matched_rows = [r for r in observed if unbind_row_matches_hard_atoms(r, atom_set)]
    hit_atoms: set[str] = set()
    for row in matched_rows:
        hit_atoms.update(unbind_row_hard_atom_keys(row) & atom_set)
    extra = 0
    if atom_set and hard_upsample > 1:
        extra = (hard_upsample - 1) * len(matched_rows)
    return {
        "unbind_hard_atoms_path": hard_atoms_receipt_path(path),
        "unbind_hard_upsample": hard_upsample,
        "n_unbind_hard_atoms_matched": len(hit_atoms),
        "n_unbind_hard_extra_copies": extra,
    }


def resolve_unbind_inferred_cap(raw: str | int | None = None) -> int:
    """Max INFERRED unbind train rows. 0 = off. Fail-closed.

    Hard low caps can starve morph-negs by dropping INFERRED rows that
    carry sibling fillers. Default stays off; do not ship a hard cap.
    """
    if raw is None:
        raw = os.environ.get(UNBIND_INFERRED_CAP_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return UNBIND_INFERRED_CAP_DEFAULT
    try:
        n = int(str(raw).strip(), 10)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{UNBIND_INFERRED_CAP_ENV} must be an int >= 0, got {raw!r}") from exc
    if n < 0:
        raise ValueError(f"{UNBIND_INFERRED_CAP_ENV} must be an int >= 0, got {n}")
    return n


def _parse_filler_denylist_obj(raw: Any, *, source: str) -> dict[str, frozenset[str]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{source} must be a JSON object of lineage → filler list")
    out: dict[str, frozenset[str]] = {}
    for key, val in raw.items():
        lineage = str(key).strip()
        if not lineage:
            raise ValueError(f"{source} has an empty lineage key")
        if not isinstance(val, list):
            raise ValueError(f"{source} value for {lineage!r} must be a list of surfaces")
        surfaces = {_norm_surface(str(item)) for item in val if _norm_surface(str(item))}
        if surfaces:
            out[lineage] = frozenset(surfaces)
    return out


def resolve_filler_denylist(
    raw: str | Mapping[str, Iterable[str]] | None = None,
    *,
    path: str | Path | None = None,
) -> dict[str, frozenset[str]]:
    """Per-lineage banned fillers for hard-neg / CE distractors only.

    Fail-closed empty default. Does not invent slang atoms. Invalid JSON or
    a missing path raises. Gold fillers are never stripped.
    """
    if raw is not None and not isinstance(raw, str):
        return _parse_filler_denylist_obj(dict(raw), source=UNBIND_FILLER_DENYLIST_ENV)
    text = raw
    if text is None:
        text = os.environ.get(UNBIND_FILLER_DENYLIST_ENV)
    path_raw = path
    if path_raw is None:
        path_raw = os.environ.get(UNBIND_FILLER_DENYLIST_PATH_ENV)
    if path_raw is not None and str(path_raw).strip():
        p = Path(str(path_raw).strip())
        if not p.is_file():
            raise ValueError(f"{UNBIND_FILLER_DENYLIST_PATH_ENV} is not a file: {p}")
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{UNBIND_FILLER_DENYLIST_PATH_ENV} is not valid JSON") from exc
        return _parse_filler_denylist_obj(loaded, source=str(p))
    if text is None or (isinstance(text, str) and not text.strip()):
        return {}
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{UNBIND_FILLER_DENYLIST_ENV} must be a JSON object") from exc
    return _parse_filler_denylist_obj(loaded, source=UNBIND_FILLER_DENYLIST_ENV)


def banned_fillers_for(
    lineage: str | None,
    denylist: Mapping[str, Iterable[str]] | None = None,
) -> frozenset[str]:
    if not lineage or not denylist:
        return frozenset()
    raw = denylist.get(lineage)
    if not raw:
        return frozenset()
    return frozenset(_norm_surface(str(x)) for x in raw if _norm_surface(str(x)))


def resolve_unbind_morph_margin(raw: str | float | int | None = None) -> float:
    """Margin for gold-vs-sibling filler ranking. Default 0.5. Fail-closed."""
    if raw is None:
        raw = os.environ.get(UNBIND_MORPH_MARGIN_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return UNBIND_MORPH_MARGIN_DEFAULT
    try:
        margin = float(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{UNBIND_MORPH_MARGIN_ENV} must be a finite number >= 0, got {raw!r}") from exc
    if margin < 0 or margin != margin or margin == float("inf"):
        raise ValueError(f"{UNBIND_MORPH_MARGIN_ENV} must be a finite number >= 0, got {raw!r}")
    return margin


def resolve_unbind_inferred_weight(raw: str | float | int | None = None) -> float:
    """Soft unbind loss scale for class != OBSERVED. Default 1.0. Fail-closed.

    Finite and in (0, 2]. Does not drop rows. Try 0.4–0.5 on Spark instead
    of a hard ``HYPERLEX_UNBIND_INFERRED_CAP`` (Morph4 CAP=1000 rejected).
    """
    if raw is None:
        raw = os.environ.get(UNBIND_INFERRED_WEIGHT_ENV)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return UNBIND_INFERRED_WEIGHT_DEFAULT
    try:
        weight = float(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{UNBIND_INFERRED_WEIGHT_ENV} must be a finite number in (0, 2], got {raw!r}"
        ) from exc
    if not math.isfinite(weight) or weight <= 0 or weight > UNBIND_INFERRED_WEIGHT_MAX:
        raise ValueError(
            f"{UNBIND_INFERRED_WEIGHT_ENV} must be a finite number in (0, 2], got {raw!r}"
        )
    return weight


def unbind_row_sample_weight(
    row: Mapping[str, Any],
    inferred_weight: float,
) -> float:
    """Per-row unbind scale. OBSERVED stays 1.0. Non-OBSERVED gets ``inferred_weight``.

    Scales CE + morph-margin for that row. Does not drop the row.
    """
    if row.get("class") == "OBSERVED":
        return 1.0
    return inferred_weight


def known_fillers(unbind_rows: Iterable[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for row in unbind_rows:
        for fill in row.get("fillers") or []:
            norm = _norm_surface(str(fill))
            if norm:
                out.add(norm)
    return out


def _is_fanum_lineage_surface(surface: str) -> bool:
    return _norm_surface(surface).startswith("fanum")


def _explicit_siblings(surface: str) -> set[str]:
    hit = _norm_surface(surface)
    out: set[str] = set()
    for cluster in MORPH_CLUSTERS:
        if hit in cluster:
            out.update(cluster)
    # Pair taxed only when gold is fanum* lineage. Standalone tax/taxed
    # must not pull fanum / fanum tax / fanumtax.
    if hit in _FANUM_BROAD_ONLY and not _is_fanum_lineage_surface(hit):
        out = {s for s in out if not _is_fanum_lineage_surface(s)}
    out.discard(hit)
    return out


def _auto_siblings(surface: str, known: set[str]) -> set[str]:
    """Same stem, different surface. Only surfaces already in ``known``."""
    hit = _norm_surface(surface)
    if not hit or " " in hit:
        return set()
    stem = inflection_stem(hit)
    if stem == hit and len(hit) < 4:
        return set()
    out: set[str] = set()
    for other in known:
        if other == hit or " " in other:
            continue
        if inflection_stem(other) == stem:
            out.add(other)
    return out


def hard_negatives_for(filler: str, known: Iterable[str]) -> list[str]:
    """Near-morph siblings that already exist as fillers. Never invents atoms.

    ``tax`` / ``taxed`` pair with fanum* only when gold is a fanum* surface.
    """
    known_set = {_norm_surface(x) for x in known if _norm_surface(x)}
    hit = _norm_surface(filler)
    if not hit or hit not in known_set:
        return []
    sibs = (_explicit_siblings(hit) | _auto_siblings(hit, known_set)) & known_set
    sibs.discard(hit)
    return sorted(sibs)


def distractor_fillers_for(
    filler: str,
    known: Iterable[str],
    *,
    lineage: str | None = None,
    denylist: Mapping[str, Iterable[str]] | None = None,
) -> list[str]:
    """Hard-neg / CE distractors. Denylist filters only; never invents atoms."""
    negs = hard_negatives_for(filler, known)
    banned = banned_fillers_for(lineage, denylist)
    if not banned:
        return negs
    return [n for n in negs if n not in banned]


def morph_pairs_for_rows(unbind_rows: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    """Contrastive (gold, neg) pairs from fillers already on the rows."""
    rows = list(unbind_rows)
    known = known_fillers(rows)
    pairs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        for fill in row.get("fillers") or []:
            gold = _norm_surface(str(fill))
            if not gold:
                continue
            explicit = _explicit_siblings(gold) & known
            auto = _auto_siblings(gold, known)
            for neg in hard_negatives_for(gold, known):
                key = (gold, neg)
                if key in seen:
                    continue
                seen.add(key)
                source = "explicit" if neg in explicit else "auto"
                if neg in explicit and neg in auto:
                    source = "explicit"
                pairs.append({"gold": gold, "neg": neg, "source": source})
    return pairs


def attach_hard_neg_fillers(
    unbind_rows: Iterable[dict[str, Any]],
    known: Iterable[str] | None = None,
    *,
    denylist: Mapping[str, Iterable[str]] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Copy rows and attach ``hard_neg_fillers``. Does not mint gold rows."""
    rows = list(unbind_rows)
    known_set = set(known) if known is not None else known_fillers(rows)
    known_set = {_norm_surface(x) for x in known_set if _norm_surface(x)}
    deny = denylist if denylist is not None else resolve_filler_denylist()
    out: list[dict[str, Any]] = []
    n_added = 0
    for row in rows:
        copy = dict(row)
        negs: list[str] = []
        seen_neg: set[str] = set()
        lineage = str(row.get("lineage") or "") or None
        for fill in row.get("fillers") or []:
            for neg in distractor_fillers_for(
                str(fill), known_set, lineage=lineage, denylist=deny
            ):
                if neg in seen_neg:
                    continue
                seen_neg.add(neg)
                negs.append(neg)
        copy["hard_neg_fillers"] = negs
        n_added += len(negs)
        out.append(copy)
    return out, n_added


def shape_unbind_train(
    unbind_rows: Iterable[dict[str, Any]],
    *,
    upsample: int | str | None = None,
    inferred_cap: int | str | None = None,
    known: Iterable[str] | None = None,
    denylist: Mapping[str, Iterable[str]] | None = None,
    hard_upsample: int | str | None = None,
    hard_atoms_path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Train-only recipe. Callers must not pass val/test rows.

    OBSERVED copies are loop multiplicity, not new SoT gold. INFERRED cap
    keeps first-seen order (no reshuffle). Hard-negs attach in memory.
    Hard-atom extras copy already-OBSERVED train rows only.
    """
    factor = resolve_unbind_observed_upsample(upsample)
    cap = resolve_unbind_inferred_cap(inferred_cap)
    hard_factor = resolve_unbind_hard_upsample(hard_upsample)
    path = resolve_unbind_hard_atoms_path(hard_atoms_path)
    atoms = load_hard_atom_texts(path)
    rows = list(unbind_rows)
    observed = [r for r in rows if r.get("class") == "OBSERVED"]
    inferred = [r for r in rows if r.get("class") != "OBSERVED"]
    if cap > 0:
        inferred = inferred[:cap]
    shaped: list[dict[str, Any]] = []
    for _ in range(factor):
        shaped.extend(observed)
    shaped.extend(inferred)
    hard_stats = hard_atom_upsample_stats(
        observed, hard_upsample=hard_factor, atoms=atoms, path=path
    )
    if hard_stats["n_unbind_hard_extra_copies"]:
        matched = [r for r in observed if unbind_row_matches_hard_atoms(r, atoms)]
        extra_rounds = hard_factor - 1
        for _ in range(extra_rounds):
            shaped.extend(dict(row) for row in matched)
    pool = known if known is not None else known_fillers(rows)
    deny = denylist if denylist is not None else resolve_filler_denylist()
    attached, _n_row_negs = attach_hard_neg_fillers(shaped, pool, denylist=deny)
    pairs = morph_pairs_for_rows(observed + inferred)
    stats = {
        "n_unbind_observed": len(observed),
        "n_unbind_inferred": len(inferred),
        "unbind_observed_upsample": factor,
        "unbind_inferred_cap": cap,
        "n_unbind_morph_negatives": len(pairs),
        "n_train_unbind": len(attached),
        "unbind_filler_denylist_lineages": len(deny),
    }
    stats.update(hard_stats)
    return attached, stats


def morph_margin_loss(
    gold_logit: float,
    neg_logits: Sequence[float],
    margin: float = UNBIND_MORPH_MARGIN_DEFAULT,
) -> float:
    """sum(relu(margin + neg - gold)). Torch loop uses the same formula."""
    total = 0.0
    for neg in neg_logits:
        gap = margin + float(neg) - float(gold_logit)
        if gap > 0:
            total += gap
    return total


def recipe_env_counts(unbind_rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Export-facing counts. Does not mutate rows or invent OBSERVED gold."""
    from .unbind_curriculum import curriculum_env_counts

    rows = list(unbind_rows)
    n_obs = sum(1 for r in rows if r.get("class") == "OBSERVED")
    n_inf = sum(1 for r in rows if r.get("class") != "OBSERVED")
    train = [r for r in rows if r.get("split") == "train"]
    path = resolve_unbind_hard_atoms_path()
    atoms = load_hard_atom_texts(path)
    hard_factor = resolve_unbind_hard_upsample()
    counts = {
        "n_unbind_observed": n_obs,
        "n_unbind_inferred": n_inf,
        "unbind_observed_upsample": resolve_unbind_observed_upsample(),
        "unbind_inferred_cap": resolve_unbind_inferred_cap(),
        "unbind_inferred_weight": resolve_unbind_inferred_weight(),
        "unbind_morph_negatives": len(morph_pairs_for_rows(train)),
        "unbind_filler_denylist_lineages": len(resolve_filler_denylist()),
    }
    counts.update(
        hard_atom_upsample_stats(
            [r for r in train if r.get("class") == "OBSERVED"],
            hard_upsample=hard_factor,
            atoms=atoms,
            path=path,
        )
    )
    counts.update(curriculum_env_counts())
    return counts
