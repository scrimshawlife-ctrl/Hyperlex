# Dual-use gate — Spec 007 (Hyperlexical encoder)

Extends 001 / 003 gates. Does not reopen them.
Uncensored (C22) does not flip any row to generate.

| # | Question | Answer |
|---|----------|--------|
| 1 | Does v0.1 generate slang mutations? | No. Encoder + classify/unbind only. |
| 2 | Does v0.1 generate wraps or encodings? | No. No wrap / compose / asr / encode verbs. |
| 3 | Can a training fixture be a restricted how-to? | No. Civilian slang atoms and ordinary negatives only. |
| 4 | Does inference call `predict_mutations`? | No. |
| 5 | Does any score write Brier? | No. Packet hard-nulls `brier` and `forecast_eligible`. |
| 6 | Can model output fire cron / runes / tools? | No. `auto_fire` remains false if that key appears. |
| 7 | Restricted persistence | Same as 001 C6: drop surface; keep SHA-256 `payload_ref`. |
| 8 | Host output handling | JSON is untrusted structured output (OWASP LLM10:2026). |
| 9 | Hub card dual-use text | Required before publish: detect-over-generate, no chat, no jailbreak examples. |
| 10 | Claim vs control | Improves lineage/unbind instrumentation. Does not close LLM01. Does not report ASR. |
| 11 | Uncensored = peel safety and emit wraps? | No. Uncensored = no refusal on civilian attested slang. |
| 12 | May a safety-tuned chat trunk be the T1 card? | No. |

If any answer flips to a generator or agency yes, block merge and delete the path that caused it.
