"""Console-script router: init/uninstall-skill vs operator CLI."""
from __future__ import annotations

import sys
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] in {"init", "uninstall-skill"}:
        from hyperlex.init_skill import dispatch

        return dispatch(raw)
    from hyperlex.cli import main as cli_main

    return cli_main(raw)


if __name__ == "__main__":
    raise SystemExit(main())
