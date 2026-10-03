"""Bit-exact local oracle. No serial I/O or implementation dependency."""

from dataclasses import dataclass
import struct

ITEM_A, ITEM_B = 0x11, 0x22
NONE, SELL, BUY = 0, 1, 2
WINDOW = 16
REQUEST = struct.Struct(">HBHBH")
RESPONSE = struct.Struct(">HBBBBH")
ACTION_NAMES = {NONE: "NONE", SELL: "SELL", BUY: "BUY"}


def u16(value, field):
    if type(value) is not int or not 0 <= value <= 65535:
        raise ValueError(f"{field} must be an integer in 0..65535")
    return value


@dataclass(frozen=True)
class Request:
    index: int
    item1: int
    price1: int
    item2: int
    price2: int

    def __post_init__(self):
        u16(self.index, "index")
        u16(self.price1, "price1")
        u16(self.price2, "price2")
        if type(self.item1) is not int or type(self.item2) is not int:
            raise ValueError("item IDs must be integers")
        if {self.item1, self.item2} != {ITEM_A, ITEM_B}:
            raise ValueError("supported requests contain exactly one A and one B")

    def pack(self):
        return REQUEST.pack(self.index, self.item1, self.price1, self.item2, self.price2)

    @classmethod
    def unpack(cls, raw):
        if len(raw) != 8:
            raise ValueError("request must contain exactly eight bytes")
        return cls(*REQUEST.unpack(raw))


class ItemReference:
    """Chronological list + full re-sum: independent of rolling-sum hardware."""

    def __init__(self):
        self.prices = []
        self.previous = None
        self.action = NONE
        self.samples = 0

    def process(self, price):
        u16(price, "price")
        old_sum = sum(self.prices)
        pointer = self.samples % WINDOW
        previous, last_action = self.previous, self.action
        if len(self.prices) < WINDOW:
            oldest = None
            updated = self.prices + [price]
            reason = "WARMUP"
        else:
            oldest = self.prices[0]
            updated = self.prices[1:] + [price]
            new_sum = sum(updated)
            if previous <= old_sum // WINDOW and price > new_sum // WINDOW:
                self.action, reason = BUY, "BUY_CROSS"
            elif previous >= old_sum // WINDOW and price < new_sum // WINDOW:
                self.action, reason = SELL, "SELL_CROSS"
            else:
                reason = "HOLD_" + ACTION_NAMES[self.action]
        self.prices = updated
        self.previous = price
        self.samples += 1
        trace = dict(old_sum=old_sum, new_sum=sum(updated),
                     old_average=old_sum // WINDOW, new_average=sum(updated) // WINDOW,
                     oldest=oldest, previous=previous, pointer=pointer,
                     last_action=last_action, action=self.action, reason=reason)
        return self.action, trace


class PacketReference:
    """Require sequential sessions; undefined index gaps are not assigned answers."""

    def __init__(self):
        self.items = {ITEM_A: ItemReference(), ITEM_B: ItemReference()}
        self.next_index = 0

    def process(self, request):
        if request.index != 0 and request.index != self.next_index:
            raise ValueError("session must start at zero and use consecutive indices")
        if request.index == 0:
            self.items = {ITEM_A: ItemReference(), ITEM_B: ItemReference()}
        self.next_index = request.index + 1
        a1, t1 = self.items[request.item1].process(request.price1)
        a2, t2 = self.items[request.item2].process(request.price2)
        return RESPONSE.pack(request.index, request.item1, a1, request.item2, a2, 0), (t1, t2)
