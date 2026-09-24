# Publish-readiness results — agent-executable steps (2026-09-24)

Executes the no-decision items of `PUBLISH-READINESS-PLAN.md`. Nothing was trained, promoted, uploaded, or settled. `BEST`, `name_gate`, and the SoT are unchanged. The test split was **not** scored. Evidence: `receipts/publish-readiness-20260924/`.

**Bottom line:** still **do not publish**. The code is now canonical and reproducible, but the corrected gate does not support morph78 over morph65. Data rights are worse than the audit estimated: 709 Wiktionary-sourced rows, not 14. The shipped vocabulary also needs scrubbing.

## Status by step

| Step | Result |
|---|---|
| **1a** canonical chain | Done. Gate/surfaces `scripts/shadow/hyperlexical/soft_ceiling.py`; settle `val_settle.py`; GPU runners `scripts/spark/soft_ceiling/`; as-used Spark scripts in `archive/`. CI tests without torch. |
| **1b** equivalence | **PASS.** `main` + this branch + the recorded recipe (`morph78-train-env.json`) reproduces every morph78 receipt count, and export content matches the training run's own export (`equiv-main-legacy.json`). Control: the Spark checkout also passes (`equiv-spark-checkout.json`). Without the recipe switch, `main` differs (+298 classify, +1 unbind rows; `equiv-main-route-rows.json`). |
| **1b** bugs found + fixed | (1) `main` routes `classify+unbind` rows to both heads; morph75–78 did not. New explicit switch `HYPERLEX_TASK_ROUTING=legacy_split` (default unchanged). (2) `data_sha256` was **nondeterministic**: ai-native typology built from a `set`, so row order varied with `PYTHONHASHSEED` (723 rows). Now order-stable; the equivalence check compares typology-normalized content. |
| **1c** provenance | Done. Train receipts record `code_commit` (read from `.git`, worktree-aware), `code_tree_sha256` (catches uncommitted edits), and the full `HYPERLEX_*` env. |
| **2a/2b** gate fix | Done. `clean_surface` drops rows in the candidate's force/hard files or train text; `decide` fails closed with `REJECT_UNKNOWN_CONTAMINATION` / `REJECT_CONTAMINATED`. `finish.py` moves `BEST` only with `--apply-best`. |
| **2c** hard slices | OOV-filler slice defined. **On val it is empty (0 rows)**: every clean-val filler also appears in train, so val cannot measure generalization to unseen words. Test has 12 OOV-filler rows. |
| **2d** corrected decide | **`REJECT_VS_BROAD_BASELINE`.** Shared clean surface (both models' force/hard excluded): n=58, morph78 **1.0** = morph65 **1.0** (`verdict-2d-clean.json`). The contaminated surface (198/256 overlap) was what showed 0.9883 vs 0.8867. |
| **3a/3b** holdout manifest | Frozen, **not scored** (`holdout-manifest.json`, status `FROZEN_NOT_SCORED`). Test was also contaminated: 17 unbind + 15 classify test rows were in force/hard files (excluded). Clean test: unbind 356 (OOV-filler 12), classify 493, of which **418 have INFERRED labels** and 75 OBSERVED; lineage `none` 293. Pin weight hashes recorded. |
| **4a** data facts | SoT 4,297 rows (all `task=classify` in store; unbind rows come from harvest sidecars). **709 rows sourced from Wiktionary pages** (CC BY-SA 4.0); **692 are mislabeled `operator-local`**; 581 are in train. Crawl4AI harvest 525 rows (mostly en.wiktionary.org); Urban Dictionary API used by the morph78 acquire script; operator "blanket-yes" settles 377+255. Full `DATA-STATEMENT.md` still needs D4/D5. |
| **4b** vocab scan | The 1,972-string `filler_vocab` in the weights config contains 2 social-media handles and a `t.co` short link (redacted in the receipt), wiki-markup debris (a Markdown image link to Wikipedia, `(“dagger”).`), and 17 non-ASCII scraps from wiki chrome (Polish category words, Cyrillic/Amharic transliterations). No emails or phone numbers. (`vocab-scan.json`) |
| **5a** calibration (val only) | morph78: temperature **5.1**; ECE **0.164 → 0.068**; NLL 1.94 → 0.72; clean-val lineage accuracy **0.776** (OBSERVED-only 0.672). Abstain at max-prob < **0.597** keeps 70% coverage at 90.4% selective accuracy. morph65: same accuracy 0.776, T=5.0. `infer --calibration` applies it. |
| **6a** Hub loader | `hf-package/modeling_hyperlexical.py` (`trust_remote_code`): builds ModernBERT-base, overlays the checkpoint, fails on head mismatch. An offline Hub-shaped folder loaded via `AutoModel` matches `infer --model-dir` on 5/5 samples (`loader-check.json`). The scratch folder with its weight copy was deleted afterwards; nothing was uploaded. |

## Operator decisions (updated evidence)

| ID | Decision | Evidence now |
|---|---|---|
| D1 | Move Spark checkout to clean `main` | Safe: `main` + recipe switch reproduces morph78 data prep exactly |
| D2 | Reproduction train | Optional; data-prep equivalence proven, weight-level reproduction still NOT_COMPUTABLE |
| D3 | BEST after corrected gate | Gate says REJECT: morph78 = morph65 on clean val (1.0, n=58), equal lineage accuracy (0.776). A6 names `seed-morph78` |
| D4 | Weights licence + owner | Unchanged |
| D5 | Wiktionary rows | **709 rows, not 14**; 692 mislabeled; 581 in train. Dropping them requires a retrain (then redo 2d/5a/3) |
| D6 | A1 reading | Unchanged (trunk 149.0M; total 150.55M) |
| D7 | Spend test split | Manifest frozen; ready when authorized |
| **D8 (new)** | Scrub the shipped filler vocab | Handles, a URL, and wiki debris ship inside `config.json`. Scrubbing needs a head remap or a retrain |

## Code changed in this step

`scripts/shadow/hyperlexical/{soft_ceiling,val_settle,provenance}.py` (new) · `loop.py` (provenance in receipt; `HYPERLEX_TASK_ROUTING`) · `export.py` (order-stable typology) · `infer.py` / `infer_model.py` (`--calibration`) · `scripts/spark/soft_ceiling/*` (new) · `hf-package/modeling_hyperlexical.py` (new) · tests `tests/shadow/test_hyperlexical_{soft_ceiling,val_settle,provenance,export_determinism}.py` + additions.

## Operator decisions taken (2026-09-24, `go D1 + relabel + filter + A7`)

| ID | Decision | Record |
|---|---|---|
| D1 | Spark checkout moved to clean `main`; prior tree saved | `receipts/d1-relabel-filter-a7-20260924/` |
| D5(a) | Wiktionary rows relabelled in SoT + harvest sidecar (`license_relabel.py`) | same |
| D8 | `HYPERLEX_FILLER_FILTER=strict` (default): drops unbind rows with non-publishable fillers; vocab guard fails closed. On the morph78 vocab it rejects 115 of 1,971 strings | `filler_filter.py` |
| D6 | Amendment **A7**: A1 counts trunk params | `amendments.md` |

Still open: D2 (skip recommended), D3, D4, D5(b) release-set exclusion, D7.

**Clean retrain constraints (for the future authorize sentence):** cold start from the base trunk (no `HYPERLEX_INIT_FROM`: morph65/78 weights were trained with Wiktionary rows); exclude `source_license=CC-BY-SA-4.0` rows from the release training set; `HYPERLEX_FILLER_FILTER=strict`; keep the rest of the morph78 recipe as the single knob; refreeze the holdout manifest on the cleaned data before training.
