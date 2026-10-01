"""REVISE_GOLD_IDENTIFIABILITY_CONTRACT — Spark/CPU read-only audit.

Audits every V1R1 row for text-only gold identifiability.
Does not train, mutate V1R1, auto-relabel, create V1R2, expand inputs,
alter Stage B, score spent reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-generalization-surface-v1r1-20261001"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "4095036e5af3ad7cfe9f038dd3e1f46e4ef0ea18db4c4b7186fc2b02e96d4274"
ANNOTATIONS = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-factorized-objective-v1-20261001/"
    "FACTORIZED_ANNOTATIONS.jsonl"
)
ANNOTATION_SHA = (
    "4ac884504e4b2fe27e0e5de159847a158c43e2c0d75832ddc5b5c657279778b6"
)
PRIVATE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-gold-identifiability-contract-20261001"
)
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict | str | list) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def write_repo(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    from hyperlexical.classification_v5_stage_a_gold_identifiability_contract import (
        CONTRACT_ID,
        CONTRACT_RULE,
        CONTRACT_STATE,
        MODEL_INPUT,
        PROPOSED_FUTURE_GATES,
        assemble_contract_receipt,
        classify_repaired_viability,
        classify_row,
        decide_primary_repair,
        is_short_atom,
    )

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset_sha_mismatch")
    if sha256_file(ANNOTATIONS) != ANNOTATION_SHA:
        fail("annotation_sha_mismatch")
    if PRIVATE.exists() and (PRIVATE / "CONTRACT.json").exists():
        fail(f"output_already_exists:{PRIVATE}")
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)

    rows = load_jsonl(DATASET)
    anns = {str(a["identity"]): a for a in load_jsonl(ANNOTATIONS)}
    if len(rows) != 3585 or len(anns) != 3585:
        fail(f"row_count_mismatch:{len(rows)}:{len(anns)}")

    classified: list[dict[str, Any]] = []
    for row in rows:
        ann = anns.get(str(row["identity"]))
        if ann is None:
            fail(f"missing_annotation:{row['identity']}")
        classified.append(classify_row(row, ann))

    # --- aggregates ---
    ident_counts = Counter(c["identifiability_state"] for c in classified)
    base_counts = Counter(c["base_identifiability"] for c in classified)
    disp_counts = Counter(c["recommended_disposition"] for c in classified)
    sa_disp = Counter(
        c["short_atom_disposition"] for c in classified if is_short_atom(
            {"primary_cell": c["primary_cell"], "evidence_label": c["current_final_gold"]}
        ) or str(c.get("cell_family")) == "SHORT_ATOM"
    )
    # fix short atom filter using cell_family
    sa_disp = Counter(
        c["short_atom_disposition"] for c in classified if c["cell_family"] == "SHORT_ATOM"
    )
    sa_disp_by_label: dict[str, Counter] = defaultdict(Counter)
    for c in classified:
        if c["cell_family"] == "SHORT_ATOM":
            sa_disp_by_label[c["short_atom_disposition"]][c["current_final_gold"]] += 1

    subtype_table: dict[str, dict[str, int]] = {}
    for c in classified:
        st = c["current_subtype"]
        subtype_table.setdefault(
            st,
            {
                "total": 0,
                "TEXT_IDENTIFIABLE": 0,
                "CONTEXT_REQUIRED": 0,
                "INSUFFICIENT_TEXT": 0,
                "INVALID_GOLD_FOR_TEXT_ONLY_MODEL": 0,
            },
        )
        subtype_table[st]["total"] += 1
        subtype_table[st][c["identifiability_state"]] += 1

    def present_breakdown(pred) -> dict[str, int]:
        subset = [
            c
            for c in classified
            if c["current_final_gold"] == "EVIDENCE_PRESENT" and pred(c)
        ]
        return {
            "total": len(subset),
            "TEXT_IDENTIFIABLE": sum(
                1 for c in subset if c["identifiability_state"] == "TEXT_IDENTIFIABLE"
            ),
            "INVALID_GOLD_FOR_TEXT_ONLY_MODEL": sum(
                1
                for c in subset
                if c["identifiability_state"] == "INVALID_GOLD_FOR_TEXT_ONLY_MODEL"
            ),
            "CONTEXT_REQUIRED_base": sum(
                1 for c in subset if c["base_identifiability"] == "CONTEXT_REQUIRED"
            ),
            "INSUFFICIENT_TEXT_base": sum(
                1 for c in subset if c["base_identifiability"] == "INSUFFICIENT_TEXT"
            ),
            "relation_train_admissible": sum(
                1 for c in subset if c["admissible_for_relation_training"]
            ),
        }

    present_all = present_breakdown(lambda c: True)
    present_sa = present_breakdown(lambda c: c["cell_family"] == "SHORT_ATOM")
    present_prose = present_breakdown(lambda c: c["cell_family"] == "PROSE")
    present_def = present_breakdown(lambda c: c["cell_family"] == "DEFINITION_STYLE")

    none_buckets = Counter(
        c["none_identifiability_bucket"]
        for c in classified
        if c["current_final_gold"] == "NO_EVIDENCE"
    )
    none_sa_buckets = Counter(
        c["none_identifiability_bucket"]
        for c in classified
        if c["current_final_gold"] == "NO_EVIDENCE" and c["cell_family"] == "SHORT_ATOM"
    )

    amb = [c for c in classified if c["current_final_gold"] == "UNCERTAIN"]
    amb_bucket = Counter(c["uncertain_reason_bucket"] for c in amb)
    amb_ftype = Counter(c["uncertain_failure_type"] for c in amb)

    ext_req = Counter()
    for c in classified:
        for x in c["required_external_information"]:
            ext_req[x] += 1

    rel_adm = sum(1 for c in classified if c["admissible_for_relation_training"])
    res_adm = sum(1 for c in classified if c["admissible_for_resolvability_training"])
    e2e_adm = sum(1 for c in classified if c["admissible_for_end_to_end_eval"])

    # Hypothetical repaired surface (planning witness only)
    keepish = {
        "KEEP_GOLD",
        "KEEP_GOLD_BUT_MASK_RELATION",
        "KEEP_FOR_RESOLVABILITY_ONLY",
    }
    repaired = [
        c
        for c in classified
        if c["recommended_disposition"] in keepish
        or (
            c["recommended_disposition"] == "KEEP_GOLD_BUT_MASK_RELATION"
        )
    ]
    # Eligible sets under recommended dispositions (not applied)
    rel_eligible = [
        c for c in classified if c["admissible_for_relation_training"]
        and c["recommended_disposition"] == "KEEP_GOLD"
    ]
    res_eligible = [
        c
        for c in classified
        if c["admissible_for_resolvability_training"]
        and c["recommended_disposition"]
        in {"KEEP_GOLD", "KEEP_FOR_RESOLVABILITY_ONLY", "KEEP_GOLD_BUT_MASK_RELATION"}
    ]
    e2e_eligible = [
        c
        for c in classified
        if c["admissible_for_end_to_end_eval"]
        and c["recommended_disposition"]
        in {"KEEP_GOLD", "KEEP_FOR_RESOLVABILITY_ONLY", "KEEP_GOLD_BUT_MASK_RELATION"}
    ]

    def gold_counts(subset):
        return Counter(c["current_final_gold"] for c in subset)

    rel_pos = sum(
        1 for c in rel_eligible if c["current_final_gold"] == "EVIDENCE_PRESENT"
    )
    rel_neg = sum(1 for c in rel_eligible if c["current_final_gold"] == "NO_EVIDENCE")
    # resolvability: RESOLVABLE=definitive keep; UNRESOLVABLE=genuine uncertain keep
    res_pos = sum(
        1
        for c in res_eligible
        if c["current_final_gold"] in {"EVIDENCE_PRESENT", "NO_EVIDENCE"}
    )
    res_neg = sum(1 for c in res_eligible if c["current_final_gold"] == "UNCERTAIN")

    source_conc = Counter(c["source_family"] for c in rel_eligible)
    domain_cov = Counter(c["topic_domain"] for c in rel_eligible)
    sa_rel = [c for c in rel_eligible if c["cell_family"] == "SHORT_ATOM"]

    balance = {
        "relation_positive": rel_pos,
        "relation_negative": rel_neg,
        "resolvability_positive": res_pos,
        "resolvability_negative": res_neg,
        "minimum_cell_support": min(rel_pos, rel_neg, res_pos, max(res_neg, 0)),
        "source_concentration_top3": source_conc.most_common(3),
        "domain_coverage_n": len([d for d in domain_cov if d]),
        "n_source_families": len(source_conc),
    }
    viability = classify_repaired_viability(balance)

    repaired_surface = {
        "relation_train_eligible": len(rel_eligible),
        "resolvability_train_eligible": len(res_eligible),
        "end_to_end_evaluation_eligible": len(e2e_eligible),
        "gold_counts_relation_eligible": dict(gold_counts(rel_eligible)),
        "gold_counts_e2e_eligible": dict(gold_counts(e2e_eligible)),
        "SHORT_ATOM_PRESENT_relation_eligible": sum(
            1 for c in sa_rel if c["current_final_gold"] == "EVIDENCE_PRESENT"
        ),
        "SHORT_ATOM_NONE_relation_eligible": sum(
            1 for c in sa_rel if c["current_final_gold"] == "NO_EVIDENCE"
        ),
        "source_family_relation_eligible": dict(source_conc),
        "topic_domain_relation_eligible": dict(domain_cov),
        "planning_witness_only": True,
        "dataset_emitted": False,
    }

    # Membership/mask changes ⇒ new dataset version later
    n_exclude = disp_counts.get("EXCLUDE_FROM_TEXT_ONLY_STAGE_A", 0)
    n_mask = disp_counts.get("KEEP_GOLD_BUT_MASK_RELATION", 0) + disp_counts.get(
        "KEEP_FOR_RESOLVABILITY_ONLY", 0
    )
    new_dataset_required = (n_exclude + n_mask) > 0

    aggregate = {
        "identifiability_counts": dict(ident_counts),
        "base_identifiability_counts": dict(base_counts),
        "disposition_counts": dict(disp_counts),
        "short_atom_disposition_counts": dict(sa_disp),
        "short_atom_disposition_by_label": {
            k: dict(v) for k, v in sa_disp_by_label.items()
        },
        "subtype_identifiability_table": subtype_table,
        "present_identifiability": {
            "all_PRESENT": present_all,
            "SHORT_ATOM_PRESENT": present_sa,
            "PROSE_PRESENT": present_prose,
            "DEFINITION_STYLE_PRESENT": present_def,
        },
        "none_identifiability": {
            "all_NONE": dict(none_buckets),
            "SHORT_ATOM_NONE": dict(none_sa_buckets),
        },
        "ambiguous_uncertainty": {
            "n": len(amb),
            "reason_buckets": dict(amb_bucket),
            "failure_types": dict(amb_ftype),
        },
        "required_external_information_distribution": dict(ext_req),
        "relation_training_admissible": rel_adm,
        "resolvability_training_admissible": res_adm,
        "e2e_evaluation_admissible": e2e_adm,
        "repaired_surface": repaired_surface,
        "class_balance": balance,
        "repaired_surface_viability": viability,
        "NEW_DATASET_VERSION_REQUIRED": new_dataset_required,
        "n_rows": len(classified),
        "split_counts": dict(Counter(c["split"] for c in classified)),
    }

    # Attach viability into decide path
    decision_preview = decide_primary_repair(aggregate)
    aggregate["decision_preview"] = decision_preview

    receipt = assemble_contract_receipt(
        row_classifications=classified, aggregate=aggregate
    )

    # Per-row audit JSONL (private only; large)
    audit_path = PRIVATE / "V1R1_IDENTIFIABILITY_AUDIT.jsonl"
    with audit_path.open("w", encoding="utf-8") as handle:
        for c in classified:
            handle.write(json.dumps(c, sort_keys=True) + "\n")
    os.chmod(audit_path, 0o600)

    write_private(PRIVATE / "CONTRACT.json", receipt)
    write_private(PRIVATE / "AGGREGATE.json", aggregate)
    write_private(PRIVATE / "SUBTYPE_TABLE.json", subtype_table)
    write_private(
        PRIVATE / "REPAIRED_SURFACE_WITNESS.json", repaired_surface
    )

    write_repo(REPO_ARTIFACTS / "gold_identifiability_contract.json", receipt)
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-gold-identifiability-contract-receipt-20261001.json",
        receipt,
    )

    md = f"""# Classification v5 — Gold Identifiability Contract V1

```text
RULE = {CONTRACT_RULE}
CONTRACT = {CONTRACT_ID}
STATE = {CONTRACT_STATE}
TRAIN_AUTHORIZED = false
DATASET_MUTATED = false
MODEL_INPUT = {list(MODEL_INPUT)}
PRIMARY_REPAIR = {receipt['PRIMARY_REPAIR']}
DATASET_CONSEQUENCE = {receipt['DATASET_CONSEQUENCE']}
NEXT_ACTION = {receipt['NEXT_ACTION']}
NEW_DATASET_VERSION_REQUIRED = {receipt['NEW_DATASET_VERSION_REQUIRED']}
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
receipt = {receipt['receipt_sha256'][:16]}…
```

Spec + read-only V1R1 audit. No train, auto-relabel, V1R2, input enrichment, Stage-B, reserve, or BEST moves.

## Canonical principle

> {receipt['CANONICAL_PRINCIPLE']}

## Identifiability counts (V1R1 n=3585)

| State | n |
|---|---:|
| TEXT_IDENTIFIABLE | {ident_counts.get('TEXT_IDENTIFIABLE', 0)} |
| CONTEXT_REQUIRED | {ident_counts.get('CONTEXT_REQUIRED', 0)} |
| INSUFFICIENT_TEXT | {ident_counts.get('INSUFFICIENT_TEXT', 0)} |
| INVALID_GOLD_FOR_TEXT_ONLY_MODEL | {ident_counts.get('INVALID_GOLD_FOR_TEXT_ONLY_MODEL', 0)} |

## SHORT_ATOM dispositions

| Disposition | n |
|---|---:|
"""
    for k in (
        "SELF_CONTAINED_RELATION",
        "LEXEME_ONLY",
        "CONTEXT_DEPENDENT_RELATION",
        "SEMANTICALLY_UNDERDETERMINED",
    ):
        md += f"| {k} | {sa_disp.get(k, 0)} |\n"

    md += f"""
## PRESENT identifiability

| Slice | total | TEXT_IDENTIFIABLE | INVALID |
|---|---:|---:|---:|
| all PRESENT | {present_all['total']} | {present_all['TEXT_IDENTIFIABLE']} | {present_all['INVALID_GOLD_FOR_TEXT_ONLY_MODEL']} |
| SHORT_ATOM PRESENT | {present_sa['total']} | {present_sa['TEXT_IDENTIFIABLE']} | {present_sa['INVALID_GOLD_FOR_TEXT_ONLY_MODEL']} |
| PROSE PRESENT | {present_prose['total']} | {present_prose['TEXT_IDENTIFIABLE']} | {present_prose['INVALID_GOLD_FOR_TEXT_ONLY_MODEL']} |
| DEFINITION_STYLE PRESENT | {present_def['total']} | {present_def['TEXT_IDENTIFIABLE']} | {present_def['INVALID_GOLD_FOR_TEXT_ONLY_MODEL']} |

## Admissibility / dispositions

```text
relation_train_admissible = {rel_adm}
resolvability_train_admissible = {res_adm}
e2e_eval_admissible = {e2e_adm}
EXCLUDE_FROM_TEXT_ONLY_STAGE_A = {disp_counts.get('EXCLUDE_FROM_TEXT_ONLY_STAGE_A', 0)}
REQUIRES_HUMAN_RESETTLEMENT = {disp_counts.get('REQUIRES_HUMAN_RESETTLEMENT', 0)}
KEEP_GOLD = {disp_counts.get('KEEP_GOLD', 0)}
KEEP_FOR_RESOLVABILITY_ONLY = {disp_counts.get('KEEP_FOR_RESOLVABILITY_ONLY', 0)}
```

## Minimum viable repaired surface (planning witness)

```text
relation_train_eligible = {repaired_surface['relation_train_eligible']}
  PRESENT = {rel_pos}  NONE = {rel_neg}
  SHORT_ATOM PRESENT = {repaired_surface['SHORT_ATOM_PRESENT_relation_eligible']}
  SHORT_ATOM NONE = {repaired_surface['SHORT_ATOM_NONE_relation_eligible']}
resolvability_train_eligible = {repaired_surface['resolvability_train_eligible']}
e2e_evaluation_eligible = {repaired_surface['end_to_end_evaluation_eligible']}
viability = {viability}
```

## Decision

```text
PRIMARY_REPAIR = {receipt['PRIMARY_REPAIR']}
DATASET_CONSEQUENCE = {receipt['DATASET_CONSEQUENCE']}
REPAIR_SCOPE = {receipt['REPAIR_SCOPE']}
NEW_DATASET_VERSION_REQUIRED = {receipt['NEW_DATASET_VERSION_REQUIRED']}
architecture_change_justified = false
input_contract_expansion_justified = false
NEXT_ACTION = {receipt['NEXT_ACTION']}
NEXT_ACTION_AUTHORIZED = false
```

Proposed future gates: relation training 100% TEXT_IDENTIFIABLE; context-required definitive gold = 0.

Do **not** apply the repair in this pass.
"""
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-gold-identifiability-contract-20261001.md",
        md,
    )
    write_private(PRIVATE / "CONTRACT.md", md)

    print(
        json.dumps(
            {
                "CONTRACT_ID": CONTRACT_ID,
                "CONTRACT_STATE": CONTRACT_STATE,
                "PRIMARY_REPAIR": receipt["PRIMARY_REPAIR"],
                "DATASET_CONSEQUENCE": receipt["DATASET_CONSEQUENCE"],
                "NEXT_ACTION": receipt["NEXT_ACTION"],
                "NEW_DATASET_VERSION_REQUIRED": receipt["NEW_DATASET_VERSION_REQUIRED"],
                "identifiability_counts": dict(ident_counts),
                "short_atom_disposition_counts": dict(sa_disp),
                "present_SHORT_ATOM": present_sa,
                "relation_train_eligible": repaired_surface["relation_train_eligible"],
                "viability": viability,
                "receipt_sha256": receipt["receipt_sha256"],
                "PROPOSED_FUTURE_GATES": PROPOSED_FUTURE_GATES,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
