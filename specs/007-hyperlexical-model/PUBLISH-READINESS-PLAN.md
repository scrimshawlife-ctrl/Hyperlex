# Publish-readiness plan — steps 1–6 (2026-09-24)

Follows `PUBLISH-AUDIT-20260924.md`. **Results of the agent-executable items:** `specs/007-hyperlexical-model/PUBLISH-READINESS-RESULTS-20260924.md`. Goal: make `seed-morph78` (or whichever pin survives step 2) publishable to a private/gated Hub repo (audit step 7). This plan starts no climb and uploads nothing. Items marked **D#** need an operator sentence.

## Dependency order

```
1 canonicalize code ──► 2 fix gate eval ──► 5a fit calibration (val) ──► 3 spend test split ──► 6 package + card
4 data + licence (starts now, runs in parallel; if rows are dropped → retrain → redo 2, 5a, 3)
5b A1 reading (any time)
```

Calibration must be fitted on val **before** the test split is spent, so its effect is measured on test, not tuned to it.

---

## 1 — Canonicalize training code

**Finding refined:** Spark's working tree vs current `main` differs only in `loop.py` (Spark filters splits directly; `main` routes through `route_rows` and records `task_accounting`). `export.py` / `unbind_recipe.py` match `main`. `scripts/spark/run_morph_train.sh` and `guard.py` match the repo. What is truly off-git is the soft_ceiling chain in `~/hlx` (~1.9k lines): `gate_soft_ceiling_decide.py` (+ test), `finish_soft_ceiling.py`, `eval_broad_observed.py`, `run_broad_eval.sh`, the val-settle launcher, the acquire/label-hold launcher, and the fair-eval template. The other ~140 files are per-morph generated copies.

| # | Work | Exit |
|---|---|---|
| 1a | Import the soft_ceiling chain into `scripts/spark/soft_ceiling/`, replacing hard-coded `/home/morpheus/...` paths and morph numbers with args/env. One parameterized `val_settle.py` replaces the per-morph launcher copies. Move `test_gate_soft_ceiling_decide.py` into `tests/shadow/`. | Chain runs from the repo; tests green in CI (no torch) |
| 1b | **Equivalence dry run** (no GPU): on Spark, run export + `prepare_unbind_splits` + classify routing with the morph78 force/hard files using `main`, and compare with the morph78 receipt (`n_train_classify` 4062, `n_train_unbind` 15536, `n_unbind_force_train` 193, `n_unbind_val_after_force_train` 164, `data_sha256`). | Receipt: counts match or the exact diff is listed |
| 1c | Train receipts record `code_commit`, `code_dirty`, and the full `HYPERLEX_*` env snapshot. | New unit test; next receipt carries them |
| 1d | **D1:** move Spark `~/Hyperlex` to clean `main`, saving the current tree to a `spark/morph78-tree` branch first. | Spark clean; no off-git training code |
| 1e | **D2 (optional, GPU):** reproduction train `seed-morph78-repro` from `main` with the recorded recipe; compare val metrics with the pin. Not a climb, and never promoted. | Repro receipt within tolerance, or the divergence documented |

## 2 — Fix the gate eval

| # | Work | Exit |
|---|---|---|
| 2a | `eval_broad_observed` (now in the repo): exclude val rows whose `(text, role_scheme)` is in the candidate's force-train or hard-atom files, and any text also in train. Report `n_excluded` and the contaminated score separately. | Unit test with a fixture overlap |
| 2b | `gate_soft_ceiling_decide`: fail closed (`REJECT_CONTAMINATED`) if the candidate's eval surface overlaps its own training files. | Unit test |
| 2c | Add a harder slice so "clean" isn't a copy task: rows whose gold fillers are **absent from the train filler vocab**, plus the dual-scheme **structure-holdout** probe (2026-09-14 recipe). | Slice definitions committed before any scoring |
| 2d | Re-run the decide for morph78 vs morph65 on the corrected surface. Leak-free val already ties at 1.0 (n=63), so the strict-greater rule would **REJECT** morph78. | Receipt with the corrected verdict |
| 2e | **D3:** BEST after the corrected verdict — keep morph78, revert to morph65, or declare a tie and pick by a pre-stated tiebreak. A6 `name_gate` is scoped to `seed-morph78`; reverting BEST needs a matching sentence on the name. | Operator sentence recorded |

## 3 — Spend the test split once

| # | Work | Exit |
|---|---|---|
| 3a | **Pre-register** a frozen eval manifest before running: pin SHAs (safetensors hash), code commit, test-row ID hash, metrics (unbind_exact overall / by scheme / OOV-filler slice; classify accuracy + macro-F1 + ECE; E1 on the fixture), baselines (stub, Spec 004 probe, morph65). Commit it. | Manifest merged before any number exists |
| 3b | Check test rows against force/hard files and train texts; any overlap is excluded and reported. | Overlap count = 0 after exclusion |
| 3c | **D7:** authorize spending the split. Run once for each pre-registered model. | Test receipt; E1 becomes computable |
| 3d | After this, test is burned for selection. Any future climb needs a new holdout, drawn and hashed before training. | Rule added to `engineering.md` |

## 4 — Data and licence (owner-gated per `AGENTS.md`)

| # | Work | Exit |
|---|---|---|
| 4a | Data statement: SoT 4,297 rows by source/provenance/licence (operator-local 3,580 · operator-attested 647 · CC BY-SA 14 · crawl 7), harvest domains, dates, settle process, known gaps. | `DATA-STATEMENT.md` |
| 4b | PII / harm scan of what ships in weights metadata: `layout.json` role/filler vocab (~1,972 strings) and `config.json`. | Scan receipt; flagged strings removed from any published vocab |
| 4c | **D5:** CC BY-SA rows. Recommended: drop them from any public-model training set (avoids share-alike ambiguity), which means a retrain → redo 2 / 5a / 3. Alternative: keep them, with attribution and a legal reading. | Sentence recorded |
| 4d | **D4:** weights licence and owner. Options: Zero State Proprietary + gated access (matches the org repo), or permissive apache-2.0 (matches the trunk). Personal repo MIT covers code only. | Licence line fixed on card + `LICENSE_POLICY` note |

## 5 — Calibration and A1

| # | Work | Exit |
|---|---|---|
| 5a | Fit temperature scaling for the classify head on clean val; add an abstain threshold for lineage; ECE before/after on val. Packet `lineage_confidence` uses the calibrated value. | Calibration receipt; test ECE measured in 3c |
| 5b | **D6:** A1 reading — count trunk only (149,014,272 ✓) or total (150,546,889 ✗). If total: prune the filler vocab or record amendment A7. Recommended: A7 "ceiling counts trunk parameters", which matches the name `149m`. | Amendment or pruning plan |

## 6 — Package and card

| # | Work | Exit |
|---|---|---|
| 6a | Hub-loadable layout: `modeling_hyperlexical.py` (`trust_remote_code`) exposing config + model + heads, plus a local loader test that loads from a Hub-shaped folder with no network. | Loader test green; `infer --model-dir` parity on 5 inputs |
| 6b | Card rewrite from receipts only: test table (3c), leak-free val, calibration (5a), data statement (4a), licence (4d), dual-use row 9 text, limitations including contamination history, E3 status. | Card reviewed against `PUBLISH-AUDIT` checklist |
| 6c | Upload dry run: the exact file list and hashes that would go to a **private/gated** repo. No upload. | Manifest ready for the step-7 sentence |

---

## Operator decisions

| ID | Decision | Blocks |
|---|---|---|
| D1 | Move Spark checkout to clean `main` | 1d |
| D2 | Reproduction train (GPU) | 1e (optional) |
| D3 | BEST after corrected gate | 2e, card identity |
| D4 | Weights licence + owner | 4d, 6b |
| D5 | CC BY-SA rows | 4c (may force retrain) |
| D6 | A1 reading | 5b |
| D7 | Spend test split | 3c |

Agent-executable now, without new sentences: 1a, 1b, 1c, 2a, 2b, 2c, 3a, 3b, 4a, 4b, 5a (val only), 6a.
