import asyncio
from itertools import count
from cpu import CPU, Instructions as Ins, HaltExecution
from ram import RAM
from bus import Bus
from enum import Enum


class VM:
    def __init__(self):
        self._fsb = Bus()
        self._ram = RAM(256)
        self._fsb.attach((0, 256), self._ram)
        self._cpu = CPU(self._fsb)

    def run(self):
        try:
            while True:
                self._cpu.next_instruction()
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


def padr(seq, num, value=0):
    padding_len = num - len(seq)
    assert padding_len >= 0
    return seq + [value] * padding_len


def padl(seq, num, value=0):
    padding_len = num - len(seq)
    assert padding_len >= 0
    return [value] * padding_len + seq


def add_test():
    vm = VM()
    a = int(input())
    b = int(input())
    program = padr([
        Ins.Ld, 253,
        Ins.Add, 254,
        Ins.St, 255,
        Ins.Halt,
    ], 128) + padl([
        a,  # 253
        b,  # 254
        0,  # 255 c = a + b
    ], 128)
    vm.load_program(program)
    print(vm.__repr__())
    vm.run()
    print('c =', vm[255])
    print()
    print()
    print(vm.__repr__())


def fact_test():
    vm = VM()
    a = int(input())
    program = padr([
        # set a[i] = a
        Ins.Ld, 254,  # 0
        Ins.St, 252,  # 2
        # iteration {
        # result = result * a[i]
        Ins.Ld, 255,  # 4
        Ins.Mul, 252,  # 6
        Ins.St, 255,  # 8
        # a[i]--
        Ins.Ld, 253,  # 10
        Ins.Neg,  # 12
        Ins.Add, 252,  # 13
        Ins.St, 252,  # 15
        # }
        # check a[n] > 1
        Ins.Gt, 253,  # 17
        # if a[n] > 1 start new iteration
        Ins.Jif, 4,  # 19
        # else halt
        Ins.Halt,
    ], 128) + padl([
        0,  # 252 a[i]
        1,  # 253 const
        a,  # 254
        1,  # 255 result
    ], 128)
    vm.load_program(program)
    vm.run()
    print('a! =', vm[255])


async def main():
    fact_test()
    return 0

if __name__ == '__main__':
    exit(asyncio.run(main()))
