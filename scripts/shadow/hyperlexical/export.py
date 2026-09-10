"""U2 civilian exporter. No hyperlex import. No ~/.hyperlex copy."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .packet import RESTRICTED_MARKER, sha256_hex

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
    "ai-native": ["compression"],
    "brainrot-aura": ["compression", "status"],
    "kinship-address": ["tribal"],
    "political-status": ["tribal", "irony_shield"],
    "gaming-meta": ["status", "hook"],
    "workplace-corp": ["camouflage"],
}

NEGATIVES = (
    "The committee approved the budget amendment.",
    "Water boils at one hundred degrees Celsius.",
    "Please find the attached invoice for March.",
    "The museum opens at ten on weekdays.",
    "Photosynthesis converts light into chemical energy.",
    "The train to Sacramento leaves from platform two.",
    "This warranty covers defects in materials.",
    "Average rainfall in July was two inches.",
    "The library card expires in December.",
    "Sodium chloride is table salt.",
    "The board meeting is scheduled for Tuesday.",
    "A rectangle has four right angles.",
    "Please confirm receipt of this shipment.",
    "The periodic table lists the elements.",
    "Oak trees drop acorns in autumn.",
    "The speed limit on this road is twenty five.",
    "This paragraph contains no slang tokens.",
    "The recipe calls for two cups of flour.",
    "Latitude and longitude specify a point.",
    "The contract is governed by California law.",
)

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


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def lexical_split(text: str) -> str:
    n = int(sha256_hex(text.lower())[:8], 16) % 10
    if n == 0:
        return "test"
    if n == 1:
        return "val"
    return "train"


def _row(**kwargs: Any) -> dict[str, Any]:
    text = kwargs["text"]
    if RESTRICTED_MARKER in text:
        raise ValueError("restricted text")
    out = {k: kwargs.get(k) for k in ROW_KEYS}
    out["split"] = kwargs.get("split") or lexical_split(text)
    out["typology"] = list(out.get("typology") or [])
    out["roles"] = list(out.get("roles") or [])
    out["fillers"] = list(out.get("fillers") or [])
    out["license"] = out.get("license") or "MIT-examples"
    out["stage"] = out.get("stage") or "circulating"
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
                    **{"class": "OBSERVED"},
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
                    **{"class": "OBSERVED"},
                    role_scheme=None,
                )
            )
    return rows


def harvest_unbind(n: int = 24) -> list[dict[str, Any]]:
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


def dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for row in rows:
        key = (row["task"], row["text"], row.get("role_scheme"), row["lineage"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def export_dataset(root: Path | None = None) -> dict[str, Any]:
    root = root or repo_root()
    rows = dedupe(
        harvest_dialect()
        + harvest_registry(root)
        + harvest_receipts(root)
        + harvest_unbind()
        + harvest_negatives()
    )
    rows.sort(key=lambda r: (r["task"], r["lineage"], r["text"]))
    payload = "\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    counts = {
        "n": len(rows),
        "classify": sum(1 for r in rows if r["task"] == "classify"),
        "unbind": sum(1 for r in rows if r["task"] == "unbind"),
        "negatives": sum(1 for r in rows if r["lineage"] == "none" and r["task"] == "classify"),
        "dialect": sum(1 for r in rows if r["provenance"] == "seed:dialect-e6"),
        "train": sum(1 for r in rows if r["split"] == "train"),
        "val": sum(1 for r in rows if r["split"] == "val"),
        "test": sum(1 for r in rows if r["split"] == "test"),
    }
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
                "note": "Civilian gold from repo fixtures. Not a T1 name-gate. No ledger copy.",
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
    args = p.parse_args(argv)
    root = repo_root()
    dest = Path(args.out) if args.out else root / "specs" / "007-hyperlexical-model" / "exports"
    bundle = export_dataset(root)
    path = write_export(dest, bundle)
    print(json.dumps({"wrote": str(path), "sha256": bundle["sha256"], "counts": bundle["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
