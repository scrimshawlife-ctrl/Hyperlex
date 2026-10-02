# Hyperlex status

**Naming:** repo **Hyperlex** is the transitional monorepo shell. Public products: **Hyperlexical** (Spec 007 model / train / eval / E2 / `name_gate` claim) and **ne0l0gist** (slang ingest — operator-named 2026-09-24, repo spelling). `name_gate` **true** for `seed-morph78` (Danny `flip name_gate`, 2026-09-24, amendment A6).

**Version:** 0.4.0  
**Observed:** 2026-10-02  
**Posture:** Hermes skill = current operator surface. **`HYPERLEX_INSTRUMENT_V1`** = Abraxas-facing representation/measurement layer (`SHADOW_INSTRUMENT_ONLY`, `READY_FOR_ABRAXAS_SHADOW_USE`). Spec 007 structure pin = model path (SHADOW). V6 final-label classifier = **REJECTED**. Spark BEST = `seed-morph78` (soft_ceiling PROMOTE_BEST 2026-09-24; broad **0.9883** n=256). Ingest product named **ne0l0gist**. Naming lock: `docs/NAMING.md` + Notion Naming lock. `name_gate` **true** for `seed-morph78` (A6). Hub card `hyperlex-structure-149m`; Hub and T13 not authorized. Abraxas shadow adapter merged ([PR #261](https://github.com/scrimshawlife-ctrl/Abraxas/pull/261)).
**Install:** `bash install.sh` → `~/.hermes/skills/hyperlex`  
**Claude (optional):** `bash install.sh --claude` → `~/.claude/skills/hyperlex`  
**Track:** Phases 0–4 complete · Phase 5.0–5.3 · Pages static run history · Instrument V1 on main · Spec 007 SHADOW structure path on main

This file is the operator snapshot. The docs site copies it to [status](https://scrimshawlife-ctrl.github.io/Hyperlex/status/). Do not treat it as a Hub card or a Brier score.

## Trajectory

| Layer | Role | State |
|-------|------|--------|
| Hermes skill | What you run today (`SKILL.md`, CLI, `src/hyperlex/`) | Ready (v0.4.0) |
| Instrument V1 | Abraxas semantic instrumentation (`observe()`) | **READY_FOR_ABRAXAS_SHADOW_USE** · not semantic truth |
| V6 classifier | Final DOMAIN/MEDIATION/FUNCTION labels | **REJECTED** (CORE QUAL FAIL) |
| T0 | Encoder baseline; card `hyperlex-encoder-*` | Specified. Not named Hyperlexical. |
| T1 | First artifact that *may* be called Hyperlexical | `seed-morph78`: trained E2 PASS + Danny `name_gate` yes (2026-09-24) — **named Hyperlexical** |
| `name_gate` | Name wall | **true** (`seed-morph78`, A6) · publish wall (Hub) still closed |
| Hub | Operator upload | Not published |

Classify volume is ready. Volume did not flip `name_gate`; Danny's sentence did. Seed smoke ≠ T1.

## Health

```bash
python3 scripts/hyperlex.py doctor
python3 scripts/release_preflight.py
python3 scripts/hyperlex.py simulate --term rizz --mode scenario
python -m hyperlex inbox list
PYTHONPATH=src python3 -m hyperlex.instrument observe "ethereum defi"
PYTHONPATH=scripts/shadow python3 -m hyperlexical.infer --text rizz --offline
```

## Instrument V1 — Abraxas dependency

```text
HYPERLEX_PRODUCT_ROLE       = REPRESENTATION_AND_MEASUREMENT_LAYER
HYPERLEX_OPERATION_MODE     = SHADOW_INSTRUMENT_ONLY
HYPERLEX_CLASSIFIER_RELEASE = REJECTED
HYPERLEX_INSTRUMENT_V1      = READY_FOR_ABRAXAS_SHADOW_USE
HYPERLEX_OUTPUT            != SEMANTIC_TRUTH
```

| Piece | Location |
|-------|----------|
| Contract | `schemas/hyperlex.instrument.v1.schema.json` |
| Runtime | `src/hyperlex/instrument/` |
| Docs | [`docs/instrument-v1.md`](docs/instrument-v1.md) |
| Program settlement | [`specs/007-hyperlexical-model/classification-v6-program-settlement-20261002.md`](specs/007-hyperlexical-model/classification-v6-program-settlement-20261002.md) |
| Instrument settlement | [`specs/007-hyperlexical-model/hyperlex-instrument-v1-settlement-20261002.md`](specs/007-hyperlexical-model/hyperlex-instrument-v1-settlement-20261002.md) |
| Notion mirror | [Instrument V1 — settlement + Abraxas shadow \| 2026-10-02](https://app.notion.com/p/3ed3e8ba2f5c81ea854de3dcb6a10958) |
| Operator Hub gate | [007 Hyperlexical — Operator Hub](https://app.notion.com/p/3d73e8ba2f5c81ad89d7c2df8e931a83) (Current gate 2026-10-02) |
| Abraxas adapter | `abraxas.evidence.hyperlex_instrument` (flag `ABX_HYPERLEX_INSTRUMENT`, default off) |
| Abraxas integration doc | [Abraxas `docs/integration/hyperlex_instrument_v1.md`](https://github.com/scrimshawlife-ctrl/Abraxas/blob/main/docs/integration/hyperlex_instrument_v1.md) |

Primary operation is `observe()`, not `classify()`. DOMAIN/MEDIATION appear only as advisory candidates. FUNCTION is experimental/advisory; `memetic_form` is research-only and not emitted.

## Spec 007 — honest gates

SHADOW / advisory. Not on `API_V1`. Pin `seed-morph78` may be called **Hyperlexical** (A6). Do not call any other checkpoint, stub, or seed smoke Hyperlexical. V6 multi-label classifier release remains **REJECTED**.

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
| `name_gate` | **true** for `seed-morph78` — Danny `flip name_gate` 2026-09-24 (A6; receipt `specs/007-hyperlexical-model/receipts/20260924-name-gate-yes-morph78.md`). E2 PASS alone did not flip it. |
| Spark BEST | **`seed-morph78`** — PROMOTE_BEST via soft_ceiling ceiling_escape: broad OBSERVED **0.9883** > morph65 **0.8867** n=256; E2 PASS; force fair 1.0 n=164 (advisory). LAST=8. Upsample freeze **11+**. |
| E2 vs Spec 004 | Stub still FAIL (expected). **Trained trunk-forward E2 PASS** on morph19 (`unbind_exact=1.0`). Seed smoke ≠ T1. |
| Hub publish | **No** — skeleton in-repo; weights stay on Spark. |
| T1 name | **Hyperlexical** approved for `seed-morph78`. Hub card `hyperlex-structure-149m` (C31). Local train-out paths keep `hyperlex-encoder-modernbert-base-seed-*`. |
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
| Spec 007 model path (T0→T1) | SHADOW · Spark BEST morph78 · broad 0.988 n=256 · force fair 1.0 n=164 · E2 PASS · LAST=8 · upsample freeze 11+ · morph69–78 closed · next climb needs new named-phrase card · `name_gate` **true** (morph78, A6) · named Hyperlexical · no Hub · T13 not authorized |
| Instrument V1 | SHADOW · `READY_FOR_ABRAXAS_SHADOW_USE` · observe()/API/SDK · Abraxas PR #261 merged · not semantic truth |
| V6 classifier program | REJECTED · CORE QUAL FAIL · research artifacts preserved · no further QUAL without task reformulation |
| 007 live ingest tap | SHADOW · pipeline/analyze/scan fail-open → `~/.hyperlex/hyperlexical/ingest_candidates.jsonl` · INFERRED only |
| Public PyPI | Not planned |
| External system hard import | Never (Abraxas consumes Hyperlex; Hyperlex does not import Abraxas) |

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

1. Instrument V1: use Abraxas shadow path with `ABX_HYPERLEX_INSTRUMENT=1` when ready; keep influence_policy `NONE`. Do not promote candidates to gold/canonical.
2. Spark BEST = **morph78**. Default **HOLD**. Operator review `specs/007-hyperlexical-model/HYPERLEXICAL-PRODUCT-PLAN.md`; a new climb needs a new named-phrase acquire card. Hub / T13 remain separate decisions.
3. Do not Hub-upload — publish audit recommends local-only (`specs/007-hyperlexical-model/PUBLISH-AUDIT-20260924.md`). Do not reopen V6 classifier QUAL. Do not extend `name_gate` beyond `seed-morph78`.

## README

Operator front door expanded for stack parity with Athanor / Semion / Yggdrasil (2026-09-11). Changelog-style dumps stay in CHANGELOG / receipts — not the main page.
