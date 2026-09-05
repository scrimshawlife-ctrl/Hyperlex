"""python -m hyperlex → package CLI (includes init)."""

from .entrypoint import main

if __name__ == "__main__":
    raise SystemExit(main())
