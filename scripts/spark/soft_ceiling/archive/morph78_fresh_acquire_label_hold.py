#!/usr/bin/env python3
"""morph78 prep under soft_ceiling: fresh civilian acquire + METHOD morph43 HOLD.

Authority: operator continue 2026-09-23 after authorize gate soft_ceiling.
Acquire+label only — no settle/force/train until explicit authorize.

Gate soft_ceiling ARMED: force-fair 1.0 advisory; promote on broad OBSERVED
> PRIOR morph65 live. split=val kept so settle expands force keys + broad val.

METHOD morph43 = positional_text_split_match only. No invented OBSERVED.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

AUTH = (
    "operator continue 2026-09-23; soft_ceiling ARMED — morph78 fresh acquire "
    "+ METHOD morph43 label HOLD"
)
PRIV = Path(
    "/home/morpheus/hlx-private/p1-spark-morph78-fresh-acquire-label-hold-20260923"
)

# Fresh queries — outside morph74/76/77 + emptied residual AUTHORIZE wall.
QUERIES: list[tuple[str, str]] = [
    # brainrot / internet-status
    ("hits different", "brainrot-aura"),
    ("goes hard", "brainrot-aura"),
    ("living rent free", "brainrot-aura"),
    ("rent free", "brainrot-aura"),
    ("main character energy", "brainrot-aura"),
    ("understood the assignment", "brainrot-aura"),
    ("no thoughts head empty", "brainrot-aura"),
    ("unalive", "brainrot-aura"),
    ("caught in 4k", "brainrot-aura"),
    ("iykyk", "brainrot-aura"),
    ("ngl fr", "brainrot-aura"),
    ("periodt", "brainrot-aura"),
    ("slay queen", "brainrot-aura"),
    ("hot take", "brainrot-aura"),
    ("cold take", "brainrot-aura"),
    # crypto / cope
    ("cope harder", "crypto-degen"),
    ("copium", "crypto-degen"),
    ("hopium", "crypto-degen"),
    ("take the L", "crypto-degen"),
    ("big L", "crypto-degen"),
    ("L plus ratio", "crypto-degen"),
    ("ratio plus L", "crypto-degen"),
    ("based and redpilled", "crypto-degen"),
    # gaming / competition
    ("diff jungle", "gaming-meta"),
    ("gap the lane", "gaming-meta"),
    ("inting", "gaming-meta"),
    ("throwing hard", "gaming-meta"),
    ("hardstuck bronze", "gaming-meta"),
    ("smurf account", "gaming-meta"),
    # kinship
    ("lowkey fire", "kinship-address"),
    ("highkey jealous", "kinship-address"),
    ("say less bro", "kinship-address"),
    ("on me fr", "kinship-address"),
    ("deadass", "kinship-address"),
    # workplace / status
    ("circle back later", "workplace-corp"),
    ("take offline", "workplace-corp"),
    ("action items", "workplace-corp"),
    ("bandwidth issue", "workplace-corp"),
]

BLOCKED_PHRASES = {
    # emptied residual AUTHORIZE (Jev defer)
    "admin abuse",
    "aloha snackbar",
    "bling bling",
    "lowkenuinely how do these people exist",
    "my guy",
    "quit lit",
    "real eyes realize clanker lies!!!",
    "using a beard",
    # morph74
    "crash out",
    "brain rot",
    "aura farming",
    "aura farm",
    "no cap",
    "let him cook",
    "touch grass",
    "to the moon",
    "rug pull",
    "diamond hands",
    "paper hands",
    "elo hell",
    "gg ez",
    # morph76
    "locked in",
    "it's giving",
    "npc behavior",
    "non npc behavior",
    "ate that up",
    "sigma grindset",
    "ohio final boss",
    "exit liquidity",
    "exit liquidity farmer",
    "bag holder",
    "merals bagholder",
    "ape in",
    "ape in blind",
    "clock in ape out",
    "ser please",
    "send it",
    "skill issue",
    "git gud",
    "one trick",
    "one trick pony",
    "mentally hard stuck",
    "hard stuck",
    "no shot",
    "highkey shawty",
    "fr fr",
    "fr fr ong",
    "quiet quitting",
    "circle back",
    "touch base",
    # morph77 settle + acquire wall
    "we're so back",
    "were so back",
    "clutch up",
    "bet that up",
    "bet that",
    "real talk",
    "fanum tax",
    "mid af",
    "its so over",
    "it's so over",
    "aura points",
    "aura point",
    "negative aura",
    "have fun staying poor",
    "probably nothing",
    "wen moon wen lambo",
    "wen lambo",
    "few understand",
    "few understand this",
    "very few understand this",
    "up only",
    "throw the game",
    "boosted animal",
    "mid diff",
    "diff mid",
    "no cap fr",
    "fr fr no cap",
    "on god",
    "say less",
    "low bandwidth",
    "rizzless",
    "gyatt",
    "brainrot",
    "cooked",
    "wagmi",
    "ngmi",
}

TYPOLOGY = {
    "brainrot-aura": ["compression", "status"],
    "crypto-degen": ["status", "tribal"],
    "gaming-meta": ["status", "tribal"],
    "kinship-address": ["tribal"],
    "workplace-corp": ["status"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _canon_tokens(text: str) -> list[str]:
    return [tok.strip(".,!?;:\"'()[]") for tok in text.strip().split()]


def _atom_ok(text: str) -> bool:
    t = (text or "").strip()
    if not t or _norm(t) in BLOCKED_PHRASES:
        return False
    if len(t) > 48:
        return False
    low = t.lower()
    for bad in (
        "http",
        "reddit_no_json",
        "person 1",
        "person 2",
        "doctor:",
        "quotations",
        "etymology",
        "alternative form",
        "wiktionary",
        "\n",
    ):
        if bad in low:
            return False
    if re.search(r"^(bro|#|\*|\"|')", low):
        return False
    toks = t.split()
    if not (2 <= len(toks) <= 4):
        return False
    for tok in toks:
        core = tok.strip(".,!?;:\"'()[]")
        if not core or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9'\-]*", core):
            return False
    return True


def _fetch_urban(term: str) -> list[dict]:
    url = "https://api.urbandictionary.com/v0/define?" + urllib.parse.urlencode(
        {"term": term}
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "Hyperlex/0.4 (morph78-fresh-acquire; operator-local)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.load(resp)
    except Exception as exc:
        return [{"_error": f"{type(exc).__name__}:{exc}", "word": term}]
    return list((data or {}).get("list") or [])


def _load_sot_norms() -> set[str]:
    store = Path("/home/morpheus/.hyperlex/hyperlexical/ingest_candidates.jsonl")
    norms: set[str] = set()
    if not store.is_file():
        return norms
    for line in store.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = _norm(str(r.get("text") or ""))
        if t:
            norms.add(t)
    return norms


def acquire() -> list[dict]:
    PRIV.mkdir(parents=True, exist_ok=True)
    sot = _load_sot_norms()
    seen: set[str] = set()
    rows: list[dict] = []
    raw_hits: list[dict] = []
    for query, lineage in QUERIES:
        defs = _fetch_urban(query)
        for d in defs[:5]:
            if "_error" in d:
                raw_hits.append({"query": query, "error": d["_error"]})
                continue
            word = str(d.get("word") or query).strip()
            raw_hits.append(
                {
                    "query": query,
                    "word": word,
                    "thumbs_up": d.get("thumbs_up"),
                    "def": (d.get("definition") or "")[:120],
                }
            )
            for cand in (word, query):
                cand = cand.strip()
                if not _atom_ok(cand):
                    continue
                key = _norm(cand)
                if key in seen:
                    continue
                seen.add(key)
                toks = _canon_tokens(cand)
                text = " ".join(toks)
                rows.append(
                    {
                        "text": text,
                        "class": "INFERRED",
                        "lineage": lineage,
                        "typology": TYPOLOGY.get(lineage, []),
                        "task": "classify",
                        "stage": "circulating",
                        "role_scheme": "positional",
                        "roles": [],
                        "fillers": [],
                        "provenance": "ingest:acquire:urban:20260923-morph78-fresh",
                        "license": "operator-local-crawl",
                        "epistemic": "INFERRED",
                        "split": "val",
                        "acquire_query": query,
                        "acquire_source": "urban",
                        "acquire_split_policy": "force_val",
                        "already_in_sot": key in sot,
                        "settle_note": (
                            "val-split acquired_civilian_candidate; not OBSERVED "
                            "until METHOD settle + explicit authorize"
                        ),
                    }
                )
    (PRIV / "urban_raw_hits.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in raw_hits),
        encoding="utf-8",
    )
    (PRIV / "candidate_atoms.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    (PRIV / "ACQUIRE_SUMMARY.json").write_text(
        json.dumps(
            {
                "as_of": _now(),
                "auth": AUTH,
                "gate": "soft_ceiling_tiebreak",
                "split_policy": "force_val",
                "queries": len(QUERIES),
                "candidate_atoms": len(rows),
                "already_in_sot": sum(1 for r in rows if r.get("already_in_sot")),
                "new_to_sot": sum(1 for r in rows if not r.get("already_in_sot")),
                "by_lineage": dict(Counter(r["lineage"] for r in rows)),
                "by_split": dict(Counter(r["split"] for r in rows)),
                "samples": [r["text"] for r in rows[:50]],
                "hold": True,
                "note": "label HOLD — no settle/train until explicit authorize",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return rows


def method_label(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        text = str(r.get("text") or "").strip()
        toks = _canon_tokens(text)
        labeled = dict(r)
        if not _atom_ok(text) or not (2 <= len(toks) <= 4):
            labeled.update(
                {
                    "decision": "ABSTAIN",
                    "why": "abstain_acquire_noise",
                    "authorization": AUTH,
                }
            )
        else:
            labeled.update(
                {
                    "decision": "AUTHORIZE",
                    "why": "positional_text_split_match",
                    "gold_fillers": [t.lower() for t in toks],
                    "gold_roles": [f"pos_{i}" for i in range(len(toks))],
                    "reparse_ok": True,
                    "authorization": AUTH,
                    "phrase": _norm(text),
                    "text": " ".join(t.lower() for t in toks),
                }
            )
        out.append(labeled)
    (PRIV / "labeled_acquired_atoms.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out),
        encoding="utf-8",
    )
    auth = [r for r in out if r.get("decision") == "AUTHORIZE"]
    counts = {
        "n": len(out),
        "AUTHORIZE": len(auth),
        "ABSTAIN": sum(1 for r in out if r.get("decision") == "ABSTAIN"),
        "by_why": dict(Counter(r.get("why") for r in out)),
        "authorize_texts": [r["text"] for r in auth],
        "authorize_phrases_unique": sorted({_norm(r["text"]) for r in auth}),
        "all_split_val": all(r.get("split") == "val" for r in out),
        "authorization": AUTH,
        "as_of": _now(),
        "hold": True,
        "gate": "soft_ceiling_tiebreak",
    }
    (PRIV / "LABEL_COUNTS.json").write_text(
        json.dumps(counts, indent=2) + "\n", encoding="utf-8"
    )
    (PRIV / "METHOD.md").write_text(
        "# morph78 fresh acquire METHOD morph43 — HOLD (soft_ceiling)\n\n"
        f"**Authority:** {AUTH}\n\n"
        "All candidates `split=val`. AUTHORIZE = positional_text_split_match. "
        "No settle / no force expand / no train until explicit operator authorize "
        "(`authorize morph78` / `authorize val-settle`).\n",
        encoding="utf-8",
    )
    (PRIV / "RESIDUAL_LABEL_METHOD.md").write_text(
        "# morph78 fresh-acquire METHOD morph43 (soft_ceiling)\n\n"
        f"**Authority:** {AUTH}\n\n"
        f"n={counts['n']}. AUTHORIZE={counts['AUTHORIZE']} / "
        f"ABSTAIN={counts['ABSTAIN']}.\n\n"
        "If AUTHORIZE>0 after Jev quality gate: next legal card is gold "
        "force/hard expand on qualify phrases with split=val, then morph78 warm "
        "morph65 under soft_ceiling finish (ceiling escape on broad OBSERVED) — "
        "only after explicit authorize.\n",
        encoding="utf-8",
    )
    return out


def main() -> None:
    PRIV.mkdir(parents=True, exist_ok=True)
    (PRIV / "STATUS.txt").write_text("ACQUIRE_LABEL_HOLD\n")
    rows = acquire()
    labeled = method_label(rows)
    print(
        json.dumps(
            {
                "phase": "acquire_label_hold",
                "gate": "soft_ceiling_tiebreak",
                "candidates": len(rows),
                "AUTHORIZE": sum(
                    1 for r in labeled if r.get("decision") == "AUTHORIZE"
                ),
                "ABSTAIN": sum(1 for r in labeled if r.get("decision") == "ABSTAIN"),
                "all_val": all(r.get("split") == "val" for r in labeled),
                "priv": str(PRIV),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
