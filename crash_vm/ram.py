from ._types import Address, NativeInt
from .bus import Slave
from itertools import count
from ctypes import memset, sizeof


class RAM(Slave):
    def __init__(self, capacity: int):
        self._capacity = capacity
        self._cells = (NativeInt * capacity)()
        self.clear()

    def __getitem__(self, address: Address) -> NativeInt:
        return NativeInt(self._cells[address.value])

    def __setitem__(self, address: Address, value: NativeInt) -> None:
        self._cells[address.value] = value

    def clear(self):
        memset(self._cells, 0, self._capacity * sizeof(NativeInt))

    def __len__(self):
        return self._capacity

    def __repr__(self):
        line_segment_len = 2
        line_segments_num = 16
        # noinspection PyTypeChecker
        hex_str = bytes(self._cells).hex()
        header = list(map(lambda i: f'{i:02x}', range(line_segments_num))) + ['..'] * line_segments_num
        hex_str = header + [hex_str[i:i + line_segment_len]
                            for i in range(0, len(hex_str), line_segment_len)]
        hex_str = [' '.join(hex_str[i:i + line_segments_num])
                   for i in range(0, len(hex_str), line_segments_num)]
        hex_str = '\n'.join(map(lambda t: (
                                f'    {t[0] * line_segments_num:06x} : '
                                if t[0] >= 0 else
                                '             ')
                                + t[1],
                                zip(count(-2), hex_str)))
        return f'RAM({self._capacity}x{sizeof(NativeInt)} bytes)\n{hex_str}'
