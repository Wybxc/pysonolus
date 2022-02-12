import operator
from functools import reduce
from typing import Iterable, Set, TypeVar

T = TypeVar("T")


def intersection(sets: Iterable[Set[T]]) -> Set[T]:
    """Return the intersection of all sets. """
    return reduce(operator.and_, sets)


def union(sets: Iterable[Set[T]]) -> Set[T]:
    """Return the union of all sets. """
    return reduce(operator.or_, sets)
