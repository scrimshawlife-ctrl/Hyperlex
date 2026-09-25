# jevgate-1 (opt-in classify)

Family classification of one short term into the eight hyperlexical families or `none`.

The default path is unchanged: lexical `match_lineage` (vector re-rank off). If that rule fires, its family decides. If it misses, the cascade returns `none`.

## Enable

```bash
export HYPERLEX_JEVGATE=1
python3 scripts/hyperlex.py classify "<term>"

# or one shot, without the env var
python3 scripts/hyperlex.py classify "<term>" --jevgate
```

`--no-jevgate` forces the registry cascade even when `HYPERLEX_JEVGATE` is set.

Package entry point: `python -m hyperlex classify "<term>" --jevgate`.

## Gate

Frozen by prereg v5. Do not tune.

| Item | Value |
|------|--------|
| Model | `jev-1.13.0` (pinned; a missing or different `model` id is an error) |
| Passes | 3 identical requests; probabilities are means |
| Tau | `0.30333` |
| Decision | a family only when mean `P(none)` is **strictly below** tau; otherwise `none` |
| Ties | earliest family in `FAMILIES` from `hyperlexical.layout` |
| Prompt sha256 | `0dab58787402cb6e5aadc92e3123a65f09d281444e100b8485ede273c7d9af53` |

`sha256(JSON.stringify(QUESTIONS))` is checked when the module loads. If it differs, the Jev path is refused.

The gate **abstains often by design**. `none` is the expected output for ordinary English, names, noise, and slang from communities outside the eight.

`jev_best_guess` (argmax over the eight families, ignoring tau), `jev_p_none`, and the per-family means are low-confidence fields. They never change `family`. Jev's own `choice`, `in_scope`, and `any_slang` may be logged under `jev_log` and never decide.

On provider error, timeout, parse failure, model mismatch, or a missing key, the call is retried once. If it still fails, the result is `none` with `jev_error.flag` and `jev_error.reason` set. Jev failures do not raise into callers.

## API key

The key is read only from the environment:

- `JEV_API_KEY` (preferred), or `TYPESAFE_AI_API_KEY`
- `JEV_KEY_FILE` — path of a file that contains the key (no default path)

There is no key in the repo. `HYPERLEX_OFFLINE=1` refuses the network call and fail-closes to `none`.
