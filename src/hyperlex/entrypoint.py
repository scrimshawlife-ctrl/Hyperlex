"""Console-script router: init/uninstall-skill vs operator CLI."""
from __future__ import annotations

import sys
from typing import List, Optional


def _moltbook_memory_cli(argv: List[str]) -> int:
    """Additive `--memory` / `--source moltbook` path (SKILL.md). Not API_V1."""
    import argparse

    from hyperlex import detect_memetic_patterns

    p = argparse.ArgumentParser(prog="hyperlex")
    p.add_argument("--query", default="agent memory context provenance")
    p.add_argument("--source", default="moltbook")
    p.add_argument("--memory", action="store_true")
    p.add_argument("--export-hyperlexical", action="store_true")
    args, _unknown = p.parse_known_args(argv)
    result = detect_memetic_patterns(
        query=args.query,
        ingest_source=args.source,
        use_structured_ingest=False,
        validate=False,
    )
    analysis = result.get("analysis") or {}
    mm = analysis.get("memetic_memory") or {}
    eff = result.get("memetic_efficiency") or analysis.get("memetic_efficiency") or {}
    print("Memory tiers:", mm.get("memory_tiers"))
    print("Efficiency:", eff.get("efficiency_score") if isinstance(eff, dict) else eff)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] in {"init", "uninstall-skill"}:
        from hyperlex.init_skill import dispatch

        return dispatch(raw)
    if raw and (
        raw[0] in {"--memory", "--export-hyperlexical"}
        or (raw[0].startswith("-") and "--memory" in raw)
    ):
        return _moltbook_memory_cli(raw)
    from hyperlex.cli import main as cli_main

    return cli_main(raw)


if __name__ == "__main__":
    raise SystemExit(main())
