"""Independent unsigned 16-bit model; no serial dependency or I/O."""

from dataclasses import dataclass, field
import struct

NONE, SELL, BUY = 0, 1, 2
ITEM_A, ITEM_B = 0x11, 0x22
REQUEST = struct.Struct(">HBHBH")
RESPONSE = struct.Struct(">HBBBBH")


@dataclass
class ItemState:
    prices: list[int] = field(default_factory=list)
    total: int = 0
    previous: int = 0
    action: int = NONE
    pointer: int = 0

    def process(self, price: int, warmup: bool) -> int:
        if not 0 <= price <= 0xFFFF:
            raise ValueError("Price must fit unsigned 16 bits")
        oldest = self.prices[0] if len(self.prices) == 16 else 0
        updated = self.total - oldest + price
        if warmup or len(self.prices) < 16:
            self.action = NONE
        elif self.previous <= self.total // 16 and price > updated // 16:
            self.action = BUY
        elif self.previous >= self.total // 16 and price < updated // 16:
            self.action = SELL
        self.prices = (self.prices + [price])[-16:]
        self.total = updated
        self.previous = price
        self.pointer = (self.pointer + 1) % 16
        assert self.total == sum(self.prices) <= 0xFFFF0
        return self.action


class ReferenceModel:
    def __init__(self):
        self.items = {ITEM_A: ItemState(), ITEM_B: ItemState()}

    def process(self, request: bytes) -> bytes:
        index, id1, price1, id2, price2 = REQUEST.unpack(request)
        if {id1, id2} != {ITEM_A, ITEM_B}:
            raise ValueError("Official packets require both distinct item IDs")
        if index == 0:
            self.__init__()
        a1 = self.items[id1].process(price1, index < 16)
        a2 = self.items[id2].process(price2, index < 16)
        return RESPONSE.pack(index, id1, a1, id2, a2, 0)
