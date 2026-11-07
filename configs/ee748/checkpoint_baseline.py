#!/usr/bin/env python3
# Copyright (c) 2026 EE748 Team 9 contributors
# SPDX-License-Identifier: BSD-3-Clause
"""Run one stage of an EE748 baseline via a KVM checkpoint handoff."""

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from benchmark_specs import SPECS

REPO = Path(__file__).resolve().parents[2]
WORKSPACE = REPO.parent
FASTFORWARD_CUSHION = 50_000_000
WARMUP = 200_000_000
DETAIL = 50_000_000


def workload(name: str, directory: Path):
    folder, executable, _ = SPECS[name]
    bench = WORKSPACE / "benchmarks/CPU2006" / folder
    ref = bench / "data/ref/input"
    binary = bench / "exe" / f"{executable}_base.gcc44-64bit"
    cwd = directory
    stdin = None
    if name == "astar":
        cwd = ref
        inputs = ["BigLakes2048.cfg"]
    elif name == "bzip2":
        inputs = [str(ref / "input.source")]
    elif name == "hmmer":
        inputs = [str(ref / "nph3.hmm"), str(ref / "swiss41")]
    elif name == "lbm":
        inputs = [
            "3000", str(directory / "reference.dat"), "0", "0",
            str(ref / "100_100_130_ldc.of"),
        ]
    elif name == "mcf":
        inputs = [str(ref / "inp.in")]
    elif name == "milc":
        inputs = []
        stdin = ref / "su3imp.in"
    elif name == "namd":
        inputs = [
            "--input", str(bench / "data/all/input/namd.input"),
            "--iterations", "38",
        ]
    elif name == "gamess":
        inputs = []
        stdin = ref / "cytosine.2.config"
    else:
        cwd = bench / "build/build_base_gcc44-64bit.0000"
        inputs = ["ctlfile", ".", "args.an4"]
    return binary, cwd, inputs, stdin, ref


def prepare_workload(name: str, directory: Path, inputs, ref: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if name == "gamess":
        for source in ref.iterdir():
            if source.is_file() and not (directory / source.name).exists():
                shutil.copy2(source, directory / source.name)
    if name == "namd":
        arguments = directory / "arguments.txt"
        expected = shlex.join(inputs) + "\n"
        if arguments.exists() and arguments.read_text() != expected:
            raise ValueError("NAMD arguments file differs from this run")
        arguments.write_text(expected)


def add_workload_args(command, name, binary, inputs, stdin, directory):
    command += ["--binary", str(binary)]
    if name == "gamess":
        command += [
            "--library-path",
            str(WORKSPACE / "legacy-runtime/usr/lib/x86_64-linux-gnu"),
        ]
    if stdin:
        command += ["--stdin-file", str(stdin)]
    if name == "namd":
        command += ["--input-file", str(directory / "arguments.txt")]
    elif inputs:
        command += ["--inputs", *inputs]
    return command


def run_gem5(command, cwd: Path, output: Path) -> int:
    if output.exists():
        raise ValueError(f"Output already exists: {output}")
    output.mkdir(parents=True)
    print(shlex.join(command), flush=True)
    with (output / "run.log").open("w") as log:
        with subprocess.Popen(
            command, cwd=cwd, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1,
        ) as process:
            assert process.stdout is not None
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            code = process.wait()
    (output / "exit-code.txt").write_text(f"{code}\n")
    return code


def verify(name: str, directory: Path) -> None:
    baseline = directory / "baseline"
    if (baseline / "exit-code.txt").read_text().strip() != "0":
        raise ValueError("Baseline gem5 process did not exit successfully")
    log = (baseline / "run.log").read_text()
    if "Success: All three-phases of simulation completed!" not in log:
        raise ValueError("Baseline did not complete all three phases")
    stats = (baseline / "stats.log").read_text()
    matches = re.findall(r"^simInsts\s+(\d+)\s+#", stats, re.M)
    if len(matches) != 1 or abs(int(matches[0]) - DETAIL) > 2:
        raise ValueError("Measured instruction count is not 50M +/- 2")
    config = (baseline / "config.ini").read_text()
    if "[board.cache_hierarchy.llc]" not in config:
        raise ValueError("Generated configuration has no LLC")
    metadata = json.loads(
        (directory / "checkpoint" / "ee748-progress.json").read_text()
    )
    remaining = metadata["remaining_fastforward_instructions"]
    if not isinstance(remaining, int) or remaining < 1:
        raise ValueError("Invalid checkpoint remainder")
    print(
        f"{name}: baseline completed; {matches[0]} measured instructions; "
        f"checkpoint progress {metadata['completed_instructions']}; "
        f"remaining Atomic fast-forward {remaining}",
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage", choices=["plan", "save", "convert", "resume", "verify"]
    )
    parser.add_argument("workload", choices=sorted(SPECS))
    parser.add_argument(
        "--output-root", type=Path,
        default=WORKSPACE / "gem5_out/baseline_checkpointed",
    )
    args = parser.parse_args()
    name = args.workload
    target = SPECS[name][2]
    if target is None:
        parser.error(f"{name}: SimPoint warmup choice has not been resolved")
    if target <= FASTFORWARD_CUSHION + 10_000_000:
        parser.error("Selected interval is too early for KVM checkpointing")

    directory = args.output_root.resolve() / name
    binary, cwd, inputs, stdin, ref = workload(name, directory)
    save_target = target - FASTFORWARD_CUSHION
    if not binary.is_file():
        parser.error(f"Missing benchmark binary: {binary}")
    if stdin and not stdin.is_file():
        parser.error(f"Missing benchmark stdin: {stdin}")
    if name == "gamess" and not (
        WORKSPACE / "legacy-runtime/usr/lib/x86_64-linux-gnu/libgfortran.so.3"
    ).is_file():
        parser.error("Missing GAMESS runtime; run its setup first")
    if args.stage == "plan":
        print(
            f"{name}: KVM+Atomic checkpoint target {save_target}; "
            f"selected warmup start {target}; warmup {WARMUP}; detail {DETAIL}"
        )
        print(f"Binary: {binary}; cwd: {cwd}; inputs: {shlex.join(inputs)}")
        return 0
    if args.stage == "convert":
        helper = REPO / "util/ee748/convert_kvm_checkpoint.py"
        return subprocess.run(
            [sys.executable, str(helper), str(directory / "checkpoint_raw"),
             str(directory / "save/stats.log"), str(directory / "checkpoint"),
             "--target-fastforward", str(target)], check=False,
        ).returncode
    if args.stage == "verify":
        verify(name, directory)
        return 0

    gem5 = REPO / "build/X86/gem5.opt"
    if not gem5.is_file():
        parser.error(f"Missing gem5 executable: {gem5}")
    prepare_workload(name, directory, inputs, ref)
    if args.stage == "save":
        output = directory / "save"
        if (directory / "checkpoint_raw").exists():
            raise ValueError(
                "Raw checkpoint already exists; choose a new output root"
            )
        command = [
            str(gem5), "-d", str(output), "--stats-file=stats.log",
            str(REPO / "configs/ee748/se_kvm.py"),
            "--fastforward-insts", str(save_target),
            "--warmup-insts", str(WARMUP),
            "--detailed-insts", str(DETAIL),
            "--checkpoint-after-fastforward",
            str(directory / "checkpoint_raw"),
        ]
    else:
        output = directory / "baseline"
        metadata = json.loads(
            (directory / "checkpoint" / "ee748-progress.json").read_text()
        )
        remaining = metadata["remaining_fastforward_instructions"]
        if not isinstance(remaining, int) or remaining < 1:
            raise ValueError(
                "Invalid remaining fast-forward instruction count"
            )
        command = [
            str(gem5), "-d", str(output), "--stats-file=stats.log",
            str(REPO / "configs/ee748/se.py"),
            "--fastforward-insts", str(remaining),
            "--warmup-insts", str(WARMUP),
            "--detailed-insts", str(DETAIL),
            "--restore-checkpoint", str(directory / "checkpoint"),
        ]
    add_workload_args(command, name, binary, inputs, stdin, directory)
    return run_gem5(command, cwd, output)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"baseline runner: {error}", file=sys.stderr)
        raise SystemExit(1)
