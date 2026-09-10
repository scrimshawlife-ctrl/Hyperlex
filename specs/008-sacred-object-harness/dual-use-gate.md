# Dual-use gate — Spec 008

Extends 001 / 003 / 007 gates. Does not reopen them.

| # | Question | Answer |
|---|----------|--------|
| 1 | Does v0.1 generate slang mutations? | No. Eval + logs only. |
| 2 | Does v0.1 generate wraps or encodings? | No. |
| 3 | Can a fixture be a restricted how-to? | No. Civilian attested atoms and ordinary negatives only. |
| 4 | Does any room call `predict_mutations`? | No. |
| 5 | Does any score write Brier? | No. |
| 6 | Can eval output fire cron / runes / tools? | No. `auto_fire` remains false. |
| 7 | Restricted persistence | Drop surface; keep SHA-256 `payload_ref`. |
| 8 | Host output handling | JSON is untrusted structured output (LLM10:2026). |
| 9 | Room B agents invent opaque codes? | Measure only. Do not reward. Do not publish the code as a recipe. |
| 10 | Room C imports exploit labs? | No. Public stage names + control assertions only. |
| 11 | May 007 train on 008 transcripts? | No in this spec. Separate operator sentence later. |
| 12 | Uncensored 007 trunk = emit wraps here? | No. |

If any answer flips to generate or agency yes, block merge and delete the path that caused it.
