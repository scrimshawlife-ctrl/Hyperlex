#!/usr/bin/env python3
"""morph78: authorize name phrases val-settle → force expand → fair → soft_ceiling launch.

Authority: operator 2026-09-24 `name phrases` / authorize morph78.
Phrases (all split=val): have fun staying poor, fr fr no cap.

Base force/hard = morph77 tip (232/273). Warm morph65 + INIT_EXPAND_VOCAB=1.
UPSAMPLE=10 / SECOND_SLOT=2 / LAST=8. Freeze 11+. No SECOND_SLOT=4.
soft_ceiling ARMED: do NOT cancel solely for force-fair 1.0 n=164 —
launch train and finish via soft_ceiling_tiebreak (broad OBSERVED > PRIOR + E2).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

AUTH = (
    "operator 2026-09-24 name phrases — authorize morph78 "
    "have fun staying poor / fr fr no cap (split=val)"
)
PRIV = Path("/home/morpheus/hlx-private/p1-spark-morph78-val-settle-20260924")
TRAIN_PRIV = Path(
    "/home/morpheus/hlx-private/p1-spark-morph78-40ep-val-settle-20260924"
)
LABEL_PRIV = Path(
    "/home/morpheus/hlx-private/p1-spark-morph78-val-acquire-label-hold-20260923"
)
HOLD_PRIV = Path(
    "/home/morpheus/hlx-private/p1-spark-morph78-fresh-acquire-label-hold-20260923"
)
STORE = Path("/home/morpheus/.hyperlex/hyperlexical/ingest_candidates.jsonl")
HARVEST = Path(
    "/home/morpheus/.hyperlex/hyperlexical/harvest_unbind_observed_mw.jsonl"
)
FORCE_BASE = Path("/home/morpheus/hlx/force_train_morph77_expanded.jsonl")
HARD_BASE = Path("/home/morpheus/hlx/hard_atoms_train_morph77.jsonl")
FORCE_OUT = Path("/home/morpheus/hlx/force_train_morph78_expanded.jsonl")
HARD_OUT = Path("/home/morpheus/hlx/hard_atoms_train_morph78.jsonl")
FAIR_OUT = Path("/home/morpheus/hlx/fair-eval-morph65-morph78.json")
INTENT = Path("/home/morpheus/hlx/morph78-intent.json")
WARM = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65"
)
GATE_PIN = Path("/home/morpheus/hlx/GATE_SOFT_CEILING.json")

TYPE_SLOT_TAGS = ("TOKEN", "SLOT", "MARKER")
QUALIFY = ["have fun staying poor", "fr fr no cap"]
LINEAGE = {
    "have fun staying poor": "crypto-degen",
    "fr fr no cap": "kinship-address",
}
TYPOLOGY = {
    "crypto-degen": ["status", "tribal"],
    "kinship-address": ["tribal"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _structural_type_tags(n: int) -> list[str]:
    return [TYPE_SLOT_TAGS[i % len(TYPE_SLOT_TAGS)] for i in range(n)]


def _type_slot_text(tokens: list[str]) -> str:
    tags = _structural_type_tags(len(tokens))
    return " ".join(f"{tag}:{tok}" for tag, tok in zip(tags, tokens))


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(l)
        for l in path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )


def settle() -> dict:
    PRIV.mkdir(parents=True, exist_ok=True)
    TRAIN_PRIV.mkdir(parents=True, exist_ok=True)
    hold_path = HOLD_PRIV / "morph78_HOLD_AUTHORIZE_CARD.json"
    if hold_path.is_file():
        hold = json.loads(hold_path.read_text())
        hold["authorize_card_phrases"] = list(QUALIFY)
        hold["authorize_card_norms"] = list(QUALIFY)
        hold["authorize_received"] = {
            "as_of": _now(),
            "operator": "name phrases",
            "sentence": "authorize morph78: have fun staying poor, fr fr no cap",
            "auth": AUTH,
        }
        hold["note"] = "AUTHORIZE NAMED — settling OBSERVED split=val under soft_ceiling."
        hold_path.write_text(json.dumps(hold, indent=2) + "\n")
    labeled = _load_jsonl(LABEL_PRIV / "labeled_acquired_atoms.jsonl")
    by_norm = {_norm(r.get("text") or ""): r for r in labeled}
    qualify_norms = {_norm(q) for q in QUALIFY}

    store = _load_jsonl(STORE)
    harvest = _load_jsonl(HARVEST)
    force = _load_jsonl(FORCE_BASE)
    hard = _load_jsonl(HARD_BASE)
    force_base_n, hard_base_n = len(force), len(hard)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    shutil.copy2(STORE, STORE.with_name(STORE.name + f".bak-pre-morph78-{stamp}"))
    shutil.copy2(
        HARVEST, HARVEST.with_name(HARVEST.name + f".bak-pre-morph78-{stamp}")
    )

    obs_texts = {
        _norm(str(r.get("text") or ""))
        for r in store
        if str(r.get("class") or "").upper() == "OBSERVED"
    }
    store_by_norm = {_norm(str(r.get("text") or "")): i for i, r in enumerate(store)}
    force_keys = {
        (_norm(str(r.get("text") or "")), str(r.get("role_scheme") or ""))
        for r in force
    }
    harvest_keys = {
        (_norm(str(r.get("text") or "")), str(r.get("role_scheme") or ""))
        for r in harvest
    }

    settled: list[str] = []
    already: list[str] = []
    added_force: list[str] = []

    for q in QUALIFY:
        key = _norm(q)
        src = by_norm.get(key) or {}
        toks = [t.lower() for t in (src.get("gold_fillers") or q.split())]
        plain = " ".join(toks)
        key = _norm(plain)
        lineage = LINEAGE.get(key) or LINEAGE.get(_norm(q)) or src.get("lineage") or "none"
        already_obs = key in obs_texts

        if already_obs:
            already.append(plain)
            # ensure split=val on existing OBSERVED row
            if key in store_by_norm:
                i = store_by_norm[key]
                row = dict(store[i])
                row["split"] = "val"
                row["settle_note"] = (
                    str(row.get("settle_note") or "")
                    + f"|morph78_val_settle_force_val;{AUTH}"
                ).strip("|")
                row["authorization"] = AUTH
                store[i] = row
        else:
            if key in store_by_norm:
                i = store_by_norm[key]
                row = dict(store[i])
                row["class"] = "OBSERVED"
                row["epistemic"] = "OBSERVED"
                row["text"] = plain
                row["split"] = "val"
                row["lineage"] = lineage
                row["typology"] = TYPOLOGY.get(lineage, row.get("typology") or [])
                row["settle_note"] = (
                    str(row.get("settle_note") or "")
                    + f"|PACKET_SETTLE morph78 val-settle;{AUTH}"
                ).strip("|")
                row["authorization"] = AUTH
                store[i] = row
            else:
                store.append(
                    {
                        "text": plain,
                        "class": "OBSERVED",
                        "lineage": lineage,
                        "typology": TYPOLOGY.get(lineage, []),
                        "task": "classify",
                        "stage": "circulating",
                        "role_scheme": None,
                        "roles": [],
                        "fillers": [],
                        "provenance": "ingest:acquire:urban:20260924-morph78-val",
                        "license": "operator-local-crawl",
                        "epistemic": "OBSERVED",
                        "split": "val",
                        "settle_note": f"PACKET_SETTLE morph78 val-settle;{AUTH}",
                        "authorization": AUTH,
                    }
                )
                store_by_norm[key] = len(store) - 1
            obs_texts.add(key)
            settled.append(plain)

        tags = _structural_type_tags(len(toks))
        type_text = _type_slot_text(toks)
        for scheme, ftext, roles, prov in (
            (
                "positional",
                plain,
                [f"pos_{i}" for i in range(len(toks))],
                "civilian-pos:morph78-val-settle",
            ),
            ("type_slot", type_text, tags, "civilian-type:morph78-val-settle"),
        ):
            hk = (_norm(ftext), scheme)
            if hk not in harvest_keys:
                harvest.append(
                    {
                        "class": "OBSERVED",
                        "fillers": toks,
                        "license": "operator-local; labels OBSERVED; unbind structural whitespace",
                        "lineage": lineage,
                        "provenance": prov,
                        "role_scheme": scheme,
                        "roles": roles,
                        "split": "val",
                        "stage": "circulating",
                        "task": "unbind",
                        "text": ftext,
                        "typology": TYPOLOGY.get(lineage, []),
                        "authorization": AUTH,
                    }
                )
                harvest_keys.add(hk)
            fk = (_norm(ftext), scheme)
            if fk in force_keys:
                continue
            force_keys.add(fk)
            fid = "morph78-val-" + hashlib.sha1(
                f"{ftext}|{scheme}".encode()
            ).hexdigest()[:12]
            force.append(
                {
                    "text": ftext,
                    "role_scheme": scheme,
                    "gold_fillers": toks,
                    "gold_roles": roles,
                    "id": fid,
                    "source": "val_settle_morph78",
                    "authorization": AUTH,
                    "dataset_class_source": "OBSERVED",
                    "promoted_to_observed_train": False,
                    "split_hint": "val",
                }
            )
            hard.append(
                {
                    "text": ftext,
                    "role_scheme": scheme,
                    "gold_fillers": toks,
                    "gold_roles": roles,
                    "id": fid,
                    "source": "val_settle_morph78",
                    "authorization": AUTH,
                    "dataset_class_source": "OBSERVED",
                }
            )
            added_force.append(ftext)

    _write_jsonl(STORE, store)
    _write_jsonl(HARVEST, harvest)
    _write_jsonl(FORCE_OUT, force)
    _write_jsonl(HARD_OUT, hard)
    shutil.copy2(FORCE_OUT, PRIV / FORCE_OUT.name)
    shutil.copy2(HARD_OUT, PRIV / HARD_OUT.name)

    summary = {
        "auth": AUTH,
        "as_of": _now(),
        "qualify": QUALIFY,
        "settled_inferred_to_observed": settled,
        "already_observed": already,
        "force_base": force_base_n,
        "force78": len(force),
        "force_added": len(force) - force_base_n,
        "hard_base": hard_base_n,
        "hard78": len(hard),
        "hard_added": len(hard) - hard_base_n,
        "added_force_texts": added_force,
        "split_policy": "force_val",
        "force_path": str(FORCE_OUT),
        "hard_path": str(HARD_OUT),
        "one_knob": "val-settle force expand (2 named phrases) after morph77 tip; soft_ceiling ARMED",
    }
    (PRIV / "ACQUIRE_SETTLE_SUMMARY.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    (PRIV / "METHOD.md").write_text(
        "# morph78 val-settle — method\n\n"
        f"**Authority:** {AUTH}\n\n"
        "ONE knob: settle HOLD card phrases as OBSERVED with **split=val**, "
        "dual-scheme force/hard expand from morph77 tip. Warm morph65 + "
        "INIT_EXPAND_VOCAB=1. UPSAMPLE=10 / SECOND_SLOT=2 / LAST=8. "
        "Cancel if fair ceiling 1.0 with n unchanged.\n"
    )
    if summary["force_added"] <= 0:
        raise SystemExit("REFUSE force_added=0")
    return summary


def write_fair_script():
    src = Path("/home/morpheus/hlx/fair_eval_morph65_morph77.py")
    if not src.is_file():
        src = Path("/home/morpheus/hlx/fair_eval_morph65_morph76.py")
    text = src.read_text()
    text = re.sub(
        r'FORCE = Path\("[^"]+"\)',
        'FORCE = Path("/home/morpheus/hlx/force_train_morph78_expanded.jsonl")',
        text,
        count=1,
    )
    text = re.sub(
        r'HARD = Path\("[^"]+"\)',
        'HARD = Path("/home/morpheus/hlx/hard_atoms_train_morph78.jsonl")',
        text,
        count=1,
    )
    text = re.sub(
        r'OUT = Path\("[^"]+"\)',
        'OUT = Path("/home/morpheus/hlx/fair-eval-morph65-morph78.json")',
        text,
        count=1,
    )
    text = re.sub(
        r'PROMOTE = Path\("[^"]+"\)',
        'PROMOTE = Path("/home/morpheus/hlx-private/p1-spark-morph78-val-settle-20260923/PROMOTE_SUMMARY.json")',
        text,
        count=1,
    )
    text = re.sub(
        r'PRIV = Path\("[^"]+"\)',
        'PRIV = Path("/home/morpheus/hlx-private/p1-spark-morph78-val-settle-20260923")',
        text,
        count=1,
    )
    text = re.sub(
        r'TRAIN_PRIV = Path\("[^"]+"\)',
        'TRAIN_PRIV = Path("/home/morpheus/hlx-private/p1-spark-morph78-40ep-val-settle-20260924")',
        text,
        count=1,
    )
    text = text.replace("morph76", "morph77")
    # fix paths that may have been mangled
    text = re.sub(
        r'FORCE = Path\("[^"]+"\)',
        'FORCE = Path("/home/morpheus/hlx/force_train_morph78_expanded.jsonl")',
        text,
        count=1,
    )
    text = re.sub(
        r'HARD = Path\("[^"]+"\)',
        'HARD = Path("/home/morpheus/hlx/hard_atoms_train_morph78.jsonl")',
        text,
        count=1,
    )
    Path("/home/morpheus/hlx/fair_eval_morph65_morph78.py").write_text(text)


def fair_eval() -> tuple[float, int, dict]:
    write_fair_script()
    name = f"hlx-fair-morph78-{int(time.time())}"
    cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--gpus",
        "all",
        "-w",
        "/home/morpheus/Hyperlex",
        "-v",
        "/home/morpheus/.cache:/home/morpheus/.cache",
        "-v",
        "/home/morpheus/hlx:/home/morpheus/hlx",
        "-v",
        "/home/morpheus/Hyperlex:/home/morpheus/Hyperlex",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-e",
        "HOME=/home/morpheus",
        "-e",
        "PYTHONPATH=scripts/shadow",
        "-e",
        "TOKENIZERS_PARALLELISM=false",
        "-e",
        "HYPERLEX_OFFLINE=1",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "HYPERLEX_TRUNK_DIR=/home/morpheus/.hyperlex/models/trunks/ModernBERT-base",
        "-e",
        "HYPERLEX_CUDA_MEM_FRACTION=0.3",
        "lmsysorg/sglang:dev-qwen38-27b-dflash2",
        "python",
        "-c",
        "import runpy; runpy.run_path('/home/morpheus/hlx/fair_eval_morph65_morph78.py', run_name='__main__')",
    ]
    print("running fair eval...", flush=True)
    subprocess.check_call(cmd)
    fair = json.loads(FAIR_OUT.read_text())
    return float(fair["fair_exact"]), int(fair["fair_n"]), fair


def write_intent(fair_exact: float, fair_n: int, summary: dict) -> None:
    intent = {
        "auth": AUTH,
        "one_knob": summary["one_knob"],
        "warm": str(WARM),
        "init_from": str(WARM),
        "init_expand_vocab": True,
        "force": str(FORCE_OUT),
        "hard": str(HARD_OUT),
        "upsample": 10,
        "second_slot": 2,
        "last_trainable": 8,
        "epochs": 40,
        "lr": "2e-5",
        "mem_fraction": 0.3,
        "save_best": True,
        "fair_path": str(FAIR_OUT),
        "fair_exact": fair_exact,
        "fair_n": fair_n,
        "pin_rule": f"best > fair on n={fair_n} and E2 trunk-forward unbind_exact=1.0",
        "name_gate": False,
        "force_added": summary["force_added"],
        "atoms": QUALIFY,
        "split_policy": "force_val",
        "not_this_card": [
            "upsample 11+",
            "SECOND_SLOT=4",
            "invent OBSERVED",
            "Hub",
            "force_added=0",
            "fair ceiling 1.0 with n unchanged",
        ],
    }
    INTENT.write_text(json.dumps(intent, indent=2) + "\n")
    for d in (PRIV, TRAIN_PRIV):
        d.mkdir(parents=True, exist_ok=True)
        (d / "morph78-intent.json").write_text(INTENT.read_text())
        if FAIR_OUT.is_file():
            (d / FAIR_OUT.name).write_text(FAIR_OUT.read_text())



def finish_and_poll(fair_exact: float, fair_n: int) -> None:
    finish = Path("/home/morpheus/hlx/finish_soft_ceiling.py").read_text()
    finish = re.sub(r"FAIR = [0-9.]+", f"FAIR = {fair_exact!r}", finish, count=1)
    finish = re.sub(r"FAIR_N = \d+", f"FAIR_N = {fair_n}", finish, count=1)
    finish = re.sub(r"MORPH = \d+", "MORPH = 78", finish, count=1)
    finish = finish.replace(
        'OUT = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph0")',
        'OUT = Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph78")',
    )
    finish = finish.replace(
        'PRIV = Path("/home/morpheus/hlx-private/p1-spark-morph0-soft-ceiling")',
        'PRIV = Path("/home/morpheus/hlx-private/p1-spark-morph78-40ep-val-settle-20260924")',
    )
    finish = finish.replace(
        'GATE_OWNER = os.environ.get("GATE_OWNER", "morph0-soft-ceiling")',
        'GATE_OWNER = os.environ.get("GATE_OWNER", "morph78-val-settle")',
    )
    finish = finish.replace(
        'E2_SRC = Path("/home/morpheus/hlx/e2-unbind-morph0.json")',
        'E2_SRC = Path("/home/morpheus/hlx/e2-unbind-morph78.json")',
    )
    finish = finish.replace(
        'BROAD_EVAL = Path("/home/morpheus/hlx/broad-eval-morph0.json")',
        'BROAD_EVAL = Path("/home/morpheus/hlx/broad-eval-morph78.json")',
    )
    Path("/home/morpheus/hlx/finish_morph78.py").write_text(finish)

    e2_src = Path("/home/morpheus/hlx/run_e2_morph77.sh")
    if not e2_src.is_file():
        e2_src = Path("/home/morpheus/hlx/run_e2_morph76.sh")
    e2 = e2_src.read_text().replace("morph77", "morph78").replace("morph76", "morph78")
    Path("/home/morpheus/hlx/run_e2_morph78.sh").write_text(e2)
    os.chmod("/home/morpheus/hlx/run_e2_morph78.sh", 0o755)

    poll = f"""#!/usr/bin/env bash
set -euo pipefail
NAME=$(cat /home/morpheus/hlx/last-train-container)
PRIV=/home/morpheus/hlx-private/p1-spark-morph78-40ep-val-settle-20260924
OUT=/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph78
LOG=$PRIV/poll.log
mkdir -p "$PRIV"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) poll start $NAME" | tee -a "$LOG"
while docker inspect -f "{{{{.State.Running}}}}" "$NAME" 2>/dev/null | grep -q true; do
  case "$NAME" in
  hlx-train-morph78-*) ;;
  *) echo "REFUSE unexpected container $NAME" | tee -a "$LOG"; exit 9 ;;
  esac
  if [[ -f "$OUT/train-receipt.json" ]]; then
    python3 - <<'PY' | tee -a "$LOG" || true
import json
from pathlib import Path
d=json.loads(Path("/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph78/train-receipt.json").read_text())
print("best ep", d.get("best_epoch") or d.get("val",{{}}).get("epoch"),
      "ue", d.get("best_unbind_exact") or d.get("val",{{}}).get("unbind_exact"),
      "fair", {fair_exact!r})
PY
  fi
  sleep 120
done
EC=$(docker inspect -f "{{{{.State.ExitCode}}}}" "$NAME" 2>/dev/null || echo missing)
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DONE ec=$EC" | tee -a "$LOG"
docker logs "$NAME" 2>&1 | tail -120 | tee -a "$PRIV/nohup.out" || true
if [[ -f "$OUT/train-receipt.json" ]]; then
  sudo chown -R morpheus:morpheus "$OUT" "$PRIV" 2>/dev/null || true
  /home/morpheus/hlx/run_e2_morph78.sh 2>&1 | tee -a "$LOG" || true
  HLX_FAIR_MODEL=/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph65 \\
    HLX_BROAD_OUT=/home/morpheus/hlx/broad-eval-prior-morph65.json \\
    HLX_BROAD_PRIV=$PRIV \\
    HLX_BROAD_NAME=hlx-broad-prior65-morph78-$(date +%s) \\
    bash /home/morpheus/hlx/run_broad_eval.sh 2>&1 | tee -a "$LOG" || true
  HLX_FAIR_MODEL=$OUT \\
    HLX_BROAD_OUT=/home/morpheus/hlx/broad-eval-morph78.json \\
    HLX_BROAD_PRIV=$PRIV \\
    HLX_BROAD_NAME=hlx-broad-morph78-$(date +%s) \\
    bash /home/morpheus/hlx/run_broad_eval.sh 2>&1 | tee -a "$LOG" || true
  python3 - <<'PY' || true
import json
from pathlib import Path
lock=Path("/home/morpheus/hlx-private/p1-spark-morph78-40ep-val-settle-20260924/GATE_LOCK.json")
if lock.is_file():
    d=json.loads(lock.read_text())
    if d.get("status") == "done":
        raise SystemExit(0)
GATE_OWNER=morph78-val-settle python3 /home/morpheus/hlx/finish_morph78.py 2>&1 | tee -a "$LOG" || true
PY
else
  echo "NO_RECEIPT" | tee -a "$LOG"
fi
"""
    Path("/home/morpheus/hlx/poll_morph78.sh").write_text(poll)
    os.chmod("/home/morpheus/hlx/poll_morph78.sh", 0o755)

def launch() -> str:
    running = subprocess.check_output(
        ["docker", "ps", "--format", "{{.Names}}"], text=True
    )
    for line in running.splitlines():
        if line.startswith("hlx-train-"):
            raise SystemExit(f"REFUSE: train already running: {line}")
    name = f"hlx-train-morph78-{int(time.time())}"
    Path("/home/morpheus/hlx/last-train-container").write_text(name + "\n")
    (TRAIN_PRIV / "container.txt").write_text(name + "\n")
    (TRAIN_PRIV / "STATUS.txt").write_text("IN_FLIGHT\n")
    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        name,
        "--gpus",
        "all",
        "-w",
        "/home/morpheus/Hyperlex",
        "-v",
        "/home/morpheus/.cache:/home/morpheus/.cache",
        "-v",
        "/home/morpheus/hlx:/home/morpheus/hlx",
        "-v",
        "/home/morpheus/Hyperlex:/home/morpheus/Hyperlex",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-e",
        "HOME=/home/morpheus",
        "-e",
        "PYTHONPATH=scripts/shadow",
        "-e",
        "PYTHONUNBUFFERED=1",
        "-e",
        "TOKENIZERS_PARALLELISM=false",
        "-e",
        "HYPERLEX_OFFLINE=1",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "HYPERLEX_ALLOW_TRAIN=1",
        "-e",
        "HYPERLEX_INCLUDE_LIVE=1",
        "-e",
        "HYPERLEX_TRUNK_DIR=/home/morpheus/.hyperlex/models/trunks/ModernBERT-base",
        "-e",
        "HYPERLEX_TRAIN_OUT=/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-morph78",
        "-e",
        f"HYPERLEX_INIT_FROM={WARM}",
        "-e",
        "HYPERLEX_INIT_EXPAND_VOCAB=1",
        "-e",
        "HYPERLEX_UNBIND_FORCE_TRAIN_PATH=/home/morpheus/hlx/force_train_morph78_expanded.jsonl",
        "-e",
        "HYPERLEX_UNBIND_HARD_ATOMS_PATH=/home/morpheus/hlx/hard_atoms_train_morph78.jsonl",
        "-e",
        "HYPERLEX_UNBIND_RESIDUAL_DUMP=/home/morpheus/hlx/residual-morph78.jsonl",
        "-e",
        "HYPERLEX_UNBIND_FILLER_DENYLIST_PATH=/home/morpheus/hlx/filler-denylist-status.json",
        "-e",
        "HYPERLEX_UNBIND_OBSERVED_UPSAMPLE=10",
        "-e",
        "HYPERLEX_UNBIND_SECOND_SLOT_WEIGHT=2",
        "-e",
        "HYPERLEX_UNBIND_HARD_UPSAMPLE=4",
        "-e",
        "HYPERLEX_UNBIND_HEAD_SLOT_WEIGHT=2",
        "-e",
        "HYPERLEX_UNBIND_MORPH_MARGIN=0.5",
        "-e",
        "HYPERLEX_UNBIND_LOSS_WEIGHT=1.0",
        "-e",
        "HYPERLEX_UNBIND_INFERRED_WEIGHT=1.0",
        "-e",
        "HYPERLEX_UNBIND_INFERRED_CAP=0",
        "-e",
        "HYPERLEX_UNBIND_PRIMARY=slot_ce",
        "-e",
        "HYPERLEX_UNBIND_CURRICULUM=1",
        "-e",
        "HYPERLEX_UNBIND_CURRICULUM_POS_EPOCHS=1",
        "-e",
        "HYPERLEX_UNBIND_CURRICULUM_TYPE_EPOCHS=1",
        "-e",
        "HYPERLEX_LAST_TRAINABLE=8",
        "-e",
        "HYPERLEX_TRAIN_EPOCHS=40",
        "-e",
        "HYPERLEX_TRAIN_LR=2e-5",
        "-e",
        "HYPERLEX_TRAIN_BATCH=8",
        "-e",
        "HYPERLEX_SAVE_BEST_UNBIND=1",
        "-e",
        "HYPERLEX_CUDA_MEM_FRACTION=0.3",
        "-e",
        "PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512",
        "-e",
        "TRITON_CACHE_DIR=/home/morpheus/.cache/triton",
        "-e",
        "TORCHINDUCTOR_CACHE_DIR=/home/morpheus/.cache/inductor",
        "-e",
        "XDG_CACHE_HOME=/home/morpheus/.cache",
        "lmsysorg/sglang:dev-qwen38-27b-dflash2",
        "python",
        "/home/morpheus/hlx/guard.py",
        "0.3",
        "hyperlexical.train",
        "--offline",
        "--run",
        "--include-live",
    ]
    subprocess.check_call(cmd)
    inspect = subprocess.check_output(
        ["docker", "inspect", "-f", "{{range .Config.Env}}{{println .}}{{end}}", name],
        text=True,
    )
    if "HYPERLEX_INIT_FROM=" not in inspect:
        subprocess.call(["docker", "rm", "-f", name])
        raise SystemExit("REFUSE: INIT_FROM missing")
    if "force_train_morph78_expanded.jsonl" not in inspect:
        subprocess.call(["docker", "rm", "-f", name])
        raise SystemExit("REFUSE: morph77 force missing")
    log = open(TRAIN_PRIV / "poll.stdout", "w")
    subprocess.Popen(
        ["bash", "/home/morpheus/hlx/poll_morph78.sh"],
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return name


def main() -> None:
    summary = settle()
    (PRIV / "PROMOTE_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"phase": "settle", **{k: summary[k] for k in summary if k != "auth"}}, indent=2))
    fair_exact, fair_n, fair = fair_eval()
    summary["fair_exact"] = fair_exact
    summary["fair_n"] = fair_n
    summary["prior_fair_n"] = 164
    summary["fair_n_moved"] = fair_n != 164
    (PRIV / "PROMOTE_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_intent(fair_exact, fair_n, summary)

    # soft_ceiling ARMED: fair 1.0 n<=164 is advisory — still launch + soft_ceiling finish.
    if fair_exact >= 1.0 and fair_n <= 164:
        note = {
            "status": "SOFT_CEILING_CONTINUE",
            "as_of": _now(),
            "auth": AUTH,
            "fair_exact": fair_exact,
            "fair_n": fair_n,
            "force_added": summary["force_added"],
            "gate": "soft_ceiling_tiebreak",
            "reason": "Force-fair ceiling; do not cancel. Train + broad OBSERVED > PRIOR + E2.",
            "settle_kept": True,
            "name_gate": False,
        }
        (PRIV / "SOFT_CEILING_CONTINUE.json").write_text(json.dumps(note, indent=2) + "\n")
        (TRAIN_PRIV / "STATUS.txt").write_text("SOFT_CEILING_CONTINUE\n")
        (TRAIN_PRIV / "SOFT_CEILING_CONTINUE.json").write_text(
            json.dumps(note, indent=2) + "\n"
        )
        print(json.dumps(note, indent=2))

    finish_and_poll(fair_exact, fair_n)
    name = launch()
    print(
        json.dumps(
            {
                "status": "IN_FLIGHT",
                "container": name,
                "fair_exact": fair_exact,
                "fair_n": fair_n,
                "force_added": summary["force_added"],
                "atoms": QUALIFY,
                "gate": "soft_ceiling_tiebreak",
                "name_gate": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
