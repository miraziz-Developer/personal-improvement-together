from __future__ import annotations

from dataclasses import dataclass

from pit.shared.domain.errors import InvariantViolation


@dataclass(frozen=True, slots=True, order=True)
class Money:
    """Amount in UZS (so'm). Always a non-negative whole number — never a float."""

    amount: int

    def __post_init__(self) -> None:
        if type(self.amount) is not int:
            raise InvariantViolation("Summa butun son (so'm) bo'lishi kerak")
        if self.amount < 0:
            raise InvariantViolation("Summa manfiy bo'lishi mumkin emas")

    @classmethod
    def zero(cls) -> Money:
        return cls(0)

    @property
    def is_zero(self) -> bool:
        return self.amount == 0

    def __add__(self, other: Money) -> Money:
        return Money(self.amount + other.amount)

    def __sub__(self, other: Money) -> Money:
        if other.amount > self.amount:
            raise InvariantViolation("Mablag' yetarli emas")
        return Money(self.amount - other.amount)

    def __str__(self) -> str:
        return f"{self.amount:,} so'm".replace(",", " ")
