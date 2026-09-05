#!/usr/bin/env python3
"""
FS smoke test runner for MyKernel.

Builds the std library test kernel and runs it in the emulator.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.project_paths import MYEMULATOR_DIR, MYKERNEL_DIR, REPO_ROOT

BUILD_TOOLCHAIN = REPO_ROOT / "qa" / "runners" / "build_toolchain.py"
MYEMU = MYEMULATOR_DIR / "target" / "release" / "myemu"
SOURCE = MYKERNEL_DIR / "tests" / "libs" / "test_std.mln"
STUB = MYKERNEL_DIR / "tests" / "libs" / "test_std_stub.masm"

STEP_LIMIT = "50000000"
MARKER = "Test PASSED!"

GREEN, RED, CYAN = "32", "31", "36"

def colored(text, code):
    return f"\033[{code}m{text}\033[0m"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix="mykernel-std-test-"))
    linked = work / "test_std_linked.mbin"

    build = subprocess.run(
        ["python3", str(BUILD_TOOLCHAIN), str(STUB), str(SOURCE),
         "-o", str(linked), "--build-dir", str(work)],
        cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=300,
    )
    if build.returncode != 0 or not linked.exists():
        print(colored("[FAIL]", RED), "std library test build failed")
        if args.verbose:
            print(build.stdout)
        else:
            print(colored("[INFO]", CYAN), "re-run with --verbose to see build output")
        return 1

    run = subprocess.run(
        [str(MYEMU), "-i", str(linked), "--step", STEP_LIMIT, "--headless"],
        cwd=work, capture_output=True, text=True, timeout=60,
    )
    out = run.stdout + run.stderr
    if args.verbose:
        print(out)

    if MARKER not in out:
        print(colored("[FAIL]", RED), "std library test did not report PASSED")
        print(colored("[INFO]", CYAN), f"emulator tail: {out[-200:]!r}")
        if not args.verbose:
            print(colored("[INFO]", CYAN), "re-run with --verbose to see output")
        return 1

    print(colored("[PASS]", GREEN), "std library test: str, bytes, bitset, ringbuf, strbuf verified")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
