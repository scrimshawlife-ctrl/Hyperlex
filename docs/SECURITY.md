# Security for Hyperlex

Hyperlex is a local analysis engine. It performs network requests only for configured real ingest sources.

## Threat Model
- Real ingest sources may return untrusted text (treat as untrusted input for downstream systems).
- Receipts contain analysis of potentially sensitive cultural signals — handle per your threat model.

## Recommendations
- Run in isolated environments when ingesting untrusted domains.
- Pin dependencies.
- Review any future LLM augmentation layers carefully.

See the main Abraxas-Orchestra-Hermes security posture for related agent guidelines.