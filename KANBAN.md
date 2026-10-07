# Kanban — Hyperlex

Board state as measured, not as remembered. Every item below was true on the date at the bottom.

| | Backlog | In progress | Blocked | Done |
|---|---|---|---|---|
| **Count** | 1 | 0 | 2 | 2 |

**Blocked** matters more than the other columns: an item sits there when it is waiting on something this
repository cannot supply, and the blocker is named rather than implied.

_Last reviewed: 2026-10-07._

## Backlog

- Decide the env-var read pattern: reload in tests, or stop caching at import. The failing tests below
  demonstrate the pattern either way.

## In progress

- Nothing.

## Blocked

| Item | Blocked on | Evidence |
|---|---|---|
| Failing tests in a full run — **class 1: vocabulary mode** (21 in the `test_classification_v2*` family, +1 guard) | An unidentified import-order coupling | The suite is **deterministic**: `26 failed, 1626 passed, 18 skipped`, identical across six runs. `tests/shadow/test_classification_v2.py` alone passes **21**; `tests/shadow/` as a directory fails **22**. The failures are vocabulary-shaped — `unknown_lineage` contract errors and family sets missing `social-status` / `approval-disapproval`, i.e. some run is using the *historical* vocabulary where forward mode is expected. **The mechanism is NOT identified.** Six hypotheses were tested and every one was falsified; see the table below before spending time on any of them. |
| Failing tests in a full run — **class 2: three real failures** | The Claude source-of-truth pin does not resolve in a plain checkout | `test_p1_fail_closed.py::test_claude_sot_pin_matches_this_tree` and `::test_doctor_emits_claude_sot_cleared` — `resolve_claude_sot_cleared(ROOT)` does not return `cleared is True` with `"pinned"` in the reason. Plus `test_claude_host.py::test_doctor_reports_claude_ok`. **A fourth, `test_memetic_memory.py`, is an install artifact**: it fails with `ModuleNotFoundError: No module named 'hyperlex'` and *passes* once `pip install -e ".[dev]"` has been run. In a scratch venv with the editable install: `3 failed, 55 passed`. |

Whole suite as measured: **26 failed, 1626 passed, 18 skipped** on macOS/Python 3.14. CI (ubuntu) reports **23 failed, 1653 passed** — the difference is not the class-1 count but how the platforms and this host's missing install distribute the non-shadow failures.

### Both failures, down to the assertion -- and a wrong revert corrected

The test `test_corrected_shortcut_diagnostic_conditions_on_gold` had **two** float-precision defects, and the
second was hidden behind the first: pytest stops at the first failing assertion, and this test asserts about
ten things in sequence. Fixing one moved the failure rather than clearing it.

**Defect 1 -- `none_surface_gap == 0.0` (line 625), fixed in `9e3b537`.** A difference of two means
(`classification_v2_surface.py:510`, from `_mean_probability` at `:462`). Both cells hold 0.13: 12 rows (atom
form) and 4 rows (prose form). On CPython <=3.11 `sum()` is a plain left-to-right accumulator, so a mean over
12 copies and a mean over 4 land one ULP apart -- `0.12999999999999998` vs `0.13` -- and the gap came out as
`2.7755575615628914e-17` instead of exactly `0.0`. Reproduced bit-for-bit before fixing:

    pre-3.12 naive sum()   atom=0.12999999999999998  prose=0.13  gap=2.7755575615628914e-17  (== 0.0 is False)
    math.fsum()            atom=0.13                 prose=0.13  gap=0.0

**Defect 2 -- `conditional_length_correlation["FAMILY_PRESENT"]["correlation"] == 1.0` (line 628), fixed in
`ad30a76`.** The same class in `pearson()`: naive `sum()` gives `0.9999999999999998` for perfectly collinear
input instead of `1.0`. Reproduced with the test's real data (6 atom rows at 1 word, 12 prose rows at 10 words):

    pre-3.12 naive sum()   correlation = 0.9999999999999998   == 1.0 ? False
    math.fsum()            correlation = 1.0                  == 1.0 ? True

**The correction.** `ad30a76` was reverted in `b444a40` on the reasoning that CI's count was unchanged --
"1 failed, 1675 passed, identical to before, so it fixed nothing". That inference was **wrong**. The count
cannot distinguish *which* assertion failed inside a single test; defect 1 was still failing and masking defect
2, so fixing defect 2 changed nothing visible. An unchanged pass/fail count is not evidence that a change was
inert when several assertions can fail in the same test. Both fixes are now in place together.

Neither fix touches an assertion. `fsum` makes the 0.0 and 1.0 claims true on every Python version rather than
widening them, which would have been loosening an assertion to make a version pass.

### Verified after the migration: no regression, and CI's one failure is pre-existing

Measured after the vocabulary-agnostic migration landed (`a758a83`):

| Environment | Result |
|---|---|
| Full clone + editable install, whole suite | **1652 passed, 18 skipped, 0 failed** |
| CI (ubuntu, `fetch-depth: 0`, installs) — 3.12 | **success** |
| CI — 3.10 and 3.11 | 1 failed, 1675 passed |
| CI on the pre-migration commit (`3aee5b0`) | **22 failed**, 1654 passed |

Three earlier claims about this repo were wrong and are corrected here:

1. **"The three Claude-SoT failures are real in CI."** They are not. They were an artifact of a **shallow local
   clone**: the pin commit `c9233c98` is not in a shallow object store, and `resolve_claude_sot_cleared` never
   consults GitHub by design, so it correctly cannot prove descent. With `git fetch --unshallow`, `git
   cat-file -e` finds the pin and `merge-base --is-ancestor` returns YES — the tests pass. CI already used
   `fetch-depth: 0` for exactly this reason. The workflow's comment says so: *"Default depth=1 hides the pin
   SHA."* The conclusion was drawn from a red badge rather than from the failing test names.
2. **"`test_memetic_memory` is a real failure."** It is an install artifact: `ModuleNotFoundError: hyperlex`
   without `pip install -e ".[dev]"`.
3. **The remaining CI failure is not a regression from the migration.** `test_corrected_shortcut_diagnostic_conditions_on_gold`
   appears **8 times in each of three earlier failing runs**, including the 2026-10-07T10:53 run taken before
   any of these changes. It is pre-existing.

**The one failure left, and the likely mechanism.** It fails on **3.10 and 3.11 only**, passing on 3.12 and on
3.14. One of its assertions requires `abs(correlation) < 1e-9` and another `== 1.0` exactly. Python **3.12
changed `sum()` to use Neumaier compensated summation for floats**, which changes the result of naive float
accumulation on precisely this kind of correlation computation. That is the most probable cause and it is
*inferred*, not measured — 3.10 and 3.11 are not available on this machine, so it cannot be confirmed here.

**Two fixes exist and neither is a drive-by.** Either the computation uses `math.fsum` so its precision is
version-independent and the 1e-9 claim survives, or the tolerance is widened — which would be *loosening an
assertion to make a version pass*, the pattern this repository's rules forbid. The first is principled and
unverifiable from here; the second is verifiable and wrong. That choice belongs to the author.

### CORRECTION: the elimination below is unsound, and the cause is now identified

An earlier version of this board claimed the failures do not depend on the vocabulary state. **That was
wrong.** The probe behind it read `FORWARD_ONTOLOGY` at the **end of the session** — after every test had
run — which is not the state the failing tests see when they execute. Measuring the wrong moment, then
concluding about the mechanism, produced a confident and false elimination.

**The identified cause, verified:**

| Evidence | Result |
|---|---|
| The six failing files, run **without** the three reloading files | **48 passed** |
| Those three reloading files | `test_classification_v2_family_retrieval.py:13-16`, `test_classification_v2_forward_hub_error_decomposition.py:13-16`, `test_classification_v2_family_retrieval_reserve_eval.py:13-16` — each sets `HLX_V2_FORWARD_ONTOLOGY=1` and calls `importlib.reload(v2)` **at module level during collection**, with no cleanup |
| One reloader plus one victim | **6 passed** — a single reloader is *not* sufficient, contrary to an earlier claim |

The three reloaders rebind `classification_v2.ACTIVE_FAMILY_VOCABULARY` in `sys.modules` from the historical
19-family tuple to the forward 18-family tuple, before the older files' tests run. Those older files
(`prototype`, `geometry_repair`, `max_anchor`, `separability_audit`, `mixed_remediation`, and part of
`test_classification_v2.py`) were written for 19 families and mostly hard-code it —
`assert len(...) == 19`, `loaded['anchors']['social-status']`, `n_anchors >= 19` — and were never updated when
the forward ontology arrived in `a912ab3` (Sep 29), which touched `classification_v2.py` and added
`test_classification_v2_forward_ontology.py` but none of them. `support_audit`
(`classification_v2.py:451`) then raises `unknown_lineage` for the two families that forward mode merges away.

**A per-module cleanup fixture does not fix this** — tried and measured: `23 failed` (one *worse*), because the
reloaders need forward mode while they run and the victims need historical, and the two are interleaved in
collection order. Restoring after one reloader breaks the next.

**The fix is the victims becoming vocabulary-agnostic**: replace hard-coded 19 with
`len(ACTIVE_FAMILY_VOCABULARY)`, look up `social-status` / `approval-disapproval` conditionally, and
parameterise expectations on the active vocabulary. That is a content migration across six files, and it is
this repository's work rather than a drive-by patch.

### Hypotheses tested and falsified — do not repeat these

Every one of these was falsified by measurement on one host, before and after, with the tree clean:

| Hypothesis | Refuting measurement |
|---|---|
| A `tests/shadow/conftest.py` that imports `classification_v2` and reloads it | `26 failed / 1626 passed` — identical to baseline. Also conflicts with `test_no_hyperlex_or_abraxas_imports` in principle, though that test fails in the baseline too. |
| The same fixture, reshaped to never import (reload only if already in `sys.modules`) | `26 / 26 / 26` — identical, three runs. |
| "The env constant cached at import is the mechanism" | Both fixtures above are inert, so the constant is not what the failing tests depend on. |
| "`test_classification_v2.py` + `test_classification_v3_reserve.py` → 3 failed" (recorded earlier in this board) | **Clean tree: `24 passed`.** The earlier reading was taken with one of the fixtures above present in the tree. The pair is fine. |
| "`test_hyperlexical_shadow.py` triggers it" | In that pair (`test_classification_v2.py` + `test_hyperlexical_shadow.py`) the v2 tests **passed**; the single failure was the guard test. The trigger was misread. |
| Adding `os.environ.setdefault("HLX_V2_FORWARD_ONTOLOGY", "1")` to `test_hyperlexical_shadow.py` — the idiom three source modules already use | `26 / 26 / 26` — identical. Reverted; the file is byte-identical to its committed state. |
| Restoring the env value in `test_classification_v2_forward_ontology.py`'s `finally` blocks instead of blindly popping (a real isolation defect, and module state *is* corrected by it) | Module state after a run becomes **forward** instead of historical — and the result is still **22 failed**. The state is not what these tests depend on. Reverted. |

Pair probes, all on a clean tree, all **passing**: `+ v2_prototype` 29 passed · `+ v5_stage_a` 30 passed ·
`+ v3_reserve` 24 passed · `+ hyperlexical_shadow` 33 passed, 1 failed (the guard). No pair reproduces the
class, so it needs a larger combination or a file further along the collection order.

### What the probe ruled out

A probe that runs the shadow suite in-process and then reads the module state produced the single most useful
fact in this investigation:

| State | `FORWARD_ONTOLOGY` | `VOCABULARY_ID` | Result |
|---|---|---|---|
| After `--collect-only` | True | forward (19 families) | — |
| After a real run, **before** any fix | **False** | `hyperlex.active_families.v1` | 22 failed |
| After a real run, with the env-restore fix below | **True** | forward (18 families) | **22 failed — unchanged** |

Twenty-one tests fail whether the module ends up forward or historical. **The failures do not depend on the
vocabulary state**, which rules out the whole ontology family of explanations — import caching, `setdefault`
ordering, reload behaviour, and the `finally`-block deregistration in
`test_classification_v2_forward_ontology.py`. That file's cleanup *is* a genuine isolation defect (it pops a
session variable and never restores it), and fixing it does move the module state — but it moves nothing that
these tests depend on.

That is a negative result and it is worth more than the seven wrong hypotheses above: a whole class of
approaches is now known to be wasted effort.

The remaining lead, not yet tested: the failing tests' own names describe **nineteen** families
(`test_max_over_anchor_scoring_is_deterministic_and_covers_nineteen_families`), which is the *historical*
size, while the forward vocabulary has 18 and the observed mismatches are family-set diffs. That points at
stale fixture data rather than module state — the same shape as Trutina's stale contract test. It is a lead,
not a finding, and it is the next thing worth measuring.

### The method that works, and the next concrete step

Reading failing test **names** and inferring a cause from them produced four wrong conclusions here. Holding the
environment constant and **pairing one file against another** is what produced real information; that is how
the four pairs above were measured.

Unidentified mechanisms are best settled by data rather than hypothesis: print the frozen values at the end of
collection — `classification_v2.FORWARD_ONTOLOGY` and `classification_v2.VOCABULARY_ID` after
`pytest tests/shadow/ --collect-only` — which names the import that froze them, deterministically. That is the
next step worth taking, and it does not require guessing.

## Done

- Restored collection: one bare `import torch` had aborted collection for roughly **1650 tests**, making CI red
  on every push since 2026-09-30. Fixed by matching the `pytest.importorskip` idiom three sibling files already
  used. This converted "collection aborted, zero tests ran" into "1654 ran, 22 failed" — the badge is still red,
  but it now means something.
- Local `main` fast-forwarded to `origin/main`.
