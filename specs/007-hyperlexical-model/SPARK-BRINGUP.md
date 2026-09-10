# Spark bring-up 007 — operator procedure

Companion to `AARON-SPARK-TRAIN.md`. That file is the **spec** (Danny owns it). This file is **procedure**: how the box gets from bare to able to run the smoke. It changes no lock. C41–C52 stand as written.

Measured on `spark-bf46.local`, 2026-09-09.

## 0. Box state as found

| Fact | Value |
|------|-------|
| Host | `spark-bf46.local` (the `192.168.12.202` in operator ssh config is stale — no route) |
| SoC / cap | GB10, `sm_121` (12, 1) — matches `hardware.md` |
| OS | Ubuntu 24.04.4, aarch64, python 3.12.3 |
| Device memory | 130.7 GB total, **5.2 GB free** |
| Host RAM | 121 GB total, ~10 GB available |
| Disk | 3.3 T free on `/` |
| Resident | `qwen38-27b` (SGLang, DFLASH spec-decode, ctx 262144, :30000) + `spark-comfyui` (:8188) |
| Host train stack | **none** — no torch, no transformers, no venv, no `~/.hyperlex/`, no repo |

The Spark is not a clean box. It is a serving box with ~5 GB of headroom. Everything below is shaped by that.

## 1. Decision — do not evict Qwen

SGLang launched with no `--mem-fraction-static`, so it **preallocated** its KV pool at startup. Its footprint is fixed, not growing. The 5.2 GB free is stable for the duration of a run.

The smoke needs far less than that:

| Term | Value |
|------|-------|
| Trunk | ModernBERT-base, 149M |
| Trainable | last 2 of 22 layers + 3 heads ≈ 15–20M params |
| Optimizer | AdamW state on trainable only ≈ 160 MB |
| Shape | `MAX_LEN = 64`, batch 8 (`layout.py`) |
| Realistic peak | ~2–2.5 GB incl. CUDA context |

So: **Qwen stays up. ComfyUI stays up.** The job is not to free memory, it is to make the trainer structurally incapable of taking the server down. See §5.

## 2. Decision — do not build a host torch

The box already holds a torch proven on this silicon, inside the SGLang image:

```
torch 2.13.0+cu130 · transformers 5.12.1 · huggingface_hub 1.28.0 · capability (12, 1)
```

Installing a second aarch64 / CUDA-13 stack on the host is a multi-GB download to reproduce what is already pulled. Instead, run a **sibling container from the same image**, mounting the repo. Zero download, known-good `sm_121`.

`transformers 5.12.1` is a major ahead of what `loop.py` was written against. `AutoModel.from_pretrained` and `out.last_hidden_state` are stable across that boundary, but this is asserted, not proven — S3 proves it before S5 spends an epoch.

---

## S0 — reach the box

```bash
ssh spark 'uname -m && python3 -V'
```

**Done:** prints `aarch64` and `3.12.x`.

If it hangs, the stale IP is the cause. Fix operator-side:

```bash
sed -i '' 's/HostName 192.168.12.202/HostName spark-bf46.local/' ~/.ssh/config
```

## S1 — grab the repo

Personal is source of truth (`docs/remotes.md`). Clone that, nothing else:

```bash
ssh spark
git clone https://github.com/scrimshawlife-ctrl/Hyperlex.git ~/Hyperlex
cd ~/Hyperlex && git checkout main && git pull --ff-only origin main
```

**Done:** `~/Hyperlex/specs/007-hyperlexical-model/AARON-SPARK-TRAIN.md` exists.

Do **not** use the `007-hyperlexical-model` branch. Spec says main.

**Do not clone `Zero-State-LLC/Hyperlex` for this.** `docs/remotes.md` calls it a 404; as of 2026-09-09 21:xx PT it is **live and public**, so the wrong URL now clones successfully instead of failing loudly. It carries no `specs/007-*` and no `scripts/shadow/` — the training code is simply absent. A clone from there fails at `PYTHONPATH=scripts/shadow` with a confusing import error, not an obvious "wrong repo". Check before you run:

```bash
git -C ~/Hyperlex remote get-url origin   # must be scrimshawlife-ctrl
ls ~/Hyperlex/scripts/shadow/hyperlexical/loop.py
```

## S2 — keep the exporter out of git

`export_dataset` writes into `specs/007-hyperlexical-model/exports/`. That path is **not gitignored and not tracked** — the run will dirty `git status`, and the spec says do not commit artifacts. Close it before the first run:

```bash
cd ~/Hyperlex
printf 'specs/007-hyperlexical-model/exports/\n' >> .git/info/exclude
```

`.git/info/exclude` rather than `.gitignore` — local-only, no repo diff, no PR for Danny to review.

**Done:** `git status --short` is clean after S3.

## S3 — grab the trunk (the only real download)

The spec asserts a local trunk but never says how it arrives. It does not arrive on its own. One-time, online, ~600 MB:

```bash
mkdir -p ~/.hyperlex/models/trunks

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME="$HOME" \
  -v "$HOME/.hyperlex:$HOME/.hyperlex" \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  hf download answerdotai/ModernBERT-base \
    --local-dir "$HOME/.hyperlex/models/trunks/ModernBERT-base"
```

No `--gpus` on this one. It is a download, it touches no device memory, it cannot disturb Qwen.

**Done:**

```bash
ls ~/.hyperlex/models/trunks/ModernBERT-base/config.json
```

Then prove the stack loads it before spending an epoch:

```bash
docker run --rm --gpus all \
  --user "$(id -u):$(id -g)" -e HOME="$HOME" \
  -v "$HOME/.hyperlex:$HOME/.hyperlex" \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  python -c "
from transformers import AutoModel, AutoTokenizer
d='$HOME/.hyperlex/models/trunks/ModernBERT-base'
t=AutoTokenizer.from_pretrained(d, local_files_only=True)
m=AutoModel.from_pretrained(d, local_files_only=True)
print('hidden', m.config.hidden_size, 'layers', m.config.num_hidden_layers)
print('offsets', 'offset_mapping' in t('rizz', return_offsets_mapping=True))
"
```

**Done:** `hidden 768 layers 22` and `offsets True`.

If hidden ≠ 768 the loop raises by design. If `offset_mapping` is absent the C47 aligner is dead and unbind is meaningless — stop, ping Danny.

## S4 — memory guard

`set_per_process_memory_fraction` is a Python call, not an env var, and `loop.py` must not be edited. So the cap goes in a launcher that lives **outside** the repo:

```bash
mkdir -p ~/hlx
cat > ~/hlx/guard.py <<'PY'
import sys, runpy, torch
frac = float(sys.argv[1])
mod = sys.argv[2]
torch.cuda.set_per_process_memory_fraction(frac)
free, total = torch.cuda.mem_get_info()
print(f"[guard] cap={frac*total/1e9:.1f}GB free={free/1e9:.1f}GB total={total/1e9:.1f}GB", flush=True)
sys.argv = [mod] + sys.argv[3:]
runpy.run_module(mod, run_name="__main__")
PY
```

`0.03 × 130.7 GB ≈ 3.9 GB` — above the ~2.5 GB the smoke needs, ~1.3 GB below the 5.2 GB free. If the estimate is wrong, **the trainer OOMs and dies. The server does not.** That is the whole point of the cap.

**Done:** `~/hlx/guard.py` exists. It is deliberately not in the repo.

## S5 — preflight, then run

Preflight and export need no GPU:

```bash
cd ~/Hyperlex
docker run --rm \
  --user "$(id -u):$(id -g)" -e HOME="$HOME" \
  -v "$HOME/Hyperlex:$HOME/Hyperlex" -v "$HOME/.hyperlex:$HOME/.hyperlex" \
  -w "$HOME/Hyperlex" \
  -e PYTHONPATH=scripts/shadow \
  -e HYPERLEX_ALLOW_TRAIN=1 \
  -e HYPERLEX_TRUNK_DIR="$HOME/.hyperlex/models/trunks/ModernBERT-base" \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  python -m hyperlexical.preflight
```

**Done:** exit 0, `ready_to_train: true`, `machine: aarch64`, `name_gate: false`. Save the JSON — Danny wants it.

Then E2 before. Spec says **expect exit 3**:

```bash
# ... same flags ...
  python -m hyperlexical.eval_unbind --out "$HOME/.hyperlex/hlx-e2-before.json"
```

**Done:** exit 3. If it exits 0 on the stub, stop and ping Danny — that is the spec's tripwire.

Now the run. This is the only step that takes device memory:

```bash
cd ~/Hyperlex
docker run --rm --gpus all --name hlx-train \
  --user "$(id -u):$(id -g)" -e HOME="$HOME" \
  -v "$HOME/Hyperlex:$HOME/Hyperlex" \
  -v "$HOME/.hyperlex:$HOME/.hyperlex" \
  -v "$HOME/hlx:$HOME/hlx" \
  -w "$HOME/Hyperlex" \
  -e PYTHONPATH=scripts/shadow \
  -e HYPERLEX_ALLOW_TRAIN=1 \
  -e HYPERLEX_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e TOKENIZERS_PARALLELISM=false \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e HYPERLEX_TRUNK_DIR="$HOME/.hyperlex/models/trunks/ModernBERT-base" \
  -e HYPERLEX_TRAIN_OUT="$HOME/.hyperlex/models/hyperlex-encoder-modernbert-base-seed" \
  -e HYPERLEX_TRAIN_EPOCHS=2 \
  -e HYPERLEX_TRAIN_BATCH=8 \
  -e HYPERLEX_TRAIN_LR=2e-5 \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  python "$HOME/hlx/guard.py" 0.03 hyperlexical.train --offline --run
```

Data it will train on (verified against this commit, `data_sha256` starts `0d6a3e34`):

| Task | train | val |
|------|-------|-----|
| classify | 110 | 13 |
| unbind | 39 | **1** |

**Done:** receipt JSON on stdout with `cuda: true`, `device: cuda`, `name_gate: false`, `e2_pass: false`, `brier: null`.

`cuda: false` means the guard fell back to CPU. Spec §6: do not accept a CPU-only named encoder — stop and return the error.

## S6 — E2 after, and hand back

```bash
# ... same non-GPU flags as preflight ...
  python -m hyperlexical.eval_unbind --out "$HOME/.hyperlex/hlx-e2-after.json"
```

Pull the evidence to the operator box:

```bash
scp spark:'~/.hyperlex/hlx-e2-*.json' .
scp spark:'~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed/{train-receipt.json,layout.json}' .
```

Send Danny: preflight JSON, data sha256, e2 before/after, `train-receipt.json`, `layout.json`, and the torch/`sm_121` note (`2.13.0+cu130`, cap `(12,1)`, ran under a 3.9 GB cap alongside a live SGLang server).

---

## 3. What persists, what does not

Asked directly: **yes, everything the run loaded leaves memory when it exits.**

| Thing | After the run |
|-------|---------------|
| Trainer device memory (~2.5 GB) | Released. Process exit destroys the CUDA context; the allocator returns every byte. |
| Trainer host RSS | Released on exit. |
| The container | Gone — `--rm`. |
| SGLang / Qwen pool | **Never touched.** Preallocated before the run, still held after. Same for ComfyUI. |
| Trunk, ~600 MB | Stays on disk at `~/.hyperlex/models/trunks/`. Disk, not memory. Keep it — S3 is once, not per run. |
| `heads.pt`, receipts, `layout.json` | Stay on disk under `~/.hyperlex/models/…seed/`. Small. |
| Repo exports | Stay in the working tree, excluded from git by S2. |

Nothing to unload by hand. No `docker stop`, no restart. The box returns to exactly its current state, plus files on a 3.3 T disk.

Verify with the same call used to measure the baseline:

```bash
ssh spark 'docker run --rm --gpus all   --user \"$(id -u):$(id -g)\" -e HOME=\"$HOME\"   lmsysorg/sglang:dev-qwen38-27b-dflash2   python -c \"import torch;f,t=torch.cuda.mem_get_info();print(round(f/1e9,1),round(t/1e9,1))\"'
```

**Done:** free returns to ~5.2 / 130.7.

## 4. Hard no — inherited, unchanged

No Hub upload. No `hyperlex-structure-149m`. No chat template. No refusal head. No Brier. No `semantic`. No 7B. No Orin. No 006 labels. No wrap rows. No weight binaries in git. No CPU-only named encoder if `sm_121` fails — stop and return the error.

Added by this procedure:

- The resident Qwen3.8-27B is **not** a trunk (C16 holds it) and **not** a source of E2 gold (C20, Wu/Sun misalignment). It is a co-tenant on the box and nothing more. It does not enter 007 by being nearby.
- Do not run the trainer without the guard. An uncapped job on 5.2 GB of headroom can OOM a server Danny is using.

## 5. Open for Danny

1. **`unbind_exact` val n=1.** C48 requires per-epoch val unbind exact. The split yields a single val unbind row, so the metric is 0.0 or 1.0 — noise, not a measurement. The receipt will look like a metric and is not one. Either accept it as decorative for the seed or re-split before reading it.
2. **`transformers 5.12.1`.** S3 proves load; nothing proves the whole loop across the 4.x→5.x boundary until S5 runs.
3. **SGLang API key in plaintext** in `docker inspect` output — readable by anyone with box access. Unrelated to 007, worth rotating.
4. **`docs/remotes.md` premise is wrong, and `push-org.sh` is a force-push trap.** See below — this is the one that can lose work.

## 6. Remotes contract — measured 2026-09-09, after PR #25

`docs/remotes.md` states the org twin is "not created or not visible (API 404)". Measured:

| Fact | Value |
|------|-------|
| `Zero-State-LLC/Hyperlex` | **exists**, created 2026-08-07, last push 2026-09-05 |
| Visibility | **public** (the 404 was a private-repo 404 for an unauthorised token; it has since been flipped) |
| Common ancestor with personal | `3e66637` (PR #4) — shared history, genuinely diverged |
| Unique to **org** main | **21 commits** |
| Unique to **personal** main | **65 commits** |
| Org `specs/007-*`, `scripts/shadow/` | absent |
| Personal `LICENSE` | MIT |
| Org `LICENSE` | Zero State Proprietary v1.0 |

The doc's *conclusion* holds — personal is SoT, do not train from an org clone. Two things under it do not:

**1. `./scripts/push-org.sh` cannot succeed as written.** It runs a bare `git push org main`. Org main holds 21 commits personal does not, so the push is rejected non-fast-forward. That failure is correct and safe. The hazard is what it invites next: `--force` from that state discards all 21, which include the **P1 fail-closed security fix (#11)**, the **proprietary license adoption (#1)**, the CodeQL baseline, and the org SDLC pack. Several exist nowhere else. The script should refuse a non-fast-forward explicitly rather than let the operator reach for `--force`:

```bash
git push org main   # add nothing. if rejected, reconcile — never --force
```

**2. Licence divergence is live and public.** The same lineage is MIT on a public personal repo and Zero State Proprietary v1.0 on a public org repo. Whichever is intended, both are currently readable by anyone. That is a call for Danny and org admin, not for this runbook — flagged, not touched.

Nothing in this bring-up depends on the resolution. S1 pins the personal URL and verifies `scripts/shadow/` before any run.
