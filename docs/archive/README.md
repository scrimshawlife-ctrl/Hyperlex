# Long-term analysis archive

## What this is

A **publish-safe** snapshot of ingest/analysis results for long-term review on
the docs site (GitHub Pages). Suitable for:

- Tracking lineage family drift over time
- Sharing sanitized summaries without operator secrets
- Browsing historical scans in git history

## What this is not

| Primary store (local) | This archive (published) |
|----------------------|---------------------------|
| `~/.hyperlex/receipts/` | Sanitized JSON summaries only |
| `~/.hyperlex/receipt_ledger.jsonl` | Optional ledger extract |
| Full raw signals / operator notes | Previews only |
| Score log with settlements | Not auto-exported (operator may add later) |

**Source of truth for calibration remains the local score log + settlements.**

## Refresh the public archive

```bash
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"

# From golden fixtures (CI-safe)
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" archive-export \
  --include-golden \
  --out-dir docs/archive/latest

# From operator home receipts + ledger
python3 "$HERMES_SKILL_DIR/scripts/hyperlex.py" archive-export \
  --include-home-receipts \
  --out-dir docs/archive/latest
```

Commit and push `docs/archive/latest/` when you want the site updated.
Pages rebuilds via `.github/workflows/docs.yml`.

## Site URL

https://scrimshawlife-ctrl.github.io/Hyperlex-Hermes-Specs/archive/latest/
