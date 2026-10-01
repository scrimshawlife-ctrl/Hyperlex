"""REVISE_HYPERLEX_V6_ONTOLOGY_BEFORE_MODELING — Spark validation.

Uses V6 TRAIN/DEV/REP only. Does not inspect QUAL rows. No train / encoder choice.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path("/home/morpheus/hlx-private/classification-v6-ontology-revision-20261001")
FOUNDATION = Path(
    "/home/morpheus/hlx-private/classification-v6-data-foundation-20261001"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ART = REPO / "artifacts" / "experiments" / "HLX-CLASSIFICATION-V6-ONTOLOGY-REVISION-001"
SPEC = REPO / "specs" / "007-hyperlexical-model"
MAX_LEN = 256

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    try:
        return sha256_file(path)
    except PermissionError:
        return subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split()[0]


def sudo_read_text(path: Path) -> str:
    if os.access(path, os.R_OK):
        return path.read_text(encoding="utf-8")
    return subprocess.run(
        ["sudo", "-n", "cat", str(path)], check=True, capture_output=True, text=True
    ).stdout


def write_private(path: Path, payload: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    text = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    )
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)


def write_repo(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def code_revision() -> str:
    env = os.environ.get("HLX_V5_STAGE_A_CODE_REVISION")
    if env:
        return env
    return subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def load_split(name: str) -> list[dict]:
    path = FOUNDATION / f"{name}.jsonl"
    rows = []
    for line in sudo_read_text(path).splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def run_proposed_geometry(rows: list[dict]) -> dict[str, Any]:
    import numpy as np
    import torch
    import torch.nn.functional as F
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors
    from hyperlexical.classification_v6_ontology_revision import geometry_cluster_id

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("MODEL_WIDE_BEST_mismatch")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("geometry requires CUDA")

    present = [
        r
        for r in rows
        if r.get("evidence_label") == "EVIDENCE_PRESENT"
        and geometry_cluster_id(str(r.get("gold_family") or ""))
    ]
    # Cap for runtime while keeping family diversity
    present = sorted(present, key=lambda r: r["identity"])[:2200]
    if not present:
        fail("no_present_for_geometry")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    apply_encoder_trainable(encoder, split.get("encoder") or {})
    freeze_encoder(encoder, last_trainable=2)
    encoder.to(device).eval()

    @torch.no_grad()
    def embed(texts: list[str], bs: int = 32) -> np.ndarray:
        outs = []
        for i in range(0, len(texts), bs):
            batch = texts[i : i + bs]
            tok = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            tok = {k: v.to(device) for k, v in tok.items()}
            pooled = F.normalize(encoder(**tok).last_hidden_state[:, 0], dim=-1)
            outs.append(pooled.float().cpu().numpy())
        return np.concatenate(outs, axis=0)

    vecs = embed([r["text"] for r in present])
    clusters = [geometry_cluster_id(str(r["gold_family"])) for r in present]
    by: dict[str, list[np.ndarray]] = defaultdict(list)
    for c, v in zip(clusters, vecs):
        if c:
            by[c].append(v)
    cents = {}
    for c, vs in by.items():
        m = np.mean(np.stack(vs), axis=0)
        cents[c] = m / max(1e-6, float(np.linalg.norm(m)))

    within = []
    for c, vs in by.items():
        mat = np.stack(vs, axis=0)
        if len(mat) < 2:
            continue
        sims = mat @ mat.T
        n = len(mat)
        for i in range(n):
            for j in range(i + 1, n):
                within.append(float(sims[i, j]))
    between = []
    names = sorted(cents)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            between.append(float(np.dot(cents[a], cents[b])))

    # nearest cluster purity
    if len(names) >= 2:
        C = np.stack([cents[n] for n in names], axis=0)
        pred_idx = (vecs @ C.T).argmax(axis=1)
        gold_idx = [names.index(c) for c in clusters]
        purity = sum(int(p == g) for p, g in zip(pred_idx, gold_idx)) / len(gold_idx)
        # confusion edges
        conf = Counter()
        for p, g in zip(pred_idx, gold_idx):
            if p != g:
                conf[(names[g], names[p])] += 1
        confusion = [
            {"gold": a, "pred": b, "n": n} for (a, b), n in conf.most_common(20)
        ]
    else:
        purity = None
        confusion = []

    within_m = float(np.mean(within)) if within else None
    between_m = float(np.mean(between)) if between else None
    return {
        "encoder": "MODEL_WIDE_BEST",
        "MODEL_WIDE_BEST": BEST_SHA,
        "n_present_mapped": len(present),
        "n_clusters": len(names),
        "cluster_counts": {k: len(v) for k, v in sorted(by.items())},
        "within_family_sim_mean": within_m,
        "between_family_sim_mean": between_m,
        "margin_within_minus_between": (
            None
            if within_m is None or between_m is None
            else within_m - between_m
        ),
        "nearest_cluster_purity": purity,
        "confusion_graph_top": confusion,
        "historical_comparison": {
            "old_within": 0.822,
            "old_between": 0.980,
            "old_purity": 0.25,
            "note": "Old figures from V6 foundation audit on exclusive 18-way labels.",
        },
        "geometry_improved": bool(
            within_m is not None
            and between_m is not None
            and (within_m - between_m) > (0.822 - 0.980)
        ),
        "geometry_adequate_alone": False,
        "note": (
            "Geometry is validation-only. Proposed ontology may still show residual "
            "overlap due to category-proxy noise in V6 PRESENT gold; human-separability "
            "and cardinality correctness remain primary."
        ),
    }


def inner() -> int:
    from hyperlexical.classification_v6_ontology_revision import (
        FAMILY_PURPOSE,
        build_ontology_receipt,
        estimate_multilabel_fractions,
        migration_consequence_counts,
        preferred_ontology,
        support_for_proposed,
        utc_now_iso,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    print("loading_v6_natural_splits", flush=True)
    # Explicitly do NOT load QUALIFICATION rows.
    splits = {
        "TRAIN": load_split("TRAIN"),
        "DEVELOPMENT_VALIDATION": load_split("DEVELOPMENT_VALIDATION"),
        "REPRESENTATIVE_VALIDATION": load_split("REPRESENTATIVE_VALIDATION"),
    }
    for k, v in splits.items():
        print(f"{k}={len(v)}", flush=True)

    multi = {
        name: estimate_multilabel_fractions(rows) for name, rows in splits.items()
    }
    # Aggregate across TRAIN+DEV+REP PRESENT
    all_present = []
    for rows in splits.values():
        all_present.extend(
            r for r in rows if r.get("evidence_label") == "EVIDENCE_PRESENT"
        )
    multi["AGGREGATE_PRESENT"] = estimate_multilabel_fractions(all_present)
    write_private(PRIVATE / "MULTILABEL_ESTIMATE.json", multi)
    write_repo(REPO_ART / "multilabel_estimate.json", multi)

    support = support_for_proposed(splits)
    write_private(PRIVATE / "PROPOSED_SUPPORT.json", support)
    write_repo(REPO_ART / "proposed_support.json", support)

    mig = migration_consequence_counts(splits)
    write_private(PRIVATE / "MIGRATION_CONSEQUENCE.json", mig)
    write_repo(REPO_ART / "migration_consequence.json", mig)

    print("geometry_under_proposed_ontology", flush=True)
    geometry = run_proposed_geometry(splits["TRAIN"] + splits["REPRESENTATIVE_VALIDATION"])
    write_private(PRIVATE / "PROPOSED_GEOMETRY.json", geometry)
    write_repo(REPO_ART / "proposed_geometry.json", geometry)

    ident = {
        label["id"]: label["identifiability"]
        for label in (
            preferred_ontology()["domains"]
            + preferred_ontology()["functions"]
            + preferred_ontology()["mediation"]
        )
    }
    # expand children
    for d in preferred_ontology()["domains"]:
        for child in d.get("children") or []:
            ident[child["id"]] = child["identifiability"]

    purpose_unclear = [
        f for f, v in FAMILY_PURPOSE.items() if v["purpose_status"] == "PURPOSE_UNCLEAR"
    ]
    remaining_human = True  # identity + social-evaluation/relationship boundaries
    audit = {
        "multilabel_estimate": multi,
        "support": support,
        "support_viable": bool(support.get("all_active_meet_minimum")),
        "migration_consequence": mig,
        "geometry": geometry,
        "identifiability": ident,
        "purpose_unclear_families": purpose_unclear,
        "remaining_human_critical": remaining_human,
        "human_agreement_sample_status": "AWAITING_OPERATOR_ANNOTATION",
        "human_dependencies": [
            {
                "boundary": "identity-affiliation resettlement",
                "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
                "confirm_if": (
                    "Dual annotators agree whether text-identifiable affiliation "
                    "maps to evaluative_stance, politics, both, or neither"
                ),
            },
            {
                "boundary": "evaluative_stance vs relational_intimacy soft boundary",
                "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
                "confirm_if": "Agree on exclusive vs co-label for partner-directed insults",
            },
            {
                "boundary": "gambling vs crypto soft market slang",
                "decidability": "NEEDS_HUMAN_AGREEMENT_EVIDENCE",
                "confirm_if": "Agree stake/token senses are separable from text alone",
            },
        ],
        "v6_present_gold_noise_note": (
            "Category-proxy PRESENT acquisition produced many off-family dictionary "
            "rows; ontology decisions are grounded in semantic contracts + co-occurrence "
            "structure, with geometry as secondary validation only."
        ),
        "QUAL_ROWS_INSPECTED": False,
    }

    receipt = build_ontology_receipt(
        code_revision=code_revision(),
        audit=audit,
        settled_at=utc_now_iso(),
    )
    write_private(PRIVATE / "ONTOLOGY_RECEIPT.json", receipt)
    write_repo(REPO_ART / "ontology_receipt.json", receipt)
    write_repo(
        SPEC / "classification-v6-ontology-revision-receipt-20261001.json",
        receipt,
    )

    summary = {
        "V6_ONTOLOGY_STATE": receipt["V6_ONTOLOGY_STATE"],
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "V6_ONTOLOGY_REVISION_RECEIPT_SHA256": receipt[
            "V6_ONTOLOGY_REVISION_RECEIPT_SHA256"
        ],
        "structure": receipt["preferred_ontology"]["structure"],
        "stage_b_task": receipt["stage_b_task"]["task"],
        "label_cardinality_finding": multi["AGGREGATE_PRESENT"].get(
            "recommended_cardinality"
        ),
        "support_viable": support.get("all_active_meet_minimum"),
        "geometry_margin": geometry.get("margin_within_minus_between"),
        "geometry_purity": geometry.get("nearest_cluster_purity"),
        "QUAL_ROWS_INSPECTED": False,
        "TRAIN": False,
        "ENCODER_CHOSEN": False,
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(
        SPEC / "classification-v6-ontology-revision-20261001.md",
        f"""# REVISE_HYPERLEX_V6_ONTOLOGY_BEFORE_MODELING

```text
V6_ONTOLOGY_STATE = {summary['V6_ONTOLOGY_STATE']}
NEXT_ACTION = {summary['NEXT_ACTION']}
RECEIPT = {summary['V6_ONTOLOGY_REVISION_RECEIPT_SHA256']}
structure = {summary['structure']}
stage_b_task = {summary['stage_b_task']}
support_viable = {summary['support_viable']}
geometry_margin(within-between) = {summary['geometry_margin']}
geometry_purity = {summary['geometry_purity']}
```

Historical 18-family ontology frozen as `HISTORICAL_RESEARCH_ONTOLOGY`.
Preferred V6 lineage: hierarchical multi-label (domain × function × mediation).
No train. No encoder choice. QUAL rows not inspected.
""",
    )
    write_repo(
        SPEC / "classification-v6-family-ontology-v1-20261001.md",
        "# HYPERLEX_V6_FAMILY_ONTOLOGY_V1\n\n"
        + "```json\n"
        + json.dumps(preferred_ontology(), indent=2, sort_keys=True)
        + "\n```\n",
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_ONTOLOGY_INNER") == "1":
        return inner()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    revision = code_revision()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--network",
        "host",
        "-v",
        f"{REPO}:{REPO}",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        str(REPO),
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V6_ONTOLOGY_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_ontology_revision.py"),
    ]
    log = PRIVATE / "ontology_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-20000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
