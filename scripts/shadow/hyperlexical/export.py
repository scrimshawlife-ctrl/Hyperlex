"""U2 civilian exporter. No hyperlex import. No ~/.hyperlex copy."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from .packet import RESTRICTED_MARKER, SCHEMES, sha256_hex
from ._negatives_data import NEGATIVES  # ordinary prose; no slang
from .unbind_recipe import recipe_env_counts

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

TYPOLOGY = {
    "betting-sharp": ["status"],
    "crypto-degen": ["status", "tribal"],
    "ai-native": ["compression", "memory", "provenance", "context"],
    "brainrot-aura": ["compression", "status"],
    "kinship-address": ["tribal"],
    "political-status": ["tribal", "irony_shield"],
    "gaming-meta": ["status", "hook"],
    "workplace-corp": ["camouflage"],
}


DIALECT = (
    "no cap fr",
    "it's giving",
    "locked in",
    "crash out",
    "left no crumbs",
    "chat is this real",
    "aura points",
    "let him cook",
)

ROW_KEYS = (
    "text",
    "split",
    "lineage",
    "typology",
    "stage",
    "roles",
    "fillers",
    "role_scheme",
    "task",
    "provenance",
    "class",
    "license",
)

COLLISION_HOLD = {"skill issue"}

# Short slang / numeric codes that len≤2 or numeric filters would false-reject.
# Prefer explicit allowlist over blanket keep of all short/numeric tokens.
SHORT_SLANG_ALLOWLIST = frozenset(
    {
        "w",
        "l",
        "ez",
        "gg",
        "gm",
        "gn",
        "bs",
        "a+",
        "ai",
        "ak",
        "3p",
        "ag",
        "bf",
        "bj",
        "bk",
        "bm",
        "420",
        "4/20",
        "4:20",
        "100",
        "404",
        "5150",
        "10-4",
        "304",
        "143",
        "007",
        "411",
        "730",
        "10-20",
    }
)

# Spec 004 type_slot vocabulary (structural placeholders — not gloss-derived POS).
TYPE_SLOT_TAGS = ("TOKEN", "SLOT", "MARKER")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def lexical_split(text: str) -> str:
    """Frozen hash split. Do not change the hash, modulus, or bucket edges.

    Settle may add rows mid-experiment. A new text gets a bucket from *its*
    hash only. Existing texts keep their split — val must not reshuffle.
    """
    n = int(sha256_hex(text.lower())[:8], 16) % 10
    if n == 0:
        return "test"
    if n == 1:
        return "val"
    return "train"


def _norm_class(raw: str | None, default: str) -> str:
    val = (raw or default).upper()
    if val not in {"OBSERVED", "INFERRED", "SPECULATIVE"}:
        return default
    if val == "SPECULATIVE":
        return "INFERRED"
    return val


def _norm_role_scheme(raw: Any) -> str | None:
    """Fail-closed: recoverable_structure allows positional|type_slot only.

    Dump / harvest leftovers such as ``civilian`` are not a third scheme.
    Classify rows with an unknown label drop to None (no unbind gold).
    """
    if raw in SCHEMES:
        return str(raw)
    return None


def _row(**kwargs: Any) -> dict[str, Any]:
    text = kwargs["text"]
    if RESTRICTED_MARKER in text:
        raise ValueError("restricted text")
    if text.lower() in COLLISION_HOLD and kwargs.get("task") == "classify":
        kwargs = dict(kwargs)
        kwargs["lineage"] = "none"
        kwargs["class"] = "INFERRED"
        kwargs["provenance"] = str(kwargs.get("provenance") or "") + ":collision-hold"
    out = {k: kwargs.get(k) for k in ROW_KEYS}
    # Spec 007 lexical split is train/val/test only. Reject store contamination
    # (e.g. blanket-yes wrote split="live") so --include-live cannot bypass the hash split.
    split = kwargs.get("split")
    if split not in {"train", "val", "test"}:
        split = lexical_split(text)
    out["split"] = split
    out["typology"] = list(out.get("typology") or [])
    out["roles"] = list(out.get("roles") or [])
    out["fillers"] = list(out.get("fillers") or [])
    out["license"] = out.get("license") or "MIT-examples"
    out["stage"] = out.get("stage") or "circulating"
    out["role_scheme"] = _norm_role_scheme(out.get("role_scheme"))
    return out


def load_registry(root: Path) -> list[dict[str, Any]]:
    path = root / "src" / "hyperlex" / "analysis" / "__init__.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if (
                isinstance(target, ast.Name)
                and target.id == "LINEAGE_REGISTRY"
                and node.value is not None
            ):
                return ast.literal_eval(node.value)
    raise RuntimeError("LINEAGE_REGISTRY missing")


def harvest_registry(root: Path) -> list[dict[str, Any]]:
    rows = []
    for entry in load_registry(root):
        fam = entry["family_id"]
        if fam not in FAMILIES:
            continue
        for term in entry.get("terms") or []:
            rows.append(
                _row(
                    text=term,
                    lineage=fam,
                    typology=TYPOLOGY.get(fam, []),
                    task="classify",
                    provenance=f"LINEAGE_REGISTRY:{fam}",
                    **{"class": "INFERRED"},
                    role_scheme=None,
                )
            )
    return rows


def harvest_receipts(root: Path) -> list[dict[str, Any]]:
    rows = []
    gold = root / "examples" / "receipts" / "golden"
    if not gold.is_dir():
        return rows
    for path in sorted(gold.glob("*.json")):
        if path.name == "MANIFEST.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        lineage = (data.get("analysis") or {}).get("lineage") or {}
        fam = lineage.get("family_id") or "none"
        if fam not in FAMILIES and fam != "none":
            fam = "none"
        terms = list(lineage.get("matched_terms") or [])
        query = ((data.get("ingest") or {}).get("query") or "").strip()
        if query:
            terms.append(query)
        seen = set()
        for term in terms:
            if not term or term in seen:
                continue
            seen.add(term)
            rows.append(
                _row(
                    text=term,
                    lineage=fam,
                    typology=TYPOLOGY.get(fam, []),
                    task="classify",
                    provenance=f"golden:{path.name}",
                    **{"class": "INFERRED"},
                    role_scheme=None,
                )
            )
    return rows


def harvest_backfill(root: Path) -> list[dict[str, Any]]:
    rows = []
    pack_dir = root / "data" / "backfill" / "2026"
    if not pack_dir.is_dir():
        return rows
    for path in sorted(pack_dir.glob("2026-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        default = data.get("provenance_default") or "INFERRED"
        for item in data.get("terms") or []:
            term = (item.get("term") or "").strip()
            if not term:
                continue
            fam = item.get("family_id") or "none"
            if fam not in FAMILIES and fam != "none":
                fam = "none"
            rows.append(
                _row(
                    text=term,
                    lineage=fam,
                    typology=TYPOLOGY.get(fam, []),
                    task="classify",
                    provenance=f"backfill:{path.name}",
                    **{"class": _norm_class(item.get("provenance"), default)},
                    role_scheme=None,
                )
            )
    return rows


def harvest_archive(root: Path) -> list[dict[str, Any]]:
    rows = []
    archive = root / "docs" / "archive"
    if not archive.is_dir():
        return rows
    for path in sorted(archive.glob("**/receipts/*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        lineage = (data.get("analysis") or {}).get("lineage") or {}
        fam = lineage.get("family_id") or data.get("lineage_family") or "none"
        if fam not in FAMILIES and fam != "none":
            fam = "none"
        terms = list(lineage.get("matched_terms") or [])
        query = ((data.get("ingest") or {}).get("query") or "").strip()
        if query:
            terms.append(query)
        seen = set()
        for term in terms:
            if not term or term in seen:
                continue
            seen.add(term)
            rows.append(
                _row(
                    text=term,
                    lineage=fam,
                    typology=TYPOLOGY.get(fam, []),
                    task="classify",
                    provenance=f"archive:{path.relative_to(root).as_posix()}",
                    **{"class": "INFERRED"},
                    role_scheme=None,
                )
            )
    return rows


def harvest_unbind(n: int = 24) -> list[dict[str, Any]]:
    """Spec 004 fixture gold under both schemes. Honest default n=24 (~45 unique).

    Fixture rows are provenance `004:tpr:*` only — not civilian name-gate gold.
    """
    sys.path.insert(0, str(repo_root() / "scripts" / "shadow"))
    from recoverable_structure.fixtures import make_spans

    rows = []
    spans = make_spans(n=n, length=4, seed=7)
    for i, sp in enumerate(spans):
        items = list(sp["item_ids"])
        tags = list(sp["type_tags"])
        rows.append(
            _row(
                text=" ".join(items),
                lineage="none",
                typology=[],
                stage="noise",
                roles=[f"pos_{k}" for k in range(len(items))],
                fillers=items,
                role_scheme="positional",
                task="unbind",
                provenance=f"004:tpr:positional:{i}",
                **{"class": "OBSERVED"},
            )
        )
        rows.append(
            _row(
                text=" ".join(f"{t}:{it}" for t, it in zip(tags, items)),
                lineage="none",
                typology=[],
                stage="noise",
                roles=tags,
                fillers=items,
                role_scheme="type_slot",
                task="unbind",
                provenance=f"004:tpr:type_slot:{i}",
                **{"class": "OBSERVED"},
            )
        )
    return rows


def _structural_type_tags(n: int) -> list[str]:
    """Assign Spec 004 TOKEN/SLOT/MARKER by index — not gloss/POS invention."""
    return [TYPE_SLOT_TAGS[i % len(TYPE_SLOT_TAGS)] for i in range(n)]


LIVE_UNBIND_MAX_LEN = 80
LIVE_UNBIND_MAX_TOKENS = 6
OBSERVED_MW_HARVEST_NAME = "harvest_unbind_observed_mw.jsonl"


def _unbind_dual_scheme_rows(
    atom: str,
    tokens: list[str],
    *,
    lineage: str,
    stage: str,
    epistemic: str,
    pos_provenance: str,
    type_provenance: str,
    license: str | None = None,
) -> list[dict[str, Any]]:
    """Emit positional + type_slot unbind rows. Fillers = real tokens only."""
    if lineage not in FAMILIES and lineage != "none":
        lineage = "none"
    extra: dict[str, Any] = {}
    if license:
        extra["license"] = license
    pos = _row(
        text=atom,
        lineage=lineage,
        typology=TYPOLOGY.get(lineage, []),
        stage=stage,
        roles=[f"pos_{k}" for k in range(len(tokens))],
        fillers=tokens,
        role_scheme="positional",
        task="unbind",
        provenance=pos_provenance,
        **{"class": epistemic},
        **extra,
    )
    tags = _structural_type_tags(len(tokens))
    typ = _row(
        text=" ".join(f"{t}:{tok}" for t, tok in zip(tags, tokens)),
        lineage=lineage,
        typology=TYPOLOGY.get(lineage, []),
        stage=stage,
        roles=tags,
        fillers=tokens,
        role_scheme="type_slot",
        task="unbind",
        provenance=type_provenance,
        **{"class": epistemic},
        **extra,
    )
    return [pos, typ]


def _positional_unbind_atoms(rows: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for row in rows:
        if row.get("task") != "unbind" or row.get("role_scheme") != "positional":
            continue
        text = str(row.get("text") or "").strip()
        if text:
            out.add(text.lower())
    return out


def _phrase_like_atom(text: str) -> tuple[str, list[str]] | None:
    """Return (stripped atom, tokens) for short multiword SoT phrases, else None."""
    atom = (text or "").strip()
    if not atom or " " not in atom:
        return None
    if len(atom) > LIVE_UNBIND_MAX_LEN:
        return None
    if atom.lower() in COLLISION_HOLD:
        return None
    tokens = [t for t in atom.split() if t]
    if len(tokens) < 2 or len(tokens) > LIVE_UNBIND_MAX_TOKENS:
        return None
    if reject_candidate_text(atom):
        return None
    return atom, tokens


def _live_unbind_epistemic(raw: dict[str, Any]) -> str:
    """Copy store epistemic. Missing/None → INFERRED. Never invent OBSERVED."""
    for key in ("epistemic", "class"):
        if key not in raw:
            continue
        val = raw.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            continue
        return _norm_class(str(val), "INFERRED")
    return "INFERRED"


def _live_unbind_lineage(raw: dict[str, Any]) -> str:
    for key in ("lineage", "family", "family_id", "lineage_family"):
        val = raw.get(key)
        if not val:
            continue
        fam = str(val).strip()
        if fam in FAMILIES or fam == "none":
            return fam
    return "none"


def _default_held_unbind_atoms() -> set[str]:
    """Civilian + fixture positional atoms. Fail-open if inventory cannot load."""
    try:
        return _positional_unbind_atoms(harvest_unbind() + harvest_civilian_unbind(repo_root()))
    except Exception:
        return set()


def harvest_civilian_unbind(root: Path) -> list[dict[str, Any]]:
    """Civilian unbind for multiword atoms under BOTH schemes.

    Fillers = real token atoms from golden/registry/dialect only.
    type_slot roles = structural TOKEN/SLOT/MARKER (no gloss invent).
    Collision-hold (`skill issue`) skipped on all paths (C37 / harvest card).
    """
    rows: list[dict[str, Any]] = []
    seen_atom: set[str] = set()

    def _add(text: str, lineage: str, source_tag: str) -> None:
        atom = text.strip()
        if not atom or " " not in atom:
            return
        key = atom.lower()
        if key in COLLISION_HOLD or key in seen_atom:
            return
        tokens = [t for t in atom.split() if t]
        if len(tokens) < 2:
            return
        seen_atom.add(key)
        rows.extend(
            _unbind_dual_scheme_rows(
                atom,
                tokens,
                lineage=lineage,
                stage="circulating",
                epistemic="OBSERVED",
                pos_provenance=f"civilian-pos:{source_tag}",
                type_provenance=f"civilian-type:{source_tag}",
            )
        )

    gold = root / "examples" / "receipts" / "golden"
    if gold.is_dir():
        for path in sorted(gold.glob("*.json")):
            if path.name == "MANIFEST.json":
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            lineage = (data.get("analysis") or {}).get("lineage") or {}
            fam = lineage.get("family_id") or "none"
            for term in lineage.get("matched_terms") or []:
                if isinstance(term, str) and " " in term.strip():
                    _add(term.strip(), fam, f"golden:{path.name}")

    for entry in load_registry(root):
        fam = entry.get("family_id") or "none"
        for term in entry.get("terms") or []:
            if isinstance(term, str) and " " in term.strip():
                _add(term.strip(), fam, f"registry:{fam}")

    for text in DIALECT:
        if " " in text:
            _add(text, "brainrot-aura", "seed:dialect-e6")

    return rows


def harvest_inferred_classify_pass(root: Path) -> list[dict[str, Any]]:
    """Optional INFERRED classify rows from harvest classify-pass artifact.

    Never upgrades class to OBSERVED. Missing file → empty list.
    """
    path = root / "specs" / "007-hyperlexical-model" / "harvest" / "inferred_classify_pass.jsonl"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        if reject_candidate_text(text):
            continue
        fam = raw.get("lineage") or "none"
        if fam not in FAMILIES and fam != "none":
            fam = "none"
        if text.lower() in COLLISION_HOLD:
            fam = "none"
        try:
            rows.append(
                _row(
                    text=text,
                    lineage=fam,
                    typology=list(raw.get("typology") or TYPOLOGY.get(fam, [])),
                    stage=raw.get("stage") or "circulating",
                    task="classify",
                    provenance=str(raw.get("provenance") or "harvest:classify-pass"),
                    **{"class": "INFERRED"},
                    role_scheme=None,
                    license=str(raw.get("license") or "operator-local; labels INFERRED"),
                    split=raw.get("split"),
                )
            )
        except ValueError:
            continue
    return rows


def harvest_dialect() -> list[dict[str, Any]]:
    return [
        _row(
            text=text,
            lineage="brainrot-aura",
            typology=["compression"],
            task="classify",
            provenance="seed:dialect-e6",
            **{"class": "OBSERVED"},
            role_scheme=None,
        )
        for text in DIALECT
    ]


def harvest_negatives() -> list[dict[str, Any]]:
    return [
        _row(
            text=text,
            lineage="none",
            typology=[],
            stage="noise",
            task="classify",
            provenance="seed:negative-prose",
            **{"class": "OBSERVED"},
            role_scheme=None,
        )
        for text in NEGATIVES
    ]


def harvest_moltbook(root: Path) -> list[dict[str, Any]]:
    """Moltbook agent discourse → ai-native rows for hyperlexical training.
    Uses pre-classified rows from scripts/moltbook_to_hyperlexical.py
    (memory tiers, efficiency, provenance, context loss).
    Also loads dedicated high-signal subset when present (for oversampling strong memory/provenance signals).
    """
    rows = []
    for p in [
        root / "data" / "moltbook_hyperlexical_rows.jsonl",
        root / "data" / "moltbook_hyperlexical_high.jsonl",
        root / "data" / "moltbook_hyperlexical_high_signal.jsonl",
    ]:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                if r.get("lineage") == "ai-native":
                    rows.append(
                        _row(
                            text=r.get("text", ""),
                            lineage="ai-native",
                            typology=r.get("typology", ["compression"]),
                            stage=r.get("stage", "circulating"),
                            roles=r.get("roles", []),
                            fillers=r.get("fillers", []),
                            role_scheme=r.get("role_scheme"),
                            task="classify+unbind",
                            provenance=r.get("provenance", {"source": "moltbook"}),
                            **{"class": r.get("class", "INFERRED")},
                            license=r.get("license", "MIT (distilled)"),
                        )
                    )
            except Exception:
                continue
    return rows


def dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedupe by (task, text, role_scheme, lineage).

    First-seen order is preserved, but a later row with a stronger ``class``
    upgrades the kept row (OBSERVED > INFERRED > other). This lets
    ``--include-live`` settled OBSERVED replace an earlier base INFERRED
    duplicate without inventing new OBSERVED labels.
    """
    rank = {"OBSERVED": 2, "INFERRED": 1, "SPECULATIVE": 0}
    best: dict[tuple, dict[str, Any]] = {}
    order: list[tuple] = []
    for row in rows:
        key = (row["task"], row["text"], row.get("role_scheme"), row["lineage"])
        if key not in best:
            best[key] = row
            order.append(key)
            continue
        prev = best[key]
        if rank.get(str(row.get("class")), 0) > rank.get(str(prev.get("class")), 0):
            best[key] = row
    return [best[k] for k in order]


def reject_candidate_text(text: str) -> str | None:
    """Return reject reason for junk live candidates, else None.

    Filters: empty/punct-only, len≤2, pure numeric, Unsupported titles.
    SHORT_SLANG_ALLOWLIST exempts known slang/codes from len/numeric kills.
    Does not promote or settle labels.
    """
    raw = (text or "").strip()
    if not raw:
        return "empty"
    low = raw.lower()
    if low in SHORT_SLANG_ALLOWLIST:
        return None
    alnum = "".join(ch for ch in raw if ch.isalnum())
    if not alnum:
        return "punct_only"
    if alnum.isdigit():
        return "numeric"
    # numeric-ish codes with separators (4/20, 10-4) — still reject unless allowlisted
    if all(ch.isdigit() or ch in "-/:." for ch in raw) and any(ch.isdigit() for ch in raw):
        return "numeric"
    if len(raw) <= 2:
        return "len_le_2"
    if "unsupported title" in low or low.startswith("unsupported"):
        return "unsupported_title"
    return None


class LiveStoreMissing(FileNotFoundError):
    """include-live was requested but the candidate store is not on disk."""


def default_live_store() -> Path:
    override = os.environ.get("HYPERLEX_LIVE_STORE", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".hyperlex" / "hyperlexical" / "ingest_candidates.jsonl"


def resolve_live_store(live_store: Path | None = None, *, required: bool = False) -> Path:
    store = Path(live_store) if live_store is not None else default_live_store()
    if required and not store.is_file():
        raise LiveStoreMissing(
            f"include-live requested but live store missing: {store}. "
            "Write ingest_candidates.jsonl or unset --include-live / HYPERLEX_INCLUDE_LIVE."
        )
    return store


def load_live_candidates(store: Path) -> list[dict[str, Any]]:
    """Load SHADOW ingest candidates for --include-live.

    Copies ``class`` from the candidate store (OBSERVED stays OBSERVED).
    Unset / unknown / SPECULATIVE → INFERRED. Never invents OBSERVED.
    """
    if not store.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in store.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw_row = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = str(raw_row.get("text") or "")
        if reject_candidate_text(text):
            continue
        prov = str(raw_row.get("provenance") or "ingest:store")
        # Preserve settled OBSERVED; default unset/live crawl to INFERRED.
        cls = _norm_class(raw_row.get("class"), "INFERRED")
        label_tag = f"labels {cls}"
        if prov.startswith("ingest:inbox") or "wiktionary" in prov.lower():
            license_ = f"CC-BY-SA-4.0+GFDL (Wiktionary text); {label_tag}"
        elif prov.startswith("ingest:pipeline"):
            license_ = f"operator-local-crawl; {label_tag}"
        else:
            license_ = str(raw_row.get("license") or "operator-local") + f"; {label_tag}"
        fam = raw_row.get("lineage") or "none"
        if fam not in FAMILIES and fam not in {"none", "ytd_leaf"}:
            fam = "none"
        try:
            out.append(
                _row(
                    text=text,
                    split=raw_row.get("split"),
                    lineage=fam,
                    typology=list(raw_row.get("typology") or TYPOLOGY.get(fam, [])),
                    stage=raw_row.get("stage") or "circulating",
                    roles=list(raw_row.get("roles") or []),
                    fillers=list(raw_row.get("fillers") or []),
                    role_scheme=raw_row.get("role_scheme"),
                    task=raw_row.get("task") or "classify",
                    provenance=prov if prov.endswith(":live") else f"{prov}:live",
                    **{"class": cls},
                    license=license_,
                )
            )
        except ValueError:
            continue
    return out


def _iter_jsonl_dicts(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict):
            out.append(raw)
    return out


def resolve_observed_mw_harvest(
    live_store: Path,
    explicit: Path | None = None,
) -> Path | None:
    """Wave A OBSERVED sidecar next to the live store (Spark path).

    Sibling ``harvest_unbind_observed_mw.jsonl``, or ``HYPERLEX_LIVE_UNBIND_OBSERVED``.
    Missing file → None. Filename does not invent OBSERVED labels.
    """
    if explicit is not None:
        path = Path(explicit)
        return path if path.is_file() else None
    env = os.environ.get("HYPERLEX_LIVE_UNBIND_OBSERVED", "").strip()
    if env:
        path = Path(env)
        return path if path.is_file() else None
    sibling = Path(live_store).expanduser().resolve().parent / OBSERVED_MW_HARVEST_NAME
    return sibling if sibling.is_file() else None


def _atom_key_from_unbind_row(row: dict[str, Any]) -> str:
    if row.get("role_scheme") == "positional":
        return str(row.get("text") or "").strip().lower()
    fillers = [str(t).strip() for t in (row.get("fillers") or []) if str(t).strip()]
    return " ".join(fillers).lower()


def _formed_unbind_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Adopt an already-built unbind row. Never upgrades missing class to OBSERVED."""
    task = raw.get("task")
    if task not in (None, "unbind"):
        return None
    scheme = _norm_role_scheme(raw.get("role_scheme"))
    if scheme not in SCHEMES:
        return None
    text = str(raw.get("text") or "").strip()
    fillers = [str(t) for t in (raw.get("fillers") or []) if str(t).strip()]
    roles = [str(t) for t in (raw.get("roles") or []) if str(t).strip()]
    if not text or not fillers or len(roles) != len(fillers):
        return None
    epistemic = _live_unbind_epistemic(raw)
    lineage = _live_unbind_lineage(raw)
    stage = str(raw.get("stage") or "").strip() or "circulating"
    license_ = raw.get("license")
    if not isinstance(license_, str) or not license_.strip():
        license_ = "operator-local"
    prefix = "live-pos:" if scheme == "positional" else "live-type:"
    prov = str(raw.get("provenance") or "")
    if not prov.startswith(("live-pos:", "live-type:")):
        prov = f"{prefix}{epistemic}"
    try:
        return _row(
            text=text,
            lineage=lineage,
            typology=list(raw.get("typology") or TYPOLOGY.get(lineage, [])),
            stage=stage,
            roles=roles,
            fillers=fillers,
            role_scheme=scheme,
            task="unbind",
            provenance=prov,
            **{"class": epistemic},
            license=license_,
        )
    except ValueError:
        return None


def _phrase_unbind_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = _phrase_like_atom(str(raw.get("text") or ""))
    if parsed is None:
        return []
    atom, tokens = parsed
    epistemic = _live_unbind_epistemic(raw)
    lineage = _live_unbind_lineage(raw)
    stage = str(raw.get("stage") or "").strip() or "circulating"
    license_ = raw.get("license")
    if not isinstance(license_, str) or not license_.strip():
        license_ = "operator-local"
    try:
        return _unbind_dual_scheme_rows(
            atom,
            tokens,
            lineage=lineage,
            stage=stage,
            epistemic=epistemic,
            pos_provenance=f"live-pos:{epistemic}",
            type_provenance=f"live-type:{epistemic}",
            license=license_,
        )
    except ValueError:
        return []


def harvest_live_unbind(
    live_store: Path,
    *,
    skip_atoms: set[str] | None = None,
    observed_harvest: Path | None = None,
) -> list[dict[str, Any]]:
    """Live SoT phrase-like atoms → dual-scheme unbind rows.

    Selects stripped multiword text (2–6 whitespace tokens, len≤80, not
    collision-hold). Dedupes by lowercased atom and skips civilian/fixture
    atoms when ``skip_atoms`` is omitted. Epistemic is copied from the row
    (``epistemic`` then ``class``); missing/None → INFERRED. Never upgraded
    to OBSERVED. Fillers are the real tokens — no gloss invention.

    When a Wave A sidecar ``harvest_unbind_observed_mw.jsonl`` sits next to
    the live store (Spark OBSERVED set, 229 atoms × dual scheme), those rows
    are adopted with their stored class. Filename does not invent OBSERVED.
    Live-store leftovers stay INFERRED unless the store row is already
    OBSERVED. Missing store → empty list (export_dataset fail-closes
    include-live).
    """
    store = Path(live_store)
    if not store.is_file():
        return []
    held = set(skip_atoms) if skip_atoms is not None else _default_held_unbind_atoms()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()

    def _take(raw: dict[str, Any], *, apply_held: bool) -> None:
        formed = _formed_unbind_row(raw)
        if formed is not None:
            key = _atom_key_from_unbind_row(formed)
            if not key or key in COLLISION_HOLD:
                return
            if apply_held and key in held:
                return
            pair = (key, str(formed.get("role_scheme") or ""))
            if pair in seen_pairs:
                return
            seen_pairs.add(pair)
            seen.add(key)
            rows.append(formed)
            return
        emitted = _phrase_unbind_rows(raw)
        if not emitted:
            return
        key = _atom_key_from_unbind_row(emitted[0])
        if not key or key in COLLISION_HOLD or key in seen:
            return
        if apply_held and key in held:
            return
        seen.add(key)
        for row in emitted:
            seen_pairs.add((key, str(row.get("role_scheme") or "")))
        rows.extend(emitted)

    sidecar = resolve_observed_mw_harvest(store, explicit=observed_harvest)
    if sidecar is not None:
        # Operator-settled Wave A set — do not drop civilian overlap; do not upgrade.
        for raw in _iter_jsonl_dicts(sidecar):
            _take(raw, apply_held=False)
    for raw in _iter_jsonl_dicts(store):
        _take(raw, apply_held=True)
    return rows


def export_dataset(
    root: Path | None = None,
    *,
    include_live: bool = False,
    live_store: Path | None = None,
) -> dict[str, Any]:
    root = root or repo_root()
    rows = (
        harvest_dialect()
        + harvest_backfill(root)
        + harvest_registry(root)
        + harvest_receipts(root)
        + harvest_archive(root)
        + harvest_unbind()
        + harvest_civilian_unbind(root)
        + harvest_negatives()
        + harvest_inferred_classify_pass(root)
        + harvest_moltbook(root) + harvest_4333_dump(root)
    )
    live_n = 0
    live_rejected = 0
    if include_live:
        store = resolve_live_store(live_store, required=True)
        # count rejects for manifest
        for line in store.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw_row = json.loads(line)
            except json.JSONDecodeError:
                live_rejected += 1
                continue
            if reject_candidate_text(str(raw_row.get("text") or "")):
                live_rejected += 1
        live_rows = load_live_candidates(store)
        live_n = len(live_rows)
        held = _positional_unbind_atoms(rows)
        live_unbind = harvest_live_unbind(store, skip_atoms=held)
        rows = rows + live_rows + live_unbind
    rows = dedupe(rows)
    rows.sort(key=lambda r: (r["task"], r["lineage"], r["text"]))
    payload = "\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    def _is_ordinary_prose_neg(r: dict[str, Any]) -> bool:
        """Name-gate negatives bucket = curated ordinary-prose only.

        Live / inbox ``lineage=none`` classify rows are *not* negatives — they are
        unclassified family-gap inventory. Folding them into ``counts.negatives``
        inflated the 200-neg quota (e.g. 2766 with ``--include-live``).
        """
        if r["task"] != "classify" or r["lineage"] != "none":
            return False
        return str(r.get("provenance") or "").startswith("seed:negative-prose")

    def _is_none_classify(r: dict[str, Any]) -> bool:
        return r["task"] == "classify" and r["lineage"] == "none"

    def _is_family_classify(r: dict[str, Any]) -> bool:
        return r["task"] == "classify" and r["lineage"] != "none"

    def _is_unbind_fixture(r: dict[str, Any]) -> bool:
        return r["task"] == "unbind" and str(r.get("provenance") or "").startswith("004:")

    def _is_unbind_civilian(r: dict[str, Any]) -> bool:
        prov = str(r.get("provenance") or "")
        return r["task"] == "unbind" and (
            prov.startswith("civilian-pos:") or prov.startswith("civilian-type:")
        )

    def _is_unbind_live(r: dict[str, Any]) -> bool:
        prov = str(r.get("provenance") or "")
        return r["task"] == "unbind" and (
            prov.startswith("live-pos:") or prov.startswith("live-type:")
        )

    classify_all = sum(1 for r in rows if r["task"] == "classify")
    classify_family = sum(1 for r in rows if _is_family_classify(r))
    classify_none = sum(1 for r in rows if _is_none_classify(r))
    negatives = sum(1 for r in rows if _is_ordinary_prose_neg(r))
    unbind_all = sum(1 for r in rows if r["task"] == "unbind")
    unbind_fixture = sum(1 for r in rows if _is_unbind_fixture(r))
    unbind_civilian = sum(1 for r in rows if _is_unbind_civilian(r))
    unbind_live = sum(1 for r in rows if _is_unbind_live(r))
    unbind_live_observed = sum(
        1 for r in rows if _is_unbind_live(r) and r.get("class") == "OBSERVED"
    )
    unbind_live_inferred = sum(
        1 for r in rows if _is_unbind_live(r) and r.get("class") == "INFERRED"
    )
    # Honesty: classify gate uses family-labeled rows only.
    # Negatives = ordinary-prose seed only (NOT live lineage=none classify).
    # Unbind = fixture(honest n=24) + civilian dual-scheme + optional live phrases.
    # Live OBSERVED vs INFERRED are counted separately — no class upgrade.
    # include_live does not flip name_gate. E2 stays on Spec 004 fixtures.
    counts = {
        "n": len(rows),
        "classify": classify_family,  # EXCLUDES negatives (honest name-gate family quota)
        "classify_all": classify_all,  # family + none-classify; do not use for 2k gate
        "classify_none": classify_none,  # all lineage=none classify (incl live inbox)
        "unbind": unbind_all,
        "unbind_fixture": unbind_fixture,
        "unbind_civilian": unbind_civilian,
        "unbind_live": unbind_live,
        "unbind_live_observed": unbind_live_observed,
        "unbind_live_inferred": unbind_live_inferred,
        "negatives": negatives,  # ordinary-prose only (seed:negative-prose)
        "dialect": sum(1 for r in rows if r["provenance"] == "seed:dialect-e6"),
        "backfill": sum(1 for r in rows if str(r["provenance"]).startswith("backfill:")),
        "observed": sum(1 for r in rows if r["class"] == "OBSERVED"),
        "inferred": sum(1 for r in rows if r["class"] == "INFERRED"),
        "train": sum(1 for r in rows if r["split"] == "train"),
        "val": sum(1 for r in rows if r["split"] == "val"),
        "test": sum(1 for r in rows if r["split"] == "test"),
        "live_included": live_n if include_live else 0,
        "live_rejected": live_rejected if include_live else 0,
        "name_gate": False,
        "name_gate_classify_gap": max(0, 2000 - classify_family),
        "name_gate_unbind_gap": max(0, 200 - unbind_all),
        "name_gate_negative_gap": max(0, 200 - negatives),
    }
    # Recipe gates are documented here; the Hyperlexical loop applies
    # upsample/cap + morph hard-negs + optional scheme curriculum.
    # Export rows stay SoT-shaped.
    unbind_only = [r for r in rows if r["task"] == "unbind"]
    counts.update(recipe_env_counts(unbind_only))
    return {"rows": rows, "sha256": digest, "counts": counts, "payload": payload}


def write_export(out_dir: Path, bundle: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl = out_dir / "civilian.v0.1.jsonl"
    manifest = out_dir / "MANIFEST.json"
    jsonl.write_text(bundle["payload"], encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "schema": "hyperlex.hyperlexical.dataset.v0.1",
                "file": jsonl.name,
                "sha256": bundle["sha256"],
                "counts": bundle["counts"],
                "brier": None,
                "trunk": "answerdotai/ModernBERT-base",
                "note": (
                    "Honest accounting: counts.classify = family-labeled only "
                    "(excludes negatives). counts.negatives = ordinary-prose "
                    "(seed:negative-prose) only — not live lineage=none classify "
                    "(see classify_none). unbind_fixture / unbind_civilian / unbind_live "
                    "(unbind_live_observed vs unbind_live_inferred). "
                    "Spec004 fixtures at n=24; civilian dual-scheme from golden/registry "
                    "(no gloss invent). Live optional via --include-live (preserves store class; "
                    "unset→INFERRED; phrase-like atoms also harvest as unbind; Wave A sidecar "
                    "harvest_unbind_observed_mw.jsonl is adopted, not upgraded). "
                    "E2 stays on Spec 004 fixtures. Not a T1 name-gate. "
                    "n_unbind_observed / n_unbind_inferred plus recipe env "
                    "(HYPERLEX_UNBIND_OBSERVED_UPSAMPLE default 1, "
                    "HYPERLEX_UNBIND_INFERRED_CAP 0=off (hard low caps can starve morph-negs), unbind_morph_negatives, "
                    "HYPERLEX_UNBIND_CURRICULUM default 0) "
                    "are counts only — loop applies train multiplicity / hard-negs / "
                    "scheme-split curriculum; "
                    "export does not invent OBSERVED SoT gold. lexical_split is frozen."
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return jsonl


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hyperlexical-export")
    p.add_argument(
        "--out",
        default="",
        help="directory; default specs/007-hyperlexical-model/exports",
    )
    p.add_argument(
        "--include-live",
        action="store_true",
        help="merge ~/.hyperlex/.../ingest_candidates.jsonl; preserve store class (OBSERVED stays OBSERVED; unset→INFERRED; reject junk)",
    )
    p.add_argument(
        "--live-store",
        default="",
        help="optional path to ingest_candidates.jsonl",
    )
    args = p.parse_args(argv)
    root = repo_root()
    dest = Path(args.out) if args.out else root / "specs" / "007-hyperlexical-model" / "exports"
    store = Path(args.live_store) if args.live_store else None
    try:
        bundle = export_dataset(root, include_live=bool(args.include_live), live_store=store)
    except LiveStoreMissing as exc:
        print(json.dumps({"abort": True, "error": str(exc), "brier": None}, indent=2), file=sys.stderr)
        return 2
    path = write_export(dest, bundle)
    print(json.dumps({"wrote": str(path), "sha256": bundle["sha256"], "counts": bundle["counts"]}, indent=2))
    return 0



def harvest_4333_dump(root: Path) -> list[dict[str, Any]]:
    """4333-row Notion vernacular dump. Pre-classified rows only.

    Fail-closed: no hyperlex/abraxas import. Dump fields only.
    Unknown ``role_scheme`` values (including leftover ``civilian``) drop to
    None — recoverable_structure allows positional|type_slot.
    """
    rows = []
    dump_file = root / "data" / "hyperlex_4333_dump.jsonl"
    if not dump_file.exists():
        print("[harvest_4333_dump] no dump file, skipping")
        return rows

    for line in dump_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            text = (r.get("text") or r.get("term") or "").strip()
            if not text or len(text) < 2:
                continue

            lineage = r.get("lineage", "ai-native")
            if lineage in ("brainrot-aura", "ai-native"):
                lineage = "ai-native"

            typology = r.get("typology", ["compression", "status"])
            if lineage == "ai-native":
                typology = list(set(typology + ["compression", "memory", "provenance", "context", "vernacular"]))

            rows.append(
                _row(
                    text=text,
                    lineage=lineage,
                    typology=typology,
                    stage=r.get("stage", "circulating"),
                    roles=r.get("roles", ["slang", "memetic"]),
                    fillers=r.get("fillers", []),
                    role_scheme=r.get("role_scheme"),
                    task="classify",
                    provenance={
                        "source": "notion",
                        "page": "Hyperlex-Vernacular-export-2026-09-10",
                        "original_provenance": r.get("provenance"),
                        "reclassify_pass": r.get("reclassify_pass"),
                        "settle_note": r.get("settle_note"),
                    },
                    **{"class": r.get("class", "INFERRED")},
                    license=r.get("license", "operator-local"),
                )
            )
        except Exception:
            continue
    print(f"[harvest_4333_dump] loaded {len(rows)} rows")
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
