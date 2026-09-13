"""Loop task selection, not source or review approval.

Provenance: Notion Sprint 001 Hub NOT_COMPUTABLE + Loop 805 Slice N/A
+ Hash: b3eee725054c1ed1dae16fad3464af005edad0cc (base).
"""
import hashlib
import json
from collections import Counter

TASKS = {"classify": ("classify",), "unbind": ("unbind",),
         "classify+unbind": ("classify", "unbind")}
HEADS = {"classify": "family", "unbind": "structure"}


def route_rows(rows):
    """Preserve input order and rows; missing masks retain declared legacy tasks.

    A present loss_masks object must specify both supported heads explicitly.
    Other heads are unsupported by this loop and rejected, not silently dropped.
    Counts describe selection before recipes/upsampling, not optimizer consumption.
    """
    selected = {task: {p: [] for p in ("train", "val")} for task in HEADS}
    reasons = Counter()
    task_counts = Counter()
    explicit = 0
    for row in rows:
        if not isinstance(row, dict) or row.get("task") not in TASKS:
            raise ValueError("unsupported task declaration")
        if row.get("split") not in {"train", "val", "test"}:
            raise ValueError("unsupported split declaration")
        masks = row.get("loss_masks")
        if "loss_masks" in row:
            if (not isinstance(masks, dict) or set(masks) != {"family", "structure"}
                    or any(type(v) is not bool for v in masks.values())):
                raise ValueError("loss_masks requires explicit family/structure booleans")
            explicit += 1
        declared = TASKS[row["task"]]
        if masks is not None and any(masks[HEADS[t]] and t not in declared for t in HEADS):
            raise ValueError("active mask has no declared task")
        active = [t for t in declared if masks is None or masks[HEADS[t]]]
        if row["split"] == "test":
            reasons["reserved_test"] += 1
        elif not active:
            reasons["all_declared_heads_masked"] += 1
        else:
            reasons["selected"] += 1
            for task in active:
                selected[task][row["split"]].append(row)
                task_counts[task + ":" + row["split"]] += 1
    accounting = {
        "input_rows": len(rows), "row_outcomes": dict(reasons),
        "task_assignments": dict(task_counts), "explicit_mask_rows": explicit,
        "legacy_declared_rows": len(rows) - explicit,
        "input_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"),
                                                 ensure_ascii=True, allow_nan=False).encode()).hexdigest(),
        "unit": "pre_recipe_row_selection", "review_proof": "NOT_COMPUTABLE",
    }
    assert sum(reasons.values()) == len(rows)
    return selected, accounting
