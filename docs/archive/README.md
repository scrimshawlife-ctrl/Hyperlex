# Run history

<div class="hlx-status" markdown>
<span><span class="hlx-dot"></span><strong>7 runs</strong></span>
<span>Static · publish-safe · GitHub Pages</span>
<span>Primary store: <code>~/.hyperlex/</code></span>
<span>Latest analysis: <code>backfill-ytd-2026-analysis</code></span>
</div>

Publish-safe history of Hyperlex runs. **Not** live operator state — that lives in `~/.hyperlex/`.

<div class="hlx-path-grid" markdown>

<div class="hlx-path-card hlx-path-card--primary" markdown>

**Researchers**

How to interpret kinds, atoms, risk, and vector scores without overclaiming.

[Reading evidence →](../demos/reading-evidence.md){ .md-button .md-button--primary }

</div>

<div class="hlx-path-card" markdown>

**Operators**

Append sanitized snapshots from local receipts / Phase 5.

[Operator loop →](../operator-loop.md){ .md-button }

</div>

</div>

**How to read this index**

| Kind | Meaning |
|------|---------|
| <span class="hlx-kind hlx-kind--analysis">analysis</span> | Receipt-backed analyze / pipeline snapshots |
| <span class="hlx-kind hlx-kind--phase5">phase5 · SPECULATIVE</span> | Research sim. **atoms** = separate lexicon terms (not one blended seed) |
| risk tier | Advisory only — not market advice; not Brier |
| vector / similarity | Cosine neighbors if present — **not** Brier; see [reading guide](../demos/reading-evidence.md) |

Machine index: [`catalog.json`](./catalog.json) ·
[Latest analysis](./latest/index.md) (`backfill-ytd-2026-analysis`) ·
[Atomic terms](../demos/atomic-terms.md) ·
[Reading evidence](../demos/reading-evidence.md) ·
[Operator loop](../operator-loop.md)

## Analysis snapshots

Receipt-backed history. Prefer these when citing lineage / receipts.

<div class="hlx-index-row hlx-index-row--analysis" markdown>

<span class="hlx-kind hlx-kind--analysis">analysis</span>
**[backfill-ytd-2026-analysis](./runs/backfill-ytd-2026-analysis/index.md)**  
16 receipts  
Families: `ai-native`×3, `betting-sharp`×2, `brainrot-aura`×5, `crypto-degen`×1, `gaming-meta`×2  
  <span class="hlx-index-note">YTD 2026 backfill packs → mock analyze receipts for Pages</span>

</div>

<div class="hlx-index-row hlx-index-row--analysis" markdown>

<span class="hlx-kind hlx-kind--analysis">analysis</span>
**[golden-seed-0.3.2](./runs/golden-seed-0.3.2/index.md)**  
9 receipts  
Families: `(none)`×1, `ai-native`×1, `betting-sharp`×1, `brainrot-aura`×1, `crypto-degen`×1  
  <span class="hlx-index-note">Hallmark redesign seed; multi-family stats</span>

</div>

<div class="hlx-index-row hlx-index-row--analysis" markdown>

<span class="hlx-kind hlx-kind--analysis">analysis</span>
**[golden-seed-0.3.1](./runs/golden-seed-0.3.1/index.md)**  
9 receipts  
Families: `betting-sharp`×5  
  <span class="hlx-index-note">Golden corpus seed for Pages static history</span>

</div>


## Phase 5 research (SPECULATIVE)

Scenario literature only — never Brier. Atoms stay separate.

<div class="hlx-index-row hlx-index-row--phase5" markdown>

<span class="hlx-kind hlx-kind--phase5">phase5 · SPECULATIVE</span>
**[backfill-phase5-sharp-2026](./runs/backfill-phase5-sharp-2026/index.md)**  
risk **LOW** · atoms `sharp` · `steam` · `revenge`  
Families: —  
  <span class="hlx-index-note">Atoms: sharp · steam · revenge</span>

</div>

<div class="hlx-index-row hlx-index-row--phase5" markdown>

<span class="hlx-kind hlx-kind--phase5">phase5 · SPECULATIVE</span>
**[backfill-phase5-ai-native-2026](./runs/backfill-phase5-ai-native-2026/index.md)**  
risk **LOW** · atoms `agentic slop` · `skill issue`  
Families: —  
  <span class="hlx-index-note">Atoms: agentic slop · skill issue</span>

</div>

<div class="hlx-index-row hlx-index-row--phase5" markdown>

<span class="hlx-kind hlx-kind--phase5">phase5 · SPECULATIVE</span>
**[phase5-rizz-ai-demo](./runs/phase5-rizz-ai-demo/index.md)**  
risk **LOW** · atoms `sigma` · `rizz` · `locked in`  
Families: —  
  <span class="hlx-index-note">Atoms: sigma · rizz · locked in (separate scenarios)</span>

</div>

<div class="hlx-index-row hlx-index-row--phase5" markdown>

<span class="hlx-kind hlx-kind--phase5">phase5 · SPECULATIVE</span>
**[backfill-phase5-rizz-2026](./runs/backfill-phase5-rizz-2026/index.md)**  
risk **LOW** · atoms `sigma` · `rizz` · `locked in`  
Families: —  
  <span class="hlx-index-note">Atoms: sigma · rizz · locked in (separate scenarios)</span>

</div>


## Published vs not

| On Pages | Stays local |
|----------|-------------|
| Sanitized receipt summaries | Full raw signals / API keys |
| Lineage, typology, virality, stage | Score-log settlements (unless you export) |
| Phase 5 digests (SPECULATIVE) | Invented Brier (never) |
| Vector method + samples | Live `~/.hyperlex/chroma` / Cloud |

## Append a run

```bash
python3 scripts/hyperlex.py archive-export --include-golden --history
python3 scripts/hyperlex.py archive-export --include-home-receipts --history
python3 scripts/hyperlex.py simulate --term rizz --out /tmp/p5.json
python3 scripts/hyperlex.py archive-export --phase5 /tmp/p5.json --history
python3 scripts/hyperlex.py archive-catalog
```

Commit + push `docs/archive/` → Pages rebuild (`.github/workflows/docs.yml`).

<p class="hlx-posture">
Hermes skill · Brier requires settlement · vector ≠ probability · primary store ~/.hyperlex
</p>
