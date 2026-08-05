# Hyperlex

<figure class="hlx-hero" markdown>
![Hyperlex — memetic emergence (Grok Imagine)](assets/images/hyperlex-imagine-hero.jpg){ width="420" }
<figcaption>Visual identity · <a href="https://grok.com/imagine/post/0fef2df1-6bec-4b18-9ee6-823dd77ba9f6">Grok Imagine</a></figcaption>
</figure>

<div class="hlx-status" markdown>
<span><span class="hlx-dot"></span><strong>v0.3.2</strong></span>
<span>Hermes skill · Python package repo</span>
<span>Phases 0–4 complete · Phase 5.0</span>
<span>Pages = static run history</span>
</div>

<p class="hlx-lead">
Detect, score, and archive memetic signals — lineage, hyperstition, settled Brier only.
Primary store is local; this site is the publish-safe desk for docs and run history.
</p>

## Desk

<div class="grid cards" markdown>

-   :material-history: **Run history**

    Dated, sanitized snapshots on Pages. Not live operator state.

    ---

    [Open catalog →](archive/index.md){ .md-button }
    [Latest analysis](archive/latest/index.md)

-   :material-download: **Install**

    Hermes skill tree → `~/.hermes/skills/hyperlex`

    ---

    ```bash
    bash install.sh
    export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
    python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" doctor
    ```

-   :material-flask-outline: **Simulate (Phase 5)**

    Transmission · multi-agent · hyperstition risk · phylogeny scaffold.
    All SPECULATIVE · `brier: null`.

    ---

    ```bash
    python3 scripts/hyperlex.py simulate --term rizz --mode scenario
    ```

    [Phase 5 docs](phase5.md)

-   :material-heart-pulse: **Status**

    Ready surface, operator loop, data dirs.

    ---

    [Skill status →](status.md)

</div>

## Rules (non-negotiable)

!!! warning "Brier requires settlement"
    Open analysis always has `provenance.brier = null`. Phase 5 keeps `brier: null`.
    Numeric Brier only after operator settlement.

Hosts may import Abraxas-shaped modules **from** Hyperlex (`hyperlex.compat.abraxas`). Hyperlex never imports Abraxas.

## Map

| Need | Go |
|------|-----|
| Skill contract | [hermes-skill](hermes-skill.md) |
| Frozen API | [api-v1](api-v1.md) |
| Lineages | [slang-lineages](slang-lineages.md) |
| Calibration | [brier-calibration](brier-calibration.md) |
| Simulation | [phase5](phase5.md) · [modules/simulation](modules/simulation.md) |
| Case study | [case-studies](case-studies.md) |
| Roadmap | [ROADMAP](ROADMAP.md) |

## Append a run to Pages

```bash
python3 scripts/hyperlex.py archive-export --include-golden --history
# or operator home:
python3 scripts/hyperlex.py archive-export --include-home-receipts --history
# Phase 5 digest:
python3 scripts/hyperlex.py simulate --term rizz --out /tmp/p5.json
python3 scripts/hyperlex.py archive-export --phase5 /tmp/p5.json --history
```

Commit `docs/archive/` and push — [docs.yml](https://github.com/scrimshawlife-ctrl/Hyperlex-Hermes-Specs/actions) rebuilds the site.

Site: [scrimshawlife-ctrl.github.io/Hyperlex-Hermes-Specs](https://scrimshawlife-ctrl.github.io/Hyperlex-Hermes-Specs/)

<p class="hlx-posture">
Hermes skill · Brier requires settlement · no Abraxas hard import · primary store ~/.hyperlex
</p>
