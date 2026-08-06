# Release notes

## 0.4.0
- Automatic backend pipeline: `pipeline` / `run` / `ingest` → full results packet.
- Ingest defaults to full results (`--raw-only` for signal-only).
- Multi-term bags expand to one result unit per atom; never auto-settles.

## 0.3.9
- Atomic multi-term seeds: `terms-split`, Phase 5 multi-term expand, per-term lineage.
- Pages demos: `docs/demos/atomic-terms.md` + `examples/demos/` fixtures.
- Scan/cron packs use atomic queries; archive Phase 5 snapshots re-exported multi-term.

## 0.3.8
- Operator loop docs; simplified command map (`commands`, `run`, `pending`).
- Ingest routes (`--route offline|live|…`) + canonical source catalog/aliases.

## 0.3.7
- Risk-tier → scan/cron schedule coupling (`risk-schedule`, `simulate --mode schedule`).
- Post-scan `scan_risk_advisory`; advisory job envelopes under `examples/cron/`.

## 0.3.6
- Transmission calibrate, multi-agent scenario library, research export.

## 0.3.5
- Hybrid lineage re-rank (lexical + vector); domain phylogeny packs.

## 0.3.4
- Vector neighbors on analyze; receipts auto-index into local vector DB.

## 0.3.3
- Local SQLite vector DB (`vector-seed` / `vector-search`) for terms + receipts.
- Chroma local + Cloud; backfill via `vector-seed --backend chroma --db ~/.hyperlex/chroma`; promote with `vector-sync --to cloud` (embeddings preserved). Hermes `.env` auto-load for `CHROMA_*` keys.
- Pages researcher guide: `demos/reading-evidence.md` + publish-safe vector sample; telemetry/archive how-to-read updated.

## 0.3.2
- Hallmark redesign of Pages: workbench home, teal identity, run-history cards.

## 0.3.1
- GitHub Pages = static history of runs (`docs/archive/runs/` + catalog).

## 0.3.0
- Phase 5.0: cultural transmission, multi-agent memetics, hyperstition risk, phylogeny scaffold, CLI `simulate`.

## 0.2.12
- YTD 2026 slang backfill packs + non-mutating lineage backpropagation.

## 0.2.11
- Pages enabled; long-term analysis archive export.

## 0.2.10
- openai_compatible LLM provider; ledger-stats; STATUS.md.

## 0.2.9
- `doctor` command; release preflight; Pages site_url.

## 0.2.8
- GitHub Pages MkDocs deploy; strict docs build; CI case study.

## 0.2.7
- MkDocs; governed LLM stub; ledger-diff CLI.

## 0.2.6
- Case study runner; gaming-meta + workplace-corp lineages.

## 0.2.5
- Virality prediction v0; community drivers; richer neologism rules.

## 0.2.4
- Hermes skill posture docs; typology expansion; CI + golden corpus growth.

## 0.2.3
- Automated Mermaid diagrams from receipts/ledger (`diagram` CLI).

## 0.2.2
- Docs refresh (ARCHITECTURE, README, QUICKSTART, connectors).
- Market signal + forecast pipeline connectors (`hyperlex.connectors`).
- Hyperstition loop feedback into future forecast stage maps (advisory).
- CLI: `signal`, `feedback`.

## 0.2.1
- Hermes skill model (Python package repo); `hyperlex.compat.abraxas` modules.
- Public API v1 freeze; golden receipt corpus.

## 0.2.0
- Rune relay, provenance fingerprints, glossary expansion, X ingest.
- Local package CLI (`python -m hyperlex`).

## 0.1.x
- Lineage, Brier calibration, settlement score log, Hermes skill install, receipt ledger, LIVE_EMERGENCE_SCAN.
