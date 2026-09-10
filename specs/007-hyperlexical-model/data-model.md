# Data model 007 — Hyperlexical inference

Packet id: `hyperlex.hyperlexical.inference.v0.1`

## Entities

- **Atom**: attested civilian string. Gold from fixtures/receipts.
- **Binding**: role scheme × fillers. Schemes locked: `positional`, `type_slot`.
- **Inference packet**: one atom in, one packet out. Never a forecast.
- **Stub embed**: `STATIC_HASH_EMBEDDING`. Control only.
- **Model embed**: `MODEL_EMBEDDING`. Requires provenance hashes.

## Required fields

`schema`, `brier` (null), `forecast_eligible` (false), `routes_claimed` (form|lexical), `class`

## Additive provenance (fold 2026-09-09)

`embed_mode`, `model_version`, `encoder_version`, `input_hash`, `vector_hash`, `selection_proxy`

`selection_proxy` ∈ {weakness, mdl, unspecified}

Forbidden keys: `symbolic`, `has_symbols`, `semantic` inside `routes_claimed`, numeric `brier`.

## Gold vs weak

| provenance | may train T0 classify | may gate E2 unbind | may name Hyperlexical |
|------------|----------------------|--------------------|------------------------|
| OBSERVED fixture / settled copy | yes | yes | yes if E2 pass |
| INFERRED detector weak label | yes | no | no |
| SPECULATIVE Phase 5 / TimesFM / LLM slang | no | no | no |
| STATIC_HASH stub | CI only | no | no |
