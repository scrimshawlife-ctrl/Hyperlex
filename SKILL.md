---
name: hyperlex
version: 0.1.0
description: "Standalone memetic emergence engine for slang detection, hyperstition tracking, and virality analysis. Real-ish ingest, bounded analysis, and receipt output."
license: MIT
metadata:
  openclaw:
    requires:
      bins: [python3]
    os: [darwin, linux]
    emoji: "🌀"
---

# Hyperlex

Hermes + OpenClaw skill for memetic signal foraging.

## Core Commands

All commands are available from the installed skill directory:

```bash
python3 scripts/hyperlex.py check
python3 scripts/hyperlex.py sources
python3 scripts/hyperlex.py ingest "<query>" --source <mock|real|glossary|web|reddit|urban|wikipedia|combined|x_search|firecrawl|crawl4ai>
python3 scripts/hyperlex.py analyze --query "<query>" [--source <source>] [--structured-ingest]
python3 scripts/hyperlex.py analyze --input <ingest.json> [--validate]
python3 scripts/hyperlex.py validate <artifact.json>
python3 scripts/hyperlex.py verify-receipt <receipt.json>
python3 scripts/hyperlex.py smoke
```

## Public API (package)

```python
from hyperlex import ingest_signal, fetch_ingest, detect_memetic_patterns
from hyperlex import mock_integrate_with_external_signal, emit_receipt, schemas

result = detect_memetic_patterns(query="sharp money revenge", ingest_source="mock")
signal = mock_integrate_with_external_signal(result)
receipt_path = emit_receipt(result)
ok, msg = schemas.validate_result(result)
```

## Notes

- `firecrawl` is backed by a Crawl4AI web crawler, and `crawl4ai` is an explicit
  alias for the same adapter. `x_search` remains a placeholder for future direct
  social ingestion.
- Outputs are validated against JSON schemas under `schemas/`.
- No required external services are required to run the baseline skill.
