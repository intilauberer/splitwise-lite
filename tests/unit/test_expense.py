"""Unit tests: pure domain logic, no I/O."""

from __future__ import annotations

import pytest

from app.expense import Expense, Participant
from app.money import Money

pytestmark = pytest.mark.unit

ALICE = Participant("Alice")
BOB = Participant("Bob")
CAROL = Participant("Carol")


def dinner(amount: Money, weights: dict[Participant, int]) -> Expense:
    return Expense(ALICE, amount, "Dinner", weights)


class TestParticipant:
    def test_rejects_blank_name(self) -> None:
        with pytest.raises(ValueError, match="must not be blank"):
            Participant("   ")

    def test_is_usable_as_a_mapping_key(self) -> None:
        assert {Participant("Alice"): 1}[Participant("Alice")] == 1


class TestValidation:
    def test_rejects_blank_description(self) -> None:
        with pytest.raises(ValueError, match="description must not be blank"):
            Expense(ALICE, Money(100), "  ", {ALICE: 1})

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            dinner(Money(-100), {ALICE: 1})

    def test_rejects_empty_participants(self) -> None:
        with pytest.raises(ValueError, match="at least one participant"):
            dinner(Money(100), {})

    def test_rejects_payer_outside_the_participant_set(self) -> None:
        with pytest.raises(ValueError, match="must be one of the participants"):
            Expense(CAROL, Money(100), "Dinner", {ALICE: 1, BOB: 1})

    def test_rejects_negative_weight(self) -> None:
        with pytest.raises(ValueError, match="weights must be non-negative"):
            dinner(Money(100), {ALICE: 1, BOB: -1})

    def test_rejects_all_zero_weights(self) -> None:
        with pytest.raises(ValueError, match="must not all be zero"):
            dinner(Money(100), {ALICE: 0, BOB: 0})


class TestImmutability:
    def test_caller_cannot_mutate_the_expense_afterwards(self) -> None:
        weights = {ALICE: 1, BOB: 1}
        expense = dinner(Money(1000), weights)
        weights[CAROL] = 98  # caller keeps their own dict
        assert expense.participants == (ALICE, BOB)

    def test_weights_view_is_read_only(self) -> None:
        expense = dinner(Money(1000), {ALICE: 1, BOB: 1})
        with pytest.raises(TypeError):
            expense.weights[CAROL] = 1  # type: ignore[index]


class TestShares:
    def test_equal_split_divides_evenly(self) -> None:
        expense = Expense.equal_split(ALICE, Money(900), "Dinner", [ALICE, BOB, CAROL])
        assert expense.shares() == {ALICE: Money(300), BOB: Money(300), CAROL: Money(300)}

    def test_indivisible_amount_loses_no_cent(self) -> None:
        expense = Expense.equal_split(ALICE, Money(1000), "Dinner", [ALICE, BOB, CAROL])
        shares = expense.shares()
        assert shares == {ALICE: Money(334), BOB: Money(333), CAROL: Money(333)}
        assert sum(s.cents for s in shares.values()) == 1000

    def test_weights_scale_the_share(self) -> None:
        expense = dinner(Money(1000), {ALICE: 3, BOB: 1})
        assert expense.shares() == {ALICE: Money(750), BOB: Money(250)}

    def test_a_zero_weight_participant_owes_nothing(self) -> None:
        expense = dinner(Money(1000), {ALICE: 1, BOB: 0})
        assert expense.shares()[BOB] == Money(0)

    def test_preserves_currency(self) -> None:
        expense = dinner(Money(1000, "USD"), {ALICE: 1, BOB: 1})
        assert all(s.currency == "USD" for s in expense.shares().values())

    @pytest.mark.parametrize("cents", [0, 1, 5, 99, 100, 999, 1000, 12345, 100_003])
    @pytest.mark.parametrize("weights", [(1, 1, 1), (1, 2, 3), (5, 1, 1), (1, 1, 1000)])
    def test_shares_always_sum_back_to_the_total(
        self, cents: int, weights: tuple[int, int, int]
    ) -> None:
        """The invariant that matters: splitting money never creates or destroys it."""
        expense = dinner(Money(cents), dict(zip((ALICE, BOB, CAROL), weights, strict=True)))
        assert sum(s.cents for s in expense.shares().values()) == cents


class TestBalances:
    def test_payer_is_owed_everything_except_their_own_share(self) -> None:
        expense = Expense.equal_split(ALICE, Money(900), "Dinner", [ALICE, BOB, CAROL])
        assert expense.balances() == {ALICE: Money(600), BOB: Money(-300), CAROL: Money(-300)}

    def test_sole_participant_who_paid_is_square(self) -> None:
        assert dinner(Money(500), {ALICE: 1}).balances() == {ALICE: Money(0)}

    @pytest.mark.parametrize("cents", [0, 1, 999, 1000, 12345])
    @pytest.mark.parametrize("weights", [(1, 1, 1), (1, 2, 3), (7, 1, 1)])
    def test_balances_always_sum_to_zero(self, cents: int, weights: tuple[int, int, int]) -> None:
        """Nobody can end up better off than the group is worse off."""
        expense = dinner(Money(cents), dict(zip((ALICE, BOB, CAROL), weights, strict=True)))
        assert sum(b.cents for b in expense.balances().values()) == 0
