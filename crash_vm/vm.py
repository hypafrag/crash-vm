import time
import sys
from .cpu import CPU, HaltExecution
from .ram import RAM
from .bus import Bus
from itertools import count
from enum import Enum


class VM:
    def __init__(self):
        self._fsb = Bus()
        self._ram = RAM(256)
        self._fsb.attach((0, 256), self._ram)
        self._cpu = CPU(self._fsb)

    def run(self, frequency=None):
        try:
            if frequency is None:
                while True:
                    self._cpu.next_instruction()
            else:
                period_ns = int(1000000000.0 / frequency)
                while True:
                    cycle_start_ts_ns = time.perf_counter_ns()
                    self._cpu.next_instruction()
                    cycle_overtime_ns = period_ns - (time.perf_counter_ns() - cycle_start_ts_ns)
                    if cycle_overtime_ns >= 0:
                        time.sleep(cycle_overtime_ns * 0.000000001)
                    else:
                        print(self._cpu, 'throttling to', 1000000000.0 / (period_ns - cycle_overtime_ns), 'Hz',
                              file=sys.stderr)
        except HaltExecution:
            pass

    def reset(self):
        self._ram.clear()
        self._cpu.reset()

    def load_program(self, program):
        assert len(program) <= len(self._ram)
        for address, value in zip(count(), program):
            if isinstance(value, Enum):
                value = value.value
            self._ram[address] = value

    def __getitem__(self, item):
        return self._fsb[item]

    def __repr__(self):
        return '\n\n'.join([self._cpu.__repr__(), self._ram.__repr__()])
