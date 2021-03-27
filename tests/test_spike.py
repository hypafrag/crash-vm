import unittest
from crash_vm import VM, asm_compile, spike_compile


def expr_spike_program():
    # 30
    return f'''
return 2 + 2 * 6 + (4 + 4) * 2
'''


class TestBasicPrograms(unittest.TestCase):
    def vm_exec(self, spike_program):
        vm = VM()
        asm_program = spike_compile(spike_program)
        program = asm_compile(asm_program)
        vm.load_program(program)
        vm.run()
        print(vm)

    def test_spike_expr(self):
        self.vm_exec(expr_spike_program())
