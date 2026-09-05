# Threat model — Spec 001

## Assets
- Lineage registry and family suffix tables.
- Receipt ledger integrity.
- Operator trust in OBSERVED / INFERRED / SPECULATIVE labels.
- Downstream hosts that might treat Hyperlex JSON as authoritative.

## Actors
- Honest operator studying slang emergence.
- Careless host that pipes trace output into an agent tool (LLM03 / LLM10).
- Adversary who wants a wrap archive or a generator.
- Supply-chain actor who poisons fixtures or LLM enrich.

## Trust boundaries
1. Raw ingest text — untrusted.
2. Parser — trusted to be deterministic and offline in v0.1; not trusted to judge harm.
3. Restricted-flag heuristic — INFERRED, fail-open toward redaction if unsure in later versions; v0.1 defaults false unless a closed civilian deny-lemma list hits after recovery.
4. Receipt store — trusted for integrity hashes; not a payload vault.
5. Abraxas / other hosts — untrusted from Hyperlex's view. Export only. No import.

## Abuse cases (defensive statements)
- **A1 Wrap factory:** attacker asks predict/trace to mint restricted paraphrases. Control: F4, C4, C9. Predict only on slang atoms from family/seed path.
- **A2 Archive reconstruction:** receipts become a cookbook. Control: C6 hash-only.
- **A3 Metric gaming:** lexicon-only watcher looks “green.” Control: pair A/B.
- **A4 Agency bleed:** high watch_score auto-relays a scan against a live model. Control: C10.
- **A5 Fixture poison:** malicious “civilian” list. Control: human review, provenance on fixture packs.
- **A6 Label laundering:** SPECULATIVE stacks reported as OBSERVED. Control: class field rules below.

## Epistemic rules for `class`
- OBSERVED: surface span literally present in input; operator is a closed-list affix or exact lexicon hit.
- INFERRED: register heuristic, decode_confidence, watch_score, recovered lemma via phonetics.
- SPECULATIVE: any link to predicted next-forms, Phase 5, hyperstition risk.

## Residual risk
v0.1 heuristics will under-detect GAME_ENCODE and CODE_SWITCH. That is accepted. Shipping a weak game parser that emits false OBSERVED is worse than omitting the parser.
