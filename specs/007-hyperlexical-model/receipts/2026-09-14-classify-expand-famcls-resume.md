# Receipt — classify expand + famcls resume (2026-09-14)

SHADOW / `name_gate=false`. No Hub. No BEST overwrite.

## Action

Operator: **continue with classification so we can resume training**.

### Classify expand pack

`~/hlx-private/p1-classify-expand-20260914/`

- Base prepare: `p1-structure-dual-expanded-prepare-20260914`
- Promoted **33** OBSERVED family-only classify rows
  - brainrot-aura: 11 (template → natural projection)
  - kinship-address: 13 (4333 dump OBSERVED surfaces)
  - gaming-meta: 9 (4333 dump OBSERVED surfaces)
- `none`: still empty (no OBSERVED short surfaces)
- INFERRED + golden matched_terms → review queues only

### Train unique (after)

| family | train unique |
|--------|-------------|
| brainrot-aura | 7 |
| kinship-address | 9 |
| gaming-meta | 7 |
| none | 0 |

### Resume train

`~/hlx-private/p1-structure-unbind-famcls-20260914/`

- Init: famsel checkpoint
- Family CE×2; family_floor=0.68; role/pointer CE×1.5
- Keep gate: family_exact > majority (~0.676) and structure/role/pointer hold

## Safety

- BEST morph19 untouched
- OBSERVED `partial_slot_miss` still hold
- No invented OBSERVED structure gold

## Next

Await famcls holdout; merge only if gate passes. Review INFERRED queue before further label expansion.
