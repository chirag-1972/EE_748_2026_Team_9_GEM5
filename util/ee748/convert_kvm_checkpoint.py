#!/usr/bin/env python3
# Copyright (c) 2026 EE748 Team 9 contributors
# SPDX-License-Identifier: BSD-3-Clause
"""Copy a KVM SE checkpoint for the assignment's non-KVM resume script.

The checkpoint's Process SimObject belongs to the KVM core in se_kvm.py.
In se.py the same process belongs to the Atomic core. gem5's checkpoint
sections use these object paths, so the process and page table would not
otherwise be restored. The source checkpoint is never modified.
"""

import argparse
import json
import re
import shutil
from pathlib import Path


def one_counter(stats: str, name: str) -> int:
    matches = re.findall(rf"^{re.escape(name)}\s+(\d+)\s+#", stats, re.M)
    if len(matches) != 1:
        raise ValueError(f"Expected one {name} counter in the save stats")
    return int(matches[0])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="KVM checkpoint directory")
    parser.add_argument(
        "save_stats", type=Path, help="KVM save run's stats.txt"
    )
    parser.add_argument(
        "destination", type=Path, help="New checkpoint directory"
    )
    parser.add_argument("--target-fastforward", type=int)
    args = parser.parse_args()

    source = args.source.resolve()
    destination = args.destination.resolve()
    if not source.is_dir() or not (source / "m5.cpt").is_file():
        parser.error("Source must contain m5.cpt")
    if destination.exists():
        parser.error("Destination already exists; choose a new directory")
    if source in destination.parents or destination in source.parents:
        parser.error("Source and destination must not be nested")

    checkpoint = (source / "m5.cpt").read_text()
    old = "board.processor.kvm.core.workload"
    new = "board.processor.atomic.core.workload"
    if checkpoint.count(f"[{old}]") != 1 or f"[{new}]" in checkpoint:
        parser.error("Checkpoint has an unexpected process object layout")
    if "ptable.size" not in checkpoint and ".ptable]" not in checkpoint:
        parser.error(
            "Checkpoint does not contain the expected process page table"
        )

    stats = args.save_stats.read_text()
    completed = one_counter(stats, "simInsts")
    kvm = one_counter(stats, "board.processor.kvm.core.commitStats0.numInsts")
    atomic = one_counter(
        stats, "board.processor.atomic.core.commitStats0.numInsts"
    )
    if completed != kvm + atomic:
        parser.error("KVM and Atomic counts do not add up to simInsts")
    if args.target_fastforward is not None:
        if args.target_fastforward < completed:
            parser.error(
                "Checkpoint is already beyond the fast-forward target"
            )
        remaining = args.target_fastforward - completed
    else:
        remaining = None

    shutil.copytree(source, destination)
    (destination / "m5.cpt").write_text(checkpoint.replace(old, new))
    metadata = {
        "completed_instructions": completed,
        "kvm_instructions": kvm,
        "atomic_instructions": atomic,
        "remaining_fastforward_instructions": remaining,
        "source_checkpoint": str(source),
    }
    (destination / "ee748-progress.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
