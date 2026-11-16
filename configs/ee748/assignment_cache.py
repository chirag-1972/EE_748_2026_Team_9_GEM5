# SPDX-License-Identifier: BSD-3-Clause
"""Classic three-level cache hierarchy for EE748 Assignment 1."""

from m5.objects import (
    LRU9RP,
    LRURP,
    TAGE_SC_L_64KB,
    BranchPredictor,
    IQUnit,
    L2XBar,
    ReturnAddrStack,
    SimpleBTB,
)

from gem5.components.cachehierarchies.classic.caches.l1dcache import L1DCache
from gem5.components.cachehierarchies.classic.caches.l1icache import L1ICache
from gem5.components.cachehierarchies.classic.caches.l2cache import L2Cache
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import (
    PrivateL1PrivateL2CacheHierarchy,
)
from gem5.components.memory.dram_interfaces.ddr3 import DDR3_1600_8x8
from gem5.components.memory.memory import ChanneledMemory
from gem5.isas import ISA


class DDR3_1600_4GiB(DDR3_1600_8x8):
    """One 4 GiB rank on a 64-bit DDR3-1600 channel."""

    ranks_per_channel = 1


def assignment_memory(size):
    return ChanneledMemory(DDR3_1600_4GiB, 1, 64, size=size)


def configure_o3(core):
    """Apply the assignment's single-core O3 width and predictor settings."""
    cpu = core.get_simobject()
    cpu.fetchWidth = 4
    cpu.decodeWidth = 4
    cpu.issueWidth = 4
    cpu.commitWidth = 4
    cpu.numROBEntries = 192
    cpu.instQueues = [IQUnit(numEntries=64)]
    cpu.LQEntries = 32
    cpu.SQEntries = 32
    cpu.branchPred = BranchPredictor(
        conditionalBranchPred=TAGE_SC_L_64KB(),
        btb=SimpleBTB(numEntries=4096),
        ras=ReturnAddrStack(numEntries=32),
    )


class AssignmentCacheHierarchy(PrivateL1PrivateL2CacheHierarchy):
    """One core's L1I/L1D -> L2 -> shared LLC -> DDR3 memory."""

    def __init__(self, *args, llc_policy="lru", **kwargs):
        super().__init__(*args, **kwargs)
        if llc_policy not in {"lru", "lru9"}:
            raise ValueError(f"Unsupported LLC policy: {llc_policy}")
        self._llc_policy = llc_policy

    def incorporate_cache(self, board):
        board.connect_system_port(self.membus.cpu_side_ports)
        for _, port in board.get_mem_ports():
            self.membus.mem_side_ports = port

        llc = self.add_root_child(
            "llc",
            L2Cache(
                size="1MiB",
                assoc=16,
                tag_latency=20,
                data_latency=20,
                response_latency=1,
                mshrs=64,
            ),
        )
        llc.cache.replacement_policy = (
            LRU9RP() if self._llc_policy == "lru9" else LRURP()
        )
        llc.cache.mem_side = self.membus.cpu_side_ports
        self.l3buses = [L2XBar()]
        self.l3buses[0].mem_side_ports = llc.cache.cpu_side

        self.l2buses = [
            L2XBar() for _ in range(board.get_processor().get_num_cores())
        ]
        for i, cpu in enumerate(board.get_processor().get_cores()):
            l2bus = self.l2buses[i]
            l2_node = self.add_root_child(
                f"l2-cache-{i}",
                L2Cache(
                    size=self._l2_size,
                    assoc=self._l2_assoc,
                    tag_latency=self._l2_tag_latency,
                    data_latency=self._l2_data_latency,
                    response_latency=self._l2_response_latency,
                    mshrs=64,
                ),
            )
            l1i_node = l2_node.add_child(
                f"l1i-cache-{i}",
                L1ICache(
                    size=self._l1i_size,
                    assoc=self._l1i_assoc,
                    tag_latency=self._l1i_tag_latency,
                    data_latency=self._l1i_data_latency,
                    response_latency=self._l1i_response_latency,
                    mshrs=32,
                ),
            )
            l1d_node = l2_node.add_child(
                f"l1d-cache-{i}",
                L1DCache(
                    size=self._l1d_size,
                    assoc=self._l1d_assoc,
                    tag_latency=self._l1d_tag_latency,
                    data_latency=self._l1d_data_latency,
                    response_latency=self._l1d_response_latency,
                    mshrs=32,
                ),
            )
            l2_node.cache.replacement_policy = LRURP()
            l1i_node.cache.replacement_policy = LRURP()
            l1d_node.cache.replacement_policy = LRURP()
            l2bus.mem_side_ports = l2_node.cache.cpu_side
            self.l3buses[0].cpu_side_ports = l2_node.cache.mem_side
            l1i_node.cache.mem_side = l2bus.cpu_side_ports
            l1d_node.cache.mem_side = l2bus.cpu_side_ports
            cpu.connect_icache(l1i_node.cache.cpu_side)
            cpu.connect_dcache(l1d_node.cache.cpu_side)
            self._connect_table_walker(i, cpu)
            if board.get_processor().get_isa() == ISA.X86:
                cpu.connect_interrupt(
                    self.membus.mem_side_ports, self.membus.cpu_side_ports
                )
            else:
                cpu.connect_interrupt()
