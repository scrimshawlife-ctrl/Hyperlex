# morph66 IN FLIGHT — residual gold force/hard (2026-09-21)

Container `hlx-train-morph66-1789969749`. One knob: force/hard morph63 residual gold expand (**164** / **206**). Held `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=8`, `HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2`, warm **morph65**, LAST=8, HEAD=2, POS=1, TYPE=1, HARD_UPSAMPLE=4, mem 0.3 exclusive, 40ep, SAVE_BEST. `name_gate=false`.

## Fair (same-surface)

Fair-eval CURRENT BEST morph65 on post-force val:

| | |
|--|--|
| fair | **0.9601990049751243** = 193/201 |
| force keys | 164 (matched 162) |
| val n after force | **201** (was 226) |

PIN only if morph66 best > fair on n=201 and E2 trunk-forward exact 1.0.

Upsample ladder frozen (no 9/10/11 replay). Qwen remains stopped+disabled. Spark poll `poll_morph66.sh` → E2 → `finish_morph66.py`.
