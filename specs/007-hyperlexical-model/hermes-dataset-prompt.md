# Hermes prompt — Hyperlexical T1 training harvest

**Voice:** harvest list = **ne0l0gist**. Training target = **Hyperlexical** (`name_gate` false).

Copy below the line. Do not run this prompt as a generator of restricted wraps.

---

You are Hermes harvesting a **training dataset** (ne0l0gist ingest) for the Hyperlexical Spec 007 T1 model path.

Trunk (frozen): `answerdotai/ModernBERT-base` (~149M). Train home: NVIDIA DGX Spark. Packet: `hyperlex.hyperlexical.inference.v0.1`. Brier is always null. Routes only `form` / `lexical`. No `semantic`. No chat. No refusal head.

## Mission

Produce the **best civilian dataset plan + harvest list** for:

1. lineage classify (E1)
2. typology multi-label
3. stage ordinal (INFERRED only)
4. unbind pairs for schemes `positional` and `type_slot` only (E2)
5. dialect / informal / vulgar civilian atoms (E6)
6. ordinary-prose negatives

Do **not** download weights. Do **not** open Spec 006 IsA. Do **not** scrape restricted how-tos, jailbreak wraps, ASR recipes, or reconstructable attack payloads.

## Gold vs weak vs forbidden

| bucket | class | may train classify | may gate E2 | notes |
|--------|-------|--------------------|-------------|-------|
| Hyperlex `examples/` + golden receipts + Spec 004 unbind fixtures | OBSERVED | yes | yes | first harvest |
| Settled Hyperlex ledger copies the operator exports | OBSERVED | yes | yes | hash the export; no `~/.hyperlex/` dump into git |
| Live-route detector labels | INFERRED | yes | no | weak |
| Urban Dictionary / Wiktionary slang glosses with license check | OBSERVED if cited | yes | no | gloss ≠ unbind gold |
| Wu/Sun-style LLM-generated slang | SPECULATIVE | no | no | C20 |
| TimesFM / Phase 5 packets | SPECULATIVE | no | no | |
| HyperLex-2016 graded LE pairs | pointer only | no | no | that is 006 |
| Restricted how-to / wrap / encode corpora | — | no | no | drop surface if a span trips; keep sha256 only |

## Lineage closed set

Use Hyperlex family ids already in the repo (8 families + `ytd_leaf` + `none`). Do not invent a ninth family. If a source atom does not map, label `none` and keep the row.

Typology tags allowed: `tribal`, `compression`, `irony_shield`, `status`, `hook`, `ritual`, `camouflage`.

Stage: `noise` | `circulating` | `contested` | `hyperstition_ish` — always INFERRED unless copied from a settled row.

## Unbind gold (E2)

Each gold unbind row needs:

- `text` (civilian atom or short phrase)
- `role_scheme`: `positional` or `type_slot`
- `roles`: ordered list
- `fillers`: aligned list
- `provenance`: fixture id or receipt hash

Start from Spec 004 fixtures. Expand only with the same two schemes. A third scheme name aborts the row.

Prefer short atoms. ModernBERT 8k context is unused. Tokenizer is official ModernBERT BPE — keep case; do not lowercase as a policy.

## Output you must return

1. Ranked source list (name, license, url or repo path, why it helps E1 vs E2 vs E6).
2. A JSONL **schema** for rows (`text`, `split`, `lineage`, `typology`, `stage`, `roles`, `fillers`, `role_scheme`, `provenance`, `class`, `license`).
3. Counts toward the T1 name-gate: 2k classify + 200 unbind + 200 negatives + dialect slice. Show the gap vs what Hyperlex already has.
4. Split rule: lexical hash split, no lemma leak into test.
5. Refusal: any source that is wrap/jailbreak/restricted how-to is listed under REJECTED with a one-line reason. No examples of the rejected content.
6. OBSERVED / INFERRED / SPECULATIVE on every source.

Work offline-first. Prefer files already in `scrimshawlife-ctrl/Hyperlex` and operator Notion civilian receipts over random web slang dumps.

---
