# Contributing

## The rules that matter here

- **Settled Brier only.** A claim about predictive performance ships with its calibration, or it does not
  ship.
- **Optional imports use `pytest.importorskip`.** One bare `import torch` at module level aborted collection
  for roughly 1650 tests and kept CI red for a week. Three sibling files already used the guarding idiom.
- **Tests must not depend on import order.** `classification_v2.py` reads an environment variable once at
  import into a module constant, so whichever test file loads first fixes the value for the session; reload
  and restore rather than relying on it.
