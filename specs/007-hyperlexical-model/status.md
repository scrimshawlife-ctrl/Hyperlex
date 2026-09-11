# Status 007 — 2026-09-10 PT evening

Specify is locked through C52 + A5. Implement U1–U3 harness is on `main`. SHADOW / advisory.

Operator scoreboard (Danny-locked; matches [Notion Operator Hub](https://app.notion.com/p/3d73e8ba2f5c81ad89d7c2df8e931a83)):

| Surface | n | Notes |
|---------|--:|-------|
| Local SoT `~/.hyperlex/hyperlexical/ingest_candidates.jsonl` | **4333** | 402 OBSERVED / 3931 INFERRED. **Not in git.** |
| Export `--include-live` (operator machine) | **6506** | classify family **2437** · unbind **1345** · negatives **208** · gaps **0/0/0** |
| Tracked `exports/civilian.v0.1.jsonl` | 883 | Seed/snapshot. Not the train SoT. |

| Gate | State |
|------|-------|
| C1–C52 + A5 | locked |
| U1 stub infer | on `main` |
| U2 harvest | landed; live SoT is local-only; `name_gate` false |
| Danny ~2500 candidate bar | **met** |
| Hermes 913 / gap-to-2500 | **superseded** — not current |
| U3 eval harness | on `main`; E2 fail (expected) |
| U3 Spark train | gated; use local SoT / `--include-live`, not the tracked seed alone |
| `name_gate` | **false** (E2 Spark-blocked). Volume ≠ name. |
| Hub upload | blocked (C11, C40) |
| 006 IsA | closed |
| Families | **8** only |

Next operator sentences that do work:

- Spark E2 on the box — train from local SoT / `--include-live`
- `open 006 IsA` — separate spec

There is no further specify work on 007 without an amendment.
