# 2026 YTD slang backfill packs

**Schema:** `hyperlex.backfill_pack.v1`  
**Purpose:** Curated monthly term packs for prior months of the current year so Hyperlex can expand the lineage registry and **backpropagate** family matches onto historical receipts without rewriting receipt integrity.

## What this is

- Month packs under `data/backfill/2026/YYYY-MM.json` (Jan–Aug for this cut).
- Each term is labeled **OBSERVED** / **INFERRED** / **SPECULATIVE** (default **INFERRED**).
- Packs are **not** a live crawl corpus; they are operator-curated seeds for matcher expansion and timeline docs.
- Applying packs merges terms into an in-memory registry overlay (or permanent registry expansion in code). Historical receipts stay immutable; backprop emits a **reclassification report**.

## Operator flow

```bash
# List packs + term inventory
python3 scripts/hyperlex.py lineage-backfill --list

# Summarize packs through a month
python3 scripts/hyperlex.py lineage-backfill --through 2026-08

# Non-mutating rematch of golden receipts with expanded registry
python3 scripts/hyperlex.py lineage-backprop --from-golden --out out/backprop/report.json

# Rematch archive / local receipts
python3 scripts/hyperlex.py lineage-backprop --from-archive --include-home
```

## Integrity rules

1. Never rewrite `provenance.integrity` on historical receipts.
2. Backprop output is a separate report (`hyperlex.lineage_backprop.v1`).
3. Archive re-export is optional and still sanitized; it does not claim OBSERVED for pack provenance.
4. Brier remains null until settlement — backfill does not invent scores.

## Pack shape

```json
{
  "schema": "hyperlex.backfill_pack.v1",
  "year": 2026,
  "month": 1,
  "label": "2026-01",
  "provenance_default": "INFERRED",
  "notes": "...",
  "terms": [
    {
      "term": "rizz",
      "family_id": "brainrot-aura",
      "first_seen_month": "2026-01",
      "prominence": "high",
      "provenance": "INFERRED",
      "branch_operator": "platform_compression",
      "notes": "..."
    }
  ]
}
```

## Families targeted

| family_id | 2026 focus |
|-----------|------------|
| brainrot-aura | Gen Alpha / TikTok carryover, status radiation |
| ai-native | model-culture, agentic speech |
| gaming-meta | competitive / platform status |
| kinship-address | fictive kinship acceleration |
| political-status | tribal judgment shorthand |
| crypto-degen | residual risk-identity slang |
| betting-sharp | line-physics cluster (stable) |
| workplace-corp | labor identity under corporate speech |
