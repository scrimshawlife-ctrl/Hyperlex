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
| Failing tests in a full run — **class 1: env-cached mode** (22 on macOS, ~22 in CI) | A decision about import-time env caching | `scripts/shadow/hyperlexical/classification_v2.py:75` reads `HLX_V2_FORWARD_ONTOLOGY` **once at import** into a module constant. Twenty-five files under `tests/shadow/` set that variable at module level and rely on it; whichever file imports first fixes the value for the session. Measured directly: `pytest tests/shadow/test_classification_v2.py` alone → **21 passed**; add `tests/shadow/test_classification_v3_reserve.py` → **3 failed**. Neither file is wrong — the order is. **The count is stable per host** (three consecutive runs here: 26 / 26 / 26), because pytest's collection order is deterministic, so this is order-*dependent* and entirely reproducible. |
| Failing tests in a full run — **class 2: host detection** (4, macOS only) | Platform assumptions in the host-detection tests | `tests/test_p1_fail_closed.py` (2), `tests/test_memetic_memory.py` (1), `tests/test_claude_host.py` (1). These never appear in CI because CI runs ubuntu; they are visible only on a developer macOS host and are a different problem from class 1 — not order, but platform. |

Whole suite as measured: **26 failed, 1626 passed, 18 skipped** on macOS/Python 3.14; **23 failed, 1653 passed, 18 skipped** in CI (ubuntu). The 23-vs-26 gap is the four host-detection failures, not a difference in the class-1 count.

A blanket `tests/shadow/conftest.py` was written and **reverted**. It set the variable per test and reloaded the module, which is the right shape for class 1 — but an autouse fixture that *imports* `classification_v2` breaks `test_hyperlexical_shadow.py::test_no_hyperlex_or_abraxas_imports`, whose whole purpose is asserting that module is not imported. Measured: 26 failed / 1626 passed with the fixture, and the same 26 / 1626 without it on this host — so the fixture changed nothing, and the conflict is the reason it stays out. The class-1 fix belongs per-file (scope the variable to the file's own tests and reload), because the variable also affects tests outside `tests/shadow/` — confirmed the hard way when a conftest scoped to that directory moved failures in files outside it.

## Done

- Restored collection: one bare `import torch` had aborted collection for roughly **1650 tests**, making CI red
  on every push since 2026-09-30. Fixed by matching the `pytest.importorskip` idiom three sibling files already
  used. This converted "collection aborted, zero tests ran" into "1654 ran, 22 failed" — the badge is still red,
  but it now means something.
- Local `main` fast-forwarded to `origin/main`.
