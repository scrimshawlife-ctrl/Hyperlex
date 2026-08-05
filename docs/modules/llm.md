# Governed LLM layer (optional)

**Default: off.** The Hermes skill runs fully without any model.

## Enable

```bash
export HYPERLEX_LLM=1
export HYPERLEX_LLM_PROVIDER=echo   # deterministic dry-run for tests
```

Or inject a real provider in process:

```python
from hyperlex.llm.governed import set_provider, enrich_neologisms

def my_provider(prompt: str, context: dict) -> str:
    # call your model; return JSON string with candidates
    return '{"candidates":[{"term":"example","formation":"llm","confidence":0.5}]}'

set_provider(my_provider)
```

## What it may do

- Suggest additional neologism candidates merged into `analysis.neologisms`
- Record status under `analysis.llm_enrichment`

## What it must not do

- Set `provenance.brier`
- Auto-settle forecasts
- Mutate score log or receipt ledger
- Claim OBSERVED without operator evidence

Candidate confidences are capped at **0.85**. Provenance defaults to **SPECULATIVE**.

## Status values

| status | meaning |
|--------|---------|
| `skipped` | `HYPERLEX_LLM` not enabled |
| `not_configured` | enabled but no provider |
| `applied` | candidates merged |
| `error` | provider raised |
