"""Settling a set of balances with as few transfers as possible.

This module knows nothing about expenses or ledgers -- it takes balances and
returns transfers. Keeping it that narrow means it can be tested against
hand-written balances, with no domain objects to construct.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.expense import Participant
from app.money import Money


@dataclass(frozen=True, slots=True)
class Transfer:
    """One payment that moves a debtor closer to square with a creditor."""

    debtor: Participant
    creditor: Participant
    amount: Money

    def __post_init__(self) -> None:
        if self.debtor == self.creditor:
            raise ValueError(f"{self.debtor} cannot pay themselves")
        if self.amount.cents <= 0:
            raise ValueError("a transfer must move a positive amount")

    def __str__(self) -> str:
        return f"{self.debtor} pays {self.creditor} {self.amount}"


def settle_greedily(balances: Mapping[Participant, Money]) -> list[Transfer]:
    """Settle ``balances`` with a small number of transfers.

    Positive means the group owes that participant; negative means they owe the
    group. Balances must sum to zero and share a currency -- both are the
    caller's responsibility, and both are checked, because a violation means a
    bug upstream rather than bad user input.

    Repeatedly matches the largest debtor against the largest creditor. Each
    pairing settles at least one of the two, so this produces at most ``n - 1``
    transfers for ``n`` participants. That is a good result, not a minimal one:
    finding the true minimum is NP-hard (it contains subset-sum), and the greedy
    answer is the accepted practical trade.

    Ties are broken by name so that the same balances always produce the same
    transfers -- reproducibility matters more here than which arbitrary
    participant is chosen.
    """
    currencies = {money.currency for money in balances.values()}
    if len(currencies) > 1:
        raise ValueError(f"cannot settle across currencies: {sorted(currencies)}")
    if sum(money.cents for money in balances.values()) != 0:
        raise ValueError("balances must sum to zero before they can be settled")
    if not currencies:
        return []

    currency = currencies.pop()

    # Largest first, so each transfer clears as much debt as it can.
    debtors = sorted(
        ((p, -m.cents) for p, m in balances.items() if m.cents < 0),
        key=lambda pair: (-pair[1], pair[0].name),
    )
    creditors = sorted(
        ((p, m.cents) for p, m in balances.items() if m.cents > 0),
        key=lambda pair: (-pair[1], pair[0].name),
    )

    transfers: list[Transfer] = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        debtor, owed = debtors[i]
        creditor, due = creditors[j]

        paid = min(owed, due)
        transfers.append(Transfer(debtor, creditor, Money(paid, currency)))

        debtors[i] = (debtor, owed - paid)
        creditors[j] = (creditor, due - paid)

        # paid == min(owed, due), so at least one side is now square.
        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1

    return transfers
