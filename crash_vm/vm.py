import time
import sys
from ._types import NativeNumber, Address, AddressRange
from .cpu import CPU, SWInterrupt
from .ram import RAM
from .bus import Bus
from itertools import count
from enum import Enum


class VM:
    def __init__(self, ram_size=256, peripherals=()):
        self._fsb = Bus()
        self._ram = RAM(ram_size)
        self._fsb.attach(AddressRange(0, ram_size), self._ram)
        next_pool_address = ram_size
        for pool_size, peripheral in peripherals:
            self._fsb.attach(AddressRange(next_pool_address, next_pool_address + pool_size), peripheral)
            next_pool_address += pool_size
        self._cpu = CPU(self._fsb)
        self._clock_interrupt_ts = int(time.time())

    def _breakpoint(self):
        print(self)

    def _cycle(self, cycle_iter):
        try:
            try:
                next(cycle_iter)
            except StopIteration:
                ts = int(time.time())
                if ts > self._clock_interrupt_ts:
                    self._clock_interrupt_ts = ts
                    self._cpu.irq(self._cpu.get_irq_levels() - 1)
                cycle_iter = self._cpu.cycle()
        except SWInterrupt as interrupt:
            if interrupt.code == SWInterrupt.ReservedCodes.Breakpoint.value:
                self._breakpoint()
            else:
                raise interrupt
        return cycle_iter

    def run(self, frequency=None):
        self._clock_interrupt_ts = int(time.time())
        try:
            if frequency is None:
                cycle_iter = self._cpu.cycle()
                while True:
                    cycle_iter = self._cycle(cycle_iter)
            else:
                period_ns = int(1000000000.0 / frequency)
                cycle_iter = self._cpu.cycle()
                while True:
                    cycle_start_ts_ns = time.perf_counter_ns()
                    cycle_iter = self._cycle(cycle_iter)
                    cycle_overtime_ns = period_ns - (time.perf_counter_ns() - cycle_start_ts_ns)
                    if cycle_overtime_ns >= 0:
                        time.sleep(cycle_overtime_ns * 0.000000001)
                    else:
                        print(self._cpu, 'throttling to', 1000000000.0 / (period_ns - cycle_overtime_ns), 'Hz',
                              file=sys.stderr)
        except SWInterrupt as interrupt:
            if interrupt.code == SWInterrupt.ReservedCodes.Halt.value:
                pass
            else:
                raise interrupt

    def reset(self):
        self._ram.clear()
        self._cpu.reset()

    def load_program(self, program):
        assert len(program) <= len(self._ram)
        for address, value in zip(count(), program):
            if isinstance(value, (Enum, NativeNumber, Address)):
                value = value.value
            self._ram[Address(address)] = NativeNumber(value)

    def __getitem__(self, item: Address) -> NativeNumber:
        return self._fsb[item]

    def __repr__(self):
        return '\n\n'.join([self._cpu.__repr__(), self._ram.__repr__()])
