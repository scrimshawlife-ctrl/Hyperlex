# morph72 IN FLIGHT — UPSAMPLE=10 non-warm (2026-09-23)

**Authority:** operator handle-new-legal-one-knob-and-continue. `name_gate=false`.

## Recommendation (executed)

After morph71 REJECT (non-warm UPSAMPLE=8, best 0.9591 < fair 0.9649 n=171, residual AUTHORIZE=0), next legal one-knob is **restore BEST morph65 UPSAMPLE=10** on the same morph71 force/hard. Freeze remains **11+** only. Warm morph65 still blocked by expanded role vocab (`pos_6+`).

## Knob

| | |
|--|--|
| one_knob | `HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=10` (was 8 on morph71) |
| force / hard | **217 / 258** (copied from morph71; force_added=0) |
| warm / INIT_FROM | **none** |
| fair morph65 | **0.9649122807017544** n=171 |
| SECOND_SLOT / LAST | 2 / 8 held |
| SAVE_BEST | 1 |
| mem_fraction | 0.3 exclusive |
| container | `hlx-train-morph72-1790129677` |

PIN iff best > fair **0.9649122807017544** n=171 and E2 trunk-forward `unbind_exact=1.0`.
