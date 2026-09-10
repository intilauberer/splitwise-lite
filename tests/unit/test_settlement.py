"""Unit tests: the settlement algorithm, against hand-written balances."""

from __future__ import annotations

import pytest

from app.expense import Participant
from app.money import Money
from app.settlement import Transfer, settle_greedily

pytestmark = pytest.mark.unit

A = Participant("Ana")
B = Participant("Ben")
C = Participant("Cleo")
D = Participant("Dev")


def balances(**cents: int) -> dict[Participant, Money]:
    """Build balances from short names, e.g. ``balances(Ana=100, Ben=-100)``."""
    return {Participant(name): Money(amount) for name, amount in cents.items()}


def apply(start: dict[Participant, Money], transfers: list[Transfer]) -> dict[Participant, Money]:
    """Settle up: debtors pay out, creditors are paid, everyone moves to zero."""
    result = dict(start)
    for transfer in transfers:
        result[transfer.debtor] = result[transfer.debtor] + transfer.amount
        result[transfer.creditor] = result[transfer.creditor] - transfer.amount
    return result


SCENARIOS = [
    pytest.param({}, id="empty"),
    pytest.param(balances(Ana=0), id="single-participant-square"),
    pytest.param(balances(Ana=0, Ben=0, Cleo=0), id="already-settled"),
    pytest.param(balances(Ana=100, Ben=-100), id="two-party"),
    pytest.param(balances(Ana=1, Ben=-1), id="one-cent"),
    pytest.param(balances(Ana=100, Ben=-50, Cleo=-50), id="one-creditor-two-debtors"),
    pytest.param(balances(Ana=-100, Ben=50, Cleo=50), id="one-debtor-two-creditors"),
    pytest.param(balances(Ana=300, Ben=-100, Cleo=-100, Dev=-100), id="one-paid-for-all"),
    pytest.param(balances(Ana=333, Ben=333, Cleo=-666), id="uneven"),
    pytest.param(balances(Ana=500, Ben=-200, Cleo=100, Dev=-400), id="mixed-both-sides"),
    pytest.param(balances(Ana=7, Ben=-3, Cleo=-3, Dev=-1), id="awkward-remainders"),
]


class TestTransfer:
    def test_rejects_paying_yourself(self) -> None:
        with pytest.raises(ValueError, match="cannot pay themselves"):
            Transfer(A, A, Money(100))

    @pytest.mark.parametrize("cents", [0, -100])
    def test_rejects_non_positive_amount(self, cents: int) -> None:
        """A zero transfer is noise; a negative one means the arrow is backwards."""
        with pytest.raises(ValueError, match="positive amount"):
            Transfer(A, B, Money(cents))

    def test_reads_as_an_instruction(self) -> None:
        assert str(Transfer(A, B, Money(250))) == "Ana pays Ben 2.50 EUR"


class TestPreconditions:
    def test_mixed_currencies_are_rejected_even_when_every_balance_is_zero(self) -> None:
        """A bucket spanning currencies is malformed regardless of its values."""
        with pytest.raises(ValueError, match="across currencies"):
            settle_greedily({A: Money(0, "EUR"), B: Money(0, "USD")})

    def test_rejects_balances_that_do_not_sum_to_zero(self) -> None:
        """Not user input -- a non-zero sum means the caller has a bug."""
        with pytest.raises(ValueError, match="must sum to zero"):
            settle_greedily(balances(Ana=100, Ben=-50))

    def test_rejects_mixed_currencies(self) -> None:
        with pytest.raises(ValueError, match="cannot settle across currencies"):
            settle_greedily({A: Money(100, "EUR"), B: Money(-100, "USD")})


class TestSettlement:
    def test_nothing_to_do_when_already_square(self) -> None:
        assert settle_greedily(balances(Ana=0, Ben=0)) == []

    def test_empty_balances_settle_to_nothing(self) -> None:
        assert settle_greedily({}) == []

    def test_two_party_debt_is_a_single_transfer(self) -> None:
        assert settle_greedily(balances(Ana=100, Ben=-100)) == [Transfer(B, A, Money(100))]

    def test_one_payer_collects_from_everyone(self) -> None:
        transfers = settle_greedily(balances(Ana=300, Ben=-100, Cleo=-100, Dev=-100))
        assert len(transfers) == 3
        assert all(t.creditor == A for t in transfers)

    def test_largest_debt_is_cleared_first(self) -> None:
        """Greedy: the biggest debtor meets the biggest creditor, so one transfer
        settles as much as possible and the pair count stays low."""
        transfers = settle_greedily(balances(Ana=500, Ben=-400, Cleo=-100))
        assert transfers[0] == Transfer(B, A, Money(400))

    def test_preserves_currency(self) -> None:
        transfers = settle_greedily({A: Money(100, "USD"), B: Money(-100, "USD")})
        assert transfers[0].amount == Money(100, "USD")

    def test_is_deterministic(self) -> None:
        args = balances(Ana=100, Ben=100, Cleo=-100, Dev=-100)
        assert settle_greedily(args) == settle_greedily(args)


class TestInvariants:
    """These hold for every input, and matter more than any single example."""

    @pytest.mark.parametrize("start", SCENARIOS)
    def test_applying_the_transfers_squares_everyone(self, start: dict[Participant, Money]) -> None:
        """The whole point: after these payments, nobody owes anybody."""
        settled = apply(start, settle_greedily(start))
        assert all(money.cents == 0 for money in settled.values())

    @pytest.mark.parametrize("start", SCENARIOS)
    def test_never_needs_more_than_n_minus_one_transfers(
        self, start: dict[Participant, Money]
    ) -> None:
        involved = sum(1 for money in start.values() if money.cents != 0)
        expected_ceiling = max(involved - 1, 0)
        assert len(settle_greedily(start)) <= expected_ceiling

    @pytest.mark.parametrize("start", SCENARIOS)
    def test_every_transfer_moves_a_positive_amount(self, start: dict[Participant, Money]) -> None:
        assert all(t.amount.cents > 0 for t in settle_greedily(start))

    @pytest.mark.parametrize("start", SCENARIOS)
    def test_nobody_pays_themselves(self, start: dict[Participant, Money]) -> None:
        assert all(t.debtor != t.creditor for t in settle_greedily(start))

    @pytest.mark.parametrize("start", SCENARIOS)
    def test_total_moved_equals_total_owed(self, start: dict[Participant, Money]) -> None:
        """No money is created or destroyed in the settling."""
        owed = sum(-m.cents for m in start.values() if m.cents < 0)
        assert sum(t.amount.cents for t in settle_greedily(start)) == owed
