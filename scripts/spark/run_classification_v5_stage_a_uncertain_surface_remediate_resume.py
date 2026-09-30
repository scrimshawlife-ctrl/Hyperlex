"""Resume V1R9 build from acquire cache — no MediaWiki re-acquire.

Rebuilds surface with tighter source-family selection, runs semantic
placement + readiness seal. Does not train or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
PRIOR = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-negative-evidence-surface-v1r8-20260930"
)
PRIOR_SHA = "c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b"
DEST = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-negative-evidence-surface-v1r9-20260930"
)
ACQUIRE_CACHE = Path(
    "/home/morpheus/hlx-private/classification-v5-uncertain-acquire-cache-20260930"
)
LEDGER = Path("/home/morpheus/hlx-private/eval-reserve-20260926/ledger.json")
SPENT_V2 = Path(
    "/home/morpheus/hlx-private/classification-v2-train-ready-20260929/reserve-eval-rows.jsonl"
)
SPENT_V3 = Path(
    "/home/morpheus/hlx-private/classification-v3-reserve-20260930/reserve-rows.jsonl"
)
SPENT_V4 = Path(
    "/home/morpheus/hlx-private/classification-v4-reserve-20260930/reserve-rows.jsonl"
)
AUTH_003 = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-train-v1r8-003-focal-20260930"
)
VAL_SCORES = (
    AUTH_003
    / "classification-v5-stage-a-003"
    / "diagnostics"
    / "uncertain_policy_investigation"
    / "VALIDATION_SCORES.jsonl"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"

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
        completed = subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.split()[0]


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def classify_present_fn(item: dict) -> str:
    p_none = float(item["P_NO_EVIDENCE"])
    p_pres = float(item["P_EVIDENCE_PRESENT"])
    p_unc = float(item["P_UNCERTAIN"])
    margin = float(item["margin_top1_top2"])
    if p_none >= 0.80 and p_pres <= 0.20:
        return "NONE_DOMINATED"
    if item.get("top1") == "UNCERTAIN" or (p_unc >= 0.30 and float(item["entropy"]) >= 0.9):
        return "GENUINELY_UNCERTAIN"
    if margin < 0.10 and max(p_none, p_pres, p_unc) < 0.70:
        return "LOW_MARGIN_PRESENT"
    if 0.20 < p_pres < 0.55 and p_none >= p_pres:
        return "CALIBRATION_SHIFT"
    if p_none >= p_pres:
        return "NONE_DOMINATED"
    return "LOW_MARGIN_PRESENT"


def genuine_present_fn_ids() -> list[str]:
    ids = []
    for row in load_jsonl(VAL_SCORES):
        if row.get("evidence_label") != "EVIDENCE_PRESENT":
            continue
        if row.get("decision_scalar_0_50_0_55") not in {"NO_EVIDENCE", "UNCERTAIN"}:
            continue
        if classify_present_fn(row) == "GENUINELY_UNCERTAIN":
            ids.append(str(row["identity"]))
    return sorted(ids)


def blocked_ids() -> set[str]:
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        load_blocked_ids,
    )

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    return load_blocked_ids(
        ledger=ledger,
        spent_row_files=(load_jsonl(SPENT_V2), load_jsonl(SPENT_V3), load_jsonl(SPENT_V4)),
    )


def main() -> int:
    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY
    from hyperlexical.classification_v5_stage_a_negative_evidence_surface import (
        canonical_json,
        sha256_text,
    )
    from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
        REMEDIATE_RULE,
        SURFACE_RULE_V1R9,
        make_inferred_uncertain_bank,
        remediate_contract,
        remediate_uncertain_surface,
        select_uncertain_pool,
        uncertain_support_table,
        source_family,
    )
    from hyperlexical.classification_v5_surface_readiness_gates import GATE_RULE
    from run_classification_v5_stage_a_uncertain_surface_remediate import (
        reevaluate_readiness_with_embedding,
        run_embedding_hardness,
    )

    # Import semantic placement from sibling module after path fix is synced.
    sys.path.insert(0, str(REPO / "scripts" / "spark"))
    from run_classification_v5_stage_a_uncertain_surface_remediate import (
        run_semantic_placement,
    )

    if sha256_file(PRIOR / "EVIDENCE_SURFACE.jsonl") != PRIOR_SHA:
        fail("prior V1R8 digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST changed")

    acquire_path = ACQUIRE_CACHE / "OBSERVED_UNCERTAIN_ACQUIRE.jsonl"
    if not acquire_path.exists():
        # Fall back to DEST copy from prior partial run.
        acquire_path = DEST / "OBSERVED_UNCERTAIN_ACQUIRE.jsonl"
    if not acquire_path.exists():
        fail("acquire cache missing")

    observed = load_jsonl(acquire_path)
    print(
        {
            "observed_n": len(observed),
            "by_family": dict(
                Counter(source_family(r.get("source_bucket")) for r in observed)
            ),
            "by_reason": dict(Counter(r["ambiguity_reason"] for r in observed)),
        },
        flush=True,
    )

    # Wipe DEST surface outputs but keep contract/acquire witnesses if present.
    if DEST.exists():
        for name in (
            "EVIDENCE_SURFACE.jsonl",
            "SPLIT_MANIFEST.json",
            "COMPONENT_SPLIT_WITNESS.json",
            "PAIR_RECORDS.json",
            "LABEL_PROVENANCE.jsonl",
            "LABEL_PROVENANCE_STATS.json",
            "EMBEDDING_HARDNESS.json",
            "SEMANTIC_PLACEMENT.json",
            "SEMANTIC_PLACEMENT_ROWS.jsonl",
            "GATE_EVAL.json",
            "READINESS.json",
            "UNCERTAIN_READINESS.json",
            "UNCERTAIN_SUPPORT.json",
            "BOUNDARY_CHECK.json",
            "DISJOINTNESS.json",
            "SETTLEMENT.json",
            "SUMMARY.json",
            "ARTIFACT_HASHES.json",
            "STAGE_A_TRAIN_CONTRACT.json",
            "REMEDIATION_STATS.json",
            "DEDUPLICATION_WITNESS.json",
            "INFERRED_UNCERTAIN_BANK.jsonl",
        ):
            path = DEST / name
            if path.exists():
                path.unlink()
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(DEST / "CONTRACT.json", remediate_contract())

    prior_rows = load_jsonl(PRIOR / "EVIDENCE_SURFACE.jsonl")
    blocked = blocked_ids()
    genuine_ids = genuine_present_fn_ids()
    write_private(
        DEST / "GENUINE_PRESENT_FN_IDS.json",
        {"n": len(genuine_ids), "identities": genuine_ids},
    )
    write_private(
        DEST / "OBSERVED_UNCERTAIN_ACQUIRE.jsonl",
        "\n".join(canonical_json(r) for r in observed) + "\n",
    )

    inferred_bank = make_inferred_uncertain_bank(
        blocked={r["identity"] for r in observed} | {r["identity"] for r in prior_rows},
        per_reason=90,
    )
    write_private(
        DEST / "INFERRED_UNCERTAIN_BANK.jsonl",
        "\n".join(canonical_json(r) for r in inferred_bank) + "\n",
    )

    # Prefer hub_obs/wik balance; hard-cap families at 0.32 in selection.
    selected = select_uncertain_pool(
        observed, inferred_bank, target_per_reason=100, max_family_share=0.30
    )
    # If still over on projected shares, iteratively drop from largest family.
    for _ in range(200):
        fam = Counter(source_family(r.get("source_bucket")) for r in selected)
        n = max(1, len(selected))
        top_fam, top_n = fam.most_common(1)[0]
        if top_n / n <= 0.30:
            break
        # Drop one row from top family that is not unique for reason floors.
        from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
            FROZEN_AMBIGUITY_REASONS,
            REASON_TRAIN_MIN,
            REASON_VAL_MIN,
        )

        drop_idx = None
        for idx in range(len(selected) - 1, -1, -1):
            row = selected[idx]
            if source_family(row.get("source_bucket")) != top_fam:
                continue
            reason = row["ambiguity_reason"]
            reason_n = sum(1 for r in selected if r["ambiguity_reason"] == reason)
            if reason_n <= REASON_TRAIN_MIN + REASON_VAL_MIN:
                continue
            # Prefer dropping OBSERVED only if enough OBSERVED remain overall.
            obs_n = sum(1 for r in selected if r.get("provenance") == "OBSERVED")
            if row.get("provenance") == "OBSERVED" and obs_n / n <= 0.42:
                continue
            drop_idx = idx
            break
        if drop_idx is None:
            break
        selected.pop(drop_idx)

    observed_sel = [r for r in selected if r["provenance"] == "OBSERVED"]
    inferred = [r for r in selected if r["provenance"] == "INFERRED"]
    print(
        {
            "selected": len(selected),
            "observed": len(observed_sel),
            "inferred": len(inferred),
            "family": dict(
                Counter(source_family(r.get("source_bucket")) for r in selected)
            ),
            "reason": dict(Counter(r["ambiguity_reason"] for r in selected)),
        },
        flush=True,
    )

    built = remediate_uncertain_surface(
        prior_rows=prior_rows,
        observed_uncertain_rows=observed_sel,
        inferred_uncertain_rows=inferred,
        blocked_ids=blocked,
        ontology=ACTIVE_FAMILY_VOCABULARY,
        genuine_present_fn_ids=genuine_ids,
        embedding_report=None,
        semantic_placement=None,
    )
    write_private(DEST / "EVIDENCE_SURFACE.jsonl", built["dataset_body"])
    if sha256_file(DEST / "EVIDENCE_SURFACE.jsonl") != built["dataset_sha256"]:
        fail("dataset digest mismatch")
    write_private(DEST / "SPLIT_MANIFEST.json", built["split_manifest"])
    write_private(DEST / "COMPONENT_SPLIT_WITNESS.json", built["component_witness"])
    write_private(DEST / "DEDUPLICATION_WITNESS.json", built["dedupe_witness"])
    write_private(DEST / "PAIR_RECORDS.json", built["pair_records"])
    write_private(DEST / "REMEDIATION_STATS.json", built["remediation_stats"])
    write_private(
        DEST / "LABEL_PROVENANCE_STATS.json",
        {k: v for k, v in built["label_provenance_stats"].items() if k != "records"},
    )
    write_private(
        DEST / "LABEL_PROVENANCE.jsonl",
        "\n".join(
            canonical_json(r) for r in built["label_provenance_stats"].get("records") or []
        )
        + "\n",
    )

    support = uncertain_support_table(built["rows"])
    print({"pre_embed_support_caps": {
        "max_family": support["max_source_family_share"],
        "val_max_family": support["validation_max_source_family_share"],
        "observed_share": support["observed_share"],
        "val_observed_share": support["validation_observed_share"],
        "atom_train": support["atom_share_train"],
        "prose_train": support["prose_share_train"],
        "atom_val": support["atom_share_validation"],
        "prose_val": support["prose_share_validation"],
    }}, flush=True)

    embedding_report = run_embedding_hardness(built["dataset_sha256"])
    semantic_placement = run_semantic_placement(built["rows"])

    final = reevaluate_readiness_with_embedding(
        built["rows"],
        built["pair_records"],
        embedding_report,
        semantic_placement,
        genuine_ids,
        blocked,
    )
    support = uncertain_support_table(built["rows"])
    write_private(DEST / "UNCERTAIN_SUPPORT.json", support)
    write_private(DEST / "GATE_EVAL.json", final["readiness"])
    write_private(DEST / "UNCERTAIN_READINESS.json", final["uncertain_readiness"])
    write_private(DEST / "BOUNDARY_CHECK.json", final["boundary"])
    write_private(DEST / "DISJOINTNESS.json", final["disjointness"])
    write_private(DEST / "READINESS.json", final["readiness"])
    write_private(DEST / "STAGE_A_TRAIN_CONTRACT.json", built["stage_a_train_contract"])

    details = final["readiness"].get("details") or {}
    original_table = {}
    for key, block in details.items():
        if isinstance(block, dict) and "pass" in block:
            original_table[key] = bool(block["pass"])
    for key, value in final["readiness"].items():
        if key.endswith("_pass"):
            original_table[key] = bool(value)
    uncertain_table = {
        name: bool(final["uncertain_readiness"]["gates"][name]["pass"])
        for name in final["uncertain_readiness"]["mandatory"]
        if name in final["uncertain_readiness"]["gates"]
    }
    hashes = {
        "EVIDENCE_SURFACE.jsonl": built["dataset_sha256"],
        "EMBEDDING_HARDNESS.json": sha256_file(DEST / "EMBEDDING_HARDNESS.json"),
        "SEMANTIC_PLACEMENT.json": sha256_file(DEST / "SEMANTIC_PLACEMENT.json"),
        "CONTRACT.json": sha256_file(DEST / "CONTRACT.json"),
    }
    write_private(DEST / "ARTIFACT_HASHES.json", hashes)

    settlement = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "dataset_sha256": built["dataset_sha256"],
        "final_state": final["final_state"],
        "gate_rule": GATE_RULE,
        "n": len(built["rows"]),
        "n_train": sum(1 for r in built["rows"] if r["split"] == "train"),
        "n_validation": sum(1 for r in built["rows"] if r["split"] == "validation"),
        "next_action": (
            "AUTHORIZE_V5_STAGE_A_NEXT_RUN_ON_REMEDIATED_SURFACE"
            if final["final_state"] == "READY"
            else "REMEDIATE_V5_UNCERTAIN_SURFACE"
        ),
        "original_v5_gate_table": original_table,
        "parent_diagnosis": "MIXED_UNCERTAIN_SURFACE_FAILURE",
        "parent_surface_dataset_sha256": PRIOR_SHA,
        "present_uncertain_boundary": final["boundary"],
        "remediate_rule": REMEDIATE_RULE,
        "reserve": "UNUSED",
        "selected_checkpoint_sha256": (
            "dba6d49103d7c895d7febc46c81491a07ea19acd551f86b3a9fd9f0a1c0782a3"
        ),
        "semantic_placement": {
            "placement_rates": semantic_placement.get("placement_rates"),
            "by_reason_keys": sorted((semantic_placement.get("by_reason") or {}).keys()),
        },
        "surface_rule": SURFACE_RULE_V1R9,
        "train": False,
        "uncertain_gate_table": uncertain_table,
        "uncertain_support": support,
        "disjointness": {
            "identity_overlap": final["disjointness"]["identity_overlap"],
            "source_hash_overlap": final["disjointness"]["source_hash_overlap"],
            "parent_lineage_overlap": final["disjointness"]["parent_lineage_overlap"],
            "cross_split_near_duplicate_clusters": final["disjointness"][
                "cross_split_near_duplicate_clusters"
            ],
        },
    }
    settlement["settlement_sha256"] = sha256_text(
        canonical_json({k: v for k, v in settlement.items() if k != "settlement_sha256"})
    )
    write_private(DEST / "SETTLEMENT.json", settlement)
    summary = {
        "BEST": "UNCHANGED",
        "dataset_sha256": built["dataset_sha256"],
        "final_state": final["final_state"],
        "n": settlement["n"],
        "n_train": settlement["n_train"],
        "n_validation": settlement["n_validation"],
        "next_action": settlement["next_action"],
        "parent_surface_dataset_sha256": PRIOR_SHA,
        "remediate_rule": REMEDIATE_RULE,
        "surface_rule": SURFACE_RULE_V1R9,
        "train": False,
        "uncertain_total": support["UNCERTAIN_total"],
        "artifact_dir": str(DEST),
    }
    write_private(DEST / "SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(
        json.dumps(
            {
                "uncertain_gate_table": uncertain_table,
                "original_v5_gate_table": original_table,
                "support_caps": {
                    "max_family": support["max_source_family_share"],
                    "val_max_family": support["validation_max_source_family_share"],
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if final["final_state"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
