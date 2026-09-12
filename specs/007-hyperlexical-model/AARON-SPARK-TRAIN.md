# Aaron — Spark train handoff (007)

**Naming:** this handoff trains the **Hyperlexical** path. Harvest / live-store ingest is **ne0l0gist**. Repo **Hyperlex** is the transitional shell. Do not treat this smoke as Hyperlexical-gated-true.

Owner of this run: Aaron on the DGX Spark.  
Owner of the spec: Danny.  
Use current **`main`**. Do not use the old `007-hyperlexical-model` branch.

This is a **seed smoke** for harness wiring, not a Hyperlexical card. E2 has not passed. Name-gate is false. Do not upload to Hugging Face. Do not say the model is Hyperlexical.

**Train data:** T1 / E2 work uses the **local SoT** (`~/.hyperlex/hyperlexical/ingest_candidates.jsonl`). Export it with `PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live`. Train the same rows with an explicit opt-in — default remains the tracked/seed export (smoke-safe):

```bash
export HYPERLEX_INCLUDE_LIVE=1
# or: python3 -m hyperlexical.train --offline --run --include-live
# optional: HYPERLEX_LIVE_STORE=/path/to/ingest_candidates.jsonl
```

If the flag/env is set and the live store is missing, train exits non-zero. Do not train the named path from tracked `exports/civilian.v0.1.jsonl` alone — that file is a seed/snapshot.

The harvest includes the 4333-row dump when `data/hyperlex_4333_dump.jsonl` is present (dump fields only). Shadow stays import-isolated — no `from hyperlex` enrichment. Recent live exports have met the ~2500 classify bar.

Layout (locked): `specs/007-hyperlexical-model/weights.md`

- Freeze encoder except last **2** layers
- `classify`: Linear(768, 9) on token 0
- `role_head` + `filler_head`: Linear(768, vocab) on last-layer token states
- No refusal / Brier / chat tensors

## 0. What you are doing

Fine-tune `answerdotai/ModernBERT-base` (~149M) with the heads above.
Box: NVIDIA DGX Spark, GB10, 128 GB unified, aarch64, `sm_121`.

## 1. Preflight

```bash
cd /path/to/Hyperlex
git fetch origin && git checkout main && git pull --ff-only origin main

uname -m          # expect aarch64
python3 -V        # 3.10+

PYTHONPATH=scripts/shadow python3 -m hyperlexical.preflight
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live
# harvest_4333_dump picks up dump fields if data/hyperlex_4333_dump.jsonl is present.
# omit --include-live only for harness wiring against the tracked seed
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --out /tmp/hlx-e2-before.json
# expect exit 3 (no trained heads yet → stub path)
```

If `eval_unbind` exits 0 on the stub, stop and ping Danny.

## 2. Local trunk (once)

```bash
mkdir -p ~/.hyperlex/models/trunks
export HYPERLEX_TRUNK_DIR="$HOME/.hyperlex/models/trunks/ModernBERT-base"
ls "$HYPERLEX_TRUNK_DIR/config.json"
```

`local_files_only=True`. No instruct/chat. No MiniLM trunk. No ModernBERT-large card.

## 3. Env

```bash
export HYPERLEX_ALLOW_TRAIN=1
export HYPERLEX_TRUNK_DIR="$HOME/.hyperlex/models/trunks/ModernBERT-base"
export HYPERLEX_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export HYPERLEX_TRAIN_OUT="$HOME/.hyperlex/models/hyperlex-encoder-modernbert-base-seed"
export HYPERLEX_TRAIN_EPOCHS=2
export HYPERLEX_TRAIN_BATCH=8
export HYPERLEX_TRAIN_LR=2e-5
# optional recipe bump (default 2, clamp 1..min(encoder layers, 8)):
# export HYPERLEX_LAST_TRAINABLE=4
# optional unbind rebalance (defaults 1.0 / 1 = current schedule; no extra epoch).
# Flat UNBIND_LOSS_WEIGHT=2 plateaued civilian val — prefer the data-shape gates:
# export HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=2
# export HYPERLEX_UNBIND_INFERRED_CAP=200
# Morph4 hard INFERRED_CAP=1000 rejected (0.229; morph_negs 305→187) — do not default a cap. Hard low caps starve morph-negs.
# Soft INFERRED unbind sample weight (default 1.0 = identity). Try 0.4–0.5
# on Spark. Scales CE + morph-margin for class != OBSERVED. Does not drop
# rows. Morph5 map expand (#55) was 0.346 — hold map churn.
# export HYPERLEX_UNBIND_INFERRED_WEIGHT=0.5
# export HYPERLEX_UNBIND_MORPH_MARGIN=0.5
# optional scheme-split unbind curriculum (default 0 = identity / full mix).
# Morph1 OBSERVED val dump (seed-morph1 BEST, not new gold): unbind_exact 0.321
# (115/358). positional 185 / 135 fail; type_slot 173 / 108 fail.
# positional_head_filler_miss dominant → spend early epochs on positional,
# then type_slot, then joint. Keep morph hard-negs. Classify path unchanged.
# export HYPERLEX_UNBIND_CURRICULUM=1
# 2-epoch smoke still hits both schemes at the 1/1 defaults. Longer card:
# export HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS=2
# export HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS=1
# remainder of HYPERLEX_TRAIN_EPOCHS is joint.
# INFERRED cap stays 0 (off) — uncomment HYPERLEX_UNBIND_INFERRED_CAP above
# only if you want to drop INFERRED train rows. Morph1: many INFERRED
# type_slot rows are proper-noun noise. Morph4 CAP=1000 lost; keep default
# off. Prefer HYPERLEX_UNBIND_INFERRED_WEIGHT=0.4–0.5 instead of a hard cap
# so sibling fillers stay in the train pool. Opt in; do not invent OBSERVED gold.
# optional hard-neg / CE distractor denylist (empty default; no invented atoms).
# Morph1 status-vocab bleed (bum/bolt/burn/mid) is operator-opt-in:
# export HYPERLEX_UNBIND_FILLER_DENYLIST='{"brainrot-aura":["bum","bolt","burn","mid"],"gaming-meta":["bum","bolt","burn","mid"]}'
# Targeted extra upsample of already-OBSERVED hard train phrases (default 1 = no extra).
# Operator JSONL lives on Spark — do not commit it:
#   /home/morpheus/hlx/hard_atoms_train.jsonl  (59 rows, text field)
# After morph3 plateau (val unbind≈0.358; SETTLE×5 left n_unbind_observed=885),
# try HARD_UPSAMPLE=3–4. Copies only rows already class==OBSERVED in the
# train unbind pool. Unmatched ignored. INFERRED is never promoted.
# Missing/invalid path fails closed.
# export HYPERLEX_UNBIND_HARD_ATOMS_PATH=/home/morpheus/hlx/hard_atoms_train.jsonl
# export HYPERLEX_UNBIND_HARD_UPSAMPLE=3
# optional: per-slot filler CE as the primary unbind train signal.
# Default OFF (mixed mean of filler CE + role CE + morph-margin). Prior
# morphs stay unchanged when unset. Civilian unbind_exact stays the
# ladder metric; unbind_token_f1 / unbind_slot_f1 still emit.
# export HYPERLEX_UNBIND_PRIMARY=slot_ce
# or: export HYPERLEX_UNBIND_SLOT_CE=1
# When armed, mean per-position filler CE is primary. Existing list /
# margin leftovers are additive aux at fixed λ=0.25 (receipt field
# unbind_slot_ce_aux_lambda). Not a search. Receipt also shows
# unbind_slot_ce_armed and unbind_primary.
# Next train sentence (live SoT). Omit for seed smoke. Fail-closed if the store is missing.
# export HYPERLEX_INCLUDE_LIVE=1
```

## 4. Train smoke

```bash
PYTHONPATH=scripts/shadow python3 -m hyperlexical.train --offline --run
# live SoT: add --include-live (or HYPERLEX_INCLUDE_LIVE=1). Default is seed export.
```

Writes outside git: `heads.pt`, `layout.json`, `train-receipt.json`, `config-train.json`.
Do not commit them.

## 5. After

```bash
# Torch-free digest/stub (CI). Loads head bytes if present; trunk_loaded stays false.
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --out /tmp/hlx-e2-after.json
```

Real E2 on Spark (trained unbind_exact vs the Spec 004 probe). Fail-closed if torch, trunk, or weights are missing. Does not flip `name_gate`. `brier` stays null.

```bash
export HYPERLEX_E2_TRUNK_FORWARD=1
export HYPERLEX_TRUNK_DIR=$HOME/.hyperlex/models/trunks/ModernBERT-base
PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --model-dir $HYPERLEX_TRAIN_OUT --out /tmp/hlx-e2-after.json
```

`--model-dir` may be omitted when `HYPERLEX_TRAIN_OUT` is set, or when the default seed-live / seed out dir exists (`~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-live` then `...-seed`). Same as `--trunk-forward` on the CLI.

Civilian `unbind_exact` requires the full filler list to match, so partial slot hits do not move the number. That number stays the operator ladder even when `HYPERLEX_UNBIND_PRIMARY=slot_ce` (or `HYPERLEX_UNBIND_SLOT_CE=1`) makes per-slot filler CE the train signal. Train val / receipt `val` now also emit `unbind_token_f1` (micro bag-of-filler F1) and `unbind_slot_f1` (per-position exact on positional / type_slot roles), plus optional token precision/recall. Operator ladder on exact is **0.45 / 0.55 / 0.65**; watch `unbind_token_f1` so progress is not invisible. seed-morph14 BEST is observed (`unbind_exact`≈0.3857, slot/token F1≈0.659, classify≈0.438, E2 PASS) — not new SoT gold. Stub/digest `eval_unbind` leaves the F1 fields null (004 probe swap has no civilian filler lists); trunk-forward fills them when those lists exist. Do not flip `name_gate`.

Re-train after this encoder-persist fix (old `…-seed-live` lacks `encoder.*` tensors); then trunk-forward E2.

Send Danny: preflight JSON, MANIFEST sha, e2 before/after, train-receipt.json, layout.json, torch/`sm_121` note. Include any high-signal oversampling notes if used (see 4333/Moltbook sections).

## 6. Hard no

No Hub upload. No `hyperlex-structure-149m`. No chat template. No refusal head. No Brier. No `semantic`. No 7B. No Orin as this box. No 006 labels. No wrap rows. No weight binaries in git. No CPU-only named encoder if `sm_121` fails — stop and return the error. Do not flip `name_gate`. Do not reshuffle `lexical_split` when settle adds rows. BEST stays operator-side (`seed-morph3`). ne0l0gist harvest is unchanged by the unbind upsample/morph/curriculum/INFERRED-weight/hard-atom/slot-CE-primary recipe (loop multiplicity + epoch phase selection + sample weight + loss composition only). Do not commit the operator hard-atoms JSONL.

## High-signal subsets (Moltbook + 4333, not the global SoT)

Moltbook and the 4333 dump (see next section) are first-class **ai-native** sources. They are **subsets**, not the full civilian T1 SoT. Use `--include-live` for the authoritative data; optionally oversample the high-signal files below for memory/provenance signals.

- High-signal file: `exports/moltbook_high_signal.jsonl` (44 rows). Optional oversample for memory/provenance typology.
- Historical tracked-export Moltbook counts (~314–360 ai-native inside the 883-row seed) are **not** current global SoT status.
- Train from local SoT / `--include-live`. Optionally weight rows with moltbook provenance or high memory+provenance efficiency.
- Refresh: `python scripts/curate_moltbook_seeds.py --high-signal`
- Mapping and history: `dataset-harvest.md`

## 4333-row Hyperlex + Vernacular dump (2026-09-11)

Another first-class **ai-native** source (Hyperlex ledger + Vernacular/GrokBot terms from Notion export). Significant volume of memory, provenance, vernacular, and compression signals.

- Source: Notion page attachments (processed 4333 rows NDJSON + CSVs).
- Pipeline: `harvest_4333_dump` (wired in export) copies dump fields only. No `from hyperlex` / `detect_memetic_patterns` import — shadow stays isolated.
- Prepared for training (in `exports/training/`):
  - `training_4333_dump.jsonl` (5019 rows)
  - `training_high_signal.jsonl` (1501 rows, 73%+ ai-native from this dump, avg eff 0.278)
  - `training_ai_native.jsonl`
- High-signal oversampling recommended for memory/provenance typology (parallel to Moltbook).
- To include: Ensure `data/hyperlex_4333_dump.jsonl` is present when running export (or it was already merged into your live ingest).
- Full scoreboard + integration notes: `specs/007-hyperlexical-model/exports/TRAINING_READINESS.md`
- Mapping/history: `dataset-harvest.md` (section "4333-row Hyperlex dump integration")

Train from the live SoT via `--include-live`. Use the high-signal files above for optional weighting/oversampling of strong memory + provenance signals.

## Including the 4333 dump (if not already in live ingest)

If the 4333 data is not yet in your ~/.hyperlex/hyperlexical/ingest_candidates.jsonl:

```bash
# Copy the processed dump (provided separately or from exports/training/training_4333_dump.jsonl)
cp /path/to/training_4333_dump.jsonl data/hyperlex_4333_dump.jsonl

# Then run export (it will pick it up via harvest_4333_dump)
PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live
```

The dump is included on export when the file is present (fields as stored; no inline memetic enrichment).

## Recommendations for this T1 run (4333 + high-signal)

- **Primary data**: Always use `--include-live` against the current operator SoT. The tracked `civilian.v0.1.jsonl` is only a seed snapshot.
- **4333 inclusion**: Copy `training_4333_dump.jsonl` (from exports/training/ or provided) to `data/hyperlex_4333_dump.jsonl` before export if not already merged into live ingest. Harvest copies dump fields only.
- **Oversampling**: Strongly recommended for memory/provenance signals. Use `exports/training/training_high_signal.jsonl` (1501 rows, 73%+ from 4333, avg eff 0.278). Prioritize rows with:
  - `memetic_efficiency` >= 0.3
  - `stage` == "hyperstition_ish" or strong "memory"/"provenance" in typology
  - Explicit 4333 provenance
- **Preflight verification**:
  ```bash
  PYTHONPATH=scripts/shadow python3 -m hyperlexical.export --include-live
  # Confirm 4333 rows appear with efficiency/tiers in output or MANIFEST
  PYTHONPATH=scripts/shadow python3 -m hyperlexical.eval_unbind --out /tmp/hlx-e2-before.json
  ```
- **Post-train**: Re-run eval_unbind. Check train-receipt for 4333 contribution. Send high-signal usage notes.
- **Artifacts to reference**:
  - `exports/training/training_high_signal.jsonl`
  - `exports/training/training_4333_dump.jsonl`
  - `exports/training/training_ai_native.jsonl`
  - `exports/TRAINING_READINESS.md` (full scoreboard)
  - `dataset-harvest.md` (integration history)
- Refresh high-signal locally if needed: `python scripts/curate_moltbook_seeds.py --high-signal` (extend for 4333 if new data).
