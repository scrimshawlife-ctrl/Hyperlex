# Design: Mutation prediction (next surface forms)

**Date:** 2026-08-06  
**Status:** Draft for approval  
**Version target:** 0.4.x (additive analysis block)  
**Approach:** A — analysis block + deterministic operators + optional governed LLM enrich  

## Problem

Hyperlex labels *historical* mutation operators (`lineage.branch_operator`, neologism `formation`) and predicts *virality*, but does not forecast **likely next surface forms** of a slang atom. Operators and researchers need speculative, auditable candidates for how a term might mutate next — without inventing Brier scores.

## Goals

1. On every analyze / pipeline unit, emit **ranked next-form candidates** for the primary atomic term (and optionally each seed atom).
2. Default path is **fully offline and deterministic** (no network, no LLM).
3. Optional **governed LLM enrich** merges extra candidates when enabled (fail-open).
4. Always **`provenance: SPECULATIVE`**, always **`brier: null`** (and never a numeric Brier on this block).
5. Fit existing packet shape and docs discipline (glossary, reading-evidence, offline demo).

## Non-goals

- Settling mutation candidates as forecasts / Brier series (Approach B — deferred).
- Map-only surface without core analyze attachment (Approach C).
- Training or fine-tuning embedding models for mutation.
- Claiming cultural certainty or market advice from candidates.
- Auto-promoting candidates into `LINEAGE_REGISTRY` or Chroma without operator action.

## Hard constraints (Hyperlex invariants)

| Rule | Mutation prediction |
|------|---------------------|
| Settled Brier only | Block always has `brier: null` |
| Phase 5 speculative | Same epistemic class as Phase 5 research |
| Offline first | Works under `HYPERLEX_OFFLINE=1` without LLM |
| Fail-open | LLM/vector failures never break analyze |
| Atomic terms | Predict per atom, not blended bags |

## Output schema

Attach under `analysis.mutation_prediction`:

```json
{
  "schema": "hyperlex.mutation_prediction.v1",
  "seed_term": "rizz",
  "family_id": "brainrot-aura",
  "family_operator": "irony_inversion",
  "candidates": [
    {
      "form": "rizzed",
      "operator": "derivational",
      "confidence": 0.42,
      "provenance": "SPECULATIVE",
      "source": "deterministic",
      "rationale": "past participle / verbing of seed"
    }
  ],
  "n_candidates": 1,
  "brier": null,
  "provenance": "SPECULATIVE",
  "note": "Next surface forms are speculative. Not calibrated probabilities / Brier."
}
```

### Candidate fields

| Field | Required | Notes |
|-------|----------|--------|
| `form` | yes | Proposed surface string (normalized display) |
| `operator` | yes | One of documented mutation operators (see below) |
| `confidence` | yes | Float in (0, 1), **SPECULATIVE** ranking weight only |
| `provenance` | yes | Always `SPECULATIVE` for v1 |
| `source` | yes | `deterministic` \| `llm` |
| `rationale` | yes | Short human reason |

### Operator vocabulary (align with docs/slang-lineages.md)

- `platform_compression` — shorten, vowel-drop, orthographic compression  
- `derivational` — -ed, -ing, -er, -y, -core, -maxxing, -pilled (family-aware)  
- `irony_inversion` — polarity / status flip patterns (e.g. negative X, X points)  
- `compound_phrase` — seed + family co-term compound  
- `sense_extension` — light domain reframe labels (kept rare offline)  
- `cross_family_borrowing` — only when multi-family evidence exists (optional, conservative)  
- `extra-grammatical` — residual rule bucket  

Do **not** invent operators outside this set in v1.

## Architecture

```text
detect_memetic_patterns / run_one
        │
        ├─ seed atoms (existing terms split)
        ├─ lineage match (existing)
        │
        └─ predict_mutations(seed, lineage, family_terms, ...)
                │
                ├─ deterministic_operator_engine  (always)
                ├─ optional enrich_mutations_llm   (if LLM on)
                └─ rank + cap → analysis.mutation_prediction
```

### New module

`src/hyperlex/analysis/mutation.py` (or `predict_mutations` colocated if tiny):

| Function | Role |
|----------|------|
| `predict_mutations(seed_term, *, family_id, family_terms, family_operator, max_candidates=8) -> dict` | Public API |
| `_deterministic_candidates(...)` | Rule engine |
| `_rank_and_cap(candidates, max_n)` | Dedupe, score, sort |
| `enrich_mutations_llm(...)` optional wrapper near `enrich_neologisms` | Fail-open |

### Integration points

1. **`detect_memetic_patterns`** — after lineage + neologisms, call `predict_mutations` for `primary_term` (and optionally each `seed_terms` atom with a compact multi-term note).
2. **Package export** — `from hyperlex import predict_mutations` (or `hyperlex.analysis.predict_mutations`).
3. **CLI** — thin subcommand `mutation-predict "rizz"` printing the same JSON; analyze/pipeline already carry the block.
4. **Demo** — offline `demo` naturally includes the block when analysis does.
5. **Docs** — glossary entry; reading-evidence claims matrix row; STATUS surface “mutation prediction (SPECULATIVE)”.

### Deterministic engine (v1 rules)

Apply only to **seed** (single atom string), with family terms as support:

| Operator | Rule sketch |
|----------|-------------|
| platform_compression | Vowel-drop if len≥4; duplicate-last-consonant slang forms sparingly; strip spaces for multiword seeds |
| derivational | Append family-aware suffixes from a fixed table: general `ed|ing|er|y`; internet `core|maxxing|pilled|posting`; status `points` |
| irony_inversion | Prefix/suffix templates: `negative {seed}`, `{seed} points`, `mid {seed}` when family is status/brainrot |
| compound_phrase | `{seed} {co}` / `{co} {seed}` for up to N highest-weight co-terms in family (exclude seed itself) |
| Filters | Drop empty; drop exact seed; drop forms already in family terms **or** mark them `already_attested: true` and down-rank; max length; ASCII-ish normalize |

**Confidence (SPECULATIVE ranking only):** base score per operator class + small bonus if co-term attested in family + penalty if already attested. Never interpret as probability of adoption.

### LLM enrich (optional)

- Gate: existing LLM enablement (`llm_enabled()` / env already used for neologisms).
- Prompt: seed, family_id, payload_note, existing deterministic candidates; ask for ≤5 JSON candidates with operators from the fixed vocabulary.
- Merge: dedupe by normalized form; LLM candidates never overwrite deterministic; total cap still `max_candidates`.
- Fail-open: any error → deterministic-only result with `llm_enrich: {applied: false, reason}`.

### Multi-term behavior

- **Primary:** predict for `analysis.primary_term`.
- **Optional:** if `multi_term` and ≤5 atoms, attach `per_term_mutations: [{seed_term, n_candidates, top_form}]` summary without exploding packet size; full candidates only for primary in v1 unless `HYPERLEX_MUTATION_ALL_ATOMS=1`.

## Ranking & caps

- Default `max_candidates = 8` (env `HYPERLEX_MUTATION_MAX` override, clamp 1–20).
- Dedupe casefold + strip.
- Sort by `confidence` desc, then deterministic before llm on ties.
- Always include `brier: null` at block root.

## Error handling

- Empty seed → `{ok: false, candidates: [], brier: null, error: "empty seed"}` or omit block.
- No lineage → still run deterministic rules with `family_id: null` and generic suffixes only.
- Never raise out of `detect_memetic_patterns`.

## Testing

| Test | Assert |
|------|--------|
| Unit deterministic | `predict_mutations("rizz", family_id="brainrot-aura", ...)` returns ≥1 candidate, all SPECULATIVE, brier null, no exact seed as top form |
| Offline analyze | `detect_memetic_patterns(..., mock)` includes `analysis.mutation_prediction` with schema v1 |
| Pipeline/demo | Offline demo JSON path still ok; mutation block present when analysis runs |
| LLM off | No network; `source` values are `deterministic` only |
| Cap | Never exceeds max_candidates |

Tests drive shipped functions (`predict_mutations`, analyze/demo CLI as appropriate), not re-implementations.

## Docs / surface

1. Glossary: **Mutation prediction** — speculative next surface forms; not Brier.  
2. Reading evidence: claims matrix row for mutation candidates.  
3. STATUS: Ready (SPECULATIVE).  
4. Optional later: map panel shows top 3 forms for `?term=` (not blocking v1).

## Implementation order (for writing-plans)

1. `predict_mutations` + deterministic engine + unit tests  
2. Wire into `detect_memetic_patterns`  
3. Export + CLI `mutation-predict`  
4. Docs (glossary, reading-evidence, STATUS)  
5. Demo/pipeline verification offline  

## Success criteria

- Offline `python3 scripts/hyperlex.py demo` (or analyze) shows `mutation_prediction` with next forms.  
- No candidate block ever sets a numeric `brier`.  
- CI offline tests green without chromadb/LLM.  

## Open decisions (locked for v1)

| Decision | Choice |
|----------|--------|
| Output kind | Next surface forms |
| Generation | Deterministic + optional LLM enrich |
| Attachment | `analysis.mutation_prediction` |
| Epistemics | SPECULATIVE / brier null |
| Settlement path | Out of scope |
