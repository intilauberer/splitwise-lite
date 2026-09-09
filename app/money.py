"""A minimal money value object.

Money is stored as an integer number of minor units (cents) so that arithmetic
is exact. Floating point is never used for monetary values.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Money:
    """An exact monetary amount in a single currency."""

    cents: int
    currency: str = "EUR"

    def __post_init__(self) -> None:
        if not self.currency.isalpha() or len(self.currency) != 3:
            raise ValueError(f"currency must be a 3-letter code, got {self.currency!r}")

    @classmethod
    def from_units(cls, units: float, currency: str = "EUR") -> Money:
        """Build from a major-unit amount, e.g. ``Money.from_units(10.35)``.

        The value is rounded to the nearest cent, ties away from zero, which is
        what people expect from a receipt.
        """
        scaled = units * 100
        rounded = int(scaled + (0.5 if scaled >= 0 else -0.5))
        return cls(rounded, currency)

    def _check_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"cannot mix {self.currency} and {other.currency}")

    def __add__(self, other: Money) -> Money:
        self._check_same_currency(other)
        return Money(self.cents + other.cents, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check_same_currency(other)
        return Money(self.cents - other.cents, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.cents, self.currency)

    def allocate(self, ratios: Sequence[int]) -> list[Money]:
        """Split this amount across ``ratios`` without losing or inventing a cent.

        Remainder cents are handed out one at a time to the parties with the
        largest fractional shortfall, ties broken by position. The returned
        amounts always sum back to exactly ``self``.
        """
        if self.cents < 0:
            raise ValueError("cannot allocate a negative amount")
        if not ratios:
            raise ValueError("need at least one ratio")
        if any(r < 0 for r in ratios):
            raise ValueError("ratios must be non-negative")

        total_ratio = sum(ratios)
        if total_ratio == 0:
            raise ValueError("ratios must not sum to zero")

        shares = [self.cents * r // total_ratio for r in ratios]
        remainders = [self.cents * r % total_ratio for r in ratios]
        leftover = self.cents - sum(shares)

        order = sorted(range(len(ratios)), key=lambda i: (-remainders[i], i))
        for i in order[:leftover]:
            shares[i] += 1

        return [Money(c, self.currency) for c in shares]

    def __str__(self) -> str:
        sign = "-" if self.cents < 0 else ""
        whole, frac = divmod(abs(self.cents), 100)
        return f"{sign}{whole}.{frac:02d} {self.currency}"
