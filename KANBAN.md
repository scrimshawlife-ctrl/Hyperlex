# Kanban — Hyperlex

Board state as measured, not as remembered. Every item below was true on the date at the bottom.

| | Backlog | In progress | Blocked | Done |
|---|---|---|---|---|
| **Count** | 1 | 0 | 1 | 2 |

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
| Failing tests in a full run (count varies: 22-23) | A decision about import-time env caching | CI run `37679298734` on `7de56bf`: **23 failed, 1653 passed, 18 skipped** in 55.6s. `test_classification_v2.py` alone: **21 passed**. Add `test_classification_v3_reserve.py` (sets `HLX_V2_FORWARD_ONTOLOGY=1` at import): **3 failed**. `classification_v2.py:75` reads the variable once at import into a module constant, so whichever file loads first fixes it for the session. The repository's own `test_classification_v2_forward_ontology.py` already demonstrates the reload-and-restore pattern. |

Neither file is wrong in isolation — the order is. The fix is a call about caching, which belongs to this
repository's author.

The count moving between 22 and 23 across runs is itself evidence for the diagnosis: which tests fail depends
on which file loads first, so the number is not stable and the failures are not independent. The same run also
shows `test_hyperlexical_shadow.py` asserting `'torch' not in {...}` and failing — the module set differs for
the same reason, since `pytest.importorskip("torch")` registers the name it tried to import.

## Done

- Restored collection: one bare `import torch` had aborted collection for roughly **1650 tests**, making CI red
  on every push since 2026-09-30. Fixed by matching the `pytest.importorskip` idiom three sibling files already
  used. This converted "collection aborted, zero tests ran" into "1654 ran, 22 failed" — the badge is still red,
  but it now means something.
- Local `main` fast-forwarded to `origin/main`.
