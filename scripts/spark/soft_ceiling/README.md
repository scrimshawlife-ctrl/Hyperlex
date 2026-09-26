# soft_ceiling chain (Spark)

Canonical, parameterized versions of the Spark `~/hlx` scripts that ran the morph75–78 soft_ceiling climb. Publish audit step 1a/2a/2b (`specs/007-hyperlexical-model/PUBLISH-READINESS-PLAN.md`).

| Step | Canonical | Needs |
|---|---|---|
| Settle named phrases + force/hard expand | `scripts/shadow/hyperlexical/val_settle.py` | operator sentence naming the phrases |
| Train | `scripts/spark/run_morph_train.sh` (unchanged) | `HYPERLEX_ALLOW_TRAIN=1` |
| E2 | `hyperlexical.eval_unbind --trunk-forward --model-dir DIR` | torch + trunk |
| Broad eval (all / clean / oov) | `eval_broad.py --model DIR --force F --hard H --out OUT` | torch + trunk |
| Decide | `finish.py ... --slice clean` (verdict only; `--apply-best` to move `BEST`) | — |

Gate logic lives in `scripts/shadow/hyperlexical/soft_ceiling.py` and is tested in CI without torch. It fails closed on unmeasured or non-zero overlap between the compared surface and the candidate's training files.

Two training flags stay off unless set:

- `HLX_SEED` — non-negative integer. Seeds Python `random`, NumPy, and PyTorch, and enables deterministic cuDNN plus `torch.use_deterministic_algorithms(True)`. Unset makes no seeding calls. `PYTHONHASHSEED` is written for child processes; it does not reseed the current process.
- `HLX_CLASSIFY_SPLIT_FILE` — JSON `{"schema":"hyperlex.classify_split_override.v0.1","base_trainval_sha256":"<optional>","split_by_row_id":{"<row_id>":"train"|"val"|"drop"}}`. Applied to classify train/val only, before admission and the holdout guard. The guard still wins. Row dicts are not rewritten. The receipt logs move and drop counts plus the file sha256, not row text or ids.

For a fair comparison, pass **both** models' force/hard files to `eval_broad.py` for both runs, so candidate and prior are scored on the same clean rows.

## archive/

The exact scripts used for morph78 (2026-09-23/24), copied from Spark for provenance. They hard-code `/home/morpheus` paths, and `morph78_fresh_acquire_label_hold.py` calls the Urban Dictionary API. Do not run them for new work; use the canonical versions above.
