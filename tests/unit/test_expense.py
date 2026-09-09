"""Unit tests: pure domain logic, no I/O."""

from __future__ import annotations

import pytest

from app.expense import Expense, Participant
from app.money import Money

pytestmark = pytest.mark.unit

ALICE = Participant("Alice")
BOB = Participant("Bob")
CAROL = Participant("Carol")
EVERYONE = (ALICE, BOB, CAROL)


def dinner(amount: Money, weights: dict[Participant, int]) -> Expense:
    return Expense(ALICE, amount, "Dinner", weights)


class TestParticipant:
    def test_rejects_blank_name(self) -> None:
        with pytest.raises(ValueError, match="must not be blank"):
            Participant("   ")

    def test_strips_surrounding_whitespace(self) -> None:
        assert Participant("  Alice  ").name == "Alice"

    def test_whitespace_variants_are_the_same_person(self) -> None:
        """Otherwise a stray space silently creates a second, invisible member."""
        assert Participant("Alice ") == ALICE
        assert hash(Participant("Alice ")) == hash(ALICE)

    def test_case_is_not_folded(self) -> None:
        """Deliberate: merging alice and Alice is a product decision, not a default."""
        assert Participant("alice") != ALICE

    def test_is_usable_as_a_mapping_key(self) -> None:
        assert {ALICE: 1}[Participant("Alice")] == 1


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

    def test_empty_is_reported_before_missing_payer(self) -> None:
        """Guard order matters: the empty case has the more useful message."""
        with pytest.raises(ValueError, match="at least one participant"):
            Expense(CAROL, Money(100), "Dinner", {})


class TestEqualSplit:
    def test_divides_evenly(self) -> None:
        expense = Expense.equal_split(ALICE, Money(900), "Dinner", EVERYONE)
        assert expense.shares() == {ALICE: Money(300), BOB: Money(300), CAROL: Money(300)}

    def test_rejects_duplicate_participants(self) -> None:
        """Silently collapsing [A, A, B] to a 1:1 split would hide a caller bug."""
        with pytest.raises(ValueError, match="duplicate participants: Alice"):
            Expense.equal_split(ALICE, Money(900), "Dinner", [ALICE, ALICE, BOB])


class TestImmutability:
    def test_caller_cannot_mutate_the_expense_afterwards(self) -> None:
        weights = {ALICE: 1, BOB: 1}
        expense = dinner(Money(1000), weights)
        weights[CAROL] = 98
        assert expense.participants == (ALICE, BOB)

    def test_weights_view_is_read_only(self) -> None:
        expense = dinner(Money(1000), {ALICE: 1, BOB: 1})
        with pytest.raises(TypeError):
            expense.weights[CAROL] = 1  # type: ignore[index]

    def test_is_hashable_despite_holding_a_mapping(self) -> None:
        a = dinner(Money(1000), {ALICE: 1, BOB: 1})
        b = dinner(Money(1000), {BOB: 1, ALICE: 1})
        assert hash(a) == hash(b)
        assert len({a, b}) == 1


class TestShares:
    def test_indivisible_amount_loses_no_cent(self) -> None:
        shares = Expense.equal_split(ALICE, Money(1000), "Dinner", EVERYONE).shares()
        assert sorted(s.cents for s in shares.values()) == [333, 333, 334]
        assert sum(s.cents for s in shares.values()) == 1000

    def test_weights_scale_the_share(self) -> None:
        assert dinner(Money(1000), {ALICE: 3, BOB: 1}).shares() == {
            ALICE: Money(750),
            BOB: Money(250),
        }

    def test_a_zero_weight_participant_owes_nothing(self) -> None:
        assert dinner(Money(1000), {ALICE: 1, BOB: 0}).shares()[BOB] == Money(0)

    def test_more_participants_than_cents(self) -> None:
        crowd = [Participant(f"P{i}") for i in range(10)]
        shares = Expense.equal_split(crowd[0], Money(5), "Coffee", crowd).shares()
        assert sorted(s.cents for s in shares.values()) == [0] * 5 + [1] * 5

    def test_preserves_currency(self) -> None:
        shares = dinner(Money(1000, "USD"), {ALICE: 1, BOB: 1}).shares()
        assert all(s.currency == "USD" for s in shares.values())

    def test_is_independent_of_caller_mapping_order(self) -> None:
        """Two equal expenses must split identically however the dict was built."""
        forwards = Expense(ALICE, Money(1000), "Dinner", {ALICE: 1, BOB: 1, CAROL: 1})
        backwards = Expense(ALICE, Money(1000), "Dinner", {CAROL: 1, BOB: 1, ALICE: 1})
        assert forwards.shares() == backwards.shares()

    def test_is_deterministic_across_calls(self) -> None:
        expense = Expense.equal_split(ALICE, Money(1000), "Dinner", EVERYONE)
        assert expense.shares() == expense.shares()

    def test_remainder_does_not_always_fall_on_the_same_person(self) -> None:
        """The bug this guards: with equal weights every remainder ties, ties break
        by position, so a fixed order makes one person overpay on every split."""
        overpayers = {
            max(
                Expense.equal_split(ALICE, Money(1000), f"Dinner {i}", EVERYONE).shares().items(),
                key=lambda item: item[1].cents,
            )[0]
            for i in range(60)
        }
        assert len(overpayers) > 1, "remainder cent is systematically biased"

    @pytest.mark.parametrize("cents", [0, 1, 5, 99, 100, 999, 1000, 12345, 100_003])
    @pytest.mark.parametrize("weights", [(1, 1, 1), (1, 2, 3), (5, 1, 1), (1, 1, 1000)])
    def test_shares_always_sum_back_to_the_total(
        self, cents: int, weights: tuple[int, int, int]
    ) -> None:
        """The invariant that matters: splitting money never creates or destroys it."""
        expense = dinner(Money(cents), dict(zip(EVERYONE, weights, strict=True)))
        assert sum(s.cents for s in expense.shares().values()) == cents


class TestBalances:
    def test_payer_is_owed_everything_except_their_own_share(self) -> None:
        expense = Expense.equal_split(ALICE, Money(900), "Dinner", EVERYONE)
        assert expense.balances() == {ALICE: Money(600), BOB: Money(-300), CAROL: Money(-300)}

    def test_sole_participant_who_paid_is_square(self) -> None:
        assert dinner(Money(500), {ALICE: 1}).balances() == {ALICE: Money(0)}

    def test_payer_balance_is_amount_minus_own_share(self) -> None:
        expense = dinner(Money(1000), {ALICE: 3, BOB: 1})
        assert expense.balances()[ALICE] == expense.amount - expense.shares()[ALICE]

    @pytest.mark.parametrize("cents", [0, 1, 999, 1000, 12345])
    @pytest.mark.parametrize("weights", [(1, 1, 1), (1, 2, 3), (7, 1, 1)])
    def test_balances_always_sum_to_zero(self, cents: int, weights: tuple[int, int, int]) -> None:
        """Nobody ends up better off than the group is worse off."""
        expense = dinner(Money(cents), dict(zip(EVERYONE, weights, strict=True)))
        assert sum(b.cents for b in expense.balances().values()) == 0
