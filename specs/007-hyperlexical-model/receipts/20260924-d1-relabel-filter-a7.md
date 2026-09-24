# D1 + D5(a) relabel + D8 filter + A7 — executed (2026-09-24)

**Operator:** Danny `go D1 + relabel + filter + A7`. Code: PR #110 (`8de7cb1`). Evidence: `d1-relabel-filter-a7-20260924/`.

## D1 — Spark checkout on clean `main`

- Saved first: local commit `d0efdb3` on branch `spark/morph78-tree` (Spark has no push credentials, so it stays local), plus a tarball + `uncommitted.diff` in `~/hlx-private/d1-spark-tree-20260924T213846Z/`. Prior HEAD: `head.txt`.
- `~/Hyperlex` is now `main` @ `8de7cb1`, clean tree.
- Post-move check: canonical code + `morph78-train-env.json` reproduces every morph78 receipt count, and content matches the training run's export (`equiv-post-d1.json`: `equivalent: true`).

## D5(a) — licence relabel (live SoT)

`python -m hyperlexical.license_relabel` from `main`. Backups: `*.bak-pre-license-relabel-20260924T214408Z`. SHA-256 before/after: `sot-sha-before.txt` / `sot-sha-after.txt`.

| | Rows |
|---|--:|
| SoT Wiktionary-sourced | 709 (692 `operator-local` → `CC BY-SA 4.0 (Wiktionary); operator-local labels`; 3 with label notes; 14 already CC) |
| Harvest sidecar unbind rows derived from them | 80 |

Invariants: row counts unchanged; only `license`, `source_license`, `source_url` changed; labels, classes, splits, texts untouched; rerun is a no-op.

Relabelling changes export content, so later data hashes differ from morph78's. That is expected: the morph78 reproduction check was run **before** the relabel.

## D8 — strict filler filter (live data, no GPU)

Under the morph78 recipe with `HYPERLEX_FILLER_FILTER=strict`: 177 train + 12 val unbind rows dropped; `filler_vocab` 1,779 (was 1,972); `assert_publishable_vocab` passes.

## A7

Amendment A7 recorded in `amendments.md`: A1 counts trunk parameters.

## D5(b) preview (not applied)

Export after relabel: 9,150 rows, 628 CC BY-SA (unbind 434, classify 194). A release set without them keeps 8,522 rows. Applying the exclusion and retraining cold still needs an authorize sentence.

No training, promotion, or upload. `BEST`, `name_gate`, labels unchanged.
