# SoT scaffolding clean + civilian acquire (2026-09-23)

**Authority:** operator 2026-09-23 — clean SoT so wiki/scaffolding INFERRED rows stop defining the residual wall; acquire new data if necessary.

`name_gate=false`. Brier null. No Hub. No invented OBSERVED fillers.

## Clean

| | |
|--|--|
| ingest before → after | **4347 → 4290** (−57 INFERRED chrome) |
| harvest sidecar | 883 → 883 (0 dropped; OBSERVED MW clean) |
| live unbind chrome after | **0** residual-theme hits |
| durable reject | `export.reject_wiki_scaffolding_text` + `reject_candidate_text` |

Quarantine reasons: quotations 19, wiktionary 13, alt_form 5, declension 4, trends 4, synonym/antonym tables 5, etymology 3, neologism gloss 2, lang gloss 2.

Private: `~/hlx-private/p1-spark-sot-clean-scaffolding-20260923/`

## Acquire

Urban (+ reddit stubs) for brainrot / crypto / gaming MW slang. METHOD morph43 positional_text_split_match:

| | n |
|--|--:|
| candidates | 33 |
| AUTHORIZE | 13 |
| ABSTAIN | 20 (noise / non-canon) |
| already OBSERVED in SoT | 11 |
| INFERRED→OBSERVED settle | **2** (`to the moon`, `elo hell`) |

## morph74 one-knob

Force/hard expand for settled atoms: **217→221 / 258→262** (`force_added=4` dual-scheme). Warm morph65 + `INIT_EXPAND_VOCAB=1`. UPSAMPLE=10 / SECOND_SLOT=2 / LAST=8 held. Fair morph65 on morph74 force = **0.9880239520958084** n=167 (was 0.9649 n=171 pre-clean). Upsample freeze **11+**. Container `hlx-train-morph74-1790179734`.

See `receipts/20260923-morph74-acquire-settle-inflight.md`.
