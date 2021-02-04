import unittest
from crash_vm import VM, asm_compile, NativeNumber, Address

factorial_asm_program = '''

        # set a[i] = arg
            Ld 0xf0
            St a_i:

        iteration_begin:

        # result = result * a[i]
            Ld result:
            Mul a_i:
            St result:

        # a[i]--
            Ld const_1:
            Neg
            Add a_i:
            St a_i:

        # iteration end

        # check a[i] > 1
            Gt const_1:
        # if a[i] > 1 start new iteration
            Jif iteration_begin:
        # else write output and halt
            Ld result:
            St 0xf1
            Halt

        # data
            const_1:
                1
            a_i:
                0
            result:
                1
'''


class ArgvPeripheral:
    def __init__(self, *args):
        super().__init__()
        self._args = args

    def __getitem__(self, address: Address) -> NativeNumber:
        return NativeNumber(self._args[address.value])


class OutputPeripheral:
    def __init__(self, size):
        super().__init__()
        self._cells = [NativeNumber(0)] * size

    def values(self):
        return tuple(self._cells)

    def __setitem__(self, address: Address, value: NativeNumber) -> None:
        self._cells[address.value] = value


class TestPeripherals(unittest.TestCase):
    def vm_exec(self, program: str, *args, ram_size: int = 0xF0, out_size: int = 1, frequency: int = None):
        argvp = ArgvPeripheral(*args)
        outp = OutputPeripheral(out_size)
        vm = VM(ram_size, ((len(args), argvp), (out_size, outp)))
        bytecode = asm_compile(program)
        vm.load_program(bytecode)
        vm.run(frequency)
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
