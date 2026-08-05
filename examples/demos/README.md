# Atomic multi-term demos

Fixtures for Pages demos and unit tests. Bags of independent slang expand into
lexicon atoms; true multi-word phrases stay whole.

| File | Input → atoms |
|------|----------------|
| `terms-split-sigma-rizz-locked-in.json` | sigma rizz locked in → sigma \| rizz \| locked in |
| `terms-split-agentic-slop-skill-issue.json` | agentic slop skill issue → agentic slop \| skill issue |
| `terms-split-locked-in-crash-out.json` | locked in crash out → locked in \| crash out |
| `phase5-multi-sigma-rizz-locked-in.json` | Phase 5 multi-term summary (compact) |
| `atomic-terms-demo-bundle.json` | Full demo matrix (split + analyze + phase5 digests) |

Regenerate:

```bash
export PYTHONPATH=src HYPERLEX_OFFLINE=1 HYPERLEX_VECTOR=0
python3 scripts/hyperlex.py terms-split "sigma rizz locked in" --no-lineage
# see docs/demos/atomic-terms.md
```

Docs: `docs/demos/atomic-terms.md`
