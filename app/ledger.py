"""A running record of a group's shared expenses.

The ledger is the aggregate: it owns the expenses and answers questions that
only make sense across a set of them. It stores the *facts* (the expenses) and
derives everything else on demand -- balances are never cached, so they cannot
go stale, and a later fix to the allocation rules corrects history rather than
leaving it wrong.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.expense import Expense, Participant
from app.money import Money
from app.settlement import Transfer, settle_greedily


class Ledger:
    """A mutable collection of expenses, grouped by currency when settled.

    Expenses in different currencies may live in the same ledger, but they are
    never netted against each other: converting between them needs an exchange
    rate, a rate source and a policy for which rate applies, none of which
    belong in this layer. Settlement therefore solves each currency separately.
    """

    def __init__(self, expenses: Iterable[Expense] = ()) -> None:
        self._expenses: list[Expense] = list(expenses)

    def add(self, expense: Expense) -> None:
        """Record an expense. Any currency is accepted."""
        self._expenses.append(expense)

    @property
    def expenses(self) -> tuple[Expense, ...]:
        """The recorded expenses, in the order they were added.

        A tuple rather than the internal list, so a caller cannot append to the
        ledger's own state behind its back.
        """
        return tuple(self._expenses)

    def __len__(self) -> int:
        return len(self._expenses)

    def currencies(self) -> frozenset[str]:
        """Every currency this ledger holds an expense in."""
        return frozenset(expense.amount.currency for expense in self._expenses)

    def balances(self) -> dict[str, dict[Participant, Money]]:
        """Net position per participant, bucketed by currency.

        Positive means the group owes them. A participant appears only in the
        currencies they actually took part in -- not as a zero in every bucket.

        Derived on each call rather than maintained incrementally: there is no
        cache to invalidate, and at this scale the aggregation is free.
        """
        buckets: dict[str, dict[Participant, Money]] = {}
        for expense in self._expenses:
            bucket = buckets.setdefault(expense.amount.currency, {})
            for participant, net in expense.balances().items():
                current = bucket.get(participant)
                bucket[participant] = net if current is None else current + net
        return buckets

    def settle(self) -> dict[str, list[Transfer]]:
        """Who should pay whom to square the group, bucketed by currency.

        Mirrors :meth:`balances`. Currencies are never netted against each
        other, so the transfers settling one are not comparable with -- nor
        summable against -- those settling another. Returning them already
        separated puts that in the type, where a caller cannot miss it: a flat
        list would make ``sum(t.amount for t in ...)`` look reasonable, and it
        raises on a ledger holding more than one currency.

        A currency with nothing left to settle maps to an empty list rather
        than being dropped, so the keys always match those of :meth:`balances`.

        Currencies are iterated in sorted order so the result is deterministic.
        """
        buckets = self.balances()
        return {currency: settle_greedily(buckets[currency]) for currency in sorted(buckets)}
