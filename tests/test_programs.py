import unittest
from enum import Enum
from crash_vm import VM, Instructions as Ins


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


def quad_equation(a, b, c):
    _a = 250
    _b = 251
    _c = 252
    _d = 253
    _4 = 249
    _temp = 248

    return padr([
        # calculate discriminant as b * b - 4 * a * c
        Ins.Ld, _b,  # 0
        Ins.Mul, _b,  # 2
        Ins.St, _temp,  # 4
        Ins.Ld, _4,  # 6
        Ins.Mul, _a,  # 8
        Ins.Mul, _c,  # 10
        Ins.Neg,  # 12
        Ins.Add, _temp,  # 13
        Ins.St, _d,  # 15
        # calculate temp as -b / (2 * a)
    ], 128) + padl([
        0,  # 248 temp
        4,  # 249 const
        a,  # 250 a
        b,  # 251 b
        c,  # 252 c
        0,  # 253 d
        0,  # 254 x1
        0,  # 255 x2
    ], 128), 254, 255, 252


class TestPrograms(unittest.TestCase):
    def test_factorial(self):
        results = [0, 1, 2, 6, 24, 120]
        for a in range(1, 6):
            vm = VM()
            program, result_index, code_segment_size = factorial_program(a)
            vm.load_program(program)
            vm.run()
            for i in range(code_segment_size):
                expected = program[i].value if isinstance(program[i], Enum) else program[i]
                self.assertEqual(vm[i], expected)
            self.assertEqual(vm[result_index], results[a])
