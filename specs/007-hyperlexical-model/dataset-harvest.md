# Hyperlex Spec 007 T1 — civilian dataset plan

## Status and decision

U2 is now present on branch `007-hyperlexical-model`. Its first executable export is a seed bundle, not the T1 name-gate dataset. This plan governs the next harvest and U2 hardening work without downloading ModernBERT.

Current U2 verification after fixing its Python keyword/annotated-assignment loading defects: 183 rows total; 138 classify, 45 unbind, 21 negatives, and 8 dialect rows. The remaining name-gate gaps are therefore 1,862 classify, 155 unbind, and 179 negatives.

## 1. Ranked sources and harvest list

| Rank | Source | Source epistemic class | License / rights | Locator | Gates | Harvest action |
|---:|---|---|---|---|---|---|
| 1 | Operator-exported settled Hyperlex ledger copies and civilian Notion receipts | **OBSERVED** only after an explicit operator settlement | Operator-owned/authorized; record the grant per export | Notion page [8], then immutable export path | E1, E2, E6 | Highest-value source. Export short atoms and settled labels. The current Notion page contains status only, so current usable row count is **0**. |
| 2 | Hyperlex golden receipts | **OBSERVED** under the 007 prompt, with a required reconciliation note because archived copies still say lineage `INFERRED` | Repository MIT; audit third-party origins before redistribution | `examples/receipts/golden/` on branch [2] | E1, negatives | U2 currently exports matched terms plus aggregate receipt queries. Before a name-gate freeze, do not treat split-out aggregate atoms as independently OBSERVED unless an operator settles them. |
| 3 | Spec 004 recoverable-structure fixtures | **OBSERVED** fixture gold | Repository MIT | `scripts/shadow/recoverable_structure/fixtures.py` [2] | E2 | U2 materializes 24 spans under both allowed schemes: 48 raw rows and 45 after exact dedupe. Preserve case and add civilian annotations rather than inflating duplicates. |
| 4 | 2026 backfill packs | **MIXED: 30 OBSERVED, 37 INFERRED** | Repository MIT; preserve each row’s provenance | `data/backfill/2026/*.json` [2] | E1; E6 candidates | Export all 67 atoms. Never upgrade the 37 weak labels. Family mix is highly skewed: 39/67 are `brainrot-aura`; use sampling weights, not duplication. |
|| 4.5 | Moltbook agent discourse (memory, agents, ai submolts + jargon threads) | **MIXED: mostly INFERRED weak labels from our classifiers, some OBSERVED via high-karma settled threads** | Repository MIT (our distillation); original platform terms apply | `out/batch_moltbook_memetics.json`, `data/agent_memetics/`, live via moltbook_heartbeat | E1 (weak), E6 (agent-native), new typology candidates | Highest-signal source for **ai-native** lineage + new typology "memory", "context_friction", "provenance". Use `detect_memetic_memory_patterns` + `compute_memetic_efficiency_score` as weak labelers. Export atoms with memory_tiers as roles/fillers where they bind structure. Continue growing `seed_examples.jsonl` (currently 25). Map high `efficiency_score` + `load_bearing` to stage `hyperstition_ish`. |
| 5 | Sanitized archive receipts not already represented by golden receipt surfaces | **INFERRED** | Repository MIT; sanitized archive only | `docs/archive/**/receipts/*.json` [2] | E1 weak, stage weak | Export 16 additional unique surfaces. Do not use Phase 5 fields. Stage remains INFERRED. |
| 6 | Static `LINEAGE_REGISTRY` atoms not covered by backfill | **INFERRED / HOLD until U2 assigns row provenance** | Repository MIT | `src/hyperlex/analysis/__init__.py` [2] | E1 weak | Inventory shows 107 unique registry atoms, 66 overlapping backfill, 41 registry-only, plus one backfill-only atom. Resolve the cross-family `skill issue` collision before export; never duplicate it across splits or labels. |
| 7 | English Wiktionary via Kaikki JSONL | Source text/tags **OBSERVED**; derived lineage/typology/stage **INFERRED** until operator-settled | Wiktionary text is dual-licensed CC BY-SA 4.0 and GFDL [3]; Kaikki distributes under the same licenses [4] | Kaikki English JSONL [4] | E1, E6 | Filter English entries/senses tagged slang, informal, vulgar, dialectal, or regional. Keep lemma, form, tags, revision/dump date, and attribution. Gloss may support adjudication but is not unbind gold. |
| 8 | Common Voice Spontaneous Speech 4.0 English transcripts | Utterance/metadata **OBSERVED**; task labels **INFERRED** until settled | CC0-1.0; retain the dataset’s no-speaker-identification condition [5] | Mozilla Data Collective [5] | E6, negatives, E1 `none` | Use transcript text only—no audio pipeline or ASR recipes. Select short, validated civilian utterances; strip speaker identifiers; operator-settle `none` and E6 tags. |
| 9 | Project Gutenberg works explicitly unrestricted in the US | Source text **OBSERVED**; negative label **INFERRED** until settled | Individual works generally unrestricted under US copyright, with Project Gutenberg trademark/redistribution terms and jurisdiction caveats [6] | Project Gutenberg license [6] | Negatives | Secondary negative source only. Select named works with an unrestricted notice, remove headers/boilerplate, keep work ID, and sample short ordinary-prose spans. |

### Harvest quotas

- **Classify:** retain the 138-row U2 seed export, then harvest at least **2,500** candidates to survive dedupe, restriction filtering, license filtering, and operator review. Stop only when the accepted lexical-grouped pool reaches 2,000 and each of the ten closed labels has held-out support.
- **Unbind:** retain the 45 unique U2 scheme rows, then annotate at least **100 new short civilian atoms under both schemes** (200 scheme rows). This clears the 155-row minimum gap with margin and gives E2 non-symbolic civilian material.
- **Negatives:** retain the 21 U2 negatives, harvest at least 300 short Common Voice transcript spans and 100 Gutenberg spans, and accept at least 179 new unique negatives after review.
- **Dialect/E6:** U2 exports eight OBSERVED seed rows, but the spec gives no numeric name-gate. Adopt an explicit operational floor of **200 OBSERVED unique atoms**, with at least 50 examples carrying each of `dialect`, `informal`, `vulgar`, and `identity_routing` provenance tags; tags may overlap. This floor is a proposal, not a normative 007 count.

## 2. Target hardened JSONL row schema

U2 currently emits the requested top-level fields plus `task`, uses `val` as the validation split, and stores provenance as a compact string. The schema below is the harvest target: it expands provenance so source class, license evidence, lexical grouping, and settlement can be audited. Adopting it is a follow-on schema change, not a description of the current seed export.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "hyperlex.hyperlexical.dataset-row.v0.1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "text", "split", "lineage", "typology", "stage", "roles",
    "fillers", "role_scheme", "provenance", "class", "license"
  ],
  "properties": {
    "text": {"type": ["string", "null"], "minLength": 1, "maxLength": 256},
    "split": {"enum": ["train", "val", "test", "reject"]},
    "lineage": {
      "enum": [
        "betting-sharp", "crypto-degen", "ai-native", "brainrot-aura",
        "kinship-address", "political-status", "gaming-meta",
        "workplace-corp", "ytd_leaf", "none"
      ]
    },
    "typology": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "enum": [
          "tribal", "compression", "irony_shield", "status",
          "hook", "ritual", "camouflage"
        ]
      }
    },
    "stage": {
      "type": ["string", "null"],
      "enum": ["noise", "circulating", "contested", "hyperstition_ish", null]
    },
    "roles": {"type": "array", "items": {"type": "string"}},
    "fillers": {"type": "array", "items": {"type": "string"}},
    "role_scheme": {
      "type": ["string", "null"],
      "enum": ["positional", "type_slot", null]
    },
    "provenance": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "source_id", "locator", "source_class", "label_method",
        "surface_sha256", "lexical_group", "license_evidence"
      ],
      "properties": {
        "source_id": {"type": "string", "minLength": 1},
        "locator": {"type": "string", "minLength": 1},
        "source_class": {"enum": ["OBSERVED", "INFERRED", "SPECULATIVE"]},
        "label_method": {"enum": ["operator_settled", "fixture", "detector", "dictionary_tag", "negative_review", "rejected"]},
        "surface_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "lexical_group": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "license_evidence": {"type": "string", "minLength": 1},
        "source_revision": {"type": ["string", "null"]},
        "observed_at": {"type": ["string", "null"], "format": "date-time"},
        "settlement_id": {"type": ["string", "null"]},
        "e6_tags": {
          "type": "array",
          "uniqueItems": true,
          "items": {"enum": ["dialect", "informal", "vulgar", "identity_routing"]}
        }
      }
    },
    "class": {"enum": ["OBSERVED", "INFERRED", "SPECULATIVE", "REJECTED"]},
    "license": {"type": "string", "minLength": 1}
  },
  "allOf": [
    {
      "if": {"properties": {"role_scheme": {"enum": ["positional", "type_slot"]}}},
      "then": {
        "properties": {
          "roles": {"minItems": 1},
          "fillers": {"minItems": 1}
        }
      },
      "else": {
        "properties": {
          "roles": {"maxItems": 0},
          "fillers": {"maxItems": 0}
        }
      }
    },
    {
      "if": {"properties": {"split": {"const": "reject"}}},
      "then": {
        "properties": {
          "text": {"type": "null"},
          "class": {"const": "REJECTED"}
        }
      },
      "else": {
        "properties": {
          "text": {"type": "string", "minLength": 1},
          "class": {"enum": ["OBSERVED", "INFERRED"]}
        }
      }
    }
  ]
}
```

Exporter invariants:

1. A third `role_scheme` aborts the row; it is never coerced.
2. `stage` is always a task label with INFERRED epistemic status even when the source row is OBSERVED. U2 should record this in its task manifest; `class=OBSERVED` must not imply an OBSERVED stage.
3. Restricted detection runs before any surface write. A restricted row uses `split=reject`, `text=null`, `class=REJECTED`, and only `provenance.surface_sha256`; it is never passed to a training loader.
4. Keep source case in `text`, `roles`, and `fillers`. Normalization is only for dedupe/grouping.
5. Typology values from old receipts do not match the new seven-label vocabulary. Do not auto-map them as gold; map by deterministic rules as INFERRED or send to operator review.

## 3. Count gap versus the T1 name-gate

Counts are from a real U2 export on branch head `f55b035421ecd40cb3c4861c9833666162d2ae1d`, before this document/fix commit [1].

| Quota | Existing raw evidence | Gate-countable after exact dedupe | Gap | Notes |
|---|---:|---:|---:|---|
| Classify, 2,000 gold+weak | U2 seed exporter | **138** | **1,862** | Includes registry, golden-receipt, dialect, and negative rows; it does not yet harvest backfill or archive sources. Labels require the provenance hardening above before name-gate freeze. |
| Unbind, 200 pairs | 24 fixture spans × 2 schemes = 48 raw | **45** | **155** | Count one row per unique `(text, role_scheme, lineage)`. Keep raw duplicates for baseline replay, not for the name-gate. |
| Negatives, 200 | U2 ordinary-prose seed set plus deduplicated `none` rows | **21** | **179** | These rows also participate in classify; quotas are reported independently. |
| Dialect slice | U2 E6 seeds | **8 OBSERVED seeds** | **Normative gap undefined** | 007 requires a dialect slice but gives no number. Proposed operational floor: 200 OBSERVED, leaving 192 against that non-normative floor. |

Additional inventory:

- Eight repository families are exactly `betting-sharp`, `crypto-degen`, `ai-native`, `brainrot-aura`, `kinship-address`, `political-status`, `gaming-meta`, and `workplace-corp`; the model adds only `ytd_leaf` and `none`.
- Registry: 108 raw entries, 107 unique atoms. `skill issue` is assigned to two families and must be adjudicated once.
- Backfill: 67 unique atoms; 66 overlap the registry, one does not. Provenance is 30 OBSERVED / 37 INFERRED.
- Archive: 50 files collapse to 25 unique receipt surfaces; 9 match golden surfaces, leaving 16 additional INFERRED rows.
- U2 emits closed-vocabulary typology from a hard-coded family map and currently marks every exported row OBSERVED. Before the name-gate, provenance hardening must keep derived typology and stage labels INFERRED unless separately operator-settled.
- There is no current `ytd_leaf` row. U2 contributes eight OBSERVED dialect seed rows; broader E6 provenance remains to be harvested.

## 4. Lexical hash split with no lemma leakage

1. Preserve original `text` and case for training output.
2. Build a separate comparison form using Unicode NFKC, Unicode case-folding, whitespace collapse, and punctuation normalization.
3. Obtain lemmas/variant links from the source when available. For repository slang, maintain an operator-reviewed alias table. Never infer an unreviewed family label from morphology.
4. Build transitive lexical components: connect rows sharing a source lemma, normalized atom, explicit alias, or inflection link. Multiword atoms stay atomic. This groups variants before splitting.
5. Set `lexical_group = sha256("hyperlex-lex-v0.1\0" + sorted(component_member_ids))`.
6. Assign the entire component by `uint64(sha256("split-v0.1\0" + lexical_group)[:8]) % 100`: `0–79=train`, `80–89=val`, `90–99=test`.
7. Deduplicate within components before counting. Never rebalance by moving individual rows; if balancing is needed, move whole components using a versioned split-salt and regenerate every split.
8. Fit label weights, thresholds, typology mappings, and stage cut-points on train only. Val/test lexical groups remain sealed.
9. Apply the official ModernBERT BPE only after split assignment. A later tokenizer stage must use a locally cached pinned tokenizer with `local_files_only=True`, record revision and tokenizer-file hashes, and abort tokenization if the cache is absent. It must not download weights or tokenizer files.
10. Reject or manually settle the cross-family registry collision before final split generation.

## 5. REJECTED / HELD sources

No rejected content is quoted.

| Source | Epistemic class | Reason |
|---|---|---|
| Wu/Sun LLM-generated slang datasets | **SPECULATIVE** | Explicitly prohibited synthetic slang; not civilian OBSERVED evidence. |
| TimesFM and Hyperlex Phase 5 outputs | **SPECULATIVE** | Forecast/simulation artifacts, not lexical truth or gold. |
| HyperLex-2016 graded lexical entailment | **OBSERVED but OUT OF SCOPE** | Reserved for Spec 006 IsA; opening it would violate the 007 boundary. |
| Restricted how-to, jailbreak-wrap, attack-payload, and ASR-recipe corpora | **REJECTED** | Prohibited dual-use material; any encountered surface is redacted to SHA-256 only. |
| Urban Dictionary API/bulk corpus without an executed license | **HELD / license status unresolved** | Urban Dictionary offers corpus licensing separately [7]; API availability is not a training-data license. If licensed later, gloss remains adjudication evidence only, never unbind gold. |
| GUM / UD English-GUM for a commercial-capable T1 | **OBSERVED but HELD** | Current treebank license is CC BY-NC-SA 4.0; use only if the operator explicitly accepts a noncommercial/share-alike artifact. |
| Reddit, X, OpenSubtitles, and random web slang dumps | **INFERRED / HELD** | Redistribution rights, consent, provenance, and stable licensing are insufficient for the default harvest. |
| Static registry rows without row-level provenance | **INFERRED / HELD** | Useful inventory but not exportable until U2 attaches source, label method, and license evidence. |

## Verification

- Offline stub command returned packet schema `hyperlex.hyperlexical.inference.v0.1`, `brier: null`, `forecast_eligible: false`, and routes `form`/`lexical`.
- U1 + U2 shadow tests: **15 passed, 1 skipped**.
- Full repository suite: **327 passed, 6 skipped, 16 subtests passed**.
- U2 export executed successfully: **183 total; 138 classify; 45 unbind; 21 negatives; 8 dialect**; SHA-256 `da9c368425f29ed5f67908d14d4efd898b9a51be7b833c110cac9e84e2b7faa7`.
- AST import audit found **0** Torch, Transformers/Hub, or Abraxas imports in `scripts/shadow/hyperlexical/` and its shadow test.
- PR #19 is open, mergeable, and all three Python validation checks are successful [1].

## Sources

[1] https://github.com/scrimshawlife-ctrl/Hyperlex/pull/19 — Hyperlex PR 19
[2] https://github.com/scrimshawlife-ctrl/Hyperlex/tree/007-hyperlexical-model — Hyperlex 007 branch
[3] https://en.wiktionary.org/wiki/Wiktionary:Copyrights — Wiktionary copyrights
[4] https://kaikki.org/dictionary/index.html — Kaikki machine-readable Wiktionary data
[5] https://mozilladatacollective.com/datasets/cmqialpeo0077nr077xqdqo0j — Common Voice Spontaneous Speech 4.0 English
[6] https://www.gutenberg.org/policy/license.html — Project Gutenberg license
[7] https://urbandictionary.biz/data — Urban Dictionary corpus licensing
[8] https://app.notion.com/p/3d73e8ba2f5c81248145ccaecc4a83d1 — Hyperlex 007 Notion status page
### Moltbook integration (added via current continuation)
- Source: Moltbook agent discourse via `out/batch_moltbook_memetics.json` + `data/agent_memetics/seed_examples.jsonl` (25+ seeds) + live `moltbook_heartbeat.py`
- Tooling: `scripts/moltbook_to_hyperlexical.py` produces `dataset_row.v0.1` compatible rows.
- Mapping:
  - lineage: "ai-native"
  - typology: "compression" (from load_bearing), "memory_<tier>", "context_<technique>"
  - stage: high `efficiency_score` → "hyperstition_ish"
  - roles/fillers: memory_tiers + context_loss_technique
  - provenance: includes efficiency, compression, source post_id
- Action: Run the exporter on fresh batches. Treat as high-value for ai-native + new "memory" typology. Continue curation to increase volume.
