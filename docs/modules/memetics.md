# Memetics typology (v0.2.4+)

Deterministic, rule-based typology on observed text (+ optional lineage prior).
All assignments are **INFERRED**.

## Primary types

| ID | Cues (examples) | Typical lineage |
|----|-----------------|-----------------|
| `tactical_edge` | sharp, steam, wiseguy, hammer | betting-sharp |
| `risk_identity` | degen, hodl, rekt, diamond hands | crypto-degen |
| `platform_agency` | agentic, slop, hallucinate, clanker | ai-native |
| `status_radiation` | aura, mid, cooked, based | brainrot-aura |
| `irony_inversion` | brainrot, cope, seethe, redpill | political-status |
| `kinship_address` | bro, sis, twin, unc, cuz | kinship-address |
| `labor_identity` | quiet quitting, rto, bandwidth | workplace-corp |
| `imitation_spread` | narrative, spread, organic velocity | (generic) |
| `one_off` | no cues | — |

Legacy alias: `betting_tactical` may still appear when primary is `tactical_edge`
(back-compat for older consumers). Prefer `typology_primary`.

## Output shape

```json
{
  "is_memetic": true,
  "typology": "risk_identity",
  "typology_primary": "risk_identity",
  "typology_scores": {"risk_identity": 0.75, "imitation_spread": 0.5},
  "rules_hit": {"risk_identity": ["degen", "hodl"]},
  "score": 0.78,
  "provenance": "INFERRED"
}
```

Lineage family soft-prior adds +0.15 to the mapped type when a family is attached.
