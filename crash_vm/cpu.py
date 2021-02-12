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

    # TODO: remove, can be performed by Neg, Add, Not
    # Eq = 0x07  # AC = 1 if AC == [A0] else 0
    Gt = 0x08  # AC = 1 if AC > [A0] else 0

    Not = 0x09  # AC = 1 if AC == 0 else 0
    And = 0x0a  # AC = 1 if AC and [A0] else 0
    Or = 0x0b  # AC = 1 if AC or [A0] else 0

    Jmp = 0x0c  # IA = [A0]
    Jif = 0x0d  # if AC != 0: IA = [A0]

    A0A = 0x10  # OM[0] = 0
    A0L = 0x11  # OM[0] = 1
    A0V = 0x12  # OM[1] = 1
    A0P = 0x13  # OM[1] = 0
    A0R = 0x14  # OM[2] = 0
    A0S = 0x15  # OM[2] = 1

    HIH = 0x20  # HI = A0
    SIH = 0x21  # SI = A0
    IHR = 0x22  #

    Stk = 0x70  # PS = [A0]
    Push = 0x71  # [SP] = AC
    Pop = 0x72  # AC = [SP]

    Sqrt = 0xe1  # sqrt(AC)

    Noop = 0xff


class InstructionArgTypes(Enum):
    NoArg = 0
    ValueAddressArg = 1
    AddressArg = 2
    ValueArg = 3


class OMFlags(Enum):
    """
    LSb2:
    00 - address of value in RAM/stack
    01 - address of pointer in RAM/stack
    10 - literal value
    11 - address of value in RAM
    """
    A0Type = 0  # 0 - address(RAM/stack), 1 - literal
    A0ValueType = 1  # 0 - value, 1 - pointer
    A0AddressingMode = 2  # 0 - RAM address, 1 - stack offset


instruction_methods: Dict[Instructions, Tuple[Callable, InstructionArgTypes]] = {}


def perform_instruction(name: Instructions, instruction_type: InstructionArgTypes = InstructionArgTypes.NoArg):
    def decorator(method: Callable):
        assert name not in instruction_methods, 'Instruction redefinition'
        instruction_methods[name] = (method, instruction_type)
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
    def __init__(self, fsb: Bus, irq_levels: int = 4, sw_interrupts: int = 32):
        super().__init__()

        self._fsb = fsb
        self._irq_levels = irq_levels
        self._interrupts_requested = {i: False for i in range(irq_levels)}
        self._sw_interrupts = sw_interrupts
        self._sw_interrupt_level = irq_levels

        self._IA = Address()  # next instruction address
        self._OC = NativeNumber()  # opcode to execute
        self._OM = NativeNumber()  # operation mode flags
        self._A0 = NativeNumber()  # operation argument
        self._AC = NativeNumber()  # accumulator
        self._SP = Address()  # stack pointer
        self._HI = Address()  # IRQ handlers table address
        self._SI = Address()  # software interrupt handlers table address
        self._IL = NativeNumber()  # current executed interrupt level + 1 (0 - no interrupt handler executed)

        self.reset()

    def reset(self):
        self._IA = Address(0)
        self._OC = NativeNumber(0)
        self._OM = NativeNumber(0)
        self._A0 = NativeNumber(0)
        self._AC = NativeNumber(0)
        self._SP = Address(0)
        self._HI = Address(0)
        self._SI = Address(0)
        self._IL = NativeNumber(0)

    def get_irq_levels(self):
        return self._irq_levels

    def _push_state(self) -> Generator:
        self._fsb[self._SP] = NativeNumber(self._IA.value)
        self._SP = Address(self._SP.value + 1)
        yield
        self._fsb[self._SP] = NativeNumber(self._IL.value)
        self._SP = Address(self._SP.value + 1)
        yield
        self._fsb[self._SP] = NativeNumber(self._AC.value)
        self._SP = Address(self._SP.value + 1)
        yield
        self._fsb[self._SP] = NativeNumber(self._OM.value)
        self._SP = Address(self._SP.value + 1)
        yield

    def _process_software_interrupt(self, interrupt: SWInterrupt) -> Generator:
        if self._SI.value == 0 or interrupt.code >= self._sw_interrupts:
            raise interrupt

        handler_address = self._fsb[Address(self._SI.value + interrupt.code)]
        if handler_address.value == 0:
            raise interrupt

        yield from self._push_state()

        self._IA = Address(handler_address.value)
        self._IL = NativeNumber(self._sw_interrupt_level + 1)
        yield

    def _process_hardware_interrupt(self, level: int) -> Generator:
        if self._HI.value == 0:
            return

        handler_address = self._fsb[Address(self._HI.value + level)]
        if handler_address.value == 0:
            return

        yield from self._push_state()

        self._IA = Address(handler_address.value)
        self._IL = NativeNumber(level + 1)
        yield

    def cycle(self) -> Generator:
        for irq_level in range(self._irq_levels - 1, max(self._IL.value - 2, 0), -1):
            if self._interrupts_requested[irq_level]:
                self._interrupts_requested[irq_level] = False
                yield from self._process_hardware_interrupt(irq_level)
                break

        # fetch opcode
        self._OC = self._fsb[self._IA]
        self._IA = Address(self._IA.value + 1)
        yield

        try:
            # decode opcode
            try:
                instruction = Instructions(self._OC.value)
            except ValueError:
                raise SWInterrupt(SWInterrupt.ReservedCodes.InvalidInstruction.value)
            method, arg_type = instruction_methods[instruction]
            yield

            if arg_type != InstructionArgTypes.NoArg:
                # fetch argument
                self._A0 = self._fsb[self._IA]
                self._IA = Address(self._IA.value + 1)
                yield

                yield from self._resolve_arg0(arg_type)

            # print(instruction.name, self)
            # execute
            method_iter = method(self)
            if method_iter is not None:
                yield from method_iter
            else:
                yield

        except SWInterrupt as swi:
            yield from self._process_software_interrupt(swi)

    @staticmethod
    def _flag(register, flag) -> int:
        return (register.value >> flag.value) & 1

    @staticmethod
    def _set_flag(register, flag, value) -> NativeNumber:
        if value:
            return NativeNumber(register.value | 1 << flag.value)
        else:
            return NativeNumber(register.value & ~(1 << flag.value))

    def _resolve_address(self, address: int) -> Address:
        if self._flag(self._OM, OMFlags.A0AddressingMode) == 0:
            return Address(address)
        else:
            return Address(self._SP.value - address - 1)

    def _resolve_arg0(self, arg_type: InstructionArgTypes) -> Generator:
        if arg_type == InstructionArgTypes.ValueAddressArg:
            if self._flag(self._OM, OMFlags.A0Type) == 0:
                # fetch argument value
                self._A0 = self._fsb[self._resolve_address(self._A0.value)]
                yield

        elif arg_type == InstructionArgTypes.AddressArg:
            self._A0 = self._resolve_address(self._A0.value)

        elif arg_type == InstructionArgTypes.ValueArg:
            return

        else:
            raise NotImplementedError()

        if self._flag(self._OM, OMFlags.A0ValueType) == 1:
            # resolve argument value as pointer
            self._A0 = self._fsb[Address(self._A0.value)]
            yield

    def irq(self, level: int):
        assert level in self._interrupts_requested
        self._interrupts_requested[level] = True

    @perform_instruction(Instructions.Noop)
    def _noop(self):
        pass

    @perform_instruction(Instructions.Int, InstructionArgTypes.ValueArg)
    def _software_interrupt(self):
        raise SWInterrupt(self._A0.value)

    @perform_instruction(Instructions.Ld, InstructionArgTypes.ValueAddressArg)
    def _load(self):
        self._AC = self._A0

    @perform_instruction(Instructions.St, InstructionArgTypes.AddressArg)
    def _store(self):
        self._fsb[Address(self._A0.value)] = self._AC

    @perform_instruction(Instructions.Add, InstructionArgTypes.ValueAddressArg)
    def _add(self):
        self._AC = NativeNumber(self._AC.value + self._A0.value)

    @perform_instruction(Instructions.Neg)
    def _neg(self):
        self._AC = NativeNumber(-self._AC.value)

    @perform_instruction(Instructions.Mul, InstructionArgTypes.ValueAddressArg)
    def _multiply(self):
        self._AC = NativeNumber(self._AC.value * self._A0.value)

    @perform_instruction(Instructions.Div, InstructionArgTypes.ValueAddressArg)
    def _divide(self):
        self._AC = float_to_native_number(self._AC.value / self._A0.value)

    @perform_instruction(Instructions.Sqrt)
    def _square_root(self):
        self._AC = float_to_native_number(sqrt(self._AC.value))

    # @perform_instruction(Instructions.Eq, 1)
    # def _equal(self):
    #     self._AC = NativeTrue if self._AC.value == self._A0.value else NativeFalse

    @perform_instruction(Instructions.Gt, InstructionArgTypes.ValueAddressArg)
    def _greater(self):
        self._AC = NativeTrue if self._AC.value > self._A0.value else NativeFalse

    @perform_instruction(Instructions.Not)
    def _not(self):
        self._AC = NativeTrue if self._AC.value == NativeFalse.value else NativeFalse

    @perform_instruction(Instructions.Or, InstructionArgTypes.ValueAddressArg)
    def _or(self):
        self._AC = NativeTrue if self._AC.value or self._A0.value else NativeFalse

    @perform_instruction(Instructions.And, InstructionArgTypes.ValueAddressArg)
    def _and(self):
        self._AC = NativeTrue if self._AC.value and self._A0.value else NativeFalse

    @perform_instruction(Instructions.Jmp, InstructionArgTypes.AddressArg)
    def _jump(self):
        self._IA = Address(self._A0.value)

    @perform_instruction(Instructions.Jif, InstructionArgTypes.AddressArg)
    def _jump_if(self):
        if self._AC.value:
            self._jump()

    @perform_instruction(Instructions.A0A)
    def _set_arg0_type_address(self):
        self._OM = self._set_flag(self._OM, OMFlags.A0Type, 0)

    @perform_instruction(Instructions.A0L)
    def _set_arg0_type_literal(self):
        self._OM = self._set_flag(self._OM, OMFlags.A0Type, 1)

    @perform_instruction(Instructions.A0V)
    def _set_arg0_value_type_literal(self):
        self._OM = self._set_flag(self._OM, OMFlags.A0ValueType, 0)

    @perform_instruction(Instructions.A0P)
    def _set_arg0_value_type_address(self):
        self._OM = self._set_flag(self._OM, OMFlags.A0ValueType, 1)

    @perform_instruction(Instructions.A0R)
    def _set_ram_addressing_mode(self):
        self._OM = self._set_flag(self._OM, OMFlags.A0AddressingMode, 0)

    @perform_instruction(Instructions.A0S)
    def _set_stack_offset_addressing_mode(self):
        self._OM = self._set_flag(self._OM, OMFlags.A0AddressingMode, 1)

    @perform_instruction(Instructions.HIH, InstructionArgTypes.AddressArg)
    def _set_hardware_interrupt_handlers_address(self):
        self._HI = Address(self._A0.value)

    @perform_instruction(Instructions.SIH, InstructionArgTypes.AddressArg)
    def _set_software_interrupt_handlers_address(self):
        self._SI = Address(self._A0.value)

    @perform_instruction(Instructions.IHR)
    def _interrupt_handler_return(self) -> Generator:
        self._OM = self._fsb[Address(self._SP.value - 1)]
        self._SP = Address(self._SP.value - 1)
        yield
        self._AC = self._fsb[Address(self._SP.value - 1)]
        self._SP = Address(self._SP.value - 1)
        yield
        self._IL = self._fsb[Address(self._SP.value - 1)]
        self._SP = Address(self._SP.value - 1)
        yield
        self._IA = self._fsb[Address(self._SP.value - 1)]
        self._SP = Address(self._SP.value - 1)
        yield

    @perform_instruction(Instructions.Stk, InstructionArgTypes.AddressArg)
    def _set_stack_pointer(self):
        self._SP = Address(self._A0.value)

    @perform_instruction(Instructions.Push)
    def _stack_push(self):
        self._fsb[self._SP] = self._AC
        self._SP = Address(self._SP.value + 1)

    @perform_instruction(Instructions.Pop, InstructionArgTypes.ValueArg)
    def _stack_pop(self):
        self._SP = Address(self._SP.value - self._A0.value)

    def to_dict(self):
        return {
            'IA': self._IA.value,
            'OC': self._OC.value,
            'OM': self._OM.value,
            'A0': self._A0.value,
            'AC': self._AC.value,
            'SP': self._SP.value,
            'HI': self._HI.value,
            'SI': self._SI.value,
            'IL': self._IL.value,
        }

    def __str__(self):
        return 'CPU(' + ', '.join(map(lambda item: f'{item[0]}: {item[1]:04x}', self.to_dict().items())) + ')'

    def __repr__(self):
        return 'CPU:\n' + '\n'.join(map(lambda item: f'    {item[0]}: {item[1]:04x}', self.to_dict().items()))
