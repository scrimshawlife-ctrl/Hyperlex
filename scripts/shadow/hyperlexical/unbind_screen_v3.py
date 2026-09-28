"""Frozen RUNE.UNBIND_SCREEN.v3.

The bucket function is the scored screen. v4 may call it to obtain a bucket.
v4 must not rewrite this decision procedure.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

FILES = {
    "noun": ("index.noun", "data.noun"),
    "verb": ("index.verb", "data.verb"),
    "adj": ("index.adj", "data.adj"),
    "adv": ("index.adv", "data.adv"),
}
STOP = {
    "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "with", "from",
    "by", "at", "as", "into", "over", "that", "this", "it", "be", "is", "are",
    "was", "were", "been", "being", "not", "no", "than", "then", "if", "but",
    "its", "who", "which", "when", "where", "what", "how", "about", "such",
    "all", "every", "other", "one",
}
GEO_HEADS = frozenset({
    "gulf", "bay", "cape", "lake", "sea", "mount", "strait", "ocean", "island",
    "river", "port", "peninsula", "isthmus", "archipelago", "republic", "kingdom",
})
INST_HEADS = frozenset({
    "department", "ministry", "bureau", "agency", "university", "committee",
    "commission", "court", "office", "board", "council", "senate", "congress",
    "parliament", "institute", "administration", "authority",
})
PLACES = frozenset({
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "hampshire", "jersey",
    "mexico", "york", "carolina", "dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "wisconsin", "wyoming", "america", "canada",
    "brazil", "argentina", "chile", "peru", "france", "germany", "italy",
    "spain", "portugal", "ireland", "scotland", "england", "britain", "europe",
    "africa", "asia", "australia", "india", "china", "japan", "korea", "egypt",
    "greece", "russia", "poland",
})
PARTICLES = frozenset({
    "out", "up", "off", "away", "down", "back", "over", "through", "apart",
    "aside", "along", "in", "on",
})
POSSESSORS = frozenset({"my", "your", "his", "her", "our", "their", "one's"})
DEGREE = frozenset({"too", "very", "more", "most", "so", "quite", "rather", "extremely"})
NUMBERS = frozenset({
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million", "billion",
})
TITLE_NOUNS = frozenset({
    "law", "laws", "theory", "rules", "principle", "theorem", "equation",
    "constant", "effect", "doctrine",
})
NAME_PARTICLES = frozenset({"de", "von", "van", "di", "da", "del", "du", "des"})
TITLE_HEADS = frozenset({"master", "bachelor", "doctor"})
PROCEDURE_TAILS = frozenset({"surgery", "procedure", "operation"})
TAXON_SUFFIX = ("idae", "aceae", "inae", "iformes", "oidea")
LATIN_SPECIES = re.compile(r"(ensis|oides|aceae|aris)$")
INITIALISM = re.compile(r"[a-z]\.$")
POSSESSIVE = re.compile(r"[a-z]+'s$")
NAME_TOKEN = re.compile(r"[a-z]+$")
YEAR = re.compile(r"\b(?:1[0-9]{3}|20[0-9]{2})\b")

def stems(text):
    out = []
    for word in re.findall(r"[a-z']+", text.lower()):
        word = word.strip("'")
        if len(word) < 3 or word in STOP:
            continue
        out.append(word[:4])
    return out

def load_index(path):
    found = {}
    for line in path.open(encoding="utf-8", errors="replace"):
        if not line or line[0] == " ":
            continue
        parts = line.split()
        if "_" not in parts[0]:
            continue
        synset_cnt = int(parts[2])
        p_cnt = int(parts[3])
        rest = parts[4 + p_cnt:]
        offsets = rest[2:2 + synset_cnt]
        if offsets:
            found[parts[0]] = offsets[0]
    return found

def load_glosses(path, wanted):
    glosses = {}
    want = set(wanted)
    if not want:
        return glosses
    for line in path.open(encoding="utf-8", errors="replace"):
        if not line or line[0] == " ":
            continue
        offset = line.split(" ", 1)[0]
        if offset not in want:
            continue
        raw = line.split("|", 1)[1].strip()
        glosses[offset] = raw.split(";", 1)[0].strip()
        if len(glosses) == len(want):
            break
    return glosses

@lru_cache(maxsize=4)
def load_indexes(root: str):
    base = Path(root)
    return {pos: load_index(base / pair[0]) for pos, pair in FILES.items()}


def gloss_for(surface, pos, root):
    """First-sense gloss clause. The gloss is screening evidence, not a target."""
    indexes = load_indexes(str(root))
    lemma = surface.replace(" ", "_")
    table = indexes.get(pos) or {}
    offset = table.get(lemma)
    if not offset:
        for alt, idx in indexes.items():
            if lemma in idx:
                pos, offset = alt, idx[lemma]
                break
    if not offset:
        return pos, ""
    data = load_glosses(Path(root) / FILES[pos][1], {offset})
    return pos, data.get(offset, "")

def screen(surface, source_pos, tokens, gloss):
    gloss_l = gloss.lower()
    if not (2 <= len(tokens) <= 6) or len(surface) > 80 or " ".join(tokens) != surface:
        return "REJECT", "surface_constraint", "exclude"
    if any(INITIALISM.fullmatch(t) for t in tokens) or YEAR.search(gloss):
        return "REJECT", "proper_person_name", "exclude"
    if "organization" in gloss_l:
        return "REJECT", "named_organization", "exclude"
    if len(tokens) >= 2 and tokens[1] == "of" and tokens[0] in GEO_HEADS:
        return "REJECT", "primarily_referential_expression", "exclude"
    if len(tokens) >= 2 and tokens[1] == "of" and tokens[0] in INST_HEADS:
        return "REJECT", "institutional_title", "exclude"
    if "saint" in tokens or "st." in tokens:
        return "REJECT", "titled_work_or_designation", "exclude"
    if any(POSSESSIVE.fullmatch(t) for t in tokens) and any(t in TITLE_NOUNS for t in tokens):
        return "REJECT", "titled_work_or_designation", "exclude"
    if tokens and tokens[0] in TITLE_HEADS and tokens[1:2] == ["of"]:
        return "REJECT", "degree_or_credential_name", "exclude"
    if (
        len(tokens) >= 5
        and any(t in NAME_PARTICLES for t in tokens)
        and all(NAME_TOKEN.fullmatch(t) for t in tokens)
    ):
        return "REJECT", "proper_person_name", "exclude"
    if any(t.endswith(TAXON_SUFFIX) for t in tokens) or (
        tokens and tokens[0] in {"family", "genus", "species", "order", "phylum", "tribe"}
    ) or "family of" in gloss_l:
        return "REJECT", "taxonomy_or_species_label", "exclude"
    if (
        source_pos == "noun"
        and len(tokens) == 2
        and all(re.fullmatch(r"[a-z]{4,}", t) for t in tokens)
        and LATIN_SPECIES.search(tokens[1])
    ):
        return "REJECT", "taxonomy_or_species_label", "exclude"
    if any(t in PLACES for t in tokens) and len(tokens) <= 3:
        return "REJECT", "primarily_referential_expression", "exclude"
    if tokens and all(t in NUMBERS for t in tokens):
        return "REJECT", "productive_numeric_expression", "exclude"
    if "per" in tokens or "unit for measuring" in gloss_l:
        return "REJECT", "technical_measurement_expression", "exclude"
    if len(tokens) >= 3 and tokens[-1] in PROCEDURE_TAILS:
        return "REJECT", "named_technical_procedure", "exclude"
    if source_pos == "adj" and len(tokens) == 2 and tokens[0] in DEGREE:
        return "REJECT", "unconstrained_free_composition", "exclude"
    if len(tokens) == 2 and tokens[0] in {"much", "more", "less"} and tokens[1] == "as":
        return "REJECT", "unconstrained_free_composition", "exclude"
    gstem = set(stems(gloss))
    sstem = stems(surface)
    overlap = 0 if not sstem else len([w for w in sstem if w in gstem]) / len(sstem)
    if source_pos == "verb" and len(tokens) == 2 and tokens[1] in PARTICLES and tokens[0][:4] not in gstem:
        return "HIGH_VALUE", "strong_phrasal_binding", "score"
    for i, tok in enumerate(tokens):
        if tok in POSSESSORS:
            rest = [w for w in tokens[i + 1:] if len(w) >= 3 and w not in STOP]
            if rest and rest[-1][:4] not in gstem:
                return "HIGH_VALUE", "lexicalized_variable_slot", "score"
    if len(tokens) == 3 and tokens[1] == "and":
        sides = [t[:4] for t in (tokens[0], tokens[2]) if len(t) >= 3]
        if sides and all(s not in gstem for s in sides):
            return "HIGH_VALUE", "fixed_nonliteral_expression", "score"
    if len(tokens) == 4 and tokens[1] == "as" and tokens[2] == "a" and tokens[3][:4] not in gstem:
        return "HIGH_VALUE", "fixed_nonliteral_expression", "score"
    if source_pos in {"verb", "adj", "adv"} and len(tokens) >= 4 and overlap == 0:
        return "HIGH_VALUE", "conventionalized_semantic_shift", "score"
    return "SECONDARY", "transparent_or_moderate", "score"
