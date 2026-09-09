#!/usr/bin/env python3
"""Compatibility entry point for the MyLangTestKit standard-library test."""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.project_paths import MYKERNEL_DIR, MYLANGTESTER_DIR, REPO_ROOT

MYTEST = MYLANGTESTER_DIR / "build" / "mytest"
SOURCE = MYKERNEL_DIR / "tests" / "libs" / "std.test.mln"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    run = subprocess.run([str(MYTEST), str(SOURCE)], cwd=REPO_ROOT,
                         capture_output=not args.verbose, text=True, timeout=300)
    if not args.verbose:
        print(run.stdout + run.stderr, end="")
    return run.returncode

if __name__ == "__main__":
    raise SystemExit(main())
