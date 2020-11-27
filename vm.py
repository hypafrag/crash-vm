import asyncio
from itertools import count
from cpu import CPU, Instructions, HaltExecution
from ram import RAM
from bus import Bus


class VM:
    def __init__(self):
        self._fsb = Bus()
        self._ram = RAM(32)
        self._fsb.attach((0, 32), self._ram)
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
        for address, value in zip(count(), program):
            self._ram[address] = value

    def __repr__(self):
        return '\n\n'.join([self._cpu.__repr__(), self._ram.__repr__()])


async def main():
    vm = VM()
    vm.load_program([
        Instructions.Load.value, 7,  # 0
        Instructions.Add.value, 8,  # 2
        Instructions.Store.value, 9,  # 4
        Instructions.Halt.value,  # 6
        2,  # 7 var a
        7,  # 8 var b
        0,  # 9 var c = a + b
    ])
    print(vm.__repr__())
    vm.run()
    print()
    print()
    print(vm.__repr__())
    return 0

if __name__ == '__main__':
    exit(asyncio.run(main()))
