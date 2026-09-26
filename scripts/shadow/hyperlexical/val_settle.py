"""Operator-authorized val-settle + force/hard expand. No torch. No network.

Canonical port of the Spark per-morph launchers (``promote_launch_morph7x_
val_settle.py``, archived under ``scripts/spark/soft_ceiling/archive/``).
Settles named phrases INFERRED→OBSERVED in the local SoT, appends dual-scheme
(positional + type_slot) OBSERVED unbind rows to the harvest sidecar, and
expands force-train / hard-atom files. Never invents phrases: every phrase is
passed explicitly with its lineage by the operator.

``split_policy``:
  - ``force_val`` (morph77/78 history): settled rows get ``split=val`` and are
    also force-trained. The soft_ceiling gate then excludes them from its
    clean surface (``soft_ceiling.clean_surface``).
  - ``train``: settled rows get ``split=train``; val is untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

TYPE_SLOT_TAGS = ("TOKEN", "SLOT", "MARKER")
TYPOLOGY = {
    "brainrot-aura": ["compression", "status"],
    "gaming-meta": ["status", "tribal"],
    "kinship-address": ["tribal"],
    "crypto-degen": ["status", "tribal"],
}
POLICIES = ("force_val", "train")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def type_slot_text(tokens: list[str]) -> str:
    tags = [TYPE_SLOT_TAGS[i % len(TYPE_SLOT_TAGS)] for i in range(len(tokens))]
    return " ".join(f"{tag}:{tok}" for tag, tok in zip(tags, tokens))


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def settle_rows(
    *,
    phrases: dict[str, str],
    tag: str,
    auth: str,
    store: list[dict],
    harvest: list[dict],
    force: list[dict],
    hard: list[dict],
    labeled: list[dict] | None = None,
    split_policy: str = "force_val",
    provenance: str = "",
) -> dict:
    """Pure settle over in-memory rows. Mutates and returns the lists + summary."""
    if split_policy not in POLICIES:
        raise ValueError(f"split_policy must be one of {POLICIES}")
    if not phrases:
        raise ValueError("no phrases: settle needs explicit operator-named phrases")
    split = "val" if split_policy == "force_val" else "train"
    by_norm = {_norm(r.get("text") or ""): r for r in (labeled or [])}
    obs = {_norm(str(r.get("text") or "")) for r in store if str(r.get("class") or "").upper() == "OBSERVED"}
    store_idx = {_norm(str(r.get("text") or "")): i for i, r in enumerate(store)}
    force_keys = {(_norm(str(r.get("text") or "")), str(r.get("role_scheme") or "")) for r in force}
    harvest_keys = {(_norm(str(r.get("text") or "")), str(r.get("role_scheme") or "")) for r in harvest}
    force_base, hard_base = len(force), len(hard)
    settled, already, added = [], [], []

    for phrase, lineage in phrases.items():
        src = by_norm.get(_norm(phrase)) or {}
        toks = [t.lower() for t in (src.get("gold_fillers") or phrase.split())]
        plain = " ".join(toks)
        key = _norm(plain)
        lineage = lineage or src.get("lineage") or "none"
        note = f"PACKET_SETTLE {tag} val-settle;{auth}"
        if key in obs:
            already.append(plain)
            if key in store_idx:
                row = dict(store[store_idx[key]])
                row["split"] = split
                row["settle_note"] = (str(row.get("settle_note") or "") + f"|{tag}_settle_{split_policy};{auth}").strip("|")
                row["authorization"] = auth
                store[store_idx[key]] = row
        else:
            if key in store_idx:
                row = dict(store[store_idx[key]])
                row.update(
                    {
                        "class": "OBSERVED",
                        "epistemic": "OBSERVED",
                        "text": plain,
                        "split": split,
                        "lineage": lineage,
                        "typology": TYPOLOGY.get(lineage, row.get("typology") or []),
                        "settle_note": (str(row.get("settle_note") or "") + "|" + note).strip("|"),
                        "authorization": auth,
                    }
                )
                store[store_idx[key]] = row
            else:
                store.append(
                    {
                        "text": plain,
                        "class": "OBSERVED",
                        "lineage": lineage,
                        "typology": TYPOLOGY.get(lineage, []),
                        "task": "classify",
                        "stage": "circulating",
                        "role_scheme": None,
                        "roles": [],
                        "fillers": [],
                        "provenance": provenance or f"ingest:acquire:{tag}",
                        "license": "operator-local-crawl",
                        "epistemic": "OBSERVED",
                        "split": split,
                        "settle_note": note,
                        "authorization": auth,
                    }
                )
                store_idx[key] = len(store) - 1
            obs.add(key)
            settled.append(plain)

        for scheme, ftext, roles in (
            ("positional", plain, [f"pos_{i}" for i in range(len(toks))]),
            ("type_slot", type_slot_text(toks), [TYPE_SLOT_TAGS[i % 3] for i in range(len(toks))]),
        ):
            hk = (_norm(ftext), scheme)
            if hk not in harvest_keys:
                harvest.append(
                    {
                        "class": "OBSERVED",
                        "fillers": toks,
                        "license": "operator-local; labels OBSERVED; unbind structural whitespace",
                        "lineage": lineage,
                        "provenance": f"civilian-{'pos' if scheme == 'positional' else 'type'}:{tag}-val-settle",
                        "role_scheme": scheme,
                        "roles": roles,
                        "split": split,
                        "stage": "circulating",
                        "task": "unbind",
                        "text": ftext,
                        "typology": TYPOLOGY.get(lineage, []),
                        "authorization": auth,
                    }
                )
                harvest_keys.add(hk)
            if hk in force_keys:
                continue
            force_keys.add(hk)
            fid = f"{tag}-val-" + hashlib.sha1(f"{ftext}|{scheme}".encode()).hexdigest()[:12]
            base = {
                "text": ftext,
                "role_scheme": scheme,
                "gold_fillers": toks,
                "gold_roles": roles,
                "id": fid,
                "source": f"val_settle_{tag}",
                "authorization": auth,
                "dataset_class_source": "OBSERVED",
            }
            force.append({**base, "promoted_to_observed_train": False, "split_hint": split})
            hard.append(dict(base))
            added.append(ftext)

    return {
        "auth": auth,
        "as_of": _now(),
        "tag": tag,
        "qualify": list(phrases),
        "settled_inferred_to_observed": settled,
        "already_observed": already,
        "force_base": force_base,
        "force_out": len(force),
        "force_added": len(force) - force_base,
        "hard_base": hard_base,
        "hard_out": len(hard),
        "hard_added": len(hard) - hard_base,
        "added_force_texts": added,
        "split_policy": split_policy,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--tag", required=True, help="e.g. morph79")
    p.add_argument("--auth", required=True, help="operator sentence, quoted")
    p.add_argument("--phrase", action="append", required=True, help="PHRASE=LINEAGE (repeat)")
    p.add_argument("--store", required=True)
    p.add_argument("--harvest", required=True)
    p.add_argument("--force-base", required=True)
    p.add_argument("--hard-base", required=True)
    p.add_argument("--force-out", required=True)
    p.add_argument("--hard-out", required=True)
    p.add_argument("--labeled", default="", help="labeled_acquired_atoms.jsonl (gold fillers)")
    p.add_argument("--split-policy", default="force_val", choices=POLICIES)
    p.add_argument("--summary", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    phrases = {}
    for item in args.phrase:
        if "=" not in item:
            p.error(f"--phrase needs PHRASE=LINEAGE, got {item!r}")
        text, lineage = item.rsplit("=", 1)
        phrases[text.strip()] = lineage.strip()
    store_p, harvest_p = Path(args.store), Path(args.harvest)
    store, harvest = load_jsonl(store_p), load_jsonl(harvest_p)
    force, hard = load_jsonl(Path(args.force_base)), load_jsonl(Path(args.hard_base))
    labeled = load_jsonl(Path(args.labeled)) if args.labeled else []
    summary = settle_rows(
        phrases=phrases,
        tag=args.tag,
        auth=args.auth,
        store=store,
        harvest=harvest,
        force=force,
        hard=hard,
        labeled=labeled,
        split_policy=args.split_policy,
    )
    summary.update({"force_path": args.force_out, "hard_path": args.hard_out, "dry_run": args.dry_run})
    if summary["force_added"] <= 0:
        print(json.dumps(summary, indent=2))
        raise SystemExit("REFUSE force_added=0")
    if not args.dry_run:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for path in (store_p, harvest_p):
            if path.is_file():
                shutil.copy2(path, path.with_name(f"{path.name}.bak-pre-{args.tag}-{stamp}"))
        write_jsonl(store_p, store)
        write_jsonl(harvest_p, harvest)
        write_jsonl(Path(args.force_out), force)
        write_jsonl(Path(args.hard_out), hard)
    Path(args.summary).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
