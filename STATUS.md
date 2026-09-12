# Hyperlex status

**Naming:** repo **Hyperlex** is the transitional monorepo shell. Public products: **Hyperlexical** (Spec 007 model / train / eval / E2 / `name_gate` claim) and **ne0l0gist** (slang ingest). `name_gate` remains false.

**Version:** 0.4.0  
**Observed:** 2026-09-10  
**Posture:** Hermes skill = current operator surface. Spec 007 = model path (SHADOW). T0 then T1 after E2.  
**Install:** `bash install.sh` → `~/.hermes/skills/hyperlex`  
**Claude (optional):** `bash install.sh --claude` → `~/.claude/skills/hyperlex`  
**Track:** Phases 0–4 complete · Phase 5.0–5.3 · Pages static run history · Spec 007 SHADOW encoder on main

This file is the operator snapshot. The docs site copies it to [status](https://scrimshawlife-ctrl.github.io/Hyperlex/status/). Do not treat it as a Hub card or a Brier score.

## Trajectory

| Layer | Role | State |
|-------|------|--------|
| Hermes skill | What you run today (`SKILL.md`, CLI, `src/hyperlex/`) | Ready (v0.4.0) |
| T0 | Encoder baseline; card `hyperlex-encoder-*` | Specified. Not named Hyperlexical. |
| T1 | First artifact that *may* be called Hyperlexical | Blocked on E2 vs Spec 004 on Spark |
| `name_gate` | Name + publish wall | **false** |
| Hub | Operator upload | Not published |

Classify volume is ready. Volume does not flip `name_gate`. Seed smoke ≠ T1.

## Health

```bash
python3 scripts/hyperlex.py doctor
python3 scripts/release_preflight.py
python3 scripts/hyperlex.py simulate --term rizz --mode scenario
python -m hyperlex inbox list
PYTHONPATH=scripts/shadow python3 -m hyperlexical.infer --text rizz --offline
```

## Spec 007 — honest gates

SHADOW / advisory. Not on `API_V1`. Do **not** call the artifact Hyperlexical. Do **not** set `name_gate` true.

Operator scoreboard **2026-09-10 PT evening** (Danny-locked; matches [Notion Operator Hub](https://app.notion.com/p/3d73e8ba2f5c81ad89d7c2df8e931a83)):

| Surface | n | Notes |
|---------|--:|-------|
| Local SoT `~/.hyperlex/hyperlexical/ingest_candidates.jsonl` | **4333** | 402 OBSERVED / 3931 INFERRED. **Not in git.** |
| Export `--include-live` (operator machine) | **6506** | classify family **2437** · unbind **1345** · negatives **208** |
| Tracked `specs/007-hyperlexical-model/exports/civilian.v0.1.jsonl` | 883 | **Seed/snapshot only.** Do not treat as the train SoT. |

Danny ~2500 candidate bar: **met**. Hermes **913** / “gap to 2500” is **superseded** — not current SoT status. Afternoon store family-labeled **1789** (stretch 2000 not reached) is the [blanket-yes receipt](docs/receipts/blanket-yes-unlock-2026-09-10.md) figure; export classify **2437** is the harvest gate. Moltbook row counts (for example ~360 ai-native) are a **Moltbook subset**, not the global SoT.

| Gate | State |
|------|--------|
| Classify volume | **Ready** — operator `--include-live` family classify **2437** (≥2k). name_gate gaps **0 / 0 / 0** on that surface. |
| `name_gate` | **false** — stays false until E2 passes on Spark. Volume ≠ name. Gaps at 0 do not flip the gate. |
| E2 vs Spec 004 | **FAIL** on the stub (expected). Trained E2 is **Spark-blocked**. Seed smoke is not a pass. |
| Hub publish | **No** — skeleton in-repo; weights stay on Spark. |
| T1 name | Not allowed. Card stays `hyperlex-encoder-*` until E2. |
| Lineage families | **8** only. No ninth family. |
| Brier | `null` on every 007 packet. |
| Crawl | Crawl4AI **0.9.3** default. `--source firecrawl` aliases to `crawl4ai`. No paid Firecrawl without Danny yes. |

Spark trains from the **local SoT** / `export --include-live`, not from the tracked seed alone.

Spark procedure (bring-up, not a product card):

- [SPARK-BRINGUP.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/SPARK-BRINGUP.md) (#28)
- [AARON-SPARK-TRAIN.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/AARON-SPARK-TRAIN.md)
- [HERMES-SPARK-RUN.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/HERMES-SPARK-RUN.md)
- A5 milestones / engineering (#33): [milestones.md](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/specs/007-hyperlexical-model/milestones.md)
- Live-split coerce (#38) is on `main` (`lexical_split` in the export path)

Pages overview: [SHADOW encoder (007)](docs/shadow-hyperlexical.md)

## Surface (ready)

| Area | Status |
|------|--------|
| Skill contract + install | Ready |
| Mock offline analyze | Ready |
| Lineage (8 families + 2026 YTD leaves) | Ready |
| YTD backfill packs (`data/backfill/2026/`) | Ready |
| Lineage backpropagation (non-mutating) | Ready |
| Typology + community drivers | Ready |
| Virality prediction (SPECULATIVE) | Ready |
| Receipts + ledger + ledger-stats/diff | Ready |
| Forecasts → settle → Brier series | Ready (settlement required) |
| Rune relay + market connectors | Ready |
| Diagrams from history | Ready |
| Case study runner | Ready |
| MkDocs + Pages (enabled) | Ready |
| Pages static run history | Ready |
| Long-term analysis archive | Ready |
| Governed LLM (echo / openai_compatible) | Opt-in |
| Phase 5 cultural transmission / multi-agent / risk / phylogeny | Ready (SPECULATIVE) |
| Local vector DB + Chroma promote | Ready |
| Mutation prediction | Ready (SPECULATIVE) |
| Hybrid lineage re-rank | Ready |
| Domain phylogeny packs | Ready |
| Transmission calibrate / scenario library | Ready |
| Risk → scan/cron schedule | Ready (advisory) |
| Ingest routes + automatic pipeline | Ready |
| Atomic multi-term seeds | Ready |
| Analysis enrichment (compression_metrics, typology tags, signal_report, integrity header) | Ready |
| Local attractor store (`~/.hyperlex/signals/`) | Ready (`inbox list|push|clear`) |
| Attractor candidate rune (`RUNE.HLX.ATTRACTOR_CANDIDATE`) | Ready (advisory only) |
| Spec 007 model path (T0→T1) | SHADOW · classify volume ready · `name_gate` false · E2 Spark-blocked · no Hub · not named Hyperlexical |
| 007 live ingest tap | SHADOW · pipeline/analyze/scan fail-open → `~/.hyperlex/hyperlexical/ingest_candidates.jsonl` · INFERRED only |
| Public PyPI | Not planned |
| External system hard import | Never |

## Operator loop

```text
pipeline "rizz" | run "rizz"
  → hyperlexical tap (INFERRED candidates)
  → pending → settle → score-series
  → scan / risk-schedule
  → relay --push-inbox
  → PYTHONPATH=scripts/shadow python3 -m hyperlexical.ingest_tap
  → inbox list
  → vector-seed / vector-sync
  → archive-export
```

007 Spark (Aaron, not the daily loop): `specs/007-hyperlexical-model/AARON-SPARK-TRAIN.md`

## Data dirs

```text
~/.hyperlex/receipts/
~/.hyperlex/receipt_ledger.jsonl
~/.hyperlex/score_log.jsonl
~/.hyperlex/mutation_watch.jsonl
~/.hyperlex/cache/
~/.hyperlex/vector.db
~/.hyperlex/chroma/
~/.hyperlex/signals/inbox.jsonl
~/.hyperlex/hyperlexical/ingest_candidates.jsonl
~/.hyperlex/models/   # Spark dumps only; not git
data/backfill/2026/
```

## Recommended next

1. Spark morph15 card — pin `seed-morph14` (unbind≈0.3857); climb toward ladder 0.45 with `slot_ce` + hard upsample + soft INFERRED + residual dump (`NEXT_MOVES_007.md` / `u3-recipe.md`).
2. Burn-in offline runs + settle path (this is how Brier becomes real).
3. Do not Hub-upload. Do not promote `scripts/shadow/hyperlexical/` into `src/hyperlex/` (T13). Do not flip `name_gate`.

## README

Operator front door expanded for stack parity with Athanor / Semion / Yggdrasil (2026-09-11). Changelog-style dumps stay in CHANGELOG / receipts — not the main page.
