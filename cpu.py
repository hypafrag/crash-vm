from bus import Bus
from enum import Enum, auto
from _types import Address
from typing import Dict, Callable, Type, Tuple, Optional
from inspect import getfullargspec


class Registers(Enum):
    IA = auto()  # next instruction address
    Acc = auto()  # accumulator


class Instructions(Enum):
    Halt = auto()

    St = auto()  # store Acc value to Address(a)
    Ld = auto()  # load Address(a) value to Acc

    Add = auto()  # Acc += a
    Neg = auto()  # Acc = -Acc
    Mul = auto()  # Acc *= a
    Div = auto()  # Acc //= a

    Eq = auto()  # Acc = 1 if Acc == a else 0
    Gt = auto()  # Acc = 1 if Acc > a else 0

    Not = auto()  # Acc = 1 if Acc == 0 else 0
    Or = auto()  # Acc = 1 if Acc or a else 0
    And = auto()  # Acc = 1 if Acc and a else 0

    Jmp = auto()  # IA = a
    Jif = auto()  # if Acc != 0: IA = a


_instruction_methods: Dict[Instructions, Tuple[Callable, int]] = {}


def perform_instruction(name: Instructions):
    def decorator(method: Callable):
        argspec = getfullargspec(method)
        assert name not in _instruction_methods, 'Instruction redefinition'
        _instruction_methods[name] = (method, len(argspec.args) - 1)
        return method

    return decorator


class InvalidInstruction(Exception):
    def __init__(self, address: Address, opcode: Optional[int]):
        self.address = address
        self.opcode = opcode


class HaltExecution(Exception):
    pass


class CPU:
    def __init__(self, bus: Bus):
        self._bus = bus
        self._registers: Dict[Registers, int] = {}
        self.reset()

    def reset(self):
        self._registers = {
            Registers.IA: 0,
            Registers.Acc: 0,
        }

    def next_instruction(self):
        instruction_address = Address(self._registers[Registers.IA])

        opcode = None
        try:
            opcode = self._bus[instruction_address]
            instruction = Instructions(opcode)
        except ValueError:
            raise InvalidInstruction(instruction_address, opcode)

        method, args_num = _instruction_methods[instruction]
        args = list(map(self._bus.__getitem__, range(instruction_address + 1, instruction_address + 1 + args_num)))

        self._registers[Registers.IA] += 1 + args_num
        method(self, *args)

    @perform_instruction(Instructions.Halt)
    def _halt(self):
        raise HaltExecution()

    @perform_instruction(Instructions.St)
    def _store(self, address: Address):
        self._bus[address] = self._registers[Registers.Acc]

    @perform_instruction(Instructions.Ld)
    def _load(self, address: Address):
        self._registers[Registers.Acc] = self._bus[address]

    @perform_instruction(Instructions.Add)
    def _add(self, address: Address):
        self._registers[Registers.Acc] += self._bus[address]

    @perform_instruction(Instructions.Neg)
    def _neg(self):
        self._registers[Registers.Acc] = -self._registers[Registers.Acc]

    @perform_instruction(Instructions.Mul)
    def _multiply(self, address: Address):
        self._registers[Registers.Acc] *= self._bus[address]

    @perform_instruction(Instructions.Div)
    def _divide(self, address: Address):
        self._registers[Registers.Acc] //= self._bus[address]

    @perform_instruction(Instructions.Eq)
    def _equal(self, address: Address):
        self._registers[Registers.Acc] = 1 if self._registers[Registers.Acc] == self._bus[address] else 0

    @perform_instruction(Instructions.Gt)
    def _greater(self, address: Address):
        self._registers[Registers.Acc] = 1 if self._registers[Registers.Acc] > self._bus[address] else 0

    @perform_instruction(Instructions.Not)
    def _not(self):
        self._registers[Registers.Acc] = 1 if self._registers[Registers.Acc] == 0 else 0

    @perform_instruction(Instructions.Or)
    def _or(self, address: Address):
        self._registers[Registers.Acc] = 1 if self._registers[Registers.Acc] or self._bus[address] else 0

    @perform_instruction(Instructions.And)
    def _and(self, address: Address):
        self._registers[Registers.Acc] = 1 if self._registers[Registers.Acc] and self._bus[address] else 0

    @perform_instruction(Instructions.Jmp)
    def _jump(self, address: Address):
        self._registers[Registers.IA] = address

    @perform_instruction(Instructions.Jif)
    def _jump_if(self, address: Address):
        if self._registers[Registers.Acc]:
            self._registers[Registers.IA] = address

    def __repr__(self):
        return 'CPU:\n' + '\n'.join(map(lambda item: f'    {item[0].name}: {item[1]:02x}', self._registers.items()))
