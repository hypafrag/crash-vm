import sys
from ._types import Address, AddressRange, NativeNumber
from typing import Tuple, List

if sys.version_info[0] == 3 and sys.version_info[1] == 7:
    class Protocol:
        pass
else:
    from typing import Protocol


class Slave(Protocol):
    def __setitem__(self, address: Address, value: NativeNumber) -> None:
        raise NotImplementedError()

    def __getitem__(self, address: Address) -> NativeNumber:
        raise NotImplementedError()


class Bus:
    def __init__(self):
        self._attached: List[Tuple[AddressRange, Slave]] = []

    def attach(self, address_range: AddressRange, slave: Slave):
        self._attached.append((address_range, slave))

    def __setitem__(self, address: Address, value: NativeNumber):
        for address_range, slave in self._attached:
            if address in address_range:
                slave[Address(address.value - address_range.start_value)] = value
                return
        raise ValueError('Invalid address')

    def __getitem__(self, address: Address):
        for address_range, slave in self._attached:
            if address in address_range:
                return slave[Address(address.value - address_range.start_value)]
        raise ValueError('Invalid address')
