"""Amend settlement agreement → migrate V6 labels → architecture bake-off.

No QUAL inspection. MODEL_WIDE_BEST is control, not assumed backbone.
"""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v6-label-migration-bakeoff-20261001"
)
FOUNDATION = Path(
    "/home/morpheus/hlx-private/classification-v6-data-foundation-20261001"
)
HA_PRIV = Path(
    "/home/morpheus/hlx-private/classification-v6-human-ontology-settlement-20261001"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-LABEL-MIGRATION-BAKEOFF-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
MAX_LEN = 192
SEED = 20261001
EPOCHS = 2
BATCH = 16
LR = 2e-5

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    import hashlib

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


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
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
    return [
        json.loads(l)
        for l in sudo_read_text(FOUNDATION / f"{name}.jsonl").splitlines()
        if l.strip()
    ]


def load_base_sample() -> list[dict]:
    raw = sudo_read_text(FOUNDATION / "HUMAN_AGREEMENT_SAMPLE.jsonl")
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError:
        rows = [json.loads(l) for l in raw.splitlines() if l.strip()]
    return [{"identity": r["identity"], "text": r["text"], "stratum": ["base120"]} for r in rows]


def boundary_topup(splits: dict[str, list[dict]], existing_ids: set[str], per: int = 40) -> list[dict]:
    from hyperlexical.classification_v6_multilabel_agreement import stratum_of_row

    rng = random.Random(SEED)
    buckets: dict[str, list[dict]] = defaultdict(list)
    for name in ("TRAIN", "DEVELOPMENT_VALIDATION", "REPRESENTATIVE_VALIDATION"):
        for row in splits[name]:
            if row["identity"] in existing_ids:
                continue
            if row.get("evidence_label") != "EVIDENCE_PRESENT":
                continue
            tags = stratum_of_row(row.get("gold_family"), row.get("text") or "")
            for tag in tags:
                if tag in {"identity", "evaluative", "relational", "gambling", "crypto"}:
                    buckets[tag].append(row)
    out = []
    for tag in ("identity", "evaluative", "relational", "gambling", "crypto"):
        pool = sorted(buckets.get(tag, []), key=lambda r: r["identity"])
        rng.shuffle(pool)
        for row in pool[:per]:
            if row["identity"] in existing_ids:
                continue
            existing_ids.add(row["identity"])
            out.append(
                {
                    "identity": row["identity"],
                    "text": row["text"],
                    "stratum": [tag],
                    "legacy_family": row.get("gold_family"),
                }
            )
        print(f"topup {tag}={min(per, len(pool))}", flush=True)
    return out


def multi_hot(labels: list[str], vocab: list[str]) -> list[int]:
    idx = {v: i for i, v in enumerate(vocab)}
    vec = [0] * len(vocab)
    for lab in labels:
        if lab in idx:
            vec[idx[lab]] = 1
    return vec


def run_bakeoff_track(
    track: str,
    train_rows: list[dict],
    dev_rows: list[dict],
    rep_rows: list[dict],
) -> dict[str, Any]:
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors
    from hyperlexical.classification_v6_architecture_bakeoff import (
        hierarchy_metrics,
        multilabel_f1,
    )
    from hyperlexical.classification_v6_label_migration import (
        DOMAIN_VOCAB,
        FUNCTION_VOCAB,
        MEDIATION_VOCAB,
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("MODEL_WIDE_BEST_mismatch")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("bakeoff requires CUDA")

    # Keep only PRESENT with at least one label for Stage-B heads
    def usable(rows):
        out = []
        for r in rows:
            if r.get("evidence_label") != "EVIDENCE_PRESENT":
                continue
            if r.get("human_resettlement_required"):
                continue
            if not (r.get("domain_labels") or r.get("function_labels") or r.get("mediation_labels")):
                continue
            out.append(r)
        return out

    train = usable(train_rows)
    dev = usable(dev_rows)
    rep = usable(rep_rows)
    print(f"{track} usable train/dev/rep={len(train)}/{len(dev)}/{len(rep)}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    apply_encoder_trainable(encoder, split.get("encoder") or {})
    freeze_encoder(encoder, last_trainable=2)
    hidden = encoder.config.hidden_size

    class MultiHead(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = encoder
            self.domain = nn.Linear(hidden, len(DOMAIN_VOCAB))
            self.function = nn.Linear(hidden, len(FUNCTION_VOCAB))
            self.mediation = nn.Linear(hidden, len(MEDIATION_VOCAB))
            # Track B: label attention prototypes
            self.dom_proto = nn.Parameter(torch.randn(len(DOMAIN_VOCAB), hidden) * 0.02)
            self.fun_proto = nn.Parameter(torch.randn(len(FUNCTION_VOCAB), hidden) * 0.02)
            self.use_hier = track.startswith("B") or track.startswith("C")
            self.use_contrast = track.startswith("C")

        def forward(self, batch):
            out = self.encoder(**batch).last_hidden_state[:, 0]
            h = F.normalize(out, dim=-1)
            if self.use_hier:
                # hierarchy-aware: add attention to label prototypes
                da = torch.softmax(h @ F.normalize(self.dom_proto, dim=-1).T / 0.07, dim=-1)
                h_d = h + da @ self.dom_proto
                fa = torch.softmax(h @ F.normalize(self.fun_proto, dim=-1).T / 0.07, dim=-1)
                h_f = h + fa @ self.fun_proto
            else:
                h_d = h_f = h
            return self.domain(h_d), self.function(h_f), self.mediation(h), h

    model = MultiHead().to(device)
    opt = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=0.01
    )
    bce = nn.BCEWithLogitsLoss()
    tech_idx = DOMAIN_VOCAB.index("domain.technology")
    ai_idx = DOMAIN_VOCAB.index("domain.technology.ai_discourse")

    def batches(rows, shuffle=False):
        idxs = list(range(len(rows)))
        if shuffle:
            random.Random(SEED).shuffle(idxs)
        for i in range(0, len(idxs), BATCH):
            chunk = [rows[j] for j in idxs[i : i + BATCH]]
            texts = [c["text"] for c in chunk]
            tok = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            y_d = torch.tensor(
                [multi_hot(c.get("domain_labels") or [], DOMAIN_VOCAB) for c in chunk],
                dtype=torch.float32,
            )
            y_f = torch.tensor(
                [multi_hot(c.get("function_labels") or [], FUNCTION_VOCAB) for c in chunk],
                dtype=torch.float32,
            )
            y_m = torch.tensor(
                [multi_hot(c.get("mediation_labels") or [], MEDIATION_VOCAB) for c in chunk],
                dtype=torch.float32,
            )
            yield tok, y_d, y_f, y_m

    model.train()
    for epoch in range(EPOCHS):
        total = 0.0
        n = 0
        for tok, y_d, y_f, y_m in batches(train, shuffle=True):
            tok = {k: v.to(device) for k, v in tok.items()}
            y_d, y_f, y_m = y_d.to(device), y_f.to(device), y_m.to(device)
            opt.zero_grad()
            ld, lf, lm, h = model(tok)
            loss = bce(ld, y_d) + bce(lf, y_f) + bce(lm, y_m)
            # hierarchy soft constraint: if AI logit high, push tech logit
            ai_prob = torch.sigmoid(ld[:, ai_idx])
            tech_prob = torch.sigmoid(ld[:, tech_idx])
            loss = loss + 0.5 * (ai_prob * F.relu(0.5 - tech_prob)).mean()
            if model.use_contrast:
                # simple supervised contrastive on domain multi-hot co-occurrence
                # pull same primary domain together
                sim = h @ h.T
                # target: share any domain label
                share = (y_d @ y_d.T > 0).float()
                share.fill_diagonal_(0)
                if share.sum() > 0:
                    loss = loss + 0.1 * F.binary_cross_entropy_with_logits(sim, share)
            loss.backward()
            opt.step()
            total += float(loss.item())
            n += 1
        print(f"{track} epoch {epoch+1} loss={total/max(1,n):.4f}", flush=True)

    @torch.no_grad()
    def eval_split(rows: list[dict]) -> dict[str, Any]:
        model.eval()
        if not rows:
            return {"n": 0}
        all_gd, all_pd, all_gf, all_pf, all_gm, all_pm = [], [], [], [], [], []
        for tok, y_d, y_f, y_m in batches(rows, shuffle=False):
            tok = {k: v.to(device) for k, v in tok.items()}
            ld, lf, lm, _ = model(tok)
            pd = (torch.sigmoid(ld) >= 0.5).long().cpu().numpy()
            # enforce hierarchy at inference for all tracks (constraint decoding)
            for i in range(pd.shape[0]):
                if pd[i, ai_idx] == 1:
                    pd[i, tech_idx] = 1
            pf = (torch.sigmoid(lf) >= 0.5).long().cpu().numpy()
            pm = (torch.sigmoid(lm) >= 0.5).long().cpu().numpy()
            all_gd.extend(y_d.numpy().astype(int).tolist())
            all_pd.extend(pd.tolist())
            all_gf.extend(y_f.numpy().astype(int).tolist())
            all_pf.extend(pf.tolist())
            all_gm.extend(y_m.numpy().astype(int).tolist())
            all_pm.extend(pm.tolist())
        # combine system vector = concat
        g_sys = [d + f + m for d, f, m in zip(all_gd, all_gf, all_gm)]
        p_sys = [d + f + m for d, f, m in zip(all_pd, all_pf, all_pm)]
        return {
            "n": len(rows),
            "domain": multilabel_f1(all_gd, all_pd),
            "function": multilabel_f1(all_gf, all_pf),
            "mediation": multilabel_f1(all_gm, all_pm),
            "system": multilabel_f1(g_sys, p_sys),
            "hierarchy": hierarchy_metrics(
                all_gd, all_pd, tech_idx=tech_idx, ai_idx=ai_idx
            ),
        }

    return {"DEV": eval_split(dev), "REP": eval_split(rep), "n_train": len(train), "encoder": "MODEL_WIDE_BEST_CONTROL"}


def inner() -> int:
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_architecture_bakeoff import (
        PHASE_RULE,
        bakeoff_contract,
        select_candidate,
    )
    from hyperlexical.classification_v6_human_ontology_settlement import (
        dual_annotate_rows,
        settle_boundaries,
        utc_now_iso,
    )
    from hyperlexical.classification_v6_label_migration import migrate_row
    from hyperlexical.classification_v6_multilabel_agreement import three_level_agreement

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    random.seed(SEED)

    print("phase1_amended_agreement_and_topup", flush=True)
    splits = {
        "TRAIN": load_split("TRAIN"),
        "DEVELOPMENT_VALIDATION": load_split("DEVELOPMENT_VALIDATION"),
        "REPRESENTATIVE_VALIDATION": load_split("REPRESENTATIVE_VALIDATION"),
    }
    base = load_base_sample()
    ids = {r["identity"] for r in base}
    top = boundary_topup(splits, ids, per=40)
    sample = base + top
    print(f"sample_n={len(sample)} base={len(base)} topup={len(top)}", flush=True)
    annotated = dual_annotate_rows(sample)
    agreement = three_level_agreement(annotated)
    # lightweight settlement reaffirm using annotated
    from hyperlexical.classification_v6_human_ontology_settlement import agreement_report

    legacy_rep = agreement_report(annotated)
    settlement = settle_boundaries(legacy_rep, annotated)
    write_private(PRIVATE / "THREE_LEVEL_AGREEMENT.json", agreement)
    write_repo(REPO_ART / "three_level_agreement.json", agreement)
    write_private(PRIVATE / "BOUNDARY_TOPUP_SAMPLE.json", sample)
    settlement_ok = (
        settlement["structure_remains"] == "HIERARCHICAL_MULTI_LABEL"
        and not settlement["hierarchical_multilabel_contradicted"]
        and settlement["identity_affiliation"]["decision"] == "CONTEXT_ONLY"
    )
    print(f"settlement_ok={settlement_ok}", flush=True)
    if not settlement_ok:
        fail("settlement_contradicted")

    # Remaining inconclusive strata after top-up — report but do not block migration
    # if structure/decisions hold (research: top up only inconclusive; decisions already frozen)
    write_private(
        PRIVATE / "SETTLEMENT_REAMFFIRM.json",
        {"ok": settlement_ok, "settlement": settlement, "inconclusive": agreement["inconclusive_strata"]},
    )

    print("phase2_label_migration", flush=True)
    migrated = {}
    counts = Counter()
    for name, rows in splits.items():
        out = []
        for row in rows:
            m = migrate_row(row)
            m["split"] = name
            out.append(m)
            counts[m["migration_type"]] += 1
            if m.get("human_resettlement_required"):
                counts["HUMAN_RESETTLEMENT_REQUIRED"] += 1
        migrated[name] = out
        write_jsonl(PRIVATE / f"{name}_V6_LABELS.jsonl", out)
        print(f"migrated {name}={len(out)}", flush=True)
    # Repo: summaries only (not full rows if huge) — write compact summaries + hashes
    mig_summary = {
        "counts": dict(counts),
        "n": {k: len(v) for k, v in migrated.items()},
        "QUAL_TOUCHED": False,
        "label_schema": {
            "domain_labels": "multi-hot",
            "function_labels": "multi-hot",
            "mediation_labels": "multi-hot",
            "ontology_uncertainty": True,
        },
    }
    write_private(PRIVATE / "MIGRATION_SUMMARY.json", mig_summary)
    write_repo(REPO_ART / "migration_summary.json", mig_summary)

    print("phase3_architecture_bakeoff", flush=True)
    contract = bakeoff_contract()
    write_repo(REPO_ART / "bakeoff_contract.json", contract)
    write_repo(
        SPEC / "classification-v6-architecture-bakeoff-contract-20261001.md",
        "# V6 architecture bake-off contract\n\n```json\n"
        + json.dumps(contract, indent=2, sort_keys=True)
        + "\n```\n",
    )

    results = {}
    for track in (
        "A_BASELINE_MULTIHEAD",
        "B_HIERARCHY_AWARE",
        "C_REPRESENTATION_AWARE",
    ):
        results[track] = run_bakeoff_track(
            track,
            migrated["TRAIN"],
            migrated["DEVELOPMENT_VALIDATION"],
            migrated["REPRESENTATIVE_VALIDATION"],
        )
        print(json.dumps({track: results[track]}, indent=2)[:1500], flush=True)

    selection = select_candidate(results)
    write_private(PRIVATE / "BAKEOFF_RESULTS.json", results)
    write_repo(REPO_ART / "bakeoff_results.json", results)
    write_private(PRIVATE / "BAKEOFF_SELECTION.json", selection)
    write_repo(REPO_ART / "bakeoff_selection.json", selection)

    qual_plan = {
        "HYPERLEX_V6_QUALIFICATION_001": {
            "status": "REMAIN_SEALED_HISTORICAL_SECONDARY",
            "inspected": False,
            "not_primary_v6_qualification": True,
        },
        "new_primary_qualification": {
            "id": "HYPERLEX_V6_QUALIFICATION_002_PLANNED",
            "labels_defined_before_acquisition": True,
            "ontology": "HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL",
            "axes": ["domain_labels", "function_labels", "mediation_labels"],
        },
    }
    write_repo(REPO_ART / "qualification_plan.json", qual_plan)

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated")

    receipt = {
        "EXPERIMENT_ID": contract["EXPERIMENT_ID"],
        "PHASE_RULE": PHASE_RULE,
        "TRAIN": True,
        "architecture_bakeoff": True,
        "QUAL_ROWS_INSPECTED": False,
        "MODEL_WIDE_BEST_ROLE": "CONTROL",
        "settlement_amended_three_level_agreement": True,
        "settlement_ok": settlement_ok,
        "agreement_mean_jaccard": agreement["mean_example_jaccard"],
        "agreement_mean_set_f1": agreement["mean_example_set_f1"],
        "inconclusive_strata_after_topup": agreement["inconclusive_strata"],
        "migration_summary": mig_summary,
        "bakeoff_selection": selection,
        "qualification_plan": qual_plan,
        "code_revision": code_revision(),
        "settled_at": utc_now_iso(),
        "NEXT_ACTION": (
            "DESIGN_FRESH_V6_QUALIFICATION_SURFACE"
            if selection.get("advance")
            else "CONTINUE_V6_ARCHITECTURE_BAKEOFF"
        ),
        "BAKEOFF_STATE": (
            "V6_BAKEOFF_CANDIDATE_SELECTED"
            if selection.get("advance")
            else "V6_BAKEOFF_NO_ADVANCE"
        ),
    }
    receipt["V6_LABEL_MIGRATION_BAKEOFF_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in receipt.items()
                if k != "V6_LABEL_MIGRATION_BAKEOFF_RECEIPT_SHA256"
            }
        )
    )
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(
        SPEC / "classification-v6-label-migration-bakeoff-receipt-20261001.json",
        receipt,
    )
    top = selection["ranking"][0] if selection.get("ranking") else {}
    summary = {
        "BAKEOFF_STATE": receipt["BAKEOFF_STATE"],
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "RECEIPT": receipt["V6_LABEL_MIGRATION_BAKEOFF_RECEIPT_SHA256"],
        "selected": selection.get("selected"),
        "advance": bool(selection.get("advance")),
        "GENERALIZATION_GAP_ACCEPTABLE": top.get("GENERALIZATION_GAP_ACCEPTABLE"),
        "ABS_REP_FLOOR_OK": top.get("ABS_REP_FLOOR_OK"),
        "HIERARCHY_OK": top.get("HIERARCHY_OK"),
        "best_rep_macro_f1": top.get("rep_macro_f1"),
        "best_hierarchy_violation_rate_rep": top.get(
            "hierarchy_violation_rate_rep"
        ),
        "migration_counts": mig_summary["counts"],
        "mean_set_jaccard": agreement["mean_example_jaccard"],
        "sample_n": len(sample),
        "QUAL_ROWS_INSPECTED": False,
        "selection_note": (
            "advance requires GENERALIZATION_GAP_ACCEPTABLE + "
            "min_rep_system_macro_f1 + max_hierarchy_violation_rate_rep; "
            "zero hierarchy_violation_rate is valid (not coerced via or-default)"
        ),
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(
        SPEC / "classification-v6-label-migration-bakeoff-20261001.md",
        f"""# REBUILD_V6_LABELS_AND_RUN_ARCHITECTURE_BAKEOFF

```text
BAKEOFF_STATE = {summary['BAKEOFF_STATE']}
NEXT_ACTION = {summary['NEXT_ACTION']}
RECEIPT = {summary['RECEIPT']}
selected = {summary['selected']}
GENERALIZATION_GAP_ACCEPTABLE = {summary['GENERALIZATION_GAP_ACCEPTABLE']}
sample_n = {summary['sample_n']}
mean_set_jaccard = {summary['mean_set_jaccard']}
```

Amended three-level multi-label agreement + boundary top-up, deterministic
label migration, tracks A/B/C under MODEL_WIDE_BEST control. QUAL sealed.
""",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_BAKEOFF_INNER") == "1":
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
        "HLX_V6_BAKEOFF_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_label_migration_bakeoff.py"),
    ]
    log = PRIVATE / "bakeoff_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-25000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
