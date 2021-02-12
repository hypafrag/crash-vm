from typing import Union

_CTYPE = False
# _CTYPE = True

if _CTYPE:

    import ctypes
    from ctypes import memset, sizeof

    NativeNumber = ctypes.c_short

    def float_to_native_number(f):
        return NativeNumber(int(f))

    def int_to_native_number(i):
        return NativeNumber(i)

    # NativeNumber = ctypes.c_double
    #
    #
    # def float_to_native_number(f):
    #     return NativeNumber(f)
    #
    #
    # def int_to_native_number(i):
    #     return NativeNumber(float(i))

    Address = ctypes.c_ushort

    def array(capacity):
        return (NativeNumber * capacity)()

else:

    class NativeNumber:
        def __init__(self, value: int = 0):
            self.value = value & 0xffff
            if self.value > 0xefff:
                self.value = self.value - 0x10000

        def __int__(self):
            return self.value

    class Address:
        def __init__(self, value: int = 0):
            self.value = value & 0xffff

        def __int__(self):
            return self.value

    def float_to_native_number(f):
        return NativeNumber(int(f))

    def int_to_native_number(i):
        return NativeNumber(i)

    def sizeof(number):
        return 2

    def memset(lst, value, size):
        num_size = sizeof(NativeNumber())
        for i in range(size // num_size):
            lst[i] = value

    def array(capacity):
        return [0] * capacity

NativeFalse = NativeNumber(0)
NativeTrue = NativeNumber(1)


class AddressRange:
    def __init__(self, start: Union[int, Address], end: Union[int, Address]):
        self.start_value = start.value if isinstance(start, Address) else start
        self.end_value = end.value if isinstance(end, Address) else end
        assert self.start_value <= self.end_value, 'Invalid range'

    def __contains__(self, item: Address):
        return self.start_value <= item.value < self.end_value
