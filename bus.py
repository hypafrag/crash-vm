from typing import Tuple, List, Protocol, Any
from _types import Address


class Slave(Protocol):
    def __setitem__(self, address: Address, value: Any) -> None:
        raise NotImplementedError()

    def __getitem__(self, address: Address) -> Any:
        raise NotImplementedError()


class Bus:
    def __init__(self):
        self._attached: List[Tuple[Tuple[Address, Address], Slave]] = []

    def attach(self, address_range: Tuple[Address, Address], slave: Slave):
        self._attached.append((address_range, slave))

    def __setitem__(self, address: Address, value: Any):
        for (address_from, address_to), slave in self._attached:
            if address_from <= address < address_to:
                slave[address - address_from] = value
                return
        raise ValueError('Invalid address')

    def __getitem__(self, address: Address):
        for (address_from, address_to), slave in self._attached:
            if address_from <= address < address_to:
                return slave[address - address_from]
        raise ValueError('Invalid address')
