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
