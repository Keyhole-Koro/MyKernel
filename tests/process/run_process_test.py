#!/usr/bin/env python3
"""
User Process, Syscall, and Preemption integration test for MyKernel.
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
SOURCE = MYKERNEL_DIR / "tests" / "process" / "test_process.mln"
STUB = MYKERNEL_DIR / "tests" / "process" / "test_stub.masm"

STEP_LIMIT = "50000000"
TIMER_INTERVAL = "3000"
MARKER = "TEST_PASSED_OK"

GREEN, RED, CYAN = "32", "31", "36"

def colored(text, code):
    return f"\033[{code}m{text}\033[0m"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix="mykernel-process-test-"))
    linked = work / "test_process_linked.mbin"

    print(colored("[BUILD]", CYAN), "building process integration test...")
    build = subprocess.run(
        ["python3", str(BUILD_TOOLCHAIN), str(STUB), str(SOURCE),
         "-o", str(linked), "--build-dir", str(work)],
        cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=300,
    )
    if build.returncode != 0 or not linked.exists():
        print(colored("[FAIL]", RED), "process test build failed")
        print(build.stdout)
        return 1

    print(colored("[RUN]", CYAN), "running emulator with timer-interval=3000...")
    run = subprocess.run(
        [str(MYEMU), "-i", str(linked),
         "--timer-interval", TIMER_INTERVAL, "--step", STEP_LIMIT, "--headless"],
        cwd=work, capture_output=True, text=True, timeout=60,
    )
    out = run.stdout + run.stderr
    if args.verbose or MARKER not in out:
        print(out)

    if MARKER not in out:
        print(colored("[FAIL]", RED), "marker TEST_PASSED_OK not seen")
        return 1

    print(colored("[PASS]", GREEN), "user process, syscall, and preemption test PASSED!")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
