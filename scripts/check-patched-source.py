#!/usr/bin/env python3
"""Compare the worktree to HEAD plus the patch using a disposable Git index."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def check_source(source: Path, patch: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="t480-patch-index-") as temporary:
        env = os.environ | {"GIT_INDEX_FILE": str(Path(temporary) / "index")}
        git = ["git", "-C", str(source.resolve())]
        for args in (
            ["read-tree", "HEAD"],
            ["apply", "--cached", str(patch.resolve())],
            ["diff", "--quiet", "--no-ext-diff", "--no-textconv", "--"],
        ):
            subprocess.run(git + args, env=env, check=True, timeout=30)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()
    try:
        check_source(args.source, args.patch)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        parser.exit(1, "Source does not match HEAD plus the reviewed patch, or Git validation failed.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
