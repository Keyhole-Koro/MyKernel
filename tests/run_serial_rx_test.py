#!/usr/bin/env python3
"""
Serial RX (input) end-to-end test for MyKernel.

Builds the sample kernel and the emulator, pipes a few bytes ending in 'q' to
the running machine, and checks the kernel's IRQ handler echoed them back and
halted cleanly on 'q'. Exercises the whole path: stdin -> emulator RX register
-> RX interrupt -> kernel handler -> echo (serial TX).

Usage:
  python3 system/MyKernel/tests/run_serial_rx_test.py [--verbose]
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.project_paths import MYEMULATOR_DIR, MYKERNEL_DIR, REPO_ROOT

KERNEL_IMAGE = MYKERNEL_DIR / "build" / "kernel_main_linked.mbin"
MYEMU = MYEMULATOR_DIR / "build" / "myemu"
STEP_LIMIT = "3000000"
PROBE = "PING"          # bytes to "type"
INPUT = PROBE + "q"     # 'q' makes the handler halt the machine

GREEN, RED, CYAN = "32", "31", "36"


def colored(text, code):
    return f"\033[{code}m{text}\033[0m"


def build(cmd, cwd, what, verbose):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        if verbose:
            sys.stderr.write(result.stdout + result.stderr)
        print(colored("[FAIL]", RED), f"could not build {what}")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not build(["python3", str(REPO_ROOT / "qa" / "run_kernel.py"), "--no-run"],
                 None, "kernel image", args.verbose) or not KERNEL_IMAGE.exists():
        return 1
    if not build(["make"], str(MYEMULATOR_DIR), "emulator", args.verbose) or not MYEMU.exists():
        return 1

    proc = subprocess.run(
        [str(MYEMU), "-i", str(KERNEL_IMAGE), "--step", STEP_LIMIT],
        input=INPUT, capture_output=True, text=True, timeout=30,
    )
    out = proc.stdout
    if args.verbose:
        print(out)

    failures = []
    if PROBE not in out:
        failures.append(f"typed {PROBE!r} was not echoed back")
    if proc.returncode != 0:
        failures.append(f"'q' did not halt the machine cleanly (exit {proc.returncode})")
    if "kernel: heap ready" not in out:
        failures.append("kernel did not boot to 'heap ready'")

    if failures:
        for f in failures:
            print(colored("[FAIL]", RED), f)
        if not args.verbose:
            print(colored("[INFO]", CYAN), "re-run with --verbose to see emulator output")
        return 1

    print(colored("[PASS]", GREEN), f"serial RX: typed {PROBE!r} echoed, 'q' halted cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
