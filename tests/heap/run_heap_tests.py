#!/usr/bin/env python3
"""
Heap allocator unit tests for MyKernel.

Each test case is a self-checking MyLang program under tests/cases/ that
returns a value in R1 (1 = pass, or a small code identifying the failed
assertion). The program is compiled together with the heap package
(src/libs/heap.mln) and its `_end` accessor (src/libs/heap_sym.masm), linked,
and run in the emulator; the final R1 is compared against the expected value.

Panic-style cases (heap exhaustion) instead assert on serial output, because a
panic halts the machine before R1 can carry a result.

Usage:
  python3 system/MyKernel/tests/run_heap_tests.py [casename] [--verbose]
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.project_paths import (
    MYASSEMBLER_DIR,
    MYEMULATOR_DIR,
    MYKERNEL_DIR,
    MYLANGCOMPILER_DIR,
    MYLINKER_DIR,
    REPO_ROOT,
)

MLC = MYLANGCOMPILER_DIR / "mlc"
MYAS = MYASSEMBLER_DIR / "build" / "myas"
MLLINKER = MYLINKER_DIR / "mllinker"
MYEMU = MYEMULATOR_DIR / "target" / "release" / "myemu"

SRC = MYKERNEL_DIR / "src"
CASES_DIR = Path(__file__).resolve().parent / "cases"

GREEN, RED, CYAN, YELLOW = "32", "31", "36", "33"

# Shared library sources linked into every heap test.
#   (path, kind)  kind: "ml" compiles via mlc, "masm" assembles directly.
LIB_SOURCES = [
    (SRC / "mm" / "heap.mln", "ml"),
    (SRC / "mm" / "heap_sym.masm", "masm"),
    (SRC / "arch" / "halt.masm", "masm"),
    (SRC / "mm" / "mem.mln", "ml"),
    (SRC / "lib" / "ringbuf.mln", "ml"),
    (SRC / "io" / "serial.mln", "ml"),
    (SRC / "debug" / "debug.mln", "ml"),
]

# name -> dict describing the assertion.
#   {"reg": N}                  expect R1 == N
#   {"serial": "substr"}        expect substr in serial output (panic cases)
CASES = {
    "basic": {"reg": 1},
    "reuse": {"reg": 1},
    "write": {"reg": 1},
    "split_remainder": {"reg": 1},
    "coalesce_forward": {"reg": 1},
    "coalesce_backward": {"reg": 1},
    "exhaustion": {"serial": "panic"},
}

VERBOSE = False


def colored(text, code):
    return f"\033[{code}m{text}\033[0m"


def status(label, msg, code=CYAN):
    print(colored(f"[{label}]", code), msg)


def run(cmd, cwd):
    proc = subprocess.run(
        [str(c) for c in cmd], cwd=cwd, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, errors="replace",
    )
    if VERBOSE:
        print("+ " + " ".join(str(c) for c in cmd))
        if proc.stdout:
            print(proc.stdout)
    return proc


def extract_serial(emu_output: str) -> str:
    lines = emu_output.splitlines()
    out, seen = [], False
    for line in lines:
        if not seen:
            if line.startswith("Loading binary from "):
                seen = True
            continue
        if line.startswith("Stack Contents:") or line.startswith("R0:"):
            break
        out.append(line)
    return "\n".join(out)


def build_and_run(name, work):
    case_src = CASES_DIR / f"{name}.mln"
    if not case_src.exists():
        return None, f"missing case source {case_src}"

    objs = []
    for src, kind in [(case_src, "ml"), *LIB_SOURCES]:
        stem = src.stem
        masm = work / f"{stem}.masm"
        if kind == "ml":
            r = run([MLC, src, masm], REPO_ROOT)
            if r.returncode != 0:
                return None, f"mlc failed for {src.name}:\n{r.stdout}"
        else:
            masm.write_bytes(src.read_bytes())
        mobj = work / f"{stem}.mobj"
        mbin = work / f"{stem}.prelink.mbin"
        r = run([MYAS, masm, mbin, "--obj", mobj], REPO_ROOT)
        if r.returncode != 0:
            return None, f"myas failed for {src.name}:\n{r.stdout}"
        objs.append(mobj)

    linked = work / f"{name}.mbin"
    r = run([MLLINKER, linked, *objs], REPO_ROOT)
    if r.returncode != 0:
        return None, f"link failed:\n{r.stdout}"

    # Run with cwd=work so the emulator's memory_dump.txt lands in the temp dir.
    r = run([MYEMU, "-i", linked, "--reg", "R1", "--headless"], work)
    if r.returncode != 0:
        return None, f"emulator failed:\n{r.stdout}"
    return r.stdout, None


def check(name, spec, output):
    if "reg" in spec:
        # `--reg R1` prints the bare integer as the last non-empty line.
        lines = [l.strip() for l in output.splitlines() if l.strip()]
        try:
            actual = int(lines[-1], 0)
        except (ValueError, IndexError):
            return False, f"could not parse R1 from output tail: {lines[-3:]}"
        if actual == spec["reg"]:
            return True, f"R1={actual}"
        return False, f"R1={actual}, expected {spec['reg']}"
    if "serial" in spec:
        serial = extract_serial(output)
        if spec["serial"] in serial:
            return True, f"serial contains '{spec['serial']}'"
        return False, f"serial missing '{spec['serial']}'; got: {serial!r}"
    return False, "no assertion in spec"


def main():
    global VERBOSE
    ap = argparse.ArgumentParser(description="Run MyKernel heap unit tests.")
    ap.add_argument("case", nargs="?", help="single case name to run")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    VERBOSE = args.verbose

    selected = CASES
    if args.case:
        if args.case not in CASES:
            print(f"[ERROR] unknown case '{args.case}'. Known: {', '.join(CASES)}")
            return 1
        selected = {args.case: CASES[args.case]}

    passed = failed = 0
    work_root = Path(tempfile.mkdtemp(prefix="mykernel-heap-tests-"))
    try:
        for name, spec in selected.items():
            work = work_root / name
            work.mkdir(parents=True, exist_ok=True)
            output, err = build_and_run(name, work)
            if err:
                status("FAIL", f"{name}: {err}", RED)
                failed += 1
                continue
            ok, detail = check(name, spec, output)
            if ok:
                status("PASS", f"{name} {detail}", GREEN)
                passed += 1
            else:
                status("FAIL", f"{name} {detail}", RED)
                failed += 1
    finally:
        import shutil
        shutil.rmtree(work_root, ignore_errors=True)

    color = GREEN if failed == 0 else RED
    status("DONE", f"Summary: {passed} passed, {failed} failed", color)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
