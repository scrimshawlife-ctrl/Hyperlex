# Labeling template — Danny / human structure gold

**Authority:** Spec 007. OBSERVED hold until authorize. `name_gate=false`.

## Schema constraints (locked)

| field | allowed |
|-------|---------|
| `role_scheme` | **`positional`** \| **`type_slot`** only |
| `gold_roles` (positional) | `pos_0`, `pos_1`, … aligned to fillers |
| `gold_roles` (type_slot) | `TOKEN`, `SLOT`, `MARKER` (Spec-locked tags) — no free-form gloss roles |
| `gold_fillers` | exact surface substrings / tokens for the span — **blank until human fill** |
| `authorized_observed_structure_gold` | `null` → `true` only after Danny authorize |
| `confirm_labels` / `confirm_rights` | stay `false` until real rights memo |

## Do not invent gold

- Package ships with **`gold_fillers: []`**, **`gold_roles: []`**,  
  **`authorized_observed_structure_gold: null`**.
- `eval_reference_fillers` is **scoring provenance only** (civilian val SoT used to
  compute miss themes). It is **not** Danny-authorized OBSERVED structure gold.
- Do not copy pred into gold. Do not auto-approve INFERRED as OBSERVED.

## Per-row checklist

1. Read `text`, `pred`, `miss_type` / `themes`, `role_scheme`.
2. If authorizing structure gold: fill `gold_roles` + `gold_fillers` under the **same**
   scheme (`positional` or `type_slot`).
3. Set `danny_decision` to one of:
   - `AUTHORIZE_OBSERVED_STRUCTURE_GOLD`
   - `HOLD`
   - `ALTERNATE_LADDER_PATH` (+ note the path in `danny_notes`)
   - `SKIP_NOT_APPLICABLE`
4. Flip `confirm_labels` / `confirm_rights` only with real attestation.
5. Leave `training_ready=false`, `best_overwrite=false`, `observed_hold=true` until a
   separate operator train authorize after gold lands.

## JSONL shape (fillable fields)

```json
{
  "id": "morph19-civ-res-…",
  "text": "…",
  "pred": ["…"],
  "miss_type": "partial_slot_miss",
  "role_scheme": "type_slot",
  "eval_reference_fillers": ["…"],
  "gold_fillers": [],
  "gold_roles": [],
  "authorized_observed_structure_gold": null,
  "danny_decision": "PENDING",
  "danny_notes": "",
  "confirm_labels": false,
  "confirm_rights": false,
  "observed_hold": true
}
```
