# Dual-use addendum — Spec 003 (detect-only L4 / L6)

Answers 2026-09-05. Required before merge to main. Extends `specs/001-mutation-grammar/dual-use-gate.md`; does not reopen it.

| # | Question | Answer |
|---|----------|--------|
| 1 | Can a v0.2 fixture be reused as a restricted wrap? | No. Civilian only: vowel-dropped slang (`rzz`, `brnrt`), leet of known slang (`r1zz`), bilingual particle + slang (`el rizz`), mixed-script slang (`rizz 리즈`), game-frame + slang (`rizz in fortnite`). No restricted how-to strings. |
| 2 | Does GAME_ENCODE generate encodings? | No. Detect-only. Closed leet-translate *into* `SUBSTITUTE_TERMS`. No encode API, no wrap verb, no language-game composer. |
| 3 | Does CODE_SWITCH generate mixed-language attacks? | No. Detect-only. Mixed Unicode scripts or closed particle + lexicon hit. No paraphrase generator. |
| 4 | Does any path call `predict_mutations` after restricted flag? | No. Detector still wall-tested against that name. Predict stays on slang-atom seeds. |
| 5 | Does watch_score write Brier? | No. Packet and watch jsonl force `brier: null`, `forecast_eligible: false`. |
| 6 | Can watch_score or watch jsonl fire tools / cron / runes? | No. Records set `auto_fire: false`. Writer is fail-open. Advisory only (C10 / constitution III, VII, X). |
| 7 | Restricted persistence | Unchanged: flag true → drop `surface_span` / `canonical_gloss`; keep SHA-256 `payload_ref`. |
| 8 | Host output handling | JSON packets **and** `--human` cards are untrusted structured output (OWASP LLM10:2026). |
| 9 | Claim vs control | Still maps to LLM01 *linguistic* injection surface. Does not close prompt injection. Does not report ASR. |
| 10 | New verbs | `trace` and `watch` only. No `wrap` / `compose` / `asr` verbs. COMPOSE remains a detector enum tag. |

If any answer flips to a generator or agency yes, block merge and delete the fixture or path that caused it.
