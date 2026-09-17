# morph49 LEGAL verdict

**LEGAL=Y** (intent). Launch **BLOCKED** until Spark tunnel recovers.

| item | value | note |
|------|-------|------|
| Lever family | last-N (escalate-named) | morph48 KEEP was LAST=6 |
| Delta | `HYPERLEX_LAST_TRAINABLE=7` | was 6 on BEST; ≠ identical LAST=6 |
| HEAD_SLOT | **2** (held) | ≠ morph45 HEAD_SLOT=3 |
| HARD | **4** (held) | ≠ morph46 HARD=6 |
| Curriculum POS | **1** (held) | ≠ morph47 POS=3 |
| Gold | morph40 force 135 / hard 180 | ≠ residual warm+force clone |
| Warm | INIT_FROM=**morph48** + SAVE_BEST=1 | new BEST warm |
| Val / fair | n=228 / morph48 **0.7412280701754386** | same gold surface; recompute fair iff val changes |
| mem_fraction | 0.3 | exclusive |
| name_gate | false | hold |
| LAST max | 8 | layout.py LAST_TRAINABLE_MAX |

**Justification:** morph48 won by unfreezing last-6 encoder layers. Next legal one-delta is LAST=7 (capacity escalate within clamp 1..8) without inventing gold, without repeating LAST=6 identically, and without replaying exhausted HEAD_SLOT=3 / HARD=6 / POS=3 / residual warm+force.

Not blocked on recipe grounds. Blocked only on Spark reachability (CF tunnel 1033).
