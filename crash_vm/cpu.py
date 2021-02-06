from .bus import Bus
from ._types import Address, NativeNumber, NativeFalse, NativeTrue, float_to_native_number
from enum import Enum
from typing import Dict, Callable, Tuple, Generator
from math import sqrt


class Instructions(Enum):
    Int = 0x00

    Ld = 0x01  # AC = [A0]
    St = 0x02  # [A0] = AC

    Add = 0x03  # AC += [A0]
    Neg = 0x04  # AC = -AC
    Mul = 0x05  # AC *= [A0]
    Div = 0x06  # AC //= [A0]

    Eq = 0x07  # AC = 1 if AC == [A0] else 0
    Gt = 0x08  # AC = 1 if AC > [A0] else 0

    Not = 0x09  # AC = 1 if AC == 0 else 0
    And = 0x0a  # AC = 1 if AC and [A0] else 0
    Or = 0x0b  # AC = 1 if AC or [A0] else 0

    Jmp = 0x0c  # IA = [A0]
    Jif = 0x0d  # if AC != 0: IA = [A0]

    A0A = 0x10  # OM[0] = 0
    A0V = 0x11  # OM[0] = 1
    ARAM = 0x12  # OM[1] = 0
    ASta = 0x13  # OM[1] = 1
    Comp = 0x14  # OM[2] = 0
    Ext = 0x15  # OM[2] = 1

    Stk = 0x70  # PS = [A0]
    Push = 0x71  # [SP] = AC
    Pop = 0x72  # AC = [SP]

    Sqrt = 0xe1  # sqrt(AC)

    Noop = 0xff


class OMFlags(Enum):
    A0ValueType = 0  # 0 - address, 1 - value
    AddressingMode = 1  # 0 - RAM address, 1 - stack offset
    CompatibilityMode = 2  # 0 - enable, 1 - disable


instruction_methods: Dict[Instructions, Tuple[Callable, int]] = {}


def perform_instruction(name: Instructions, arg_num: int = 0):
    def decorator(method: Callable):
        assert name not in instruction_methods, 'Instruction redefinition'
        instruction_methods[name] = (method, arg_num)
        return method

    return decorator


class SWInterrupt(Exception):
    class ReservedCodes(Enum):
        Halt = 0
        InvalidInstruction = 1
        Breakpoint = 2

    def __init__(self, code):
        super().__init__()
        self.code = code


class CPU:
    def __init__(self, fsb: Bus):
        self._fsb = fsb
        self._IA = Address()  # next instruction address
        self._OC = NativeNumber()  # opcode to execute
        self._OM = NativeNumber()  # operation mode flags
        self._A0 = NativeNumber()  # operation argument
        self._V0 = NativeNumber()  # resolved operation argument value
        self._AC = NativeNumber()  # accumulator
        self._SP = Address()  # stack pointer
        self.reset()

    def reset(self):
        self._IA = Address(0)
        self._OC = NativeNumber(0)
        self._OM = NativeNumber(0)
        self._A0 = NativeNumber(0)
        self._V0 = NativeNumber(0)
        self._AC = NativeNumber(0)
        self._SP = Address(0)

    def cycle(self) -> Generator:
        # fetch opcode
        self._OC = self._fsb[self._IA]
        self._IA = Address(self._IA.value + 1)
        yield

        # decode opcode
        try:
            instruction = Instructions(self._OC.value)
        except ValueError:
            raise SWInterrupt(SWInterrupt.ReservedCodes.InvalidInstruction.value)
        method, args_num = instruction_methods[instruction]
        yield

        if args_num > 0:
            # fetch argument
            self._A0 = self._fsb[self._IA]
            self._IA = Address(self._IA.value + 1)
            yield
            # fetch argument value
            self._V0 = self._fetch(self._A0)
            yield
        # execute
        method(self)

    def _fetch(self, address):
        if self._OM.value & (1 << OMFlags.A0ValueType.value) == 0:
            if self._OM.value & (1 << OMFlags.AddressingMode.value) == 0:
                return self._fsb[Address(address.value)]
            else:
                return self._fsb[Address(self._SP.value - address.value - 1)]
        else:
            return self._A0

    @perform_instruction(Instructions.Noop)
    def _noop(self):
        pass

    @perform_instruction(Instructions.Int, 1)
    def _software_interrupt(self):
        if (self._OM.value & (1 << OMFlags.CompatibilityMode.value)) == 0:
            # compatibility mode
            raise SWInterrupt(self._A0.value)
        else:
            # extended mode
            raise SWInterrupt(self._V0.value)

    @perform_instruction(Instructions.Ld, 1)
    def _load(self):
        self._AC = self._V0

    @perform_instruction(Instructions.St, 1)
    def _store(self):
        if (self._OM.value & (1 << OMFlags.CompatibilityMode.value)) == 0:
            # compatibility mode
            self._fsb[Address(self._A0.value)] = self._AC
        else:
            # extended mode
            self._fsb[Address(self._V0.value)] = self._AC

    @perform_instruction(Instructions.Add, 1)
    def _add(self):
        self._AC = NativeNumber(self._AC.value + self._V0.value)

    @perform_instruction(Instructions.Neg)
    def _neg(self):
        self._AC = NativeNumber(-self._AC.value)

    @perform_instruction(Instructions.Mul, 1)
    def _multiply(self):
        self._AC = NativeNumber(self._AC.value * self._V0.value)

    @perform_instruction(Instructions.Div, 1)
    def _divide(self):
        self._AC = float_to_native_number(self._AC.value / self._V0.value)

    @perform_instruction(Instructions.Sqrt)
    def _square_root(self):
        self._AC = float_to_native_number(sqrt(self._AC.value))

    @perform_instruction(Instructions.Eq, 1)
    def _equal(self):
        self._AC = NativeTrue if self._AC.value == self._V0.value else NativeFalse

    @perform_instruction(Instructions.Gt, 1)
    def _greater(self):
        self._AC = NativeTrue if self._AC.value > self._V0.value else NativeFalse

    @perform_instruction(Instructions.Not)
    def _not(self):
        self._AC = NativeTrue if self._AC.value == NativeFalse.value else NativeFalse

    @perform_instruction(Instructions.Or, 1)
    def _or(self):
        self._AC = NativeTrue if self._AC.value or self._V0.value else NativeFalse

    @perform_instruction(Instructions.And, 1)
    def _and(self):
        self._AC = NativeTrue if self._AC.value and self._V0.value else NativeFalse

    @perform_instruction(Instructions.Jmp, 1)
    def _jump(self):
        if (self._OM.value & (1 << OMFlags.CompatibilityMode.value)) == 0:
            # compatibility mode
            self._IA = self._A0
        else:
            # extended mode
            self._IA = self._V0

    @perform_instruction(Instructions.Jif, 1)
    def _jump_if(self):
        if self._AC.value:
            if (self._OM.value & (1 << OMFlags.CompatibilityMode.value)) == 0:
                # compatibility mode
                self._IA = self._A0
            else:
                # extended mode
                self._IA = self._V0

    @perform_instruction(Instructions.A0A)
    def _set_arg0_address_mode(self):
        self._OM = NativeNumber(self._OM.value & ~(1 << OMFlags.A0ValueType.value))

    @perform_instruction(Instructions.A0V)
    def _set_arg0_value_mode(self):
        self._OM = NativeNumber(self._OM.value | 1 << OMFlags.A0ValueType.value)

    @perform_instruction(Instructions.ARAM)
    def _set_ram_addressing_mode(self):
        self._OM = NativeNumber(self._OM.value & ~(1 << OMFlags.AddressingMode.value))

    @perform_instruction(Instructions.ASta)
    def _set_stack_offset_addressing_mode(self):
        self._OM = NativeNumber(self._OM.value | 1 << OMFlags.AddressingMode.value)

    @perform_instruction(Instructions.Comp)
    def _set_compatibility_mode(self):
        self._OM = NativeNumber(self._OM.value & ~(1 << OMFlags.CompatibilityMode.value))

    @perform_instruction(Instructions.Ext)
    def _set_extended_mode(self):
        self._OM = NativeNumber(self._OM.value | 1 << OMFlags.CompatibilityMode.value)

    @perform_instruction(Instructions.Stk, 1)
    def _set_stack_pointer(self):
        self._SP = self._V0

    @perform_instruction(Instructions.Push)
    def _stack_push(self):
        self._fsb[self._SP] = self._AC
        self._SP = Address(self._SP.value + 1)

    @perform_instruction(Instructions.Pop, 1)
    def _stack_pop(self):
        self._SP = Address(self._SP.value - self._V0.value)

    def to_dict(self):
        return {
            'IA': self._IA.value,
            'OC': self._OC.value,
            'OM': self._OM.value,
            'A0': self._A0.value,
            'V0': self._V0.value,
            'AC': self._AC.value,
            'SP': self._SP.value,
        }

    def __str__(self):
        return 'CPU(' + ', '.join(map(lambda item: f'{item[0]}: {item[1]:04x}', self.to_dict().items())) + ')'

    def __repr__(self):
        return 'CPU:\n' + '\n'.join(map(lambda item: f'    {item[0]}: {item[1]:04x}', self.to_dict().items()))
