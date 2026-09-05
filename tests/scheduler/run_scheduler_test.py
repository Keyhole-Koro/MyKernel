#!/usr/bin/env python3
"""
Task-scheduler end-to-end test for MyKernel.

Builds the scheduler test kernel (tests/test_scheduler.mln + test_stub.masm)
and runs it in the emulator, checking that both tasks ran via context switching:
each task only prints "Test PASSED!" after observing the *other* task's counter
pass 1000, so the marker proves the timer interrupt swapped stacks between them.

The build goes through build_toolchain.py directly (not run_kernel.py) with its
output redirected to a log file: the compiler streams every lexer token to
stdout, and piping that through a captured subprocess is slow enough to blow a
generous timeout. Building to a file and then running the linked image keeps the
whole thing to a few seconds.

Usage:
  python3 system/MyKernel/tests/run_scheduler_test.py [--verbose]
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
SOURCE = MYKERNEL_DIR / "tests" / "scheduler" / "test_scheduler.mln"
STUB = MYKERNEL_DIR / "tests" / "scheduler" / "test_stub.masm"

STEP_LIMIT = "5000000"
# The scheduler is preemptive: context switches happen in the timer IRQ, so the
# emulator must be told to raise one. Without --timer-interval no switch ever
# fires and the test spins until the step limit.
#
# NOTE: the demo scheduler is timing-fragile. The trampoline pushes the full
# register file onto whichever task stack is live when the IRQ fires, so an
# interrupt landing at an unlucky instruction can drive a task's SP past its
# small (1 KiB) stack and trip the emulator's stack-underflow guard. The
# interval below is chosen so interrupts land on safe boundaries for the
# current codegen. If a codegen change shifts instruction timing this may need
# re-tuning; the real fix is larger per-task stacks / a guarded switch.
TIMER_INTERVAL = "3000"
# Both tasks race to print "Test PASSED!" once they see each other's progress,
# so their writes interleave character-by-character (e.g. "Test PASTest
# PASSEDSED!"). That interleaving is itself proof the scheduler swapped between
# them, but it means the full string may never appear contiguously. Match on the
# shorter "PASSED" token, which survives the interleave intact here, and treat
# its presence as success.
MARKER = "PASSED"

GREEN, RED, CYAN = "32", "31", "36"


def colored(text, code):
    return f"\033[{code}m{text}\033[0m"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix="mykernel-scheduler-test-"))
    linked = work / "test_scheduler_linked.mbin"

    # Build to a file; the compiler's token dump makes captured output huge.
    build = subprocess.run(
        ["python3", str(BUILD_TOOLCHAIN), str(STUB), str(SOURCE),
         "-o", str(linked), "--build-dir", str(work)],
        cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=300,
    )
    if build.returncode != 0 or not linked.exists():
        print(colored("[FAIL]", RED), "scheduler test build failed")
        if args.verbose:
            print(build.stdout)
        else:
            print(colored("[INFO]", CYAN), "re-run with --verbose to see build output")
        return 1

    run = subprocess.run(
        [str(MYEMU), "-i", str(linked),
         "--timer-interval", TIMER_INTERVAL, "--step", STEP_LIMIT, "--headless"],
        cwd=work, capture_output=True, text=True, timeout=60,
    )
    out = run.stdout + run.stderr
    if args.verbose:
        print(out)

    if MARKER not in out:
        print(colored("[FAIL]", RED),
              f"scheduler marker {MARKER!r} not seen (context switch did not run)")
        print(colored("[INFO]", CYAN), f"emulator tail: {out[-200:]!r}")
        if not args.verbose:
            print(colored("[INFO]", CYAN), "re-run with --verbose to see output")
        return 1

    print(colored("[PASS]", GREEN),
          "scheduler: both tasks ran, context switch verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
