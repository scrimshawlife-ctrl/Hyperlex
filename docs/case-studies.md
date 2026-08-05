# Case studies

See the repo folder [`examples/case-studies/`](https://github.com/scrimshawlife-ctrl/Hyperlex-Hermes-Specs/tree/main/examples/case-studies).

## End-to-end mock scan

Walkthrough: `examples/case-studies/e2e-mock-scan.md`

```bash
export HERMES_SKILL_DIR="${HOME}/.hermes/skills/hyperlex"
python3 "$HERMES_SKILL_DIR/scripts/run_case_study.py" --out-dir out/case-study
```

Produces analyze JSON, forecasts, rune envelopes, market signal, and Mermaid diagrams.
`provenance.brier` remains `null` until operator settlement.
