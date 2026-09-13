"""Verify a local preparation package without model loading. Provenance: WF-003."""
import argparse
import json
from pathlib import Path

from .training_prepare import verify_package


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        report = verify_package(args.directory)
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"status": "PACKAGE_INVALID", "training_ready": False}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
