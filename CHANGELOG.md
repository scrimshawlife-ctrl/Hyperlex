# Changelog

## Unreleased

- **Trained inference (Spec 007):** `hyperlexical.infer --model-dir` runs a local
  checkpoint (lazy torch, local trunk, fail-closed exit 2) and emits a
  `MODEL_EMBEDDING` inference packet; only the approved pin carries
  `hyperlex-structure-149m`. Default CLI stays the offline stub.

- **Card rename (Spec 007):** Hub card `hyperlex-structure-149m` for `seed-morph78`.
  `name_gate.py` pins the approved checkpoint; `eval_unbind` sets `name_gate`
  true only for a trunk-forward eval of that pin; eval schema field is boolean.
  Training contract and HF dump writer unchanged (new checkpoints stay unnamed).

- **`name_gate` yes (`seed-morph78`):** Danny `flip name_gate` — pin may be called
  **Hyperlexical** (amendment A6; receipt `specs/007-hyperlexical-model/receipts/20260924-name-gate-yes-morph78.md`). Card IDs, packet/schema
  field, Hub, and T13 unchanged.

- **Naming persistence lock:** `docs/NAMING.md` + Notion Naming lock page +
  Public Claims CLAIM-HLX-NAME-001/002/003. Operator Hub / Spine Owner /
  Core Model Spine updated. Org mirror stays lag (do not train from it).
  Does **not** flip Hyperlexical `name_gate`.

- **Operator name ne0l0gist (ingest):** Danny `name neologist as in repo` —
  public ingest product **`ne0l0gist`** (repo spelling). Receipt
  `specs/007-hyperlexical-model/receipts/20260924-name-ne0l0gist-as-in-repo.md`.
  Does **not** flip Hyperlexical `name_gate`.

- **Hygiene + name-gate plan:** `pyproject.toml` version aligned to `VERSION`
  **0.4.0**; ROADMAP trained-E2 line (no stale Spark-blocked checkbox); drop tracked
  `__pycache__`, tip probe, `.tmp` restore junk. Draft
  `specs/007-hyperlexical-model/NAME-GATE-AND-NAMED-PHRASES.md` (morph77 HOLD
  phrases already settled; morph78/reprobe empty; Danny yes still required).
  Does not flip `name_gate`.

- **Spec 007 tip CI: restore unbind force-train API:** `loop.py` imported
  `apply_unbind_force_train` but tip `unbind_recipe.py` lacked the helpers
  (`HYPERLEX_UNBIND_FORCE_TRAIN_PATH`, resolve/load/apply). Restored + tests
  `tests/shadow/test_hyperlexical_unbind_force_train.py`.

- **Spec 007 Hyperlexical product plan (draft):**
  `specs/007-hyperlexical-model/HYPERLEXICAL-PRODUCT-PLAN.md` — climb under
  soft_ceiling, engineering hygiene, name_gate/Hub packaging, PR triage
  (#100 / #99 / #95). Does not flip `name_gate`.

- **Spec 007 morph74 IN FLIGHT (SoT clean + acquire-settle):** quarantined **57**
  INFERRED wiki/scaffolding from Spark SoT; durable `reject_wiki_scaffolding_text`.
  Settle `to the moon` + `elo hell` → force/hard **217→221 / 258→262**. Warm
  morph65 + `INIT_EXPAND_VOCAB=1`. Fair **0.9880239520958084** n=167. Container
  `hlx-train-morph74-1790179734`. Receipts:
  `receipts/20260923-sot-clean-acquire-civilian.md`,
  `receipts/20260923-morph74-acquire-settle-inflight.md`.

- **Spec 007 morph73 REJECT_VS_BEST:** expand-warm tied fair **0.9649122807017544**
  n=171 → REJECT. Residual AUTHORIZE=0 scaffolding — cleaned for morph74.

- **Earlier Unreleased Spec 007 / docs / P1 entries:** morph72→morph56 ladder and
  0.4.0… history preserved in branch history / operator workspace `CHANGELOG.md`.
