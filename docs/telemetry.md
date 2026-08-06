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
Open analysis never invents Brier. Settlement is the only manual step for real scores.
</p>

<div class="hlx-path-grid" markdown>

<div class="hlx-path-card hlx-path-card--primary" markdown>

**If you are reading evidence**

Start with provenance layers, the claims matrix, and a publish-safe vector sample.

[Reading evidence →](demos/reading-evidence.md){ .md-button .md-button--primary }

</div>

<div class="hlx-path-card" markdown>

**If you are running the skill**

Install → pipeline → pending → settle → optional vector seed / Cloud promote.

[Operator loop →](operator-loop.md){ .md-button .md-button--primary }

</div>

</div>

## Start here (automatic backend)

```bash
export HERMES_SKILL_DIR="${HERMES_SKILL_DIR:-$HOME/.hermes/skills/hyperlex}"
export HLX="python3 $HERMES_SKILL_DIR/scripts/hyperlex.py"

bash install.sh && $HLX doctor

# AUTO: ingest → analyze → receipt → forecasts → score log → Phase 5 risk
$HLX pipeline "rizz" --route offline
$HLX pipeline "sigma rizz locked in"   # atoms: sigma | rizz | locked in

# Only manual step for real scores:
$HLX pending
$HLX settle --forecast-id <id> --decision TRUE
$HLX score-series --mean-shift --verify-chain
```

Week-one: `bash examples/ops/burn-in.sh`

## Desk

<div class="grid cards" markdown>

-   :material-book-open-page-variant: **Reading evidence**

    **Primary for researchers.** Layers, provenance, claims matrix, vector sample.

    ---

    [Open guide →](demos/reading-evidence.md){ .md-button }

-   :material-play-circle: **Pipeline (auto)**

    Ingest → analyze → receipt → forecasts → Phase 5.  
    Multi-term bags expand to atoms. May auto-index local vectors.

    ---

    ```bash
    $HLX pipeline "rizz" --route offline
    $HLX pipeline "sigma rizz locked in"
    ```

    [Commands](commands.md) · [Operator loop](operator-loop.md)

-   :material-vector-arrange-below: **Atomic terms**

    `"sigma rizz locked in"` is **input text**, not one slang item.

    ---

    [Demos →](demos/atomic-terms.md)  
    [Example run](archive/runs/backfill-phase5-rizz-2026/index.md)

-   :material-history: **Run history**

    Sanitized snapshots. Not live operator state.

    ---

    [Catalog →](archive/index.md){ .md-button }  
    [Latest](archive/latest/index.md)

-   :material-vector-polyline: **Vector index**

    Local sqlite/chroma · auto on ingest · promote to Cloud is explicit.  
    **Similarity ≠ Brier.**

    ---

    ```bash
    $HLX vector-seed --backend chroma --db ~/.hyperlex/chroma \
      --through 2026-08 --include-home --include-golden
    $HLX vector-search "rizz sigma aura" --backend chroma --db ~/.hyperlex/chroma --kind term
    $HLX vector-sync --from-path ~/.hyperlex/chroma --to cloud
    ```

    [How to read scores →](demos/reading-evidence.md) · [Backend map](modules/vectordb.md)

-   :material-flask-outline: **Phase 5**

    Transmission · multi-agent · risk · phylogeny.  
    **SPECULATIVE** · `brier: null`.

    ---

    [Phase 5](phase5.md) · [Modules](modules/simulation.md)

-   :material-heart-pulse: **Status**

    Ready surface and data dirs.

    ---

    [Skill status →](status.md)

</div>

## How to read Pages content

| You see | Means |
|---------|--------|
| **atoms** `sigma` · `rizz` · `locked in` | Three separate scenarios (good) |
| **term** `rizz` | Single-atom run |
| **original_seed** | Free-text input only — not a blended lexicon item |
| **vector neighbors / cosine score** | Embedding similarity — **not** a probability, **not** Brier |
| **risk tier** | Advisory Phase 5 — not market advice, not Brier |
| **Brier `null`** | Correct until you settle forecasts |
| **Families** on analysis cards | Lineage counts from receipt summaries |
| **OBSERVED / INFERRED / SPECULATIVE** | Provenance of the claim |

Full guide: [Reading Hyperlex evidence](demos/reading-evidence.md).

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
| **Researcher reading** | [demos/reading-evidence](demos/reading-evidence.md) |
| Auto backend | [commands](commands.md) · [operator-loop](operator-loop.md) |
| Multi-term demos | [demos/atomic-terms](demos/atomic-terms.md) |
| Skill contract | [hermes-skill](hermes-skill.md) |
| Lineages | [slang-lineages](slang-lineages.md) |
| Calibration | [brier-calibration](brier-calibration.md) |
| Simulation | [phase5](phase5.md) |
| Run history | [archive](archive/index.md) |
| Splash | [Home](index.md) |

## Publish a snapshot to Pages

```bash
$HLX archive-export --include-home-receipts --history
$HLX simulate --term "sigma rizz locked in" --out /tmp/p5.json
$HLX archive-export --phase5 /tmp/p5.json --history --snapshot-id "phase5-atoms-$(date -u +%Y%m%d)"
```

Commit `docs/archive/` and push — docs workflow rebuilds the site.

Site: [scrimshawlife-ctrl.github.io/Hyperlex](https://scrimshawlife-ctrl.github.io/Hyperlex/)

<p class="hlx-posture">
pipeline = auto · Brier requires settlement · vector ≠ probability · primary store ~/.hyperlex
</p>
