import ctypes
from typing import Union

NativeInt = ctypes.c_byte
Address = ctypes.c_ubyte

NativeFalse = NativeInt(0)
NativeTrue = NativeInt(1)


class AddressRange:
    def __init__(self, start: Union[int, Address], end: Union[int, Address]):
        self.start_value = start.value if isinstance(start, Address) else start
        self.end_value = end.value if isinstance(end, Address) else end
        assert self.start_value <= self.end_value, 'Invalid range'

    def __contains__(self, item: Address):
        return self.start_value <= item.value < self.end_value
