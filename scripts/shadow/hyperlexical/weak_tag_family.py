"""Deterministic weak tag → family mapper (8 families + none only).

Epistemic: labels produced here are **INFERRED** weak. Never promote to OBSERVED.

Rules (everything else stays ``none``):
1. **Exact seed map** — curated dialect/seed lemmas with a single family.
2. **Kaikki / Wiktionary topic+tag map** — lemma exact match only when:
   - a sense (or entry) carries exactly one of the mapped topics/categories, AND
   - the sense is tagged slang/informal/Internet/colloquial **or** the lemma is multiword, AND
   - the lemma is not on the polysemy denylist, AND
   - the lemma is not ``skill issue`` (collision-hold → none).
3. Bare ``English slang`` / ``en:Politics`` / ``en:Sports`` / ``en:Computing`` alone
   never assign a family (too broad).

Topic → family (deterministic):
- video-games, computer-games, role-playing-games → gaming-meta
- cryptocurrency, cryptocurrencies → crypto-degen
- gambling, poker → betting-sharp

Category prefixes (same families): en:Video games, en:Cryptocurrency(-ies),
en:Gambling, en:Bookmaking.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

FAMILIES = (
    "betting-sharp",
    "crypto-degen",
    "ai-native",
    "brainrot-aura",
    "kinship-address",
    "political-status",
    "gaming-meta",
    "workplace-corp",
)

COLLISION_HOLD = frozenset({"skill issue"})

TOPIC_FAMILY: dict[str, str] = {
    "video-games": "gaming-meta",
    "computer-games": "gaming-meta",
    "role-playing-games": "gaming-meta",
    "cryptocurrency": "crypto-degen",
    "cryptocurrencies": "crypto-degen",
    "gambling": "betting-sharp",
    "poker": "betting-sharp",
}

CAT_PREFIX_FAMILY: tuple[tuple[str, str], ...] = (
    ("en:video games", "gaming-meta"),
    ("en:video game", "gaming-meta"),
    ("en:cryptocurrency", "crypto-degen"),
    ("en:cryptocurrencies", "crypto-degen"),
    ("en:gambling", "betting-sharp"),
    ("en:bookmaking", "betting-sharp"),
)

WEAK_TAGS = frozenset({"slang", "informal", "Internet", "internet", "colloquial"})

# Ultra-polysemous shorts that appear under gaming/gambling topics but must not
# auto-label as family via weak exact map.
DENYLIST = frozenset(
    {
        "ai",
        "bot",
        "bm",
        "bf",
        "bk",
        "bg",
        "book",
        "bank",
        "action",
        "bet",
        "burn",
        "bust",
        "bug",
        "bubble",
        "boat",
        "brick",
        "beard",
        "abc",
        "bicycle",
        "blaze",
        "blind",
        "bluff",
        "rag",
        "ammo",
        "bit",
        "moon",
        "token",
        "mid",
        "cap",
        "throw",
        "beta",
        "boss",
        "broken",
        "aggressive",
        "badge",
        "bumper",
        "buffer",
        "booster",
        "barker",
        "bleeder",
        "npc",
        "rekt",
        "diff",
        "meta",
        "gg",
        "ez",
        "nerf",
        "buff",
        "sweaty",
        "juice",  # too many non-betting senses; prefer registry vig/revenge bet
    }
)

# Exact-only seed expansions (INFERRED). Short polysemes kept here so they never
# enter substring match_lineage as registry atoms unless also listed in LINEAGE_REGISTRY.
SEED_FAMILY: dict[str, str] = {
    # brainrot-aura (internet / Gen-Z leaves; not a 9th family)
    "chopped": "brainrot-aura",
    "mew": "brainrot-aura",
    "bruh": "brainrot-aura",
    "sheesh": "brainrot-aura",
    "fr fr": "brainrot-aura",
    "on god": "brainrot-aura",
    "say less": "brainrot-aura",
    "lowkey": "brainrot-aura",
    "highkey": "brainrot-aura",
    "periodt": "brainrot-aura",
    "iykyk": "brainrot-aura",
    "big w": "brainrot-aura",
    "took an l": "brainrot-aura",
    "rag": "ai-native",  # RAG acronym exact; denylist blocks gambling 'rag'
    # gaming-meta status verbs (exact only)
    "boosted": "gaming-meta",
    "cracked": "gaming-meta",
    "washed": "gaming-meta",
    "tilt": "gaming-meta",
    "owned": "gaming-meta",
    "booter": "gaming-meta",
    "botted": "gaming-meta",
    "blobber": "gaming-meta",
    "blops": "gaming-meta",
    "blox": "gaming-meta",
    "bobux": "gaming-meta",
    "akimbo": "gaming-meta",
    "assrun": "gaming-meta",
    "border gore": "gaming-meta",
    "afk": "gaming-meta",
    "pwn": "gaming-meta",
    "pwned": "gaming-meta",
    # crypto greetings / short CT (exact)
    "gm": "crypto-degen",
    "gn": "crypto-degen",
    "ath": "crypto-degen",
    "dyor": "crypto-degen",
    "lfg": "crypto-degen",
    # betting short exact
    "clv": "betting-sharp",
    # kinship
    "fam": "kinship-address",
    "bestie": "kinship-address",
    "broski": "kinship-address",
}


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _families_from_topics(topics: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for t in topics:
        fam = TOPIC_FAMILY.get(str(t).strip().lower().replace(" ", "-"))
        if fam is None:
            fam = TOPIC_FAMILY.get(str(t).strip())
        if fam:
            out.add(fam)
        # also accept underscore form
        key = str(t).strip().lower().replace("_", "-")
        if key in TOPIC_FAMILY:
            out.add(TOPIC_FAMILY[key])
    return out


def _families_from_categories(categories: Iterable[Any]) -> set[str]:
    out: set[str] = set()
    for c in categories:
        if isinstance(c, dict):
            name = str(c.get("orig") or c.get("name") or "")
        else:
            name = str(c)
        nl = name.strip().lower()
        if not nl:
            continue
        if "video game" in nl:
            out.add("gaming-meta")
        if "cryptocurrenc" in nl:
            out.add("crypto-degen")
        for pref, fam in CAT_PREFIX_FAMILY:
            if nl == pref or nl.startswith(pref):
                out.add(fam)
    return out


def _sense_slangish(tags: Iterable[str], categories: Iterable[Any] | None = None) -> bool:
    tagset = {str(t) for t in tags}
    if tagset & WEAK_TAGS:
        return True
    for c in categories or []:
        if isinstance(c, dict):
            name = str(c.get("orig") or c.get("name") or "")
        else:
            name = str(c)
        if "slang" in name.lower():
            return True
    return False


def family_from_kaikki_entry(entry: Mapping[str, Any]) -> Optional[str]:
    """Return a single family_id or None for one Kaikki/wiktextract-like object."""
    word = _norm(str(entry.get("word") or entry.get("title") or ""))
    if not word or word in COLLISION_HOLD or word in DENYLIST:
        return None

    fams: set[str] = set()
    slangish = _sense_slangish(entry.get("tags") or [])
    fams |= _families_from_topics(entry.get("topics") or [])

    for sense in entry.get("senses") or []:
        if not isinstance(sense, Mapping):
            continue
        if _sense_slangish(sense.get("tags") or [], sense.get("categories") or []):
            slangish = True
        fams |= _families_from_topics(sense.get("topics") or [])
        fams |= _families_from_categories(sense.get("categories") or [])

    fams |= _families_from_categories(entry.get("categories") or [])
    fams = {f for f in fams if f in FAMILIES}
    if len(fams) != 1:
        return None
    multi = " " in word
    if not (slangish or multi):
        return None
    if len(word) < 4 and not multi:
        return None
    return next(iter(fams))


def family_from_wiktionary_categories(categories: Iterable[str]) -> Optional[str]:
    """Map OBSERVED Wiktionary category strings → at most one family (else none)."""
    fams = _families_from_categories(categories)
    fams = {f for f in fams if f in FAMILIES}
    if len(fams) == 1:
        return next(iter(fams))
    return None


def build_lemma_family_map(
    entries: Iterable[Mapping[str, Any]],
    *,
    include_seeds: bool = True,
) -> dict[str, str]:
    """Merge Kaikki entry evidence + optional seed exact map (seeds win on conflict? no — drop)."""
    acc: dict[str, set[str]] = {}
    for entry in entries:
        word = _norm(str(entry.get("word") or entry.get("title") or ""))
        fam = family_from_kaikki_entry(entry)
        if not word or not fam:
            continue
        acc.setdefault(word, set()).add(fam)

    out: dict[str, str] = {}
    for word, fams in acc.items():
        if len(fams) == 1:
            out[word] = next(iter(fams))

    if include_seeds:
        for term, fam in SEED_FAMILY.items():
            tl = _norm(term)
            if tl in COLLISION_HOLD or fam not in FAMILIES:
                continue
            if tl in out and out[tl] != fam:
                # conflict → drop (stay none at classify time)
                out.pop(tl, None)
                continue
            out[tl] = fam
    return out


def weak_family_for_text(text: str, lemma_map: Mapping[str, str] | None = None) -> Optional[str]:
    """Exact-text weak family lookup. Returns family_id or None."""
    tl = _norm(text)
    if not tl or tl in COLLISION_HOLD:
        return None
    if lemma_map is not None:
        return lemma_map.get(tl)
    return SEED_FAMILY.get(tl)


__all__ = [
    "CAT_PREFIX_FAMILY",
    "COLLISION_HOLD",
    "DENYLIST",
    "FAMILIES",
    "SEED_FAMILY",
    "TOPIC_FAMILY",
    "WEAK_TAGS",
    "build_lemma_family_map",
    "family_from_kaikki_entry",
    "family_from_wiktionary_categories",
    "weak_family_for_text",
]
