# Hyperlexical model product — completion plan

**Status:** DRAFT (operator review) · **Date:** 2026-09-23  
**Naming:** repo **Hyperlex** = transitional shell. Public products: **Hyperlexical** (this plan) and **ne0l0gist** (ingest). Hermes skill ≠ Hyperlexical.  
**Hard locks (unchanged):** `name_gate=false` until Danny yes · no Hub upload · no invented OBSERVED · upsample freeze **11+** · no `SECOND_SLOT=4` · schemes `positional|type_slot` only · Brier `null` on every 007 packet.

This plan turns Spec 007 from a SHADOW Spark climb into a shippable Hyperlexical product. It does **not** flip `name_gate`.

---

## Current honest state (2026-09-23)

| Layer | State |
|-------|--------|
| Hermes skill (`SKILL.md`, CLI, `src/hyperlex/`) | **Ready** (v0.4.0 operator surface; pyproject may read 1.6.0 — hygiene debt) |
| Spec 007 shadow train/eval | **Ready enough to climb** — BEST=`seed-morph65`, E2 PASS on trained trunk |
| Force fair | **1.0** n=164 (classic promote wall) |
| soft_ceiling | **ARMED** — at fair 1.0, promote only if live broad OBSERVED **>** PRIOR morph65 (**0.88671875** n=256) + E2 |
| Gold path | morph78 acquire + residual reprobe → **empty gold**; `authorize val-settle` → **CANCELLED_EMPTY_GOLD** |
| Hyperlexical name / Hub / T13 promote into `src/hyperlex/` | **Blocked** |

Verdict: skill is production-ready as a Hermes skill. The **Hyperlexical model product** is not — name wall, Hub, packaging, and live-gold path still open.

---

## Product definition (what “complete” means)

Hyperlexical is complete when all of the following are true:

1. **Train artifact** — pinned BEST checkpoint on Spark with receipts (fair surface + E2 + soft_ceiling decide if armed).
2. **Eval gates** — E2 PASS on the pin; stub FAIL still expected; seed smoke ≠ T1.
3. **Dataset honesty** — OBSERVED only from settled/authorized gold; no invent; force-train / hard-atoms are operator JSONL, not SoT.
4. **Name** — Danny explicit yes flips `name_gate`; card may then be called Hyperlexical (not before).
5. **Publish** — Hub upload is a **named** operator action after name_gate; weights stay out of git until then.
6. **Operator surface** — infer CLI + packet schema + model card shipped; optional later T13 promote into `src/hyperlex/` (separate sentence).

Until (4), the artifact stays `hyperlex-encoder-*`.

---

## Workstreams

### A. Climb / gold (Spark · soft_ceiling)

| Step | Action | Exit |
|------|--------|------|
| A1 | Idle: do **not** re-burn empty settle / empty acquire | HOLD until named phrases |
| A2 | Operator `authorize morph78 …` or `authorize val-settle` **listing phrases**, **or** acquire that clears Jev `force_expand_safe` | Non-empty authorize card |
| A3 | Val-settle → force tip expand → fair baseline on new tip | Fair surface receipt |
| A4 | Train next morph under soft_ceiling; decide via `gate_soft_ceiling_decide.py` | PROMOTE or REJECT_VS_BEST |
| A5 | If PROMOTE: update BEST pin + PRIOR broad for next soft_ceiling compare | New BEST held |

Constraints: upsample freeze 11+; no SECOND_SLOT=4; Qwen stopped unless re-enabled.

### B. Engineering hygiene (main / tip)

| Step | Action | Exit |
|------|--------|------|
| B1 | Restore `apply_unbind_force_train` + tests on tip (#99 CI) | validate green |
| B2 | Align `VERSION` ↔ `pyproject.toml` version (0.4.0 vs 1.6.0 skew) | Single source of truth |
| B3 | Drop / quarantine stale probe files and truncated CHANGELOG placeholders on tip | Docs match receipts |
| B4 | Keep force-train path env-only; val move ⇒ fair re-baseline | Receipt stats present |

### C. Product packaging (post–name_gate, separate authorize)

| Step | Action | Exit |
|------|--------|------|
| C1 | Finalize `model-card.draft.md` / `hf-package/README.md` with pin metrics | Card ready, still no upload |
| C2 | Operator Hub upload sentence | Weights + card on Hub |
| C3 | Optional T13: promote shadow package into `src/hyperlex/` | Separate PR + tests |
| C4 | Flip `name_gate` only on Danny yes | Public Hyperlexical name |

### D. Adjacent Hyperlex PRs (skill track — not model name)

| PR | Role | Handle |
|----|------|--------|
| **#100** pytrends evidence | Skill route evidence | CI green / mergeable. Recommend merge after operator live `analyze --route trends` check. Independent of Hyperlexical name. |
| **#99** Spec 007 tip docs + climb | Model path | Stay **draft** until CI green + operator merge yes. Large docs+receipts surface. |
| **#95** HYPERLEX-Q1 | Epistemic interchange | Stay **draft**; rebase onto current `main`; remains UNQUALIFIED / pairwise BLOCKED. Spec-only. |

Do **not** merge any of these without explicit operator yes.

---

## Sequencing (recommended)

```
B1 (CI fix) ──► #100 operator check + merge authorize
       │
       ├──► A2–A5 climb under soft_ceiling (needs gold)
       │
       ├──► B2–B3 hygiene on tip / follow-up PR
       │
       └──► #95 rebase only (no qualify claim)

When climb + packaging ready:
  Danny name_gate yes ──► C1–C2 Hub ──► optional C3 T13
```

Climb (A) and skill PR #100 can proceed in parallel. Name/Hub (C) never parallel-jumps ahead of Danny yes.

---

## Explicit non-goals

- Inventing OBSERVED fillers or empty-gold settles
- Hub upload or `name_gate` flip without Danny
- Warm-clone spam / upsample 11+ / SECOND_SLOT=4
- Treating Hermes skill readiness as Hyperlexical product readiness
- Calling stub or seed smoke a T1 pass

---

## Definition of done (product)

- [ ] soft_ceiling path either PROMOTE’s a new BEST or operator closes climb with held morph65
- [ ] Tip CI green; force-train API present; version skew fixed
- [ ] Model card filled from live pin metrics
- [ ] Danny `name_gate` yes (or explicit hold)
- [ ] Hub upload done **or** explicit “no Hub this cycle”
- [ ] STATUS / ROADMAP / milestones updated to match reality (no stale “E2 Spark-blocked” once trained E2 PASS is the pin)

---

## Pointers

- Climb next: root `NEXT_MOVES_007.md`
- Soft_ceiling receipts: `receipts/20260923-authorize-gate-soft-ceiling.md`, `receipts/gate-soft-ceiling-20260923/`
- Empty gold: `receipts/20260923-authorize-val-settle-cancelled-empty-gold.md`
- Gates: `milestones.md`, `spec.md`, `dual-use-gate.md`
