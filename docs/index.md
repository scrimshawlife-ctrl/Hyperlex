---
hide:
  - toc
---

# Hyperlex

<div class="hlx-status" markdown>
<span><span class="hlx-dot"></span><strong>v0.4.0</strong></span>
<span>Hermes skill surface · Python package</span>
<span>Settled Brier only</span>
<span>007 model path SHADOW · T0→T1 after E2</span>
</div>

<p class="hlx-lead hlx-purpose">
<strong>Hyperlex detects emerging slang and cultural signals, traces their lineage,
scores virality and hyperstition potential, and emits integrity-hashed receipts.</strong>
Brier calibration is computed <em>only</em> after outcomes are settled — never invented on open analysis.
The Hermes skill is the <em>current operator surface</em>. Spec 007 is the
<em>model path</em> (T0, then T1 after E2) — still SHADOW, not named Hyperlexical.
</p>

## Skill now, model next

| Layer | State |
|-------|--------|
| **Hermes skill** | Shipping v0.4.0 — ingest, 8-family lineage, receipts, settle → Brier |
| **T0 encoder** | Specified baseline (`hyperlex-encoder-*`). Not a Hyperlexical name. |
| **T1 encoder** | Allowed to take the Hyperlexical name **only after E2** on Spark. Not there. |
| **`name_gate` / Hub** | **false** / not published |

Classify volume is ready. E2 is Spark-blocked. [SHADOW encoder (007)](shadow-hyperlexical.md) · [Status](status.md).

## What happens on a run

```mermaid
flowchart LR
  A[Ingest] --> B[Analyze]
  B --> C[Receipt]
  C --> D[Forecasts]
  D --> E[Settle]
  E --> F[Brier score]
  B -.-> G[Phase 5 research]
  B -.-> H[007 model path]
```

Phase 5 is optional and always **SPECULATIVE** with `brier: null` — see [glossary](start/glossary.md#phase-5). Spec 007 is **SHADOW / advisory**: classify volume is ready; `name_gate` is false; E2 is Spark-blocked. Do not call the encoder Hyperlexical.

| Stage | What you get |
|-------|----------------|
| **Ingest → analyze** | Lineage family, atomic terms, virality signals |
| **Receipt** | Integrity-hashed JSON (auditable) |
| **Forecasts** | Open probabilities waiting for settlement |
| **Settle → score** | Real Brier only after operator outcome |
| **Phase 5** | Speculative sims — never Brier |
| **007 model path** | SHADOW T0→T1 — `name_gate` false; not named Hyperlexical |

## Start here — three actions

<div class="hlx-cta-grid" markdown>

<div class="hlx-cta-card hlx-cta-card--primary" markdown>

### 1. Try offline

Zero config. No API keys. Produces a real receipt; `brier` stays `null`.

```bash
python3 scripts/hyperlex.py demo
```

[Try offline →](start/quickstart.md){ .md-button .md-button--primary }

</div>

<div class="hlx-cta-card" markdown>

### 2. Operator loop

Daily path: pipeline → pending → settle → score-series.

[Operator loop →](operator-loop.md){ .md-button .md-button--primary }

</div>

<div class="hlx-cta-card" markdown>

### 3. See real runs

Golden receipts, archive snapshots, featured example.

[See it work →](start/see-it-work.md){ .md-button .md-button--primary }

</div>

</div>

## Featured example (30 seconds)

**Golden receipt · brainrot-aura** · query `brainrot aura farming mid cooked`

| Field | Value |
|-------|--------|
| Lineage family | `brainrot-aura` |
| Matched atoms | brainrot · aura · mid · cooked · … |
| Confidence | 0.98 (INFERRED) |
| Integrity | `e8e43b010371` |
| **Brier** | **`null`** (correct — not settled) |

[Human summary + JSON →](start/see-it-work.md#featured-brainrot-aura) ·
[Open map on this family →](map/index.md?family=brainrot-aura) ·
[Archive catalog →](archive/index.md)

## Explore the rest

<div class="hlx-gateway" markdown>

| Need | Go |
|------|-----|
| **Commands** | [Command map](commands.md) |
| **Architecture** | [Architecture](architecture.md) |
| **Case studies** | [Case studies](case-studies.md) |
| **Slang lineages** | [Lineages](slang-lineages.md) · [Map](map/index.md) |
| **Status / specs** | [Status](status.md) · [Spec kit](specs/index.md) · [SHADOW 007](shadow-hyperlexical.md) |
| **Glossary** | [Terms and hard constraints](start/glossary.md) |
| **Why settled Brier** | [Settled Brier only](start/settled-brier.md) |
| **Contribute** | [Contribute](contributing.md) |

</div>

## Hard rules (one line each)

- **No fabricated Brier** — open analysis always has `brier: null`.
- **Phase 5 is SPECULATIVE** — research tooling, not measurement.
- **Spec 007 is the model path, still SHADOW** — T0 then T1 after E2; `name_gate` false; no Hub.
- **No Abraxas hard import** — hosts may import Hyperlex; not the reverse.
- **Local-first** — durable state in `~/.hyperlex/`; Pages is static history.

Full glossary: [start/glossary.md](start/glossary.md)

---

<p class="hlx-splash-brand-foot">READ DEEPER. THINK WIDER.</p>

<p class="hlx-posture">
v0.4.0 · Hermes skill surface · 007 model path SHADOW · settled Brier only
</p>
