# Governed LLM layer (optional)

**Default: off.** The Hermes skill runs fully without any model.

## Enable

```bash
export HYPERLEX_LLM=1

# Deterministic dry-run (no network) — tests / CI
export HYPERLEX_LLM_PROVIDER=echo

# OpenAI-compatible HTTP (stdlib urllib; no openai package required)
export HYPERLEX_LLM_PROVIDER=openai_compatible
export HYPERLEX_LLM_API_KEY=sk-...          # or OPENAI_API_KEY
export HYPERLEX_LLM_BASE_URL=https://api.openai.com/v1   # optional
export HYPERLEX_LLM_MODEL=gpt-4o-mini                    # optional
export HYPERLEX_LLM_TIMEOUT=30                           # seconds
```

`HYPERLEX_OFFLINE=1` refuses `openai_compatible` network calls (fail closed).

Or inject a provider in process:

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
