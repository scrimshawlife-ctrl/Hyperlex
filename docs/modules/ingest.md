# Ingest Module Design

## Goals
- Ground analysis in **real** current slang and signals
- Support multiple sources with graceful fallback
- Keep ingest deterministic when possible for testing

## Current Sources
- **real**: Scrapes Action Network betting terms glossary
- **reddit**: Best-effort search (JSON fallback on blocks)
- **mock**: Fully deterministic test data

## Planned
- X/Twitter via xurl or official API (rate-limited)
- Firecrawl for broader web signals
- Community glossaries and forums

## Requirements
- Must return string signal
- Must record `ingest_source` in provenance
- Failures must not crash — return informative fallback text
