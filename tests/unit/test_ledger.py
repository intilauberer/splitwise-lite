"""Unit tests: the ledger aggregate."""

from __future__ import annotations

import pytest

from app.expense import Expense, Participant
from app.ledger import Ledger
from app.money import Money

pytestmark = pytest.mark.unit

ANA = Participant("Ana")
BEN = Participant("Ben")
CLEO = Participant("Cleo")
EVERYONE = (ANA, BEN, CLEO)


def dinner(payer: Participant, cents: int, currency: str = "EUR", note: str = "Dinner") -> Expense:
    return Expense.equal_split(payer, Money(cents, currency), note, EVERYONE)


class TestRecording:
    def test_starts_empty(self) -> None:
        ledger = Ledger()
        assert len(ledger) == 0
        assert ledger.balances() == {}
        assert ledger.settle() == {}

    def test_accepts_expenses_up_front(self) -> None:
        assert len(Ledger([dinner(ANA, 900), dinner(BEN, 600)])) == 2

    def test_does_not_alias_the_list_it_was_given(self) -> None:
        """The ledger copies on construction: the caller keeps their own list."""
        source = [dinner(ANA, 900)]
        ledger = Ledger(source)
        source.append(dinner(BEN, 600))
        assert len(ledger) == 1

    def test_add_appends(self) -> None:
        ledger = Ledger()
        ledger.add(dinner(ANA, 900))
        assert len(ledger) == 1

    def test_keeps_insertion_order(self) -> None:
        first, second = dinner(ANA, 900), dinner(BEN, 600, note="Taxi")
        assert Ledger([first, second]).expenses == (first, second)

    def test_does_not_expose_its_internal_list(self) -> None:
        """A caller must not be able to append behind the ledger's back."""
        ledger = Ledger([dinner(ANA, 900)])
        with pytest.raises(AttributeError):
            ledger.expenses.append(dinner(BEN, 600))  # type: ignore[attr-defined]
        assert len(ledger) == 1


class TestBalances:
    def test_single_expense_leaves_the_payer_owed(self) -> None:
        ledger = Ledger([dinner(ANA, 900)])
        assert ledger.balances() == {"EUR": {ANA: Money(600), BEN: Money(-300), CLEO: Money(-300)}}

    def test_expenses_accumulate(self) -> None:
        ledger = Ledger([dinner(ANA, 900), dinner(BEN, 900, note="Taxi")])
        assert ledger.balances()["EUR"] == {ANA: Money(300), BEN: Money(300), CLEO: Money(-600)}

    def test_opposite_expenses_cancel_out(self) -> None:
        """Ana buys dinner, Ben buys an identical taxi -- nobody owes anyone."""
        ledger = Ledger()
        ledger.add(Expense.equal_split(ANA, Money(1000), "Dinner", (ANA, BEN)))
        ledger.add(Expense.equal_split(BEN, Money(1000), "Taxi", (ANA, BEN)))
        assert ledger.balances()["EUR"] == {ANA: Money(0), BEN: Money(0)}
        assert ledger.settle() == {"EUR": []}

    def test_is_derived_not_cached(self) -> None:
        """Balances must reflect an expense added after they were first read."""
        ledger = Ledger([dinner(ANA, 900)])
        before = ledger.balances()["EUR"][ANA]
        ledger.add(dinner(ANA, 900, note="Taxi"))
        assert ledger.balances()["EUR"][ANA] == before + Money(600)

    def test_balances_sum_to_zero_per_currency(self) -> None:
        ledger = Ledger([dinner(ANA, 901), dinner(BEN, 1000, "USD"), dinner(CLEO, 77)])
        for bucket in ledger.balances().values():
            assert sum(money.cents for money in bucket.values()) == 0

    def test_zero_amount_expense_changes_nothing(self) -> None:
        ledger = Ledger([dinner(ANA, 0)])
        assert all(m == Money(0) for m in ledger.balances()["EUR"].values())
        assert ledger.settle() == {"EUR": []}


class TestCurrencies:
    def test_reports_the_currencies_held(self) -> None:
        ledger = Ledger([dinner(ANA, 900), dinner(BEN, 1000, "USD")])
        assert ledger.currencies() == frozenset({"EUR", "USD"})

    def test_buckets_are_independent(self) -> None:
        ledger = Ledger([dinner(ANA, 900), dinner(BEN, 900, "USD")])
        assert ledger.balances()["EUR"][ANA] == Money(600, "EUR")
        assert ledger.balances()["USD"][BEN] == Money(600, "USD")

    def test_a_participant_absent_from_a_currency_is_not_listed_in_it(self) -> None:
        """Not a zero entry -- they simply took no part in those expenses."""
        ledger = Ledger([Expense.equal_split(ANA, Money(900, "USD"), "Dinner", (ANA, BEN))])
        assert CLEO not in ledger.balances()["USD"]

    def test_currencies_are_never_netted_against_each_other(self) -> None:
        ledger = Ledger([dinner(ANA, 900), dinner(BEN, 900, "USD")])
        transfers = ledger.settle()
        assert set(transfers) == {"EUR", "USD"}
        assert all(t.creditor == ANA for t in transfers["EUR"])
        assert all(t.creditor == BEN for t in transfers["USD"])
        assert all(t.amount.currency == c for c, ts in transfers.items() for t in ts)


class TestSettle:
    def test_settles_a_single_expense(self) -> None:
        transfers = Ledger([dinner(ANA, 900)]).settle()["EUR"]
        assert len(transfers) == 2
        assert all(t.creditor == ANA and t.amount == Money(300) for t in transfers)

    def test_is_deterministic(self) -> None:
        ledger = Ledger([dinner(ANA, 901), dinner(BEN, 1000, "USD"), dinner(CLEO, 77)])
        assert ledger.settle() == ledger.settle()

    def test_currencies_are_settled_in_sorted_order(self) -> None:
        ledger = Ledger([dinner(ANA, 900, "USD"), dinner(BEN, 900, "EUR")])
        seen = list(ledger.settle())
        assert seen == sorted(seen)

    @pytest.mark.parametrize(
        "expenses",
        [
            pytest.param([(ANA, 900, "EUR")], id="one-expense"),
            pytest.param([(ANA, 1000, "EUR")], id="indivisible"),
            pytest.param([(ANA, 901, "EUR"), (BEN, 77, "EUR")], id="two-expenses"),
            pytest.param([(ANA, 900, "EUR"), (BEN, 1000, "USD")], id="two-currencies"),
            pytest.param(
                [(ANA, 1234, "EUR"), (BEN, 567, "EUR"), (CLEO, 89, "EUR")], id="three-payers"
            ),
        ],
    )
    def test_settling_squares_the_whole_group(
        self, expenses: list[tuple[Participant, int, str]]
    ) -> None:
        """The invariant: apply every transfer and no balance is left standing."""
        ledger = Ledger([dinner(payer, cents, currency) for payer, cents, currency in expenses])
        remaining = {currency: dict(bucket) for currency, bucket in ledger.balances().items()}
        for currency, transfers in ledger.settle().items():
            for transfer in transfers:
                bucket = remaining[currency]
                bucket[transfer.debtor] = bucket[transfer.debtor] + transfer.amount
                bucket[transfer.creditor] = bucket[transfer.creditor] - transfer.amount
        assert all(m.cents == 0 for bucket in remaining.values() for m in bucket.values())
