from ._types import Address, NativeNumber, memset, sizeof, array
from .bus import Slave
from itertools import count


class RAM(Slave):
    def __init__(self, capacity: int):
        self._capacity = capacity
        self._cells = array(capacity)
        self.clear()

    def __getitem__(self, address: Address) -> NativeNumber:
        return NativeNumber(int(self._cells[address.value]))

    def __setitem__(self, address: Address, value: NativeNumber) -> None:
        assert isinstance(value, NativeNumber)
        self._cells[address.value] = value

    def clear(self):
        memset(self._cells, 0, self._capacity * sizeof(NativeNumber))

    def __len__(self):
        return self._capacity

    def __repr__(self):
        line_segment_len = 4
        line_segments_num = 16
        header = list(map(lambda i: f'{i:0{line_segment_len}x}',
                          range(line_segments_num))) + ['....'] * line_segments_num
        hex_str = header + [f'{int(v):0{line_segment_len}x}' for v in self._cells]
        hex_str = [' '.join(hex_str[i:i + line_segments_num])
                   for i in range(0, len(hex_str), line_segments_num)]
        hex_str = '\n'.join(map(lambda t: (
                                f'    {t[0] * line_segments_num:0{line_segment_len}x} : '
                                if t[0] >= 0 else
                                '    ' + ' ' * (line_segment_len + 3))
                                + t[1],
                                zip(count(-2), hex_str)))
        return f'RAM({self._capacity}x{sizeof(NativeNumber) * 8} bits)\n{hex_str}'
