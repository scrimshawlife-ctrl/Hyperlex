# Hermes run order — 007 Spark seed smoke (bring-up + train)

*Operator note: hand this entire file to Hermes. It is self-contained — no other document is needed to execute it. Human-facing procedure detail is in `SPARK-BRINGUP.md`; the spec locks are in `AARON-SPARK-TRAIN.md`. This file changes neither.*

---

**You are Hermes.** This document is your complete run order for a **gated seed smoke** of Hyperlex Spec 007 on the DGX Spark. Everything required to execute is in it.

| | |
|---|---|
| **Your role** | Plan, delegate, adjudicate. You never run a command yourself. |
| **Executor** | **Forge**, your subagent, running on the **operator Mac** — *not* on the Spark. Every slice reaches the box over `ssh`. |
| **Start** | **A0 first, always.** Then the three bring-up chains, then B1–B5 in order. Every A slice is idempotent — re-running a passed slice is safe and is the normal way to resume after a halt. |
| **Finish** | When C1 has opened the PR, return *Output Hermes must return* and stop. There is no follow-on work; do not go looking for any. |
| **Escalation** | Danny owns the spec but you have **no channel to him**. Every stop, every anomaly, goes to the **human operator** who handed you this file. |

Filenames cited below (`SPARK-BRINGUP.md`, `AARON-SPARK-TRAIN.md`, `docs/remotes.md`, `amendments.md`) are provenance for humans. They live in the repo A1 clones. You do not need to read them and nothing here waits on them.

You do not improvise around a stop.

## What this run is

Fine-tune `answerdotai/ModernBERT-base` (~149M) with a classify head and two unbind heads, freezing all but the last 2 of 22 layers.

**This is a harness smoke, not a model delivery.** Read this twice:

- E2 is **expected to fail**. `name_gate` is false. `e2_pass` is false. `brier` is null.
- The word *Hyperlexical* does not attach to the output. The card is `hyperlex-encoder-modernbert-base-seed`.
- Nothing is uploaded anywhere.
- A run that ends with E2 failing and a receipt written is a **success**. A run where E2 passes is a **defect** — stop and report it.

Do not tune, re-split, re-seed, or extend epochs to improve a number. There is no number to improve in this unit.

## Box, as measured 2026-09-09

| Fact | Value |
|------|-------|
| Host | `spark-bf46.local`, Ubuntu 24.04.4, aarch64 |
| SoC | GB10, `sm_121`, capability (12, 1) |
| Device memory | 130.7 GB total, **~5.2 GB free** |
| Co-tenants | `qwen38-27b` (SGLang :30000) and `spark-comfyui` (:8188) — **both stay up** |
| Host train stack | none — no torch, no transformers, no venv |
| Image to reuse | `lmsysorg/sglang:dev-qwen38-27b-dflash2` — torch 2.13.0+cu130, transformers 5.12.1 |

Every slice runs in a throwaway container off that image. Nothing is installed on the host.

## Preconditions — verified 2026-09-09, do not re-derive

| Check | State |
|-------|-------|
| `morpheus` in `docker` group | yes — **never use `sudo`** |
| `lmsysorg/sglang:dev-qwen38-27b-dflash2` | already pulled locally — **never `docker pull`** |
| `~/.cache` | exists, `morpheus`-owned, mounted by every slice |
| github.com / huggingface.co | reachable (200) |
| Disk | 3.3 T free |

**Torch writes caches outside `$HOME/.cache`.** Triton defaults to `~/.triton`, which is *not* the mounted path, and the forward pass dies with `PermissionError: [Errno 13] Permission denied: '/home/morpheus/.triton'`. Every torch slice therefore sets `TRITON_CACHE_DIR`, `TORCHINDUCTOR_CACHE_DIR` and `XDG_CACHE_HOME` under the mounted `~/.cache`. Verified: without them B3 fails on its first forward pass; with them it completes. Do not drop these.

**No slice uses `--rm`.** Forge's safety detector blocks that flag, so every container is given a unique `--name` instead and is left behind on exit. This is deliberate. Do not add `--rm` back, and do not try to route around the detector by hiding the flag in a script — if `--rm` is wanted, that is an allowlist decision for the human operator to make in Forge's config, not something this run works around.

Stopped containers cost only disk metadata. The operator may clear them later; no slice does it.

Every container runs `--user "$(id -u):$(id -g)"` so artifacts are owned by `morpheus`, not root. A consequence: `$HOME` **inside** the container is a root-owned mount parent, so `$HOME/.cache` is not writable unless mounted. Every slice below mounts it. Removing that mount breaks `hf download` and torch's caches with a bare permission-denied — verified, not theoretical.

Forge runs on the Mac. The Spark is remote, so **every slice below is an `ssh` heredoc**:

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
… commands run on the Spark …
REMOTE
```

The quoted `<<'REMOTE'` delimiter is load-bearing: it stops the Mac expanding `$HOME` and `$(id -u)`, so they resolve on the Spark where they mean the right thing. `ssh` returns the remote exit code, so every exit-code check below still holds. Verified, including nested heredocs.

**Do not** run any slice's commands locally. A slice that reports a hostname other than `spark-bf46` has run on the wrong machine — stop and report.

## Slice graph

| Slice | Does | Needs | GPU |
|-------|------|-------|-----|
| **A0** | **reach the Spark; repair stale ssh config** | — | no |
| A1 | clone repo, verify it is the right one | A0 | no |
| A2 | exclude exports from git | A1 | no |
| A3 | check trunk (A3a) → fetch if needed (A3b) → verify (A3c) | A0 | no |
| A4 | prove the stack loads the trunk | A3 | yes |
| A5 | write the memory guard | A0 | no |
| B1 | preflight | A1 A2 A3 | no |
| B2 | E2 before | A1 | no |
| B3 | **train** — launch detached (B3a) then poll (B3b) | A1–A5, B1, B2 | **yes** |
| B4 | E2 after | B3 | no |
| B5 | collect evidence | B4 | no |
| C1 | open the draft PR (**on the Mac**) | B5 | no |

**A0 gates everything.** After it passes, three independent bring-up chains — `A1 → A2`, `A3 → A4`, and `A5` alone — may run concurrently. Everything in B is strictly ordered and every B slice needs all of A done.

## How to delegate

Forge is your subagent on the box. You plan and adjudicate; Forge executes.

1. **Pass slice text verbatim.** Do not summarise, re-word, or "clean up" a command. Mount paths, env vars and the `0.03` cap are load-bearing — a paraphrase that drops `-v "$HOME/.cache:$HOME/.cache"` fails with a bare permission-denied that looks like something else entirely.
2. **One slice per delegation.** Collect exit code and stdout before dispatching the next.
3. **Check the done-condition yourself.** Forge reports; you adjudicate. A slice is not done because Forge says it is — it is done because the stated condition is observably true.
4. **A stop halts the chain.** Do not re-dispatch, do not vary the command, do not route around it with a different slice. Return the error and wait for a human.
5. **Exit 255 is transport, not a slice result.** `ssh` returns 255 when the *connection* fails — the remote command may never have run at all, and nothing was decided. Re-dispatch the slice once. If it returns 255 twice, escalate to the human operator. This is the one retry the run permits, and it applies only to 255. A non-zero exit produced by the remote command is a real result: adjudicate it, never retry it.
6. **Never invent a slice.** If something is needed that is not in A1–B5, that is a spec gap. Return it to the human operator. Do not improvise on a box running someone else's live services.

---

## Slice A0 — reach the Spark

Runs **on the Mac**, not over ssh. This is the only local slice.

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 spark 'hostname' 2>&1 || true
```

If that printed `spark-bf46`, A0 is done. If it printed `No route to host`, the operator's ssh config holds a stale IP. Repair it once, idempotently:

```bash
cp ~/.ssh/config ~/.ssh/config.bak.$(date +%Y%m%d%H%M%S)
sed -i '' 's/^  HostName 192\.168\.12\.202$/  HostName spark-bf46.local/' ~/.ssh/config
ssh -o BatchMode=yes -o ConnectTimeout=8 spark 'hostname'
```

**Done:** `ssh spark 'hostname'` prints `spark-bf46`.

**Stop if:** it still fails after the repair. The box may be off or off-network. Return to the human operator — do not try other hostnames, other users, or a password prompt.

**Stop if:** `hostname` returns anything containing `Mac` or matching the machine Forge runs on. That means the command executed locally instead of over ssh, and every later slice would corrupt the wrong machine.


**A0b — harden the connection.** Every later slice opens an ssh session. Without multiplexing they are separate TCP connections against sshd's default `MaxStartups 10:30:100`, and a transient drop returns exit 255 with nothing run. Add keepalives and connection reuse — idempotent, safe to re-run:

```bash
CFG="$HOME/.ssh/config"
cp "$CFG" "$CFG.bak.$(date +%Y%m%d%H%M%S)"
if ! awk '/^Host spark$/{f=1;next} /^Host /{f=0} f&&/ControlMaster/{print "yes"}' "$CFG" | grep -q yes; then
  awk '
    /^Host spark$/ {
      print
      print "  ServerAliveInterval 15"
      print "  ServerAliveCountMax 4"
      print "  ConnectTimeout 15"
      print "  ConnectionAttempts 3"
      print "  ControlMaster auto"
      print "  ControlPath ~/.ssh/cm-%r@%h:%p"
      print "  ControlPersist 10m"
      next
    }
    { print }
  ' "$CFG" > "$CFG.new" && mv "$CFG.new" "$CFG"
  echo "hardening inserted"
else
  echo "hardening already present"
fi
grep -c ControlMaster "$CFG"
ssh spark 'hostname'
```

**Done:** `ControlMaster` appears exactly once and `ssh spark 'hostname'` prints `spark-bf46`. Measured effect: first connection ~0.55 s, subsequent ~0.02 s.

`ControlPath` must stay short — a unix socket path over 104 bytes fails with `ControlPath too long`. Do not relocate it to a long temp directory.


## Slice A1 — clone

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
if [ -d ~/Hyperlex/.git ]; then
  echo "checkout exists — updating in place"
  cd ~/Hyperlex && git fetch origin && git checkout main && git pull --ff-only origin main
else
  git clone https://github.com/scrimshawlife-ctrl/Hyperlex.git ~/Hyperlex
  cd ~/Hyperlex && git checkout main
fi
git remote get-url origin
git rev-parse --short HEAD
ls scripts/shadow/hyperlexical/loop.py
hostname
REMOTE
```

**Done:** remote contains `scrimshawlife-ctrl`, `loop.py` exists, and `hostname` prints `spark-bf46`.

Safe to re-run: it updates an existing checkout instead of failing on `git clone`.

**Stop if:** the remote is `Zero-State-LLC`. That repo is live and public but holds **no** `specs/007-*` and **no** `scripts/shadow/`. A clone from it succeeds and then fails later with a confusing import error. Personal is source of truth (`docs/remotes.md`).

Do not use the `007-hyperlexical-model` branch. Spec says `main`.

## Slice A2 — keep exports out of git

`export_dataset` writes into `specs/007-hyperlexical-model/exports/`, which is neither tracked nor ignored.

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
cd ~/Hyperlex
grep -qxF 'specs/007-hyperlexical-model/exports/' .git/info/exclude \
  || printf 'specs/007-hyperlexical-model/exports/\n' >> .git/info/exclude
grep -n 'exports' .git/info/exclude
REMOTE
```

`.git/info/exclude`, not `.gitignore` — local only, no diff for Danny to review.

**This slice is now largely vestigial and that is expected.** As of main `e3425ab`, ten files under `specs/007-hyperlexical-model/exports/` are **tracked** upstream. `.git/info/exclude` only suppresses *untracked* paths, so it cannot hide changes to those. B3 regenerates them via `write_export`, and they will show as modified. Keep the exclude for any genuinely new file the exporter emits; expect the tracked ones to go dirty regardless. See B5.

**Done:** the `exports/` line appears exactly once. Safe to re-run — the append is guarded.

## Slice A3 — fetch the trunk

The only network download in the run. **Verify first** — the trunk may already be complete from an earlier attempt, in which case the fetch is skipped entirely.

**A3a — state check.** Read-only. Runs no container, changes nothing:

```bash
ssh spark bash -s <<'REMOTE'
set -uo pipefail
T="$HOME/.hyperlex/models/trunks/ModernBERT-base"

# read-only orphan detection — this slice never stops or removes a container
ORPHAN=$(docker ps -a --format '{{.Names}} {{.Status}} {{.Command}}' | grep -i 'hf download' || true)
if [ -n "$ORPHAN" ]; then
  echo "ORPHAN_PRESENT:"; echo "$ORPHAN"
else
  echo "no orphan download containers"
fi

MISSING=0
for f in config.json model.safetensors tokenizer.json tokenizer_config.json special_tokens_map.json; do
  if [ -s "$T/$f" ]; then echo "  ok: $f"; else echo "  MISSING: $f"; MISSING=1; fi
done
INC=$(find "$T" -name '*.incomplete' 2>/dev/null | wc -l)
echo "incomplete_files=$INC"
if [ "$MISSING" = "0" ] && [ "$INC" = "0" ]; then
  echo "TRUNK_COMPLETE — skip A3b, go straight to A3c"
else
  echo "TRUNK_INCOMPLETE — run A3b"
fi
REMOTE
```

**Done:** prints either `TRUNK_COMPLETE` or `TRUNK_INCOMPLETE`, and `no orphan download containers`.

**Stop if:** `ORPHAN_PRESENT`. A container is still writing into the same directory and the two would fight over lock files. **You may not stop it** — container lifecycle is not yours, and Forge's safety policy blocks it correctly. Return to the human operator with the container name and ask them to clear it, then re-dispatch A3a.

**If `TRUNK_COMPLETE`:** skip A3b entirely and dispatch A3c. Do not re-download to be thorough — it is 600 MB for no gain.

**A3b — fetch.** Only when A3a reported `TRUNK_INCOMPLETE`.

`answerdotai/ModernBERT-base` holds 16 files: the weights, a ~598 MB `pytorch_model.bin` duplicate, and 8 ONNX exports. An unfiltered `hf download` pulls all of it — well over 2 GB — and will exceed your executor's command timeout. Fetch only the five files the run uses:

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
mkdir -p ~/.hyperlex/models/trunks
docker run --name "hlx-a3-$(date +%s)" \
  --user "$(id -u):$(id -g)" -e HOME="$HOME" \
  -v "$HOME/.hyperlex:$HOME/.hyperlex" \
  -v "$HOME/.cache:$HOME/.cache" \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  hf download answerdotai/ModernBERT-base \
    --local-dir "$HOME/.hyperlex/models/trunks/ModernBERT-base" \
    --include config.json \
    --include model.safetensors \
    --include tokenizer.json \
    --include tokenizer_config.json \
    --include special_tokens_map.json
REMOTE
```

`hf download` resumes rather than restarting, so a partial directory is safe to run this over.

**Each pattern needs its own `--include` flag.** Space-separating them (`--include a.json b.json`) is silently wrong: `hf` treats the extras as positional filenames, prints `Ignoring --include since filenames have been explicitly set`, downloads only the last one — and **still exits 0**. Verified on this box. That is why A3c is not optional: the exit code will not catch it.

The `--include` list is exhaustive. Do not add to it, and in particular do not fetch `onnx/` or `pytorch_model.bin`.

**A3c — verify. Never skip this**, whichever path you took:

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
cd ~/.hyperlex/models/trunks/ModernBERT-base
for f in config.json model.safetensors tokenizer.json tokenizer_config.json special_tokens_map.json; do
  [ -s "$f" ] || { echo "MISSING: $f"; exit 1; }
done
if find . -name '*.incomplete' | grep -q .; then echo "INCOMPLETE FILES PRESENT"; exit 1; fi
python3 -c "import json;json.load(open('config.json'));print('config.json parses')"
stat -c '%n %s bytes' model.safetensors
echo "A3_VERIFIED"
REMOTE
```

**Done:** prints `A3_VERIFIED`, and `model.safetensors` is 598,635,032 bytes.

**Stop if:** any file reports `MISSING`, or `.incomplete` files remain. Dispatch A3b once more — it resumes. If A3c fails twice, return to the human operator.

**Stop if:** the download resolves to any `*-instruct`, chat, MiniLM, or ModernBERT-**large** checkpoint. The trunk is frozen by A2 in `amendments.md` and may not be swapped.

## Slice A4 — prove the stack

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
docker run --gpus all --name "hlx-$$-$(date +%s)" \
  --user "$(id -u):$(id -g)" -e HOME="$HOME" \
  -v "$HOME/.hyperlex:$HOME/.hyperlex" \
  -v "$HOME/.cache:$HOME/.cache" \
  -e TRITON_CACHE_DIR="$HOME/.cache/triton" \
  -e XDG_CACHE_HOME="$HOME/.cache" \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  python -c "
from transformers import AutoModel, AutoTokenizer
d='$HOME/.hyperlex/models/trunks/ModernBERT-base'
t=AutoTokenizer.from_pretrained(d, local_files_only=True)
m=AutoModel.from_pretrained(d, local_files_only=True)
print('hidden', m.config.hidden_size, 'layers', m.config.num_hidden_layers)
print('offsets', 'offset_mapping' in t('rizz', return_offsets_mapping=True))
"
REMOTE
```

**Done:** prints `hidden 768 layers 22` and `offsets True`.

**Stop if:** hidden ≠ 768 (the loop raises by design), or `offsets` is False. Without `offset_mapping` the C47 char-span aligner is dead and unbind is meaningless. Do not substitute `k+1` indexing — C47 forbids it explicitly.

`transformers` here is 5.12.1, a major ahead of what `loop.py` was written against. This slice is what proves the boundary before B3 spends an epoch.

## Slice A5 — memory guard

`set_per_process_memory_fraction` is a Python call, not an env var, and `loop.py` must not be edited. The cap goes in a launcher **outside** the repo.

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
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
REMOTE
```

`0.03 × 130.7 GB ≈ 3.9 GB` — above the measured 0.73 GB at batch 1 (batch 8 stays well under the cap), ~1.3 GB below what is free. If the estimate is wrong, **the trainer dies and the server does not.** That is the entire purpose of this slice.

**Done:** `~/hlx/guard.py` exists and is not inside `~/Hyperlex`.

---

## Slice B1 — preflight

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
cd ~/Hyperlex
docker run --name "hlx-$$-$(date +%s)" \
  --user "$(id -u):$(id -g)" -e HOME="$HOME" \
  -v "$HOME/Hyperlex:$HOME/Hyperlex" \
  -v "$HOME/.hyperlex:$HOME/.hyperlex" \
  -v "$HOME/.cache:$HOME/.cache" \
  -w "$HOME/Hyperlex" \
  -e PYTHONPATH=scripts/shadow \
  -e HYPERLEX_ALLOW_TRAIN=1 \
  -e HYPERLEX_TRUNK_DIR="$HOME/.hyperlex/models/trunks/ModernBERT-base" \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  python -m hyperlexical.preflight | tee ~/.hyperlex/preflight.json
REMOTE
```

**Done:** exit 0, with `ready_to_train: true`, `machine: "aarch64"`, `name_gate: false`.

**Stop if:** exit 2 — the gate is closed. Read `reason` in the JSON. Do not set env vars the spec did not list to force it open.

Expected `data_counts` as of main `e3425ab` (2026-09-11): **classify 1922, unbind 437, negatives 208**, `data_sha256` beginning `637f800b`.

`classify` deliberately **excludes** negatives — it is the honest family quota for the 2,000 name-gate. `classify_all` is the larger number and is *not* the gate figure. Do not substitute one for the other.

Name-gate gaps now: classify **78**, unbind **0**, negatives **0**. Two of three are closed.

A different sha means the dataset moved again — report the new value and its counts, then continue. It is no longer a stop: this dataset is under active harvest and `0d6a3e34` (183 rows) is the retired seed snapshot.

## Slice B2 — E2 before

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
cd ~/Hyperlex
docker run --name "hlx-$$-$(date +%s)" \
  --user "$(id -u):$(id -g)" -e HOME="$HOME" \
  -v "$HOME/Hyperlex:$HOME/Hyperlex" \
  -v "$HOME/.hyperlex:$HOME/.hyperlex" \
  -v "$HOME/.cache:$HOME/.cache" \
  -w "$HOME/Hyperlex" \
  -e PYTHONPATH=scripts/shadow \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  python -m hyperlexical.eval_unbind --out "$HOME/.hyperlex/hlx-e2-before.json"
REMOTE
```

No `--gpus`, no trunk, no train env. `eval_unbind` imports no torch.

**Done:** **exit 3.** That is the correct, expected result.

**Stop if:** exit 0. `e2_pass: true` on an untrained stub means the gate is broken. Halt the run and return to the human operator — this is the spec's tripwire, and the one outcome nobody wants silently swallowed. Do not proceed to B3.

## Slice B3 — train

The only slice that takes device memory, and the only one whose duration is unknown. **Launch it detached, then poll** — a foreground run that outlives your executor's command timeout gets SIGTERM'd mid-epoch and wastes the whole slice.

**B3a — launch.** Returns immediately:

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
mkdir -p ~/hlx ~/.cache/triton ~/.cache/inductor
NAME="hlx-train-$(date +%s)"
echo "$NAME" > ~/hlx/last-train-container
cd ~/Hyperlex
docker run -d --name "$NAME" --gpus all \
  --user "$(id -u):$(id -g)" -e HOME="$HOME" \
  -v "$HOME/Hyperlex:$HOME/Hyperlex" \
  -v "$HOME/.hyperlex:$HOME/.hyperlex" \
  -v "$HOME/.cache:$HOME/.cache" \
  -v "$HOME/hlx:$HOME/hlx" \
  -w "$HOME/Hyperlex" \
  -e PYTHONPATH=scripts/shadow \
  -e HYPERLEX_ALLOW_TRAIN=1 \
  -e HYPERLEX_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e TOKENIZERS_PARALLELISM=false \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e TRITON_CACHE_DIR="$HOME/.cache/triton" \
  -e TORCHINDUCTOR_CACHE_DIR="$HOME/.cache/inductor" \
  -e XDG_CACHE_HOME="$HOME/.cache" \
  -e HYPERLEX_TRUNK_DIR="$HOME/.hyperlex/models/trunks/ModernBERT-base" \
  -e HYPERLEX_TRAIN_OUT="$HOME/.hyperlex/models/hyperlex-encoder-modernbert-base-seed" \
  -e HYPERLEX_TRAIN_EPOCHS=2 \
  -e HYPERLEX_TRAIN_BATCH=8 \
  -e HYPERLEX_TRAIN_LR=2e-5 \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  python "$HOME/hlx/guard.py" 0.03 hyperlexical.train --offline --run
echo "launched: $NAME"
REMOTE
```

**B3b — poll.** Short and re-runnable. Dispatch it repeatedly until it reports a terminal state:

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
NAME=$(cat ~/hlx/last-train-container)
STATUS=$(docker inspect -f '{{.State.Status}}' "$NAME")
CODE=$(docker inspect -f '{{.State.ExitCode}}' "$NAME")
echo "container=$NAME status=$STATUS exit=$CODE"
if [ "$STATUS" = "exited" ]; then
  docker logs "$NAME" > ~/.hyperlex/train-stdout.json 2>~/.hyperlex/train-stderr.txt
  echo "--- stdout ---"; tail -40 ~/.hyperlex/train-stdout.json
  echo "--- stderr ---"; tail -20 ~/.hyperlex/train-stderr.txt
else
  echo "still running — re-dispatch this slice"
  docker logs --tail 5 "$NAME" 2>&1 | tail -5
fi
REMOTE
```

Re-dispatch B3b until `status=exited`. Do not launch B3a a second time — that starts a competing trainer against the same memory cap.

Trains on roughly **4,375 train / 541 val / 551 test** rows at main `e3425ab` — about 29× the retired seed. `MAX_LEN` 64, batch 8.

Two consequences. Runtime is now minutes rather than seconds, so B3b may need several polls; that is expected, not a hang. And the val-metric caveat is **gone** — unbind val is ~64 rows, not 1, so `unbind_exact` is finally a real measurement.

Per the updated `AARON-SPARK-TRAIN.md`, the operator SoT is the primary source. If the run should train against live candidates rather than the tracked snapshot, that is `--include-live`, and it is the spec owner's call — do not add the flag on your own initiative.

**Done:** `status=exited exit=0`, and the receipt in `train-stdout.json` shows `cuda: true`, `device: "cuda"`, `name_gate: false`, `e2_pass: false`, `brier: null`, and `n_unfrozen_encoder` > 0.

**Stop if:**

- `cuda: false` — it fell back to CPU. `AARON-SPARK-TRAIN.md` §6: no CPU-only named encoder if `sm_121` fails. Return the error, do not accept the run.
- CUDA OOM in stderr. Report it. Do **not** raise `0.03`, and do **not** stop a co-tenant container to make room. Both are for a human to decide.
- `n_unfrozen_encoder` is 0 — the freeze walked the wrong module tree and nothing trained.
- `exit=4` with an `error` field — return it verbatim.
- Any non-zero exit not listed above — return stderr verbatim, do not retry.

## Slice B4 — E2 after

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
cd ~/Hyperlex
docker run --name "hlx-$$-$(date +%s)" \
  --user "$(id -u):$(id -g)" -e HOME="$HOME" \
  -v "$HOME/Hyperlex:$HOME/Hyperlex" \
  -v "$HOME/.hyperlex:$HOME/.hyperlex" \
  -v "$HOME/.cache:$HOME/.cache" \
  -w "$HOME/Hyperlex" \
  -e PYTHONPATH=scripts/shadow \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  python -m hyperlexical.eval_unbind --out "$HOME/.hyperlex/hlx-e2-after.json"
REMOTE
```

No `--gpus`, no trunk, no train env. `eval_unbind` imports no torch.

**Done:** exit 3, and the file is **byte-identical to `hlx-e2-before.json`**.

That is not a bug and not a failed run. `eval_unbind` never loads the trained heads — it reports `trunk_loaded: false`, `model_id: "stub"`, and compares a sha256-derived stub against a seed-7 probe. Both sides are deterministic, so training cannot move it. Verified byte-identical across repeat runs.

**Do not** attempt to make "after" differ from "before". Nothing in this unit wires the trained model into E2. Record the identity as a finding and move on.

## Slice B5 — evidence

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
cd ~/.hyperlex
sha256sum models/hyperlex-encoder-modernbert-base-seed/* > evidence-sha256.txt
ls -la models/hyperlex-encoder-modernbert-base-seed/
git -C ~/Hyperlex status --short
docker run --gpus all --name "hlx-$$-$(date +%s)" \
  --user "$(id -u):$(id -g)" -e HOME="$HOME" \
  lmsysorg/sglang:dev-qwen38-27b-dflash2 \
  python -c "import torch;f,t=torch.cuda.mem_get_info();print(round(f/1e9,1),round(t/1e9,1))"
REMOTE
```

Measured from a throwaway container, **not** by `docker exec` into the server — the hard-nos forbid touching it.

Then pull the evidence back. This block runs **on the Mac**, not over ssh — the artifacts are on the Spark and your report is not:

```bash
mkdir -p ~/hlx-evidence
scp spark:'~/.hyperlex/preflight.json' ~/hlx-evidence/
scp spark:'~/.hyperlex/hlx-e2-before.json' ~/hlx-evidence/
scp spark:'~/.hyperlex/hlx-e2-after.json' ~/hlx-evidence/
scp spark:'~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed/train-receipt.json' ~/hlx-evidence/
scp spark:'~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed/layout.json' ~/hlx-evidence/
scp spark:'~/.hyperlex/evidence-sha256.txt' ~/hlx-evidence/
diff ~/hlx-evidence/hlx-e2-before.json ~/hlx-evidence/hlx-e2-after.json && echo "E2 BYTE-IDENTICAL (expected)"
ls -la ~/hlx-evidence/
```

Weights stay on the Spark. Do **not** copy `model.safetensors` or `heads.pt` to the Mac — `~/.hyperlex/models/` is the Spark dump location and no weight binary travels.

**Done:** the Spark output dir holds `config.json`, `layout.json`, `train-receipt.json`, `config-train.json`, and one of `model.safetensors` / `heads.pt`. Free memory is back to baseline. Six files are in `~/hlx-evidence/` on the Mac and the `diff` reported identical.

**On `git status`: a dirty tree here is expected, not a failure.** B3 calls `write_export`, which regenerates the ten tracked files under `specs/007-hyperlexical-model/exports/`. They will appear as modified. The check is that *nothing outside that directory* changed:

```bash
ssh spark bash -s <<'REMOTE'
set -euo pipefail
cd ~/Hyperlex
echo "--- modified ---"; git status --short
OUTSIDE=$(git status --porcelain | awk '{print $2}' | grep -v '^specs/007-hyperlexical-model/exports/' || true)
if [ -n "$OUTSIDE" ]; then echo "UNEXPECTED changes outside exports/:"; echo "$OUTSIDE"; exit 1; fi
echo "EXPORTS_ONLY_OK"
REMOTE
```

**Done:** prints `EXPORTS_ONLY_OK`.

**Stop if:** anything outside `exports/` is modified. Report the paths — the run touched something it should not have.

Do **not** commit the regenerated exports, and do **not** `git checkout --` them away. They are the spec owner's artifacts; leave them as they lie and record the `data_sha256` from the receipt instead.

## Slice C1 — open the PR

Runs **on the Mac**, not over ssh. `gh` is not installed on the Spark, and `prabu-openclaw` has **pull-only** access to `scrimshawlife-ctrl/Hyperlex` — so this is a fork-PR, not a branch push.

**Only two files ever go in.** The run's artifacts — weights, receipts, exports — are forbidden in git by `AARON-SPARK-TRAIN.md` §6 and stay on the Spark. Their numbers travel in the PR *body*, never as committed files.

**C1a — build the PR body** from what B5 pulled back:

```bash
cd "$HOME/hlx-evidence"
python3 - <<'PY' > pr-body.md
import json, pathlib
d = pathlib.Path(".")
def j(n):
    try: return json.loads((d/n).read_text())
    except Exception: return {}
r, pre = j("train-receipt.json"), j("preflight.json")
before, after = (d/"hlx-e2-before.json"), (d/"hlx-e2-after.json")
identical = before.exists() and after.exists() and before.read_bytes() == after.read_bytes()
print("Operator procedure for the 007 seed smoke. Companion to `AARON-SPARK-TRAIN.md`; changes no lock.\n")
print("## What this adds\n")
print("- `SPARK-BRINGUP.md` — human runbook, measured box state")
print("- `HERMES-SPARK-RUN.md` — orchestrator run order, 12 slices\n")
print("## Run evidence\n")
print("| Field | Value |")
print("|---|---|")
for k in ("device","cuda","epochs","n_train_classify","n_train_unbind",
          "n_unfrozen_encoder","last_loss","weight_file","name_gate","e2_pass","brier"):
    if k in r: print("| `%s` | `%s` |" % (k, r[k]))
if r.get("val"): print("| `val` | `%s` |" % json.dumps(r["val"]))
if pre.get("data_sha256"): print("| `data_sha256` | `%s…` |" % pre["data_sha256"][:16])
print("| E2 before/after | %s |" % ("byte-identical (expected)" if identical else "DIFFER — investigate"))
print("\n`e2_pass` and `name_gate` are false by design. This is a seed smoke, not a Hyperlexical card.")
print("\nWeights, receipts and exports stay on the Spark under `~/.hyperlex/` and are not in this PR.\n")
print("## Open for the spec owner\n")
print("- `unbind_exact` val is computed over **one** row; the metric can only be 0.0 or 1.0.")
print("- `eval_unbind` never loads the trained heads, so E2 before/after cannot differ as the harness stands.")
print("- `docs/remotes.md` states the org twin is a 404; it is live and public, and `push-org.sh` cannot fast-forward onto it.\n")
print("🤖 Generated with [Claude Code](https://claude.com/claude-code)")
PY
head -5 pr-body.md
```

**Done:** `pr-body.md` exists and its first lines render.

**C1b — stage, with a guard:**

```bash
REPO="$HOME/Documents/claude/Hyperlex-scrimshaw"
[ -d "$REPO/.git" ] || { echo "STOP: no clone at $REPO"; exit 1; }
cd "$REPO"
git fetch origin && git checkout main && git pull --ff-only origin main
git checkout -b 007-spark-runbooks

git add specs/007-hyperlexical-model/SPARK-BRINGUP.md \
        specs/007-hyperlexical-model/HERMES-SPARK-RUN.md

STAGED=$(git diff --cached --name-only | sort)
EXPECT=$(printf '%s\n' \
  specs/007-hyperlexical-model/HERMES-SPARK-RUN.md \
  specs/007-hyperlexical-model/SPARK-BRINGUP.md | sort)
if [ "$STAGED" != "$EXPECT" ]; then
  echo "STOP: unexpected staged files:"; echo "$STAGED"; exit 1
fi
echo "staged (verified):"; echo "$STAGED"
```

**Done:** prints exactly the two documentation paths.

**Stop if:** the guard fires. Something outside the two documents was staged — most likely `exports/`, which A2 should have excluded, or a file under `~/.hyperlex/`. Do not `git add -A`, do not `git add .`, do not force past it.

**C1c — commit, fork, open the draft PR:**

```bash
cd "$HOME/Documents/claude/Hyperlex-scrimshaw"
git commit -m "docs(007): Spark bring-up runbook + Hermes run order

Operator procedure for the 007 seed smoke on the DGX Spark.
Companion to AARON-SPARK-TRAIN.md; changes no lock (C41-C52 stand).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"

gh repo fork scrimshawlife-ctrl/Hyperlex --remote=false --clone=false 2>/dev/null || true
git remote get-url fork >/dev/null 2>&1 \
  || git remote add fork "https://github.com/prabu-openclaw/Hyperlex.git"
git push -u fork 007-spark-runbooks

gh pr create --repo scrimshawlife-ctrl/Hyperlex \
  --base main --head "prabu-openclaw:007-spark-runbooks" --draft \
  --title "docs(007): Spark bring-up runbook + Hermes run order" \
  --body-file "$HOME/hlx-evidence/pr-body.md"
```

**Done:** `gh pr create` prints a PR URL, and the PR shows exactly two changed files.

**Stop if:** `gh` reports no authenticated account, or the fork push is rejected. Return to the human operator. Do not retry with different credentials, and do not push to `origin` — `prabu-openclaw` lacks write access and it will fail.

The PR opens as a **draft** deliberately: it is created by an automated run, and a human marks it ready. Drop `--draft` only if the operator asks.


## Hard no — applies to every slice

Inherited from `AARON-SPARK-TRAIN.md` §6: No Hub upload. No `hyperlex-structure-149m`. No chat template. No refusal head. No Brier. No `semantic`. No 7B. No Orin. No 006 labels. No wrap rows. No weight binaries in git. No CPU-only named encoder.

Added for an autonomous executor:

- **Never stop, restart, remove, `docker exec` into, or reconfigure any container you did not launch in this run** — `qwen38-27b` and `spark-comfyui` above all. They are someone else's live services.
- **No slice stops or removes a container, including its own.** Forge's safety policy blocks container-lifecycle verbs and that is correct. If a container must be cleared, that is a human action — report it and wait. Never work around the policy.
- Never raise the guard fraction above `0.03`.
- Never edit any file under `~/Hyperlex`. Not `loop.py`, not `layout.py`, not `.gitignore`. The repo is read-only to this run; the only writes are the untracked exports A2 excludes.
- Never `git commit`, `git push`, or `gh pr create` **from the Spark clone** (`~/Hyperlex`). It stays pristine. The single exception is Slice C1, which runs on the Mac clone and may commit **only** the two documentation files it names.
- Never commit a weight, a receipt, an export, or anything under `~/.hyperlex/`. Their numbers go in the PR body; the files stay on the Spark.
- Never `git add -A` or `git add .` in C1. Stage the two named paths and let the guard verify.
- Never clone or read from `Zero-State-LLC/Hyperlex`.
- Never install packages on the host. Every step runs in a container off the already-pulled image.
- Never retry past a **Stop if**. Halt the slice, return the error, wait for a human.
- Never present this output as a trained Hyperlexical model. It is a seed smoke that fails E2 by design.

## Output Hermes must return

1. Per slice: name, exit code, done-condition met yes/no, and any stop triggered.
2. `preflight.json`, `hlx-e2-before.json`, `hlx-e2-after.json`, `train-receipt.json`, `layout.json`.
3. `data_sha256` from preflight, and whether it matched `0d6a3e34…`.
4. Confirmation that before/after E2 are byte-identical, stated as expected behaviour.
5. The torch note for Danny: version, CUDA, capability, and that it ran under a 3.9 GB cap beside a live SGLang server.
6. Free device memory before the run and after, showing the trainer released everything.
7. The PR URL from C1, and confirmation it shows exactly two changed files.
8. **The `--include-live` divergence, stated plainly.** `AARON-SPARK-TRAIN.md` says to train from the live SoT via `--include-live`. This run did not, for two reasons: `run_loop` calls `export_dataset(root)` with no `include_live` parameter and `train.py` exposes no flag or env var for it, so it is not expressible; and the Spark has no live store (`~/.hyperlex/hyperlexical/ingest_candidates.jsonl` does not exist), so it would have contributed zero rows. The tracked export was the complete dataset on this box. Report this as a known, deliberate divergence — not as an oversight, and not as a defect.
8. Anything that stopped a slice, verbatim, with no attempt at a fix.

Every number you return is OBSERVED or it does not go in. No INFERRED metrics. `brier` stays null.

---
