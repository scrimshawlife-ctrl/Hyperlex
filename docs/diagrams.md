# Diagram generation from receipts

Automated Mermaid diagrams from receipt history. No network required for generation;
optional HTML uses a Mermaid CDN for interactive viewing.

## CLI

```bash
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
H="$HERMES_SKILL_DIR/scripts/hyperlex.py"

# Golden corpus (default if no flags and corpus present)
python3 "$H" diagram --from-golden --out-dir out/diagrams

# Receipt ledger
python3 "$H" diagram --from-ledger --out-dir out/diagrams

# Specific receipts
python3 "$H" diagram --input path/to/receipt.json --out-dir out/diagrams

# Filter family on ledger
python3 "$H" diagram --from-ledger --lineage-family betting-sharp
```

## Kinds

| Key | Content |
|-----|---------|
| `lineage_distribution` | Pie of family frequencies |
| `receipt_timeline` | LR timeline of receipts (stage + confidence) |
| `family_graph` | Families → matched terms |
| `flow_<name>` | Per-receipt intake→analysis→archive flow |

## Library

```python
from hyperlex import diagram_from_receipt_files, write_diagram_bundle
from pathlib import Path

diagrams = diagram_from_receipt_files(Path("examples/receipts/golden").glob("*.json"))
write_diagram_bundle(diagrams, "out/diagrams", html=True)
```

## Epistemic labels

- Structure from receipt indexes is **OBSERVED** (paths, hashes, timestamps on ledger).
- Family assignment remains **INFERRED** (lineage matcher).
- Diagrams never invent Brier scores (`brier=null` on flow archive node).
