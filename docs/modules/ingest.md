# Ingest Module Design

## Goals
- Ground analysis in **real** current slang and signals
- Support multiple sources with graceful fallback
- Keep ingest deterministic when possible for testing

## Current Sources
- **real**: Scrapes Action Network betting terms glossary
- **reddit**: Best-effort search (JSON fallback on blocks)
- **firecrawl**: Crawl4AI-powered web crawl
- **crawl4ai**: explicit alias to crawl-backed source
- **mock**: Fully deterministic test data

## Planned
- X/Twitter via xurl or official API (rate-limited)
- `x_search` remains a placeholder for direct social ingestion
- Community glossaries and forums

## Requirements
- Must return string signal
- Must record `ingest_source` in provenance
- Failures must not crash — return informative fallback text
