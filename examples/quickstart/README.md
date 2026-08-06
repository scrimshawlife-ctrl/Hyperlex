# Quickstart sample (offline demo)

## Run it

From the repo root (no API keys, no Hermes host):

```bash
python3 scripts/hyperlex.py demo
# optional:
python3 scripts/hyperlex.py demo --query "locked in"
```

## What you get

| Artifact | Description |
|----------|-------------|
| `demo_summary.json` | Compact result of a successful offline demo |
| `sample_receipt.json` | One integrity-hashed receipt (`brier: null`) |
| `out/` (gitignored) | Fresh receipts + score log when you re-run demo |

## Expected checks

- `ok: true`
- `brier: null` and `provenance_brier: null`
- `lineage_family` set for known slang (e.g. `brainrot-aura` for `rizz`)
- `receipt` path present

Docs: [docs/start/quickstart.md](../../docs/start/quickstart.md)
