"""A single shared expense and how its cost lands on each participant.

This module is pure domain logic: it knows nothing about storage or HTTP, and
performs no I/O.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.money import Money


@dataclass(frozen=True, slots=True)
class Participant:
    """Someone who takes part in an expense."""

    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("participant name must not be blank")

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class Expense:
    """An amount paid by one participant on behalf of several.

    ``weights`` maps each participant to their relative share of the cost. An
    equal split is simply every weight set to 1; a participant who benefits
    twice as much gets a weight of 2. The payer must appear in ``weights``:
    paying for something does not exempt you from your own share of it.
    """

    payer: Participant
    amount: Money
    description: str
    weights: Mapping[Participant, int]

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise ValueError("description must not be blank")
        if self.amount.cents < 0:
            raise ValueError("expense amount must not be negative")
        if not self.weights:
            raise ValueError("an expense needs at least one participant")
        if self.payer not in self.weights:
            raise ValueError(f"payer {self.payer} must be one of the participants")
        if any(w < 0 for w in self.weights.values()):
            raise ValueError("weights must be non-negative")
        if sum(self.weights.values()) == 0:
            raise ValueError("weights must not all be zero")

        # Defensive copy: the caller keeps their dict, we keep an immutable view,
        # so an Expense cannot be mutated out from under its own invariants.
        object.__setattr__(self, "weights", MappingProxyType(dict(self.weights)))

    @classmethod
    def equal_split(
        cls,
        payer: Participant,
        amount: Money,
        description: str,
        participants: Iterable[Participant],
    ) -> Expense:
        """Build an expense divided evenly, the common case."""
        return cls(payer, amount, description, {p: 1 for p in participants})

    @property
    def participants(self) -> tuple[Participant, ...]:
        """Participants in a stable order, so allocation is deterministic."""
        return tuple(self.weights)

    def shares(self) -> dict[Participant, Money]:
        """What each participant's slice of the cost is.

        The returned amounts always sum to exactly ``self.amount``: remainder
        cents are distributed by :meth:`Money.allocate`, never dropped.
        """
        ordered = self.participants
        allocated = self.amount.allocate([self.weights[p] for p in ordered])
        return dict(zip(ordered, allocated, strict=True))

    def balances(self) -> dict[Participant, Money]:
        """Each participant's net position for this expense.

        Positive means the group owes them, negative means they owe the group.
        The payer fronted the whole amount but still consumes their own share,
        so their balance is ``amount - own share``. Balances sum to zero.
        """
        net = {participant: -share for participant, share in self.shares().items()}
        net[self.payer] = net[self.payer] + self.amount
        return net
