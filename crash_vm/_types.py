import ctypes
from typing import Union

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

NativeFalse = NativeNumber(0)
NativeTrue = NativeNumber(1)


class AddressRange:
    def __init__(self, start: Union[int, Address], end: Union[int, Address]):
        self.start_value = start.value if isinstance(start, Address) else start
        self.end_value = end.value if isinstance(end, Address) else end
        assert self.start_value <= self.end_value, 'Invalid range'

    def __contains__(self, item: Address):
        return self.start_value <= item.value < self.end_value
