"""A single shared expense and how its cost lands on each participant.

Pure domain logic: no storage, no HTTP, no I/O. All arithmetic is delegated to
:class:`~app.money.Money`, so this module never touches a cent directly.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.money import Money


@dataclass(frozen=True, slots=True)
class Participant:
    """Someone who takes part in an expense.

    Identity is the name. That is a simplification -- a real system would carry
    an opaque id so that people can rename themselves -- but it is enough while
    a group is a transient thing.

    Names are stripped on construction. Leading and trailing whitespace is never
    meaningful, and since a Participant is used as a mapping key, ``"Alice "``
    would otherwise become a second, invisible person. Case is deliberately
    *not* folded: whether ``alice`` and ``Alice`` are the same human is a product
    question, and guessing wrong silently merges two people.
    """

    name: str

    def __post_init__(self) -> None:
        stripped = self.name.strip()
        if not stripped:
            raise ValueError("participant name must not be blank")
        object.__setattr__(self, "name", stripped)

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class Expense:
    """An amount paid by one participant on behalf of several.

    ``weights`` maps each participant to their relative share of the cost. An
    equal split is every weight set to 1; someone who benefits twice as much
    gets 2; someone present but not consuming gets 0. Using weights rather than
    an equal/unequal mode means there is a single allocation path, so the
    remainder-cent handling cannot drift between the two cases.

    The payer must appear in ``weights``: fronting the bill does not exempt you
    from your own share of it.
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

        # Defensive copy behind a read-only view: the caller keeps their dict, so
        # an Expense cannot be mutated out from under its own invariants.
        object.__setattr__(self, "weights", MappingProxyType(dict(self.weights)))

    def __hash__(self) -> int:
        # Defined explicitly because the generated __hash__ would try to hash the
        # weights mapping and raise TypeError at some distant call site. dataclass
        # honours an explicit __hash__ in the class body.
        items = tuple((p, self.weights[p]) for p in self.participants)
        return hash((self.payer, self.amount, self.description, items))

    @classmethod
    def equal_split(
        cls,
        payer: Participant,
        amount: Money,
        description: str,
        participants: Iterable[Participant],
    ) -> Expense:
        """Build an expense divided evenly -- the common case.

        Raises on a repeated participant rather than silently collapsing them:
        a caller who passes ``[alice, alice, bob]`` almost certainly has a bug,
        and quietly returning a 1:1 split would hide it.
        """
        seen = list(participants)
        duplicates = {p for p in seen if seen.count(p) > 1}
        if duplicates:
            names = ", ".join(sorted(str(p) for p in duplicates))
            raise ValueError(f"duplicate participants: {names}")
        return cls(payer, amount, description, {p: 1 for p in seen})

    @property
    def participants(self) -> tuple[Participant, ...]:
        """Participants in a caller-independent order (by name).

        Sorting rather than trusting mapping order means two Expenses built from
        equal dicts allocate identically regardless of insertion sequence.
        """
        return tuple(sorted(self.weights, key=lambda p: p.name))

    def _allocation_order(self) -> tuple[Participant, ...]:
        """Participants rotated by a stable offset derived from the expense.

        ``Money.allocate`` breaks equal-remainder ties by position, so on an
        equal split whoever sits at index 0 absorbs the extra cent -- every
        time. Left alone that is a systematic transfer: the same person pays a
        cent more at every weekly dinner, forever.

        Rotating by a digest of the expense itself keeps allocation fully
        deterministic (the same expense always produces the same split, which
        randomness would not) while spreading the remainder across the group as
        the descriptions vary.
        """
        ordered = self.participants
        seed = f"{self.description}|{self.amount.cents}|{self.amount.currency}".encode()
        digest = hashlib.blake2b(seed, digest_size=8).digest()
        offset = int.from_bytes(digest, "big") % len(ordered)
        return ordered[offset:] + ordered[:offset]

    def shares(self) -> dict[Participant, Money]:
        """What each participant's slice of the cost is.

        The amounts always sum to exactly ``self.amount``: remainder cents are
        distributed by :meth:`Money.allocate`, never dropped.
        """
        ordered = self._allocation_order()
        allocated = self.amount.allocate([self.weights[p] for p in ordered])
        return dict(zip(ordered, allocated, strict=True))

    def balances(self) -> dict[Participant, Money]:
        """Each participant's net position for this expense.

        Positive means the group owes them; negative means they owe the group.
        The payer fronted the whole amount but still consumes their own share,
        so their balance is ``amount - own share``. Balances sum to zero by
        construction.
        """
        net = {participant: -share for participant, share in self.shares().items()}
        net[self.payer] = net[self.payer] + self.amount
        return net
