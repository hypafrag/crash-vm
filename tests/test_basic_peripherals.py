import unittest
import time
from crash_vm import VM, asm_compile, NativeNumber, Address
from typing import Type

factorial_asm_program = '''

    # set a[i] = arg
        Ld 0xf0
        St :a_i

    iteration_begin:

    # result = result * a[i]
        Ld :result
        Mul :a_i
        St :result

    # a[i]--
        Ld :const_1
        Neg
        Add :a_i
        St :a_i

    # iteration end

    # check a[i] > 1
        Gt :const_1
    # if a[i] > 1 start new iteration
        Jif :iteration_begin
    # else write output and halt
        Ld :result
        St 0xf1
        Int 0

    # data
        const_1:
            1
        a_i:
            0
        result:
            1
'''

clock_tick_asm_program = '''
init:
    STK :stack
    HIH :hardware_interrupt_handlers_table

cycle:
    A0A
    LD :clock_counter
    A0L
    GT 4
    NOT
    JIF :cycle
    INT 0

fun_clock_hwi_handler:
    A0A
    LD :clock_counter
    A0L
    ADD 1
    A0A
    ST :clock_counter
    ST :out
    IHR

hardware_interrupt_handlers_table:
    0
    0
    0
    :fun_clock_hwi_handler

stack:

OFFSET 0xE0
clock_counter:
    0
OFFSET 0xF0
out:
'''


class ArgvPeripheral:
    def __init__(self, *args):
        super().__init__()
        self._args = args

    def __getitem__(self, address: Address) -> NativeNumber:
        return NativeNumber(self._args[address.value])


class TupleOutputPeripheral:
    def __init__(self, size):
        super().__init__()
        self._cells = [NativeNumber(0)] * size

    def values(self):
        return tuple(self._cells)

    def __getitem__(self, address: Address) -> NativeNumber:
        return NativeNumber(0)

    def __setitem__(self, address: Address, value: NativeNumber) -> None:
        self._cells[address.value] = value


class ProfiledQueuesOutputPeripheral:
    def __init__(self, num_queues=1):
        super().__init__()
        self._cells = [[]] * num_queues

    def values(self):
        return [list(queue) for queue in self._cells]

    def __getitem__(self, address: Address) -> NativeNumber:
        return NativeNumber(0)

    def __setitem__(self, address: Address, value: NativeNumber) -> None:
        self._cells[address.value].append((time.perf_counter_ns(), value))


class TestPeripherals(unittest.TestCase):
    def vm_exec(self, program: str,
                *args,
                ram_size: int = 0xF0,
                out_size: int = 1,
                frequency: int = None,
                out_cls: Type = TupleOutputPeripheral):

        peripherals = []
        outp = None

        if len(args) > 0:
            argvp = ArgvPeripheral(*args)
            peripherals.append((len(args), argvp))

        if out_size > 0:
            outp = out_cls(out_size)
            peripherals.append((out_size, outp))

        vm = VM(ram_size, peripherals)
        bytecode = asm_compile(program)
        vm.load_program(bytecode)
        vm.run(frequency)

        if out_size > 0:
            return outp.values()

    factorial_test_set = [
        (1, 1),
        (2, 2),
        (3, 6),
        (4, 24),
        (5, 120),
    ]

    def test_factorial_asm(self):
        for test_in, test_out in self.factorial_test_set:
            actual_out, = self.vm_exec(factorial_asm_program, test_in)
            self.assertEqual(actual_out.value, test_out)

    def test_clock_tick_asm_program(self):
        actual_out, = self.vm_exec(clock_tick_asm_program, out_cls=ProfiledQueuesOutputPeripheral)
        self.assertSequenceEqual(list(map(lambda n: n[1].value, actual_out)), [1, 2, 3, 4, 5])
        self.assertEqual((actual_out[-1][0] - actual_out[0][0]) // 1000000000, 4)
