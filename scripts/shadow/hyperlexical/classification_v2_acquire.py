"""Frozen evidence map for Classification v2 training acquisition.

A row is eligible only when an English Wiktionary definition line carries
one of these sense labels, or a frozen definitional gloss, and no second
family. Category membership, bare keywords, and model output do not qualify.
The training string is that definition. The page title is kept only when the
definition prose is empty. This module does not fetch, train, or touch BEST.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, Sequence

ACTIVE_TARGETS: tuple[str, ...] = (
    "internet-slang",
    "memetic",
    "social-status",
    "relationship-dating",
    "approval-disapproval",
    "conflict-aggression",
    "technology-ai",
    "workplace-career",
    "sports-competition",
    "music-entertainment",
    "fashion-aesthetic",
    "regional-cultural",
    "spiritual-mystic",
    "identity-affiliation",
    "politics-civic",
)

# Exact sense-label arguments. Bare slang, computing, and internet are absent.
SENSE_LABELS: dict[str, tuple[str, ...]] = {
    "internet-slang": ("internet slang", "reddit slang", "2channel slang"),
    "memetic": ("meme",),
    "social-status": ("honorific",),
    "relationship-dating": ("dating",),
    "approval-disapproval": ("derogatory", "endearing"),
    "conflict-aggression": ("military", "military slang", "military ranks", "naval slang"),
    "technology-ai": (
        "programming",
        "software",
        "computer science",
        "software engineering",
        "computer hardware",
        "computer security",
    ),
    "workplace-career": ("business",),
    "sports-competition": ("sports", "ball games", "winter sports", "water sports"),
    "music-entertainment": ("music", "film", "television", "music industry"),
    "fashion-aesthetic": ("fashion", "clothing", "aesthetic"),
    "spiritual-mystic": (
        "occult",
        "mysticism",
        "astrology",
        "wicca",
        "paganism",
        "spiritualism",
    ),
    "identity-affiliation": (
        "demonym",
        "lgbtq slang",
        "gay slang",
        "transgender slang",
        "ethnic slur",
    ),
    "politics-civic": ("politics", "government", "political science", "geopolitics"),
}

CONJUNCTIONS: dict[str, tuple[tuple[str, ...], ...]] = {
    "internet-slang": (("internet", "slang"),),
}

SUPPORTED_FAMILY_LABELS: frozenset[str] = frozenset(
    {
        "artificial intelligence",
        "betting",
        "gambling",
        "cryptocurrency",
        "cryptocurrencies",
        "gaming",
        "video game",
        "video games",
        "computer games",
        "poker",
        "poker slang",
    }
)

GLOSS_RULES: tuple[tuple[str, str], ...] = (
    ("memetic", r"\b(internet meme|image macro|copypasta)\b"),
    ("social-status", r"\b(social status|social standing)\b"),
    ("relationship-dating", r"\b(romantic relationship|courtship)\b"),
)

DISCOVERY_QUERIES: dict[str, tuple[str, ...]] = {
    "internet-slang": ("Internet slang", "Reddit slang", "2channel slang"),
    "memetic": ("meme",),
    "social-status": ("honorific",),
    "relationship-dating": ("dating",),
    "approval-disapproval": ("derogatory", "endearing"),
    "conflict-aggression": ("military", "military slang", "military ranks", "naval slang"),
    "technology-ai": ("programming", "software", "computer science", "software engineering"),
    "workplace-career": ("business",),
    "sports-competition": ("sports",),
    "music-entertainment": ("music", "film", "television"),
    "fashion-aesthetic": ("fashion", "clothing"),
    "regional-cultural": (
        "Southern US",
        "Cockney",
        "African-American Vernacular",
        "Scottish",
        "Yorkshire",
        "Australian",
        "Indian English",
        "Ireland",
        "New Zealand",
    ),
    "spiritual-mystic": (
        "occult",
        "mysticism",
        "astrology",
        "Wicca",
        "paganism",
        "spiritualism",
    ),
    "identity-affiliation": (
        "demonym",
        "LGBTQ slang",
        "gay slang",
        "transgender slang",
        "ethnic slur",
    ),
    "politics-civic": ("politics", "government", "political science"),
}

GLOSS_DISCOVERY: dict[str, tuple[str, ...]] = {
    "memetic": ("internet meme", "image macro", "copypasta"),
    "social-status": ("social status", "social standing"),
    "relationship-dating": ("romantic relationship", "courtship"),
}

PREFERRED_OBSERVED = 8
ACCEPTABLE_OBSERVED = 4

_SENSE_LABEL = re.compile(
    r"\{\{\s*(lb|lbl|tlb)\s*\|\s*en\s*\|([^{}]*)\}\}",
    re.IGNORECASE,
)
_LINK = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
_MARKUP = re.compile(r"''+")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_GLOSS = tuple((family, re.compile(pattern, re.IGNORECASE)) for family, pattern in GLOSS_RULES)

REGIONAL_LABELS: tuple[str, ...] = (
    'North America',
    'North American',
    'Canada',
    'CA',
    'Canadian',
    'CanE',
    'Canadian English',
    'Acadia',
    'Acadian',
    'Alberta',
    'Atlantic Canada',
    'British Columbia',
    'Canadian Prairies',
    'Labrador',
    'Manitoba',
    'New Brunswick',
    'Newfoundland',
    'Northwest Territories',
    'Northwestern Ontario',
    'northwestern Ontario',
    'Northwest Ontario',
    'northwest Ontario',
    'Nova Scotia',
    'Nunavut',
    'Ontario',
    'Prince Edward Island',
    'Quebec',
    'Québec',
    'Saskatchewan',
    'Yukon',
    'US',
    'U.S.',
    'United States',
    'United States of America',
    'USA',
    'US English',
    'U.S. English',
    'America',
    'American',
    'American English',
    'African-American Vernacular',
    'AAVE',
    'African American Vernacular',
    'African American Vernacular English',
    'African-American Vernacular English',
    'BVE',
    'African-American',
    'AA',
    'African-American English',
    'African American',
    'African American English',
    'AAE',
    'Alabama',
    'Alaska',
    'Appalachia',
    'Appalachian',
    'Arizona',
    'Arkansas',
    'Baltimore',
    'Boston',
    'Cajun',
    'California',
    'Chicago',
    'Cincinnati',
    'Colorado',
    'Connecticut',
    'District of Columbia',
    'DC',
    'Washington, DC',
    'Eastern New England',
    'Florida',
    'Georgia (US)',
    'Hawaii',
    'Illinois',
    'Indiana',
    'Kentucky',
    'Louisiana',
    'Maine',
    'Maryland',
    'Massachusetts',
    'Memphis',
    'Michigan',
    'Mid-Atlantic US',
    'Midland US',
    'Midwestern US',
    'Midwest US',
    'Mississippi',
    'Missouri',
    'New England',
    'New Jersey',
    'New Mexico',
    'New Orleans',
    'New York City',
    'NYC',
    'New York',
    'NY',
    'North Carolina',
    'North Midland US',
    'Northern Midland US',
    'Northeastern US',
    'Northeast US',
    'Northern California',
    'Northwestern US',
    'Northwest US',
    'Pacific Northwest',
    'Ohio',
    'Oklahoma',
    'Pennsylvania',
    'Philadelphia',
    'Pittsburgh',
    'Pittsburghese',
    'Rhode Island',
    'South Carolina',
    'South Midland US',
    'Southern Midland US',
    'Southern California',
    'Southern US',
    'Southern American English',
    'southern US',
    'US South',
    'Southwestern US',
    'southwestern US',
    'Southwest US',
    'southwest US',
    'St. Louis',
    'St. Vincent',
    'Texas',
    'Upper Midwestern US',
    'Upper Midwest US',
    'Vermont',
    'Virginia',
    'Western Pennsylvania',
    'Western Pennsylvania English',
    'Western US',
    'western US',
    'Wisconsin',
    'Australian Aboriginal',
    'Australian aboriginal',
    'Australian Aboriginal English',
    'Australian aboriginal English',
    'Aboriginal Australian',
    'aboriginal Australian',
    'Aboriginal Australian English',
    'aboriginal Australian English',
    'Australia',
    'Australian',
    'AU',
    'AuE',
    'Aus',
    'AusE',
    'Canberra',
    'New South Wales',
    'NSW',
    'New Zealand',
    'NZ',
    'NZE',
    'Northern Territory',
    'NT',
    'Northern US',
    'Northern American English',
    'northern US',
    'US North',
    'Queensland',
    'South Australia',
    'Tasmania',
    'Victoria',
    'Western Australia',
    'Cork',
    'Dublin',
    'Ireland',
    'Irish',
    'IE',
    'Munster',
    'UK',
    'United Kingdom',
    'British',
    'Britain',
    'Great Britain',
    'Antrim',
    'Bedfordshire',
    'Berkshire',
    'Birmingham',
    'Bristol',
    'Bristolian',
    'Caithness',
    'Cambridge University',
    'University of Cambridge',
    'Cantab',
    'Channel Islands',
    'Cockney',
    'Cornwall',
    'Cornish',
    'Cumbria',
    'Cumbrian',
    'Derbyshire',
    'Devon',
    'Devonshire',
    'Dorset',
    'Dundee',
    'Durham University',
    'Durham',
    'East Anglia',
    'East Midlands',
    'England',
    'English',
    'England and Wales',
    'E&W',
    'Essex',
    'Exmoor',
    'Gloucestershire',
    'Guernsey',
    'Hartlepool',
    'Herefordshire',
    'Isle of Man',
    'Manx',
    'Isle of Wight',
    'Jersey',
    'Kent',
    'Kentish',
    'Lancashire',
    'Lewis',
    'Isle of Lewis',
    'Lincolnshire',
    'Liverpool',
    'Scouse',
    'London',
    'Manchester',
    'Mancunian',
    'Mid-Ulster',
    'Mid-Ulster English',
    'Midlands',
    'English Midlands',
    'South Midlands',
    'Norfolk',
    'North Wales',
    'Northern England',
    'northern England',
    'North England',
    'north England',
    'Northern Ireland',
    'Northern Irish',
    'NI',
    'Northern Isles',
    'Northumberland',
    'Northumbria',
    'Northumbrian',
    'Northeast England',
    'North-East England',
    'North East England',
    'Nottinghamshire',
    'Orkney',
    'Orcadian',
    'Oxbridge',
    'Oxford City',
    'Oxford University',
    'University of Oxford',
    'Oxon',
    'Oxfordshire',
    'Pitmatic',
    'Potteries',
    'Scotland',
    'Scottish',
    'Scottish English',
    'ScE',
    'Shetland',
    'Shetland Islands',
    'Shetlands',
    'Shropshire',
    'Somerset',
    'South Wales',
    'Southern England',
    'southern England',
    'South England',
    'south England',
    'Southern English',
    'Suffolk',
    'Sussex',
    'Teesside',
    'Ulster',
    'Wales',
    'Welsh',
    'Wearside',
    'West Country',
    'West England',
    'west England',
    'West Cumbria',
    'West Midlands',
    'Wiltshire',
    'Yorkshire',
    'South Asia',
    'Indic',
    'South Asian',
    'SA',
    'Afghanistan',
    'Bangladesh',
    'Nepal',
    'Sri Lanka',
    'Sri Lankan',
    'Pakistan',
    'Pakistani',
    'British Pakistani',
    'British India',
    'India',
    'Indian',
    'Indian English',
    'InE',
    'North India',
    'South India',
    'South Indian',
    'West Bengal',
    'Africa',
    'African',
    'Antarctica',
    'Asia',
    'Bahamas',
    'Barbados',
    'Belize',
    'Bermuda',
    'Botswana',
    'Brunei',
    'Cameroon',
    'CM',
    'Cameroonian',
    'Cameroonian English',
    'en-CM',
    'Caribbean',
    'West Indies',
    'Cebu',
    'Central America',
    'Ceylon',
    'China',
    'Chinese Filipino',
    'Chinese-Filipino',
    'Commonwealth',
    'Cuba',
    'East Africa',
    'East Asia',
    'Egypt',
    'Europe',
    'European',
    'Fiji',
    'Ghana',
    'Guyana',
    'Hong Kong',
    'HK',
    'Hungary',
    'Indonesia',
    'Israel',
    'Japan',
    'Jamaica',
    'Jamaican English',
    'Jamaican',
    'Kenya',
    'Liberia',
    'Libya',
    'Macau',
    'Mainland China',
    'Mainland',
    'mainland',
    'mainland China',
    'Malaysia',
    'Malaysian',
    'Malta',
    'Mexico',
    'Middle East',
    'Myanmar',
    'Burma',
    'Namibia',
    'Natal',
    'Nigeria',
    'Nigerian',
    'Oceania',
    'Palestine',
    'Papua New Guinea',
    'Philippines',
    'Philippine',
    'Philippine English',
    'Baguio',
    'Réunion',
    'Rhodesia',
    'Rwanda',
    'Singapore',
    'SG',
    'Singaporean',
    'Solomon Islands',
    'South Africa',
    'South African',
    'South African English',
    'ZA',
    'South America',
    'South American',
    'South Korea',
    'Southeast Asia',
    'Southeast Asian',
    'South-East Asia',
    'South-East Asian',
    'South-east Asia',
    'South-east Asian',
    'SEA',
    'Taiwan',
    'Taiwanese',
    'Tanzania',
    'Tanzanian',
    'Thailand',
    'Trinidad and Tobago',
    'Trinidad',
    'Tobago',
    'Trinidadian',
    'Uganda',
    'Vanuatu',
    'Vietnam',
    'West Africa',
    'West African',
    'Zimbabwe'
)


def normalize_label(text: str) -> str:
    collapsed = text.casefold().replace("-", " ")
    return re.sub(r"\s+", " ", collapsed).strip()


def sense_label_arguments(definition_line: str) -> list[str]:
    if not definition_line.startswith("# ") or definition_line.startswith(("#:", "##")):
        return []
    found: list[str] = []
    for match in _SENSE_LABEL.finditer(definition_line):
        for part in match.group(2).split("|"):
            argument = part.strip()
            if argument:
                found.append(argument)
    return found


def definition_prose(definition_line: str) -> str:
    text = definition_line[2:] if definition_line.startswith("# ") else definition_line
    previous = None
    while text != previous:
        previous = text
        text = _TEMPLATE.sub(" ", text)
    text = _LINK.sub(lambda match: match.group(2), text)
    text = _MARKUP.sub("", text)
    return re.sub(r"\s+", " ", text).strip(" .")


def _families_from_labels(tokens: Sequence[str]) -> list[str]:
    found: list[str] = []
    token_set = set(tokens)
    for family, labels in SENSE_LABELS.items():
        if any(token in labels for token in tokens) and family not in found:
            found.append(family)
    for family, groups in CONJUNCTIONS.items():
        if family in found:
            continue
        if any(all(part in token_set for part in group) for group in groups):
            found.append(family)
    if any(token in _REGIONAL for token in tokens) and "regional-cultural" not in found:
        found.append("regional-cultural")
    return found


def _families_from_gloss(prose: str) -> list[str]:
    if not prose:
        return []
    return [family for family, pattern in _GLOSS if pattern.search(prose)]


def match_definition(label_arguments: Sequence[str], prose: str) -> dict[str, Any]:
    """One definition line. Unique family, or a refusal status."""
    tokens = [normalize_label(argument) for argument in label_arguments]
    if any(token in SUPPORTED_FAMILY_LABELS for token in tokens):
        return {"status": "supported_family_excluded", "family": None, "evidence": "sense_label"}
    named = _families_from_labels(tokens)
    glossed = _families_from_gloss(prose)
    families = list(dict.fromkeys([*named, *glossed]))
    evidence = "sense_label" if named else "definitional_gloss" if glossed else "none"
    if len(families) == 1:
        return {"status": "unique", "family": families[0], "evidence": evidence}
    if len(families) > 1:
        return {"status": "ambiguous", "family": None, "evidence": evidence}
    return {"status": "absent", "family": None, "evidence": "none"}


def _english_section(wikitext: str) -> str:
    parts = re.split(r"\n(?===[^=])", "\n" + wikitext)
    for part in parts:
        lines = part.strip().splitlines()
        if lines and lines[0].strip("= ").casefold() == "english":
            return part
    return ""


def classify_wikitext(wikitext: str) -> dict[str, Any]:
    """Admit a page only when its English senses name one target family."""
    refused = {
        "status": "absent",
        "family": None,
        "evidence": "none",
        "sense_label_arguments": [],
        "definition_prose": "",
        "definition_line": "",
    }
    if not wikitext or wikitext.lstrip().lower().startswith("#redirect"):
        refused["status"] = "redirect" if wikitext else "absent"
        return refused
    section = _english_section(wikitext)
    if not section:
        refused["status"] = "no_english"
        return refused
    decisions: list[dict[str, Any]] = []
    for line in section.splitlines():
        if not line.startswith("# ") or line.startswith(("#:", "##")):
            continue
        arguments = sense_label_arguments(line)
        prose = definition_prose(line)
        decision = match_definition(arguments, prose)
        if decision["status"] == "absent":
            continue
        decision = dict(decision)
        decision["sense_label_arguments"] = arguments
        decision["definition_prose"] = prose
        decision["definition_line"] = line
        decisions.append(decision)
    if not decisions:
        return refused
    if any(item["status"] != "unique" for item in decisions):
        first = decisions[0]
        return {
            "status": "ambiguous" if any(item["status"] == "ambiguous" for item in decisions) else first["status"],
            "family": None,
            "evidence": first["evidence"],
            "sense_label_arguments": first["sense_label_arguments"],
            "definition_prose": first["definition_prose"],
            "definition_line": first["definition_line"],
        }
    families = {item["family"] for item in decisions}
    if len(families) != 1:
        first = decisions[0]
        return {
            "status": "ambiguous",
            "family": None,
            "evidence": first["evidence"],
            "sense_label_arguments": first["sense_label_arguments"],
            "definition_prose": first["definition_prose"],
            "definition_line": first["definition_line"],
        }
    return decisions[0]


def evidence_seal() -> str:
    payload = "\n".join(
        [
            "sense:" + family + "=" + ",".join(SENSE_LABELS.get(family, ()))
            for family in ACTIVE_TARGETS
        ]
        + [
            "conj:" + family + "=" + "|".join("+".join(group) for group in groups)
            for family, groups in CONJUNCTIONS.items()
        ]
        + ["gloss:" + family + "=" + pattern for family, pattern in GLOSS_RULES]
        + ["regional:" + ",".join(REGIONAL_LABELS)]
        + ["supported:" + ",".join(sorted(SUPPORTED_FAMILY_LABELS))]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def training_row(title: str, decision: Mapping[str, Any], revision: Mapping[str, Any]) -> dict[str, Any]:
    if decision.get("status") != "unique" or decision.get("family") not in ACTIVE_TARGETS:
        raise ValueError("only a unique target-family decision can become a training row")
    revid = revision.get("revision_id")
    if not isinstance(revid, int):
        raise ValueError("mediawiki revision id is required")
    prose = str(decision.get("definition_prose") or "").strip()
    return {
        "class": "OBSERVED",
        "fillers": [],
        "license": "CC-BY-SA-4.0+GFDL (Wiktionary text); labels OBSERVED",
        "lineage": decision["family"],
        "provenance": {
            "source": "en.wiktionary.org",
            "page": title,
            "revision_id": revid,
            "revision_sha1": revision.get("revision_sha1"),
            "revision_timestamp": revision.get("revision_timestamp"),
            "sense_labels": list(decision.get("sense_label_arguments") or []),
            "definition_prose": decision.get("definition_prose") or "",
            "training_text": "definition_prose" if prose else "title",
            "evidence": decision.get("evidence"),
            "evidence_seal": evidence_seal(),
            "rights": "CC BY-SA 4.0 and GFDL",
            "oldid_from_mediawiki": True,
        },
        "role_scheme": None,
        "roles": [],
        "split": "train",
        "stage": "circulating",
        "task": "classify",
        "text": prose or title,
        "typology": [],
    }

_REGIONAL = frozenset(normalize_label(label) for label in REGIONAL_LABELS)
