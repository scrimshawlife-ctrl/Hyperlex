# Telemetry

Operator desk on Pages — **publish-safe**, not a live dashboard.  
Real state lives in `~/.hyperlex/` (receipts, score log, vector DB).

<div class="hlx-status" markdown>
<span><span class="hlx-dot"></span><strong>v0.4.0</strong></span>
<span>Hermes skill · auto pipeline</span>
<span>Atomic multi-term · settled Brier only</span>
<span>Pages = static history</span>
</div>

<p class="hlx-lead">
<strong>One command → full results.</strong> Ingest runs the backend automatically.
Open analysis never invents Brier. Settlement is the only manual step.
</p>

## Start here (automatic backend)

```bash
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
export HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"

# Install / health
bash install.sh
$HLX doctor

# AUTO: ingest → analyze → receipt → forecasts → score log → Phase 5 risk
$HLX pipeline "rizz" --route offline
# same path:
$HLX run "rizz"
$HLX ingest "rizz"                 # --raw-only = signal only

# Free-text bag → separate atoms (not one blended seed)
$HLX pipeline "sigma rizz locked in"
# → results for: sigma | rizz | locked in

# Only manual step for real scores:
$HLX pending
$HLX settle --forecast-id <id> --decision TRUE
$HLX score-series --mean-shift --verify-chain
```

Week-one script: `bash examples/ops/burn-in.sh`

## Desk

<div class="grid cards" markdown>

-   :material-play-circle: **Pipeline (auto)**

    Ingest → analyze → receipt → forecasts → Phase 5 risk.  
    Multi-term bags expand to atoms.

    ---

    ```bash
    $HLX pipeline "rizz" --route offline
    $HLX pipeline "sigma rizz locked in"
    ```

    [Command map](commands.md) · [Operator loop](operator-loop.md)

-   :material-vector-arrange-below: **Atomic terms**

    `"sigma rizz locked in"` is **input text**, not one slang item.  
    Engine splits to `sigma` · `rizz` · `locked in`.

    ---

    ```bash
    $HLX terms-split "sigma rizz locked in"
    ```

    [Full demos →](demos/atomic-terms.md)  
    [Example run](archive/runs/backfill-phase5-rizz-2026/index.md)

-   :material-history: **Run history**

    Sanitized snapshots on Pages. Not live operator state.

    ---

    [Catalog →](archive/index.md){ .md-button }  
    [Latest analysis](archive/latest/index.md)

-   :material-download: **Install**

    Hermes skill → `~/.hermes/skills/hyperlex`

    ---

    ```bash
    bash install.sh
    export HERMES_SKILL_DIR="$HOME/.hermes/skills/hyperlex"
    $HLX doctor
    ```

-   :material-flask-outline: **Phase 5 (research)**

    Transmission · multi-agent · risk · phylogeny.  
    SPECULATIVE · `brier: null`. Prefer atomic seeds.

    ---

    ```bash
    $HLX simulate --term rizz --mode scenario
    $HLX simulate --term "sigma rizz locked in"   # expands
    ```

    [Phase 5](phase5.md) · [Simulation modules](modules/simulation.md)

-   :material-vector-polyline: **Vector DB**

    SQLite default · **local Chroma backfill** · promote to Cloud.  
    **Terms are atomic.** Similarity ≠ Brier.

    ---

    ```bash
    # Local Chroma (recommended iterate path)
    $HLX vector-seed --backend chroma --db ~/.hyperlex/chroma \
      --through 2026-08 --include-home --include-golden
    $HLX vector-stats --backend chroma --db ~/.hyperlex/chroma
    $HLX vector-search "rizz" --backend chroma --db ~/.hyperlex/chroma --kind term

    # Promote when good (creds in ~/.hermes/.env)
    $HLX vector-sync --from-path ~/.hyperlex/chroma --to cloud
    $HLX vector-stats --cloud
    ```

    [Vector DB · Chroma map →](modules/vectordb.md)

-   :material-heart-pulse: **Status**

    Ready surface, data dirs, recommended next.

    ---

    [Skill status →](status.md)

</div>

## How to read Pages content

| You see | Means |
|---------|--------|
| **atoms** `sigma` · `rizz` · `locked in` | Three separate scenarios (good) |
| **term** `rizz` | Single-atom run |
| **original_seed** | Free-text input only — not a blended lexicon item |
| **risk tier** | Advisory Phase 5 signal — not Brier, not market advice |
| **Brier `null`** | Correct until you settle forecasts |
| **Families** on analysis cards | Lineage counts from receipt summaries |

## Rules (non-negotiable)

!!! warning "Brier requires settlement"
    Pipeline / analyze / Phase 5 keep `brier: null`.  
    Numeric Brier only after operator `settle` → `score-series`.

!!! note "Primary store is local"
    Pages never replaces `~/.hyperlex/`. Archive export is sanitized static history.

Hosts may import Abraxas-shaped modules **from** Hyperlex. Hyperlex never imports Abraxas.

## Map

| Need | Go |
|------|-----|
| Auto backend | [commands](commands.md) · [operator-loop](operator-loop.md) |
| Multi-term demos | [demos/atomic-terms](demos/atomic-terms.md) |
| Skill contract | [hermes-skill](hermes-skill.md) |
| Lineages | [slang-lineages](slang-lineages.md) |
| Calibration | [brier-calibration](brier-calibration.md) |
| Simulation | [phase5](phase5.md) |
| Cron / risk schedule | [cron-live-emergence](cron-live-emergence.md) |
| Run history | [archive](archive/index.md) |
| Splash | [Home](index.md) |

## Publish a snapshot to Pages

```bash
# After local pipeline runs:
$HLX archive-export --include-home-receipts --history

# Phase 5 multi-term digest (atoms stay separate on the site):
$HLX simulate --term "sigma rizz locked in" --out /tmp/p5.json
$HLX archive-export --phase5 /tmp/p5.json --history --snapshot-id "phase5-atoms-$(date -u +%Y%m%d)"
```

Commit `docs/archive/` and push — docs workflow rebuilds the site.

Site: [scrimshawlife-ctrl.github.io/Hyperlex](https://scrimshawlife-ctrl.github.io/Hyperlex/)

<p class="hlx-posture">
pipeline = auto results · Brier requires settlement · no Abraxas hard import · primary store ~/.hyperlex
</p>
