from bus import Bus
from enum import Enum, auto
from _types import Address
from typing import Dict, Callable, Type, Tuple, Optional
from inspect import getfullargspec
from itertools import count
from functools import update_wrapper


class Registers(Enum):
    InstructionAddress = auto()
    Accumulator = auto()


class Instructions(Enum):
    Store = auto()
    Load = auto()
    Add = auto()
    Halt = auto()


_instruction_methods: Dict[Instructions, Tuple[Callable, int]] = {}


def perform_instruction(name: Instructions):
    def decorator(method: Callable):
        types: Dict[int, Type] = {}
        argspec = getfullargspec(method)
        for arg_index, arg_name in zip(count(), argspec.args):
            try:
                types[arg_index] = argspec.annotations[arg_name]
            except KeyError:
                pass

        def wrapper(*args):
            for arg_index, arg in zip(count(), args):
                try:
                    # noinspection PyTypeHints
                    assert isinstance(arg, types[arg_index]), 'Invalid argument type'
                except KeyError:
                    pass
            method(*args)

        decorated = update_wrapper(wrapper, method)
        assert name not in _instruction_methods, 'Instruction redefinition'
        _instruction_methods[name] = (decorated, len(argspec.args) - 1)
        return decorated

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
            Registers.InstructionAddress: 0,
            Registers.Accumulator: 0,
        }

    def next_instruction(self):
        instruction_address = Address(self._registers[Registers.InstructionAddress])

        opcode = None
        try:
            opcode = self._bus[instruction_address]
            instruction = Instructions(opcode)
        except ValueError:
            raise InvalidInstruction(instruction_address, opcode)

        method, args_num = _instruction_methods[instruction]
        args = list(map(self._bus.__getitem__, range(instruction_address + 1, instruction_address + 1 + args_num)))

        self._registers[Registers.InstructionAddress] += 1 + args_num
        method(self, *args)

    @perform_instruction(Instructions.Store)
    def _store(self, address: Address):
        self._bus[address] = self._registers[Registers.Accumulator]

    @perform_instruction(Instructions.Load)
    def _load(self, address: Address):
        self._registers[Registers.Accumulator] = self._bus[address]

    @perform_instruction(Instructions.Add)
    def _add(self, address: Address):
        self._registers[Registers.Accumulator] += self._bus[address]

    @perform_instruction(Instructions.Halt)
    def _halt(self):
        raise HaltExecution()

    def __repr__(self):
        return 'CPU:\n' + '\n'.join(map(lambda item: f'    {item[0].name}: {item[1]:02x}', self._registers.items()))
