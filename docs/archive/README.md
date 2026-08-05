# Run history

<div class="hlx-status" markdown>
<span><span class="hlx-dot"></span><strong>7 runs</strong></span>
<span>Static · publish-safe · GitHub Pages</span>
<span>Primary store: <code>~/.hyperlex/</code></span>
<span>Latest analysis: <code>backfill-ytd-2026-analysis</code></span>
</div>

Publish-safe history of Hyperlex runs. Not live operator state.
Machine index: [`catalog.json`](./catalog.json) ·
[Latest analysis](./latest/index.md) (`backfill-ytd-2026-analysis`)

## Snapshots

<div class="grid cards" markdown>

-   :material-flask-outline: **[backfill-phase5-ai-native-2026](./runs/backfill-phase5-ai-native-2026/index.md)**

    `phase5_scenario` · risk **MODERATE** · term `agentic slop skill issue`

    Families: —

    ---

    [Open snapshot →](./runs/backfill-phase5-ai-native-2026/index.md)

-   :material-flask-outline: **[backfill-phase5-sharp-2026](./runs/backfill-phase5-sharp-2026/index.md)**

    `phase5_scenario` · risk **ELEVATED** · term `sharp steam revenge`

    Families: —

    ---

    [Open snapshot →](./runs/backfill-phase5-sharp-2026/index.md)

-   :material-flask-outline: **[backfill-phase5-rizz-2026](./runs/backfill-phase5-rizz-2026/index.md)**

    `phase5_scenario` · risk **MODERATE** · term `sigma rizz locked in`

    Families: —

    ---

    [Open snapshot →](./runs/backfill-phase5-rizz-2026/index.md)

-   :material-file-document-outline: **[backfill-ytd-2026-analysis](./runs/backfill-ytd-2026-analysis/index.md)**

    `analysis` · 16 receipts

    Families: `ai-native`×3, `betting-sharp`×2, `brainrot-aura`×5, `crypto-degen`×1, `gaming-meta`×2

    ---

    [Open snapshot →](./runs/backfill-ytd-2026-analysis/index.md)

-   :material-flask-outline: **[phase5-rizz-ai-demo](./runs/phase5-rizz-ai-demo/index.md)**

    `phase5_scenario` · risk **MODERATE** · term `sigma rizz locked in`

    Families: —

    ---

    [Open snapshot →](./runs/phase5-rizz-ai-demo/index.md)

-   :material-file-document-outline: **[golden-seed-0.3.2](./runs/golden-seed-0.3.2/index.md)**

    `analysis` · 9 receipts

    Families: `(none)`×1, `ai-native`×1, `betting-sharp`×1, `brainrot-aura`×1, `crypto-degen`×1

    ---

    [Open snapshot →](./runs/golden-seed-0.3.2/index.md)

-   :material-file-document-outline: **[golden-seed-0.3.1](./runs/golden-seed-0.3.1/index.md)**

    `analysis` · 9 receipts

    Families: `betting-sharp`×5

    ---

    [Open snapshot →](./runs/golden-seed-0.3.1/index.md)

</div>

## Published vs not

| On Pages | Stays local |
|----------|-------------|
| Sanitized receipt summaries | Full raw signals / API keys |
| Lineage, typology, virality, stage | Score-log settlements (unless you export) |
| Phase 5 digests (SPECULATIVE) | Invented Brier (never) |

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
Hermes skill · Brier requires settlement · no Abraxas hard import · primary store ~/.hyperlex
</p>
