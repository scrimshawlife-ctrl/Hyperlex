# T11 Dual-use merge gate

Answered 2026-09-04. Required before merge to main.

| # | Question | Answer |
|---|----------|--------|
| 1 | Can a test fixture be reused as a restricted wrap? | No. Civilian only: `rizz`, `unalive`, `it's giving`, productive suffixes, eggcorns. No restricted how-to strings in-repo. |
| 2 | Does any path call `predict_mutations` after restricted flag? | No. `tests/test_mutation_grammar.py::test_predict_not_used_on_restricted` asserts `grammar.py` does not contain that name. Predict stays on slang-atom seeds. |
| 3 | Does watch_score write Brier? | No. Schema and packet force `brier: null`, `forecast_eligible: false`. |
| 4 | Can watch_score fire tools / cron? | No. C10 / constitution. Advisory envelopes only. |
| 5 | Restricted persistence | `restricted_intent_suspected` → drop `surface_span` and `canonical_gloss`; keep SHA-256 `payload_ref`. |
| 6 | Host output handling | Treat packets as untrusted (OWASP LLM10:2026). |
| 7 | Claim vs control | Maps to LLM01 linguistic injection *surface*. Does not close prompt injection. |

If any answer flips to yes, block merge and delete the fixture or path that caused it.
