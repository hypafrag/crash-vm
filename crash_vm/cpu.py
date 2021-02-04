from .bus import Bus
from ._types import Address, NativeNumber, NativeFalse, NativeTrue, float_to_native_number
from enum import Enum
from typing import Dict, Callable, Tuple, Generator
from math import sqrt


class Instructions(Enum):
    Noop = 0x00

    Ld = 0x01  # load Address(a) value to Acc
    St = 0x02  # store Acc value to Address(a)

    Add = 0x03  # Acc += a
    Neg = 0x04  # Acc = -Acc
    Mul = 0x05  # Acc *= a
    Div = 0x06  # Acc //= a

    Eq = 0x07  # Acc = 1 if Acc == a else 0
    Gt = 0x08  # Acc = 1 if Acc > a else 0

    Not = 0x09  # Acc = 1 if Acc == 0 else 0
    And = 0x0a  # Acc = 1 if Acc and a else 0
    Or = 0x0b  # Acc = 1 if Acc or a else 0

    Jmp = 0x0c  # IA = a
    Jif = 0x0d  # if Acc != 0: IA = a

    Sqrt = 0xe1  # sqrt(Acc)

    Halt = 0xff


instruction_methods: Dict[Instructions, Tuple[Callable, int]] = {}


def perform_instruction(name: Instructions, arg_num: int = 0):
    def decorator(method: Callable):
        assert name not in instruction_methods, 'Instruction redefinition'
        instruction_methods[name] = (method, arg_num)
        return method

    return decorator


class HWInterrupt(Exception):
    pass


class InvalidInstruction(HWInterrupt):
    pass


class HaltExecution(HWInterrupt):
    pass


class CPU:
    def __init__(self, bus: Bus):
        self._bus = bus
        self._IA = Address()  # next instruction address
        self._OC = NativeNumber()  # opcode to execute
        self._Arg0 = Address()  # operation argument
        self._Acc = NativeNumber()  # accumulator
        self.reset()

    def reset(self):
        self._IA = Address(0)
        self._OC = NativeNumber(0)
        self._Arg0 = Address(0)
        self._Acc = NativeNumber(0)

    def cycle(self) -> Generator:
        # fetch opcode
        self._OC = self._bus[self._IA]
        self._IA = Address(self._IA.value + 1)
        yield

        # decode opcode
        try:
            instruction = Instructions(self._OC.value)
        except ValueError:
            raise InvalidInstruction()
        method, args_num = instruction_methods[instruction]
        yield

        if args_num > 0:
            # fetch argument
            self._Arg0 = self._bus[self._IA]
            self._IA = Address(self._IA.value + 1)
            yield

        # execute
        method(self)

    @perform_instruction(Instructions.Noop)
    def _noop(self):
        pass

    @perform_instruction(Instructions.Halt)
    def _halt(self):
        raise HaltExecution()

    @perform_instruction(Instructions.St, 1)
    def _store(self):
        self._bus[self._Arg0] = self._Acc

    @perform_instruction(Instructions.Ld, 1)
    def _load(self):
        self._Acc = self._bus[self._Arg0]

    @perform_instruction(Instructions.Add, 1)
    def _add(self):
        self._Acc = NativeNumber(self._Acc.value + self._bus[self._Arg0].value)

    @perform_instruction(Instructions.Neg)
    def _neg(self):
        self._Acc = NativeNumber(-self._Acc.value)

    @perform_instruction(Instructions.Mul, 1)
    def _multiply(self):
        self._Acc = NativeNumber(self._Acc.value * self._bus[self._Arg0].value)

    @perform_instruction(Instructions.Div, 1)
    def _divide(self):
        self._Acc = float_to_native_number(self._Acc.value / self._bus[self._Arg0].value)

    @perform_instruction(Instructions.Sqrt)
    def _square_root(self):
        self._Acc = float_to_native_number(sqrt(self._Acc.value))

    @perform_instruction(Instructions.Eq, 1)
    def _equal(self):
        self._Acc = NativeTrue if self._Acc == self._bus[self._Arg0] else NativeFalse

    @perform_instruction(Instructions.Gt, 1)
    def _greater(self):
        self._Acc = NativeTrue if self._Acc.value > self._bus[self._Arg0].value else NativeFalse

    @perform_instruction(Instructions.Not)
    def _not(self):
        self._Acc = NativeTrue if self._Acc.value == NativeFalse.value else NativeFalse

    @perform_instruction(Instructions.Or, 1)
    def _or(self):
        self._Acc = NativeTrue if self._Acc.value or self._bus[self._Arg0].value else NativeFalse

    @perform_instruction(Instructions.And, 1)
    def _and(self):
        self._Acc = NativeTrue if self._Acc.value and self._bus[self._Arg0].value else NativeFalse

    @perform_instruction(Instructions.Jmp, 1)
    def _jump(self):
        self._IA = self._Arg0

    @perform_instruction(Instructions.Jif, 1)
    def _jump_if(self):
        if self._Acc:
            self._IA = self._Arg0

    def to_dict(self):
        return {
            'IA': self._IA.value,
            'OC': self._OC.value,
            'Arg0': self._Arg0.value,
            'Acc': self._Acc.value,
        }

    def __str__(self):
        return 'CPU(' + ', '.join(map(lambda item: f'{item[0]}: {item[1]:02x}', self.to_dict().items())) + ')'

    def __repr__(self):
        return 'CPU:\n' + '\n'.join(map(lambda item: f'    {item[0]}: {item[1]:02x}', self.to_dict().items()))
