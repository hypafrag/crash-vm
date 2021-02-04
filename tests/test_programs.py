import unittest
from enum import Enum
from crash_vm import VM, Instructions as Ins, Address, NativeNumber, asm_compile


def padr(seq, num, value=0):
    padding_len = num - len(seq)
    assert padding_len >= 0
    return seq + [value] * padding_len


def padl(seq, num, value=0):
    padding_len = num - len(seq)
    assert padding_len >= 0
    return [value] * padding_len + seq


def factorial_program(a):
    return padr([
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
    ], 128), 255, 252


def factorial_asm_program(a):
    return (f'''

        # set a[i] = a
            Ld a:
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

        # check a[n] > 1
            Gt const_1:
        # if a[n] > 1 start new iteration
            Jif iteration_begin:
        # else halt
            Halt

        Offset 250
            a_i:
                0
            const_1:
                1
            a:
                {a}

        Offset 255
            result:
                1
    ''', 255, 250)


def quad_equation(a, b, c):
    _temp = 247
    _2 = 248
    _4 = 249

    _a = 250
    _b = 251
    _c = 252

    _sqrt_D = 253
    _x1 = 254
    _x2 = 255

    return padr([
        # calculate sqrt(D) as sqrt(b * b - 4 * a * c)
        Ins.Ld, _b,
        Ins.Mul, _b,
        Ins.St, _temp,
        Ins.Ld, _4,
        Ins.Mul, _a,
        Ins.Mul, _c,
        Ins.Neg,
        Ins.Add, _temp,
        Ins.Sqrt,
        Ins.St, _sqrt_D,
        # calculate x1 as (-b + sqrt(D)) / (2 * a)
        Ins.Ld, _b,
        Ins.Neg,
        Ins.Add, _sqrt_D,
        Ins.Div, _2,
        Ins.Div, _a,
        Ins.St, _x1,
        # calculate x2 as -(b + sqrt(D)) / (2 * a)
        Ins.Ld, _b,
        Ins.Add, _sqrt_D,
        Ins.Neg,
        Ins.Div, _2,
        Ins.Div, _a,
        Ins.St, _x2,
        Ins.Halt,
    ], 128) + padl([
        0,  # 247 temp
        2,  # 248 const
        4,  # 249 const
        a,  # 250 a
        b,  # 251 b
        c,  # 252 c
        0,  # 253 sqrt(D)
        0,  # 254 x1
        0,  # 255 x2
    ], 128), (_sqrt_D, _x1, _x2), 247


class TestPrograms(unittest.TestCase):
    def assertCodeSegmentUnchanged(self, program: list, vm: VM, instructions_segment_size: int):
        for i in range(instructions_segment_size):
            expected = NativeNumber(program[i].value if isinstance(program[i], (Enum, NativeNumber, Address))
                                    else program[i])
            self.assertEqual(vm[Address(i)].value, expected.value)

    def vm_exec(self, program, frequency=None):
        vm = VM()
        program_code, results_addresses, instructions_segment_size = program
        if isinstance(program_code, str):
            program_code = asm_compile(program_code)
        vm.load_program(program_code)
        vm.run(frequency)
        self.assertCodeSegmentUnchanged(program_code, vm, instructions_segment_size)

        def addr_value(result_address):
            return vm[Address(result_address)].value

        if isinstance(results_addresses, tuple):
            return tuple(map(addr_value, results_addresses))
        else:
            return addr_value(results_addresses)

    factorial_test_set = [
        (1, 1),
        (2, 2),
        (3, 6),
        (4, 24),
        (5, 120),
    ]

    def test_factorial(self):
        for test_in, test_out in self.factorial_test_set:
            actual_out = self.vm_exec(factorial_program(test_in))
            self.assertEqual(actual_out, test_out)

    def test_factorial_asm(self):
        for test_in, test_out in self.factorial_test_set:
            actual_out = self.vm_exec(factorial_asm_program(test_in))
            self.assertEqual(actual_out, test_out)

    def test_factorial_clocked(self):
        for test_in, test_out in self.factorial_test_set:
            actual_out = self.vm_exec(factorial_program(test_in), 1000)
            self.assertEqual(actual_out, test_out)

    def test_quad_equation(self):
        test_set = [
            ((1, 1, 0), (1, 0, -1)),
            ((1, 2, 1), (0, -1, -1)),
            ((1, 8, 1), (7, 0, -7)),
        ]
        for test_in, test_out in test_set:
            actual_out = self.vm_exec(quad_equation(*test_in))
            self.assertEqual(actual_out, test_out)
