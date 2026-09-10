# Amendments 007

## A1 — C6 ceiling 150M
T1 ≤ 150M.

## A2 — freeze trunk ModernBERT-base
`answerdotai/ModernBERT-base`.

## A3 — U3 specify lock
C33–C40.

## A4 — keepable train layout (2026-09-09)
C41–C46. Freeze last-2. Classify + token-state unbind heads. Values still from Spark.

## A5 — milestones + engineering guidelines (2026-09-10)
Notion-first, then disk.
- `milestones.md` — name-gate 2k/200/200, T0/T1/T2 pointer, R2 exit. Does not fork locked spec tiers.
- `engineering.md` — classify / files / merge / Spark-later rules.
- Notion: https://app.notion.com/p/3d73e8ba2f5c81e9aac1e7dc992e3481 · https://app.notion.com/p/3d73e8ba2f5c813db326e3f68ac77ee9
Does not train. Does not set `name_gate`. Does not open 006 or 008.
