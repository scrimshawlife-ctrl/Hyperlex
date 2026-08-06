# See it work

Concrete artifacts you can read in under a minute — no install required for the
static examples; offline CLI for a live receipt.

## Featured: brainrot-aura golden receipt {#featured-brainrot-aura}

**Source:** [`examples/receipts/golden/brainrot-aura.json`](https://github.com/scrimshawlife-ctrl/Hyperlex/blob/main/examples/receipts/golden/brainrot-aura.json)

### Human-readable summary

| Field | Value |
|-------|--------|
| Query (ingest) | `brainrot aura farming mid cooked` |
| Lineage family | `brainrot-aura` |
| Matched terms | brainrot, aura, aura farming, mid, cooked, let him cook |
| Confidence | 0.98 · provenance **INFERRED** |
| Receipt integrity | `e8e43b010371` |
| **Brier** | **`null`** (open analysis — not settled) |

**Observed (excerpt):** Mock memetic channel on brainrot / aura farming vocabulary
with status-radiation payload (content degradation + identity signaling).

**What you may claim:** this query matches the brainrot-aura lineage family with
high lexical confidence under the offline registry.

**What you must not claim:** a numeric Brier or “50% chance this goes viral”
from the open receipt alone.

### Lineage on the map

[Open constellation · family brainrot-aura →](../map/index.md?family=brainrot-aura)

### JSON (collapsible)

??? note "Open golden receipt JSON (excerpt)"
    Full file in the repo. Core shape:

    ```json
    {
      "ingest": { "query": "brainrot aura farming mid cooked" },
      "analysis": {
        "lineage": {
          "family_id": "brainrot-aura",
          "matched_terms": ["brainrot", "aura", "aura farming", "mid", "cooked", "let him cook"],
          "confidence": 0.98,
          "provenance": "INFERRED"
        }
      },
      "provenance": { "brier": null },
      "receipt": { "integrity": "e8e43b010371" }
    }
    ```

## Archive: YTD analysis snapshot

[backfill-ytd-2026-analysis](../archive/runs/backfill-ytd-2026-analysis/index.md) —
16 receipt summaries, multi-family distribution, publish-safe Pages history.

## Live offline (one minute)

```bash
python3 scripts/hyperlex.py demo --query "rizz"
```

Writes a receipt and prints a compact result packet with `brier: null`.

## Case study walkthrough

[Case studies](../case-studies.md) · e2e mock scan under `examples/case-studies/`.

## Related

- [Quickstart](quickstart.md)
- [Reading evidence](../demos/reading-evidence.md)
- [Settled Brier only](settled-brier.md)
