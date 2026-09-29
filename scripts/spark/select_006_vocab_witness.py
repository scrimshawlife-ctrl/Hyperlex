"""Read two checkpoint vocabs and report expansion counts. No filler names."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _load(path: str) -> tuple[list[str], list[str]]:
    blob = json.loads(Path(path).read_text(encoding="utf-8"))
    roles = blob.get("role_vocab")
    fillers = blob.get("filler_vocab")
    if not isinstance(roles, list) or not isinstance(fillers, list):
        raise SystemExit("VOCAB_EXPANSION_SPEC_INCOMPLETE: missing vocabs")
    return [str(item) for item in roles], [str(item) for item in fillers]


def _ordered(labels: list[str]) -> bool:
    if not labels or labels[0] != "<unk>":
        return False
    rest = labels[1:]
    return rest == sorted(rest) and "<unk>" not in rest


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("VOCAB_EXPANSION_SPEC_INCOMPLETE: expected warm and current configs")
    warm_roles, warm_fillers = _load(sys.argv[1])
    current_roles, current_fillers = _load(sys.argv[2])
    warm_role_set = set(warm_roles)
    current_role_set = set(current_roles)
    warm_filler_set = set(warm_fillers)
    current_filler_set = set(current_fillers)
    new_roles = [label for label in current_roles if label not in warm_role_set]
    report = {
        "configs_agree": True,
        "mapped_existing_fillers": sum(1 for label in warm_fillers if label in current_filler_set),
        "mapped_existing_roles": sum(1 for label in warm_roles if label in current_role_set),
        "new_role_names_in_sorted_order": new_roles,
        "newly_initialized_fillers": sum(1 for label in current_fillers if label not in warm_filler_set),
        "newly_initialized_roles": len(new_roles),
        "role_order_ok": _ordered(warm_roles) and _ordered(current_roles),
        "skipped_warm_start_only": sum(1 for label in warm_fillers if label not in current_filler_set),
        "target_filler_count": len(current_fillers),
        "target_role_count": len(current_roles),
        "warm_start_filler_count": len(warm_fillers),
        "warm_start_only_roles": sum(1 for label in warm_roles if label not in current_role_set),
        "warm_start_role_count": len(warm_roles),
    }
    sys.stdout.write(json.dumps(report, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
