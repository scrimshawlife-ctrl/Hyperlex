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

## A6 — `name_gate` yes for `seed-morph78` (2026-09-24)
Danny: **`flip name_gate`**. Receipt: `receipts/20260924-name-gate-yes-morph78.md`.
- Sets product-level `name_gate=true` for pin `seed-morph78` only. That pin may be called **Hyperlexical**.
- Basis: T1 tier (`milestones.md`) — ModernBERT-base trunk (A2, ≤150M per A1), unbind heads, trained E2 PASS vs Spec 004 probe; dataset buckets 0/0/0; soft_ceiling PROMOTE_BEST.
- Amends `engineering.md` merge rule: a PR may set `name_gate` true only when it records a Danny yes as an amendment (this one).
- Does not rename card/package identifiers (`hyperlex-encoder-*`; C31 target `hyperlex-structure-149m`), does not change SHADOW packet/schema `name_gate` fields, does not authorize Hub upload or T13, does not start a climb.
