# morph71 IN FLIGHT — role-vocab expand / non-warm longer new-atoms (2026-09-22)

**Authority:** operator continue after morph70 REJECT. `name_gate=false`.

## Recommendation (executed)

After morph70 REJECT (tie fair 0.9649 n=171; role-vocab filter force_added=2), the only remaining legal one-knob for the 23 held longer `local-label-new-atoms` AUTHORIZE is **role-vocab expand / non-warm**. Warm morph65 cannot absorb `pos_6`/`pos_7` (`INIT_FROM role_vocab mismatch`).

## Knob

| | |
|--|--|
| one_knob | role-vocab expand / non-warm for held longer AUTHORIZE |
| force_added | **23** (194→**217**) |
| hard_added | **23** (235→**258**) |
| role max | **pos_7** (morph65 max `pos_5`) |
| warm / INIT_FROM | **none** (cold trunk) |
| fair morph65 | **0.9649122807017544** n=171 |
| UPSAMPLE / SECOND_SLOT / LAST | 8 / 2 / 8 held |
| SAVE_BEST | 1 |
| mem_fraction | 0.3 exclusive |
| container | `hlx-train-morph71-1790110734` |

PIN iff best > fair **0.9649122807017544** n=171 and E2 trunk-forward `unbind_exact=1.0`.

METHOD morph43 positional_text_split_match. SoT class OBSERVED (PACKET_SETTLE classify); harvest unbind roles/fillers. No invented fillers. Qwen stopped+disabled.
