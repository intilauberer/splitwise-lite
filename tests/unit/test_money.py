"""Unit tests: pure logic, no I/O, microseconds each."""

from __future__ import annotations

import pytest

from app.money import Money

pytestmark = pytest.mark.unit


class TestConstruction:
    def test_rejects_non_iso_currency(self) -> None:
        with pytest.raises(ValueError, match="3-letter code"):
            Money(100, "EUROS")

    def test_from_units_rounds_to_nearest_cent(self) -> None:
        assert Money.from_units(10.351) == Money(1035)
        assert Money.from_units(10.355) == Money(1036)

    def test_from_units_rounds_ties_away_from_zero(self) -> None:
        assert Money.from_units(-0.005) == Money(-1)

    def test_is_immutable(self) -> None:
        with pytest.raises(AttributeError):
            Money(100).cents = 200  # type: ignore[misc]


class TestArithmetic:
    def test_add_and_subtract(self) -> None:
        assert Money(100) + Money(250) == Money(350)
        assert Money(100) - Money(250) == Money(-150)

    def test_negate(self) -> None:
        assert -Money(100) == Money(-100)

    @pytest.mark.parametrize("op", ["add", "sub"])
    def test_refuses_to_mix_currencies(self, op: str) -> None:
        a, b = Money(100, "EUR"), Money(100, "USD")
        with pytest.raises(ValueError, match="cannot mix"):
            a + b if op == "add" else a - b


class TestAllocate:
    def test_even_split_is_exact(self) -> None:
        assert Money(900).allocate([1, 1, 1]) == [Money(300)] * 3

    def test_indivisible_amount_loses_no_cent(self) -> None:
        shares = Money(1000).allocate([1, 1, 1])
        assert shares == [Money(334), Money(333), Money(333)]
        assert sum(s.cents for s in shares) == 1000

    def test_weighted_split(self) -> None:
        assert Money(1000).allocate([3, 1]) == [Money(750), Money(250)]

    def test_remainder_goes_to_largest_shortfall_first(self) -> None:
        # 0.05 across weights 3:1:1 -> exact shares 3.0, 1.0, 1.0 cents
        shares = Money(5).allocate([3, 1, 1])
        assert [s.cents for s in shares] == [3, 1, 1]

    def test_zero_amount_allocates_zeros(self) -> None:
        assert Money(0).allocate([1, 2]) == [Money(0), Money(0)]

    def test_preserves_currency(self) -> None:
        assert all(s.currency == "USD" for s in Money(300, "USD").allocate([1, 1]))

    @pytest.mark.parametrize(
        ("amount", "ratios", "message"),
        [
            (-100, [1, 1], "negative amount"),
            (100, [], "at least one ratio"),
            (100, [1, -1], "non-negative"),
            (100, [0, 0], "sum to zero"),
        ],
    )
    def test_invalid_input(self, amount: int, ratios: list[int], message: str) -> None:
        with pytest.raises(ValueError, match=message):
            Money(amount).allocate(ratios)


class TestFormatting:
    @pytest.mark.parametrize(
        ("cents", "expected"),
        [(0, "0.00 EUR"), (5, "0.05 EUR"), (1234, "12.34 EUR"), (-1234, "-12.34 EUR")],
    )
    def test_str(self, cents: int, expected: str) -> None:
        assert str(Money(cents)) == expected
